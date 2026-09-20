from django.conf import settings
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PriceHistory, ScrapeLog, TrackedProduct
from .scraper import scrape_products
from .serializers import (
    PriceHistorySerializer,
    ScrapeLogSerializer,
    StoreProductSerializer,
    TrackStoreProductSerializer,
    TrackedProductSerializer,
)
from .store_client import StoreClientError, fetch_store_product, search_store_products


class TrackedProductListCreateView(generics.ListCreateAPIView):
    queryset = TrackedProduct.objects.all()
    serializer_class = TrackedProductSerializer


class TrackedProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrackedProduct.objects.all()
    serializer_class = TrackedProductSerializer


class StoreProductSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            products = search_store_products(query)
        except StoreClientError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = StoreProductSerializer(
            [
                {
                    "id": product.id,
                    "slug": product.slug,
                    "name": product.name,
                    "brand": product.brand,
                    "category": product.category,
                    "sku": product.sku,
                    "description": product.description,
                    "url": product.url,
                }
                for product in products
            ],
            many=True,
        )
        return Response(serializer.data)


class TrackStoreProductView(APIView):
    def post(self, request):
        serializer = TrackStoreProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store_product_id = serializer.validated_data["store_product_id"]
        interval = serializer.validated_data.get("scrape_interval_minutes", 120)

        try:
            store_product = fetch_store_product(store_product_id)
        except StoreClientError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            tracked_product, created = TrackedProduct.objects.update_or_create(
                store_product_id=str(store_product.id),
                defaults={
                    "name": store_product.name,
                    "url": store_product.url,
                    "description": store_product.description,
                    "currency": "INR",
                    "scrape_interval_minutes": interval,
                    "is_active": True,
                    "metadata": {
                        "slug": store_product.slug,
                        "brand": store_product.brand,
                        "category": store_product.category,
                        "sku": store_product.sku,
                        "store_product": store_product.raw,
                    },
                },
            )

        response_serializer = TrackedProductSerializer(tracked_product)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PriceHistoryListView(generics.ListAPIView):
    serializer_class = PriceHistorySerializer

    def get_queryset(self):
        queryset = PriceHistory.objects.select_related("product").all()
        product_id = self.kwargs.get("product_id") or self.request.query_params.get(
            "product_id"
        )
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


class ScrapeRunView(APIView):
    def post(self, request):
        product_id = request.data.get("product_id")
        auth_header = request.headers.get("Authorization", "")
        bearer_token = (
            auth_header.split("Bearer ", 1)[1].strip()
            if "Bearer " in auth_header
            else ""
        )
        provided_secret = (
            request.headers.get("X-Cron-Secret")
            or bearer_token
            or request.query_params.get("secret")
            or request.data.get("secret")
        )
        expected_secret = settings.CRON_SECRET

        # If it's not an individual product scrape triggered from UI, require cron secret
        if not product_id and expected_secret and provided_secret != expected_secret:
            return Response(
                {"detail": "Invalid cron secret."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # For automated cron sweeps, run asynchronously in a background thread
        # so cron-job.org gets an instant 200 OK without hitting its 30s free-tier timeout.
        is_cron = not product_id and (
            request.path.rstrip("/").endswith("/cron/scrape")
            or bool(request.query_params.get("secret"))
        )
        if is_cron:
            import threading
            from django.db import close_old_connections

            def run_in_bg():
                close_old_connections()
                try:
                    scrape_products(
                        product_id=None,
                        force=False,
                        headed=False,
                    )
                except Exception:
                    import logging
                    logging.exception("Background cron scrape failed")
                finally:
                    close_old_connections()

            threading.Thread(target=run_in_bg, daemon=True).start()
            return Response({"ok": True, "status": "job_started"})

        try:
            summary = scrape_products(
                product_id=product_id,
                force=bool(request.data.get("force", False)),
                headed=bool(request.data.get("headed", False)),
            )
            return Response(summary)
        except Exception as exc:
            import logging
            logging.exception("ScrapeRunView failed")
            return Response(
                {"detail": f"Scrape execution failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        return self.post(request)


class ScrapeLogListView(generics.ListAPIView):
    serializer_class = ScrapeLogSerializer

    def get_queryset(self):
        queryset = ScrapeLog.objects.select_related("product").all()
        product_id = self.kwargs.get("product_id") or self.request.query_params.get(
            "product_id"
        )
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset
