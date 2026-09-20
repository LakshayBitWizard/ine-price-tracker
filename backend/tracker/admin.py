from django.contrib import admin

from .models import PriceHistory, ScrapeLog, TrackedProduct

admin.site.register(TrackedProduct)
admin.site.register(PriceHistory)
admin.site.register(ScrapeLog)
