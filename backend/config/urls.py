from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse(
        {
            "status": "healthy",
            "service": "INE Product Price Tracker API",
            "endpoints": {
                "products": "/api/products/",
                "search": "/api/store/search/?q=<name>",
                "cron_scrape": "/api/cron/scrape/",
                "db_check": "/api/db-check/",
            },
        }
    )


def db_check(request):
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            val = cursor.fetchone()
        from tracker.models import TrackedProduct
        count = TrackedProduct.objects.count()
        return JsonResponse({"status": "connected", "select_1": val, "products_count": count})
    except Exception as exc:
        import traceback
        return JsonResponse(
            {"status": "db_error", "error": str(exc), "traceback": traceback.format_exc()},
            status=500,
        )


urlpatterns = [
    path("", health_check),
    path("api/db-check/", db_check),
    path("admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
]

