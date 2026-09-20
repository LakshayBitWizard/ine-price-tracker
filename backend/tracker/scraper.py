import re
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PriceHistory, ScrapeLog, TrackedProduct


class ScrapeError(Exception):
    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        page_structure_changed: bool = False,
    ):
        super().__init__(message)
        self.http_status = http_status
        self.page_structure_changed = page_structure_changed


@dataclass(frozen=True)
class ScrapedOffer:
    price: Decimal
    currency: str
    stock_quantity: int | None
    in_stock: bool
    raw_price_text: str
    raw_stock_text: str
    http_status: int | None = None


FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def parse_price(price_text: str) -> tuple[Decimal, str]:
    cleaned = (
        price_text.translate(FULLWIDTH_DIGITS)
        .replace("\u200b", "")
        .replace("\xa0", " ")
        .strip()
    )
    currency = "INR"
    if "$" in cleaned:
        currency = "USD"
    elif "€" in cleaned:
        currency = "EUR"

    candidates = re.findall(r"\d[\d,.\s]*", cleaned)
    if not candidates:
        raise ScrapeError(
            f"Could not parse price from {price_text!r}",
            page_structure_changed=True,
        )

    raw_number = candidates[-1].replace(" ", "")
    last_comma = raw_number.rfind(",")
    last_dot = raw_number.rfind(".")

    if last_comma > last_dot and len(raw_number) - last_comma - 1 == 2:
        normalized = raw_number.replace(".", "").replace(",", ".")
    elif last_dot > last_comma and len(raw_number) - last_dot - 1 == 2:
        normalized = raw_number.replace(",", "")
    else:
        normalized = raw_number.replace(",", "").replace(".", "")

    try:
        value = Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ScrapeError(
            f"Could not normalize price from {price_text!r}",
            page_structure_changed=True,
        ) from exc

    if value <= 0:
        raise ScrapeError(
            f"Extracted non-positive price {value}",
            page_structure_changed=True,
        )
    return value, currency


def parse_stock(stock_text: str) -> tuple[int | None, bool]:
    cleaned = stock_text.translate(FULLWIDTH_DIGITS).replace("\u200b", "").strip()
    if re.search(r"out\s+of\s+stock", cleaned, re.IGNORECASE):
        return 0, False
    match = re.search(r"\d+", cleaned)
    if match:
        return int(match.group(0)), True
    if re.search(r"in\s+stock|left|selling\s+fast|hurry", cleaned, re.IGNORECASE):
        return None, True
    raise ScrapeError(
        f"Could not parse stock from {stock_text!r}",
        page_structure_changed=True,
    )


def due_products():
    now = timezone.now()
    products = TrackedProduct.objects.filter(is_active=True).order_by("created_at")
    due_ids = []
    for product in products:
        if product.last_scrape_at is None:
            due_ids.append(product.id)
            continue
        next_due_at = product.last_scrape_at + timedelta(
            minutes=product.scrape_interval_minutes
        )
        if next_due_at <= now:
            due_ids.append(product.id)
    return TrackedProduct.objects.filter(id__in=due_ids).order_by("created_at")


