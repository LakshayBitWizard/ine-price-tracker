from rest_framework import serializers

from .models import PriceHistory, ScrapeLog, TrackedProduct


class TrackedProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedProduct
        fields = [
            "id",
            "store_product_id",
            "name",
            "url",
            "image_url",
            "description",
            "currency",
            "current_price",
            "current_stock_quantity",
            "currently_in_stock",
            "scrape_interval_minutes",
            "is_active",
            "last_successful_scrape_at",
            "last_scrape_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_price",
            "current_stock_quantity",
            "currently_in_stock",
            "last_successful_scrape_at",
            "last_scrape_at",
            "created_at",
            "updated_at",
        ]


class StoreProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    brand = serializers.CharField()
    category = serializers.CharField()
    sku = serializers.CharField()
    description = serializers.CharField()
    url = serializers.URLField()


class TrackStoreProductSerializer(serializers.Serializer):
    store_product_id = serializers.IntegerField()
    scrape_interval_minutes = serializers.IntegerField(required=False, min_value=1)


class PriceHistorySerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)

    class Meta:
        model = PriceHistory
        fields = [
            "id",
            "product_id",
            "scrape_log_id",
            "price",
            "currency",
            "stock_quantity",
            "in_stock",
            "scraped_at",
            "created_at",
        ]


class ScrapeLogSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)

    class Meta:
        model = ScrapeLog
        fields = [
            "id",
            "product_id",
            "run_id",
            "attempted_at",
            "outcome",
            "attempt_number",
            "http_status",
            "duration_ms",
            "error_message",
            "page_structure_changed",
            "headed",
            "notes",
            "created_at",
        ]
