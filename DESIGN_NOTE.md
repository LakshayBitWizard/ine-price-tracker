# Design Note: Scraping Reliability, Trade-offs, and Iteration

## 1. How We Made the Scraping Reliable

The INE mock store (`demo.inelabteamdev.com`) is deliberately built to be difficult and awkward for automated scrapers:
- **Client-Side Anti-Bot Gate**: Prices are initially hidden behind a `.price-block` with a disabled button. The underlying JavaScript tracks mouse movement intervals (`kr = 40ms`), requires at least 8 distinct mouse movements (`minMoves: 8`), and enforces a minimum hover dwell time (`minDwellMs: 600ms`) before enabling the "Reveal price" action.
- **Obfuscated / Dynamic Text**: Prices and stock badges frequently contain zero-width characters (`\u200b`), non-breaking spaces, fullwidth Unicode numbers (`０-９`), or erratic currency formatting.
- **Flaky & Asynchronous Loads**: Intermittent slow responses, occasional HTTP 429 / 500 errors, and delays in price payload decryption.

### Reliability Solutions Implemented:
1. **Realistic Cursor Physics & Dwell Time**: The Playwright scraper calculates the bounding box of the price container, smoothly interpolates cursor positions across multiple steps separated by 70ms delays, and waits for the required dwell time before triggering click events.
2. **Explicit Locators & State Confirmation**: We avoid blind `sleep()` calls. The scraper waits on concrete DOM states (`.price-block.price-success`) and monitors the background network response for the price endpoint.
3. **Multi-Step Sanitization Engine**: Extracted text passes through a normalization pipeline that strips zero-width spaces, translates full-width digits, harmonizes European/Indian currency decimal markers, and validates positive numeric ranges before committing to the database.
4. **Honest Scrape Logging with Atomic Transactions**: If any attempt fails or times out, the failure is honestly recorded in `ScrapeLogs` with the error message and HTTP status code. No phantom or empty price rows are ever written to `PriceHistory`.

---

## 2. Trade-offs Made

1. **Playwright Headless Browser vs. Direct HTTP Scraping**:
   - *Trade-off*: Headless browsers consume more memory (~150MB per Chromium instance) than lightweight `requests` or `BeautifulSoup`.
   - *Decision*: The store's price reveal logic executes complex client-side encryption and validation tokens tied to mouse movements and timing. Emulating that via raw HTTP requests is brittle and easily broken by client bundle changes. Using Playwright guarantees 100% fidelity to the user experience.
2. **External Webhook (cron-job.org) vs. In-Process Celery/Redis**:
   - *Trade-off*: Setting up an in-process Celery worker or `APScheduler` keeps scheduling logic inside Python.
   - *Decision*: Render's free tier spins down web instances after 15 minutes of inactivity, terminating any internal thread or Celery process. An external webhook via `cron-job.org` wakes up the Render web service every 2 hours, triggers the scrape sweep, and shuts down gracefully without incurring extra infrastructure costs.
3. **Multi-Pass Catalog Search**:
   - *Trade-off*: Querying multiple catalog pages adds slight latency to search (~1–2 seconds).
   - *Decision*: The mock store randomizes items across pages, meaning a single-page fetch would frequently miss products. A 2-pass deduplicated sweep ensures high discovery accuracy for any queried item.

---

## 3. What AI Tools Got Wrong on the First Attempt & How We Corrected It

1. **Static HTML Parsing Assumption**:
   - *AI Mistake*: Initial suggestions attempted to parse prices directly from raw HTML using standard HTTP GET requests (`requests.get`), expecting the price to be present in the server-rendered markup.
   - *Correction*: Inspection revealed that prices are only revealed after client-side JavaScript execution, anti-bot mouse hovering, and user interactions. We shifted the architecture to Playwright with headless Chromium.
2. **Simple Button Click vs. Dwell-Time Validation**:
   - *AI Mistake*: The initial automation simply called `page.click("button:has-text('Reveal price')")`. This failed repeatedly because the button is initially disabled and will not respond to a click until mouse trajectory data and a 600ms dwell time are recorded in the client runtime.
   - *Correction*: We analyzed the client bundle (`index-B9UiQq4X.js`), identified the `minMoves: 8` and `minDwellMs: 600` constraints, and implemented an automated mouse sweep simulation to reliably unlock the button.
3. **Search Substring Matching**:
   - *AI Mistake*: The catalog search initially used exact substring matching (`query in product_name`), which caused queries like `"Larkspur Smart Plug Air"` to fail if words were slightly reordered or spaced differently in the catalog descriptions.
   - *Correction*: We refactored the search filter to tokenize queries into word sets and require all tokens to exist across `name`, `brand`, `category`, and `sku` fields.
