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
            },
        }
    )


urlpatterns = [
    path("", health_check),
    path("admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
]

