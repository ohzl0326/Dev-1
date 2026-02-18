"""
Eventbrite scraper — catches finance/investment networking events in SG and Sydney
that aren't hosted on specialist platforms.
Uses Eventbrite's public search API.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.ingestion.base_scraper import BaseEventScraper, ScrapedEvent

logger = logging.getLogger(__name__)

# Eventbrite category IDs
FINANCE_CATEGORY_ID = "102"       # Finance & Economics
BUSINESS_CATEGORY_ID = "101"     # Business & Professional


class EventbriteScraper(BaseEventScraper):
    source_name = "eventbrite_finance"
    API_BASE = "https://www.eventbriteapi.com/v3"

    SEARCH_CONFIGS = [
        {
            "query": "asset management networking",
            "location_address": "Singapore",
            "location_within": "10km",
            "city": "Singapore",
        },
        {
            "query": "institutional investment networking Singapore",
            "location_address": "Singapore",
            "location_within": "10km",
            "city": "Singapore",
        },
        {
            "query": "asset management networking",
            "location_address": "Sydney, NSW, Australia",
            "location_within": "25km",
            "city": "Sydney",
        },
        {
            "query": "fund management investment professional networking Sydney",
            "location_address": "Sydney, NSW, Australia",
            "location_within": "25km",
            "city": "Sydney",
        },
        {
            "query": "CFA investment professional",
            "location_address": "Singapore",
            "location_within": "10km",
            "city": "Singapore",
        },
        {
            "query": "private markets alternatives investment",
            "location_address": "Singapore",
            "location_within": "10km",
            "city": "Singapore",
        },
    ]

    async def scrape(self) -> list[ScrapedEvent]:
        events = []
        seen: set[str] = set()

        for config in self.SEARCH_CONFIGS:
            logger.info(
                f"[{self.source_name}] Searching: '{config['query']}' in {config['city']}"
            )
            batch = await self._scrape_search(config)
            for event in batch:
                if event.fingerprint not in seen:
                    seen.add(event.fingerprint)
                    events.append(event)

        logger.info(f"[{self.source_name}] Total unique events: {len(events)}")
        return events

    async def _scrape_search(self, config: dict) -> list[ScrapedEvent]:
        # Try the public Eventbrite search page (no API key needed)
        from urllib.parse import urlencode, quote_plus
        params = {
            "q": config["query"],
            "location.address": config["location_address"],
            "location.within": config["location_within"],
            "categories": f"{FINANCE_CATEGORY_ID},{BUSINESS_CATEGORY_ID}",
            "start_date.range_start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        url = "https://www.eventbrite.com/d/online/finance/"
        # Use the HTML search endpoint
        search_url = (
            f"https://www.eventbrite.com/d/"
            f"{quote_plus(config['location_address'].lower().replace(',', '').replace(' ', '-'))}/"
            f"finance--asset-management/"
        )

        soup = await self._get(search_url)
        if not soup:
            # Fallback to generic search
            soup = await self._get(
                "https://www.eventbrite.com/e/",
                params={"q": config["query"], "location": config["location_address"]},
            )
        if not soup:
            return []

        return self._parse_results(soup, config["city"])

    def _parse_results(self, soup, city: str) -> list[ScrapedEvent]:
        events = []

        # Eventbrite uses different card structures
        cards = soup.select(
            "[data-testid='event-card'], "
            ".event-card, "
            "article.eds-event-card, "
            "[class*='EventCard'], "
            ".eds-l-pad-bot-4"
        )

        for card in cards:
            event = self._parse_card(card, city)
            if event:
                events.append(event)

        return events

    def _parse_card(self, card, city: str) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one(
                "[data-testid='event-card-title'], "
                ".eds-event-card__formatted-name, "
                "h2, h3, "
                "[class*='EventCard__Title']"
            )
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None

            link_el = card.select_one("a[href*='eventbrite'], a[href*='/e/']")
            url = link_el.get("href", "").split("?")[0] if link_el else ""
            if not url:
                return None

            date_el = card.select_one(
                "[data-testid='event-card-date'], "
                ".eds-event-card-content__sub-title, "
                "time, [class*='EventDateTime']"
            )
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", date_el.get_text(strip=True))
            event_date = self._parse_date(date_text)

            loc_el = card.select_one(
                "[data-testid='event-card-location'], "
                ".card-text--truncated__one, "
                "[class*='EventCardLocation']"
            )
            location = loc_el.get_text(strip=True) if loc_el else city
            is_online = any(w in location.lower() for w in ["online", "virtual"])

            price_el = card.select_one("[data-testid='event-card-price'], .eds-text-bm")
            price_text = price_el.get_text(strip=True) if price_el else ""
            is_free = "free" in price_text.lower() if price_text else None

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="",
                event_type="networking",
                location=location,
                city=city,
                is_online=is_online,
                event_date=event_date,
                is_free=is_free,
                cost=price_text,
                themes=["networking", "finance", "investment"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%A, %B %d · %I:%M %p",
            "%a, %b %d",
        ]:
            try:
                return datetime.strptime(text.strip()[:25], fmt)
            except ValueError:
                continue
        return None
