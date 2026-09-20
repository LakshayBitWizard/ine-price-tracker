from django.core.management.base import BaseCommand, CommandError

from tracker.scraper import scrape_products


class Command(BaseCommand):
    help = "Scrape tracked INE store products once."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", help="TrackedProduct UUID to scrape.")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Scrape every active product instead of only due products.",
        )
        parser.add_argument(
            "--headed",
            action="store_true",
            help="Run Chromium headed so the scrape can be recorded.",
        )

    def handle(self, *args, **options):
        if options["product_id"] and options["all"]:
            raise CommandError("Use either --product-id or --all, not both.")

        summary = scrape_products(
            product_id=options["product_id"],
            force=options["all"],
            headed=options["headed"],
        )
        self.stdout.write(self.style.SUCCESS(f"Scraped {summary['count']} product(s)."))
        for result in summary["results"]:
            self.stdout.write(str(result))
