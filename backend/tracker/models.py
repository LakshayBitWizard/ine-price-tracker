import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TrackedProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_product_id = models.TextField(unique=True, null=True, blank=True)
    name = models.TextField()
    url = models.TextField(unique=True)
    image_url = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    currency = models.TextField(default="USD")
    current_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    current_stock_quantity = models.IntegerField(null=True, blank=True)
    currently_in_stock = models.BooleanField(null=True, blank=True)
    scrape_interval_minutes = models.PositiveIntegerField(
        default=120, validators=[MinValueValidator(1)]
    )
    is_active = models.BooleanField(default=True)
    last_successful_scrape_at = models.DateTimeField(null=True, blank=True)
    last_scrape_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "TrackedProducts"
        managed = settings.DJANGO_MANAGE_TABLES
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScrapeLog(models.Model):
    class Outcome(models.TextChoices):
        SUCCESS = "success", "success"
        RETRIED = "retried", "retried"
        FAILED = "failed", "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        TrackedProduct,
        on_delete=models.CASCADE,
        related_name="scrape_logs",
        db_column="product_id",
    )
    run_id = models.UUIDField(default=uuid.uuid4)
    attempted_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    attempt_number = models.PositiveIntegerField(default=1)
    http_status = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    page_structure_changed = models.BooleanField(default=False)
    headed = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ScrapeLogs"
        managed = settings.DJANGO_MANAGE_TABLES
        ordering = ["-attempted_at"]

    def __str__(self):
        return f"{self.product_id} {self.outcome} {self.attempted_at}"


class PriceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        TrackedProduct,
        on_delete=models.CASCADE,
        related_name="price_history",
        db_column="product_id",
    )
    scrape_log = models.ForeignKey(
        ScrapeLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="price_points",
        db_column="scrape_log_id",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.TextField(default="USD")
    stock_quantity = models.IntegerField(null=True, blank=True)
    in_stock = models.BooleanField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PriceHistory"
        managed = settings.DJANGO_MANAGE_TABLES
        ordering = ["-scraped_at"]

    def __str__(self):
        return f"{self.product_id} {self.price} @ {self.scraped_at}"