def scrape_product(product: TrackedProduct, *, headed: bool = False) -> dict[str, Any]:
    run_id = uuid.uuid4()
    max_attempts = settings.SCRAPER_MAX_ATTEMPTS
    last_error: ScrapeError | None = None

    for attempt_number in range(1, max_attempts + 1):
        started = time.perf_counter()
        try:
            offer = _scrape_once(product, headed=headed)
            duration_ms = round((time.perf_counter() - started) * 1000)
            with transaction.atomic():
                log = ScrapeLog.objects.create(
                    product=product,
                    run_id=run_id,
                    outcome=ScrapeLog.Outcome.SUCCESS,
                    attempt_number=attempt_number,
                    http_status=offer.http_status,
                    duration_ms=duration_ms,
                    headed=headed,
                    notes=(
                        f"price={offer.raw_price_text}; "
                        f"stock={offer.raw_stock_text}"
                    ),
                )
                PriceHistory.objects.create(
                    product=product,
                    scrape_log=log,
                    price=offer.price,
                    currency=offer.currency,
                    stock_quantity=offer.stock_quantity,
                    in_stock=offer.in_stock,
                )
                product.current_price = offer.price
                product.currency = offer.currency
                product.current_stock_quantity = offer.stock_quantity
                product.currently_in_stock = offer.in_stock
                product.last_scrape_at = timezone.now()
                product.last_successful_scrape_at = product.last_scrape_at
                product.save(
                    update_fields=[
                        "current_price",
                        "currency",
                        "current_stock_quantity",
                        "currently_in_stock",
                        "last_scrape_at",
                        "last_successful_scrape_at",
                        "updated_at",
                    ]
                )
            return {
                "product_id": str(product.id),
                "store_product_id": product.store_product_id,
                "outcome": "success",
                "attempts": attempt_number,
                "price": str(offer.price),
                "currency": offer.currency,
                "stock_quantity": offer.stock_quantity,
                "in_stock": offer.in_stock,
            }
        except ScrapeError as exc:
            last_error = exc
            duration_ms = round((time.perf_counter() - started) * 1000)
            is_final = attempt_number == max_attempts
            ScrapeLog.objects.create(
                product=product,
                run_id=run_id,
                outcome=(
                    ScrapeLog.Outcome.FAILED
                    if is_final
                    else ScrapeLog.Outcome.RETRIED
                ),
                attempt_number=attempt_number,
                http_status=exc.http_status,
                duration_ms=duration_ms,
                error_message=str(exc),
                page_structure_changed=exc.page_structure_changed,
                headed=headed,
            )
            product.last_scrape_at = timezone.now()
            product.save(update_fields=["last_scrape_at", "updated_at"])
            if not is_final:
                time.sleep(min(1.5 * attempt_number, 6))

    return {
        "product_id": str(product.id),
        "store_product_id": product.store_product_id,
        "outcome": "failed",
        "attempts": max_attempts,
        "error": str(last_error) if last_error else "unknown scraper failure",
    }


def scrape_products(
    *,
    product_id: str | None = None,
    force: bool = False,
    headed: bool = False,
) -> dict[str, Any]:
    if product_id:
        products = TrackedProduct.objects.filter(id=product_id, is_active=True)
    elif force:
        products = TrackedProduct.objects.filter(is_active=True).order_by("created_at")
    else:
        products = due_products()

    results = [scrape_product(product, headed=headed) for product in products]
    return {
        "requested_product_id": product_id,
        "force": force,
        "headed": headed,
        "count": len(results),
        "results": results,
    }


def _scrape_once(product: TrackedProduct, *, headed: bool = False) -> ScrapedOffer:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScrapeError(
            "Playwright is not installed. Run `pip install -r requirements.txt` "
            "and `python -m playwright install chromium`."
        ) from exc

    product_path_id = product.store_product_id or product.metadata.get("store_id")
    if not product_path_id:
        raise ScrapeError("Tracked product is missing store_product_id")

    target_url = product.url or f"{settings.STORE_BASE_URL}/product/{product_path_id}"
    price_api_status: int | None = None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not headed,
            slow_mo=settings.SCRAPER_SLOW_MO_MS if headed else 0,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent=settings.STORE_USER_AGENT,
            locale="en-IN",
        )
        page = context.new_page()
        page.set_default_timeout(settings.SCRAPER_TIMEOUT_MS)

        def remember_price_response(response):
            nonlocal price_api_status
            if f"/api/products/{product_path_id}/price" in response.url:
                price_api_status = response.status

        page.on("response", remember_price_response)

        try:
            response = page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=settings.SCRAPER_TIMEOUT_MS,
            )
            if response and response.status >= 500:
                raise ScrapeError(
                    f"Product page returned HTTP {response.status}",
                    http_status=response.status,
                )

            _dismiss_cookie_banner(page)
            page.locator(".price-block").first.wait_for(
                state="visible", timeout=settings.SCRAPER_TIMEOUT_MS
            )
            _perform_price_hover(page)
            _click_reveal_price(page)
            page.locator(".price-block.price-success").first.wait_for(
                state="visible", timeout=settings.SCRAPER_TIMEOUT_MS
            )
            extracted = page.evaluate(
                """
                () => {
                  const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== "none" &&
                      style.visibility !== "hidden" &&
                      rect.width > 0 &&
                      rect.height > 0;
                  };
                  const clean = (value) => (value || "")
                    .replace(/\\u200b/g, "")
                    .replace(/\\s+/g, " ")
                    .trim();
                  const priceMain = document.querySelector(".price-main");
                  if (!priceMain) {
                    return { error: "missing .price-main" };
                  }
                  const candidates = Array.from(priceMain.querySelectorAll("*"))
                    .filter(visible)
                    .map((el) => ({
                      text: clean(el.innerText || el.textContent),
                      tag: el.tagName,
                      className: String(el.className || ""),
                      fontSize: Number.parseFloat(
                        window.getComputedStyle(el).fontSize || "0"
                      ),
                    }))
                    .filter((item) => item.text);
                  const priceCandidate =
                    candidates.find((item) => item.className.includes("pv-")) ||
                    candidates.find((item) => item.tag === "OUTPUT") ||
                    candidates
                      .slice()
                      .sort((a, b) => b.fontSize - a.fontSize)[0];
                  const stock = document.querySelector(".stock-badge");
                  return {
                    priceText: priceCandidate ? priceCandidate.text : "",
                    stockText: clean(stock ? stock.innerText || stock.textContent : ""),
                    candidates,
                  };
                }
                """
            )
        except PlaywrightTimeoutError as exc:
            raise ScrapeError(
                "Timed out waiting for the price block to reveal",
                http_status=price_api_status,
                page_structure_changed=True,
            ) from exc
        finally:
            context.close()
            browser.close()

    if extracted.get("error"):
        raise ScrapeError(
            extracted["error"],
            http_status=price_api_status,
            page_structure_changed=True,
        )
    price_text = extracted.get("priceText") or ""
    stock_text = extracted.get("stockText") or ""
    price, currency = parse_price(price_text)
    stock_quantity, in_stock = parse_stock(stock_text)
    return ScrapedOffer(
        price=price,
        currency=currency,
        stock_quantity=stock_quantity,
        in_stock=in_stock,
        raw_price_text=price_text,
        raw_stock_text=stock_text,
        http_status=price_api_status,
    )


def _dismiss_cookie_banner(page) -> None:
    for label in ("Accept cookies", "Accept", "Decline cookies", "Decline"):
        button = page.get_by_role("button", name=label)
        try:
            if button.first.is_visible(timeout=500):
                button.first.click(timeout=1000)
                return
        except Exception:
            continue


def _perform_price_hover(page) -> None:
    block = page.locator(".price-block").first
    box = block.bounding_box()
    if not box:
        raise ScrapeError("Price block has no visible bounding box")
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    page.mouse.move(center_x - 80, center_y - 20, steps=8)
    for offset in range(10):
        page.mouse.move(
            center_x - 60 + offset * 13,
            center_y + ((offset % 3) - 1) * 10,
            steps=3,
        )
        page.wait_for_timeout(70)
    page.wait_for_timeout(850)


def _click_reveal_price(page) -> None:
    button = page.get_by_role(
        "button", name=re.compile(r"Reveal price|Refresh price|Try again", re.I)
    ).first
    for _ in range(3):
        try:
            button.wait_for(state="visible", timeout=3000)
            if button.is_enabled(timeout=1000):
                button.click(timeout=3000)
                page.wait_for_timeout(600)
                if page.locator(".price-block.price-success").first.is_visible(
                    timeout=1000
                ):
                    return
        except Exception:
            page.wait_for_timeout(600)
    if not page.locator(".price-block.price-success").first.is_visible(timeout=1000):
        raise ScrapeError("Could not trigger the store's reveal price action")
