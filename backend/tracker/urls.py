from django.urls import path

from .views import (
    PriceHistoryListView,
    ScrapeLogListView,
    ScrapeRunView,
    StoreProductSearchView,
    TrackStoreProductView,
    TrackedProductDetailView,
    TrackedProductListCreateView,
)

urlpatterns = [
    path("store/search/", StoreProductSearchView.as_view(), name="store-product-search"),
    path("products/", TrackedProductListCreateView.as_view(), name="product-list-create"),
    path("products/track/", TrackStoreProductView.as_view(), name="product-track"),
    path("products/<uuid:pk>/", TrackedProductDetailView.as_view(), name="product-detail"),
    path("price-history/", PriceHistoryListView.as_view(), name="price-history-list"),
    path("scrape-logs/", ScrapeLogListView.as_view(), name="scrape-log-list"),
    path("scrape/run/", ScrapeRunView.as_view(), name="scrape-run"),
    path(
        "products/<uuid:product_id>/price-history/",
        PriceHistoryListView.as_view(),
        name="product-price-history",
    ),
    path(
        "products/<uuid:product_id>/scrape-logs/",
        ScrapeLogListView.as_view(),
        name="product-scrape-logs",
    ),
]
