"""
CFA Society event scrapers — Singapore and Sydney chapters.
These are the highest-value networking events for AM professionals in both cities.
"""
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseEventScraper, ScrapedEvent

logger = logging.getLogger(__name__)


class CFASingaporeScraper(BaseEventScraper):
    """CFA Society Singapore — premier AM networking in SG."""
    source_name = "cfa_singapore"
    BASE_URL = "https://cfasingapore.org.sg"
    EVENTS_URL = "https://cfasingapore.org.sg/events/"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        # The CFA Singapore site uses The Events Calendar plugin (WordPress)
        cards = soup.select(
            "article.type-tribe_events, "
            ".tribe-events-calendar-list__event, "
            ".tribe_events_cat, "
            "article[class*='tribe']"
        )

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        # Fallback: any article or event-like div
        if not events:
            cards = soup.select("article, .event-item, [class*='event-']")
            for card in cards:
                event = self._parse_card(card)
                if event:
                    events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one(
                ".tribe-event-url, "
                "h2 a, h3 a, h4 a, "
                ".tribe-events-calendar-list__event-title a, "
                "[class*='event-title'] a"
            )
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else ""
            if not name or not url:
                return None

            # Date
            date_el = card.select_one(
                "time, .tribe-event-date-start, "
                "[class*='event-date'], abbr[title]"
            )
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get("title", "")
                event_date = self._parse_date(dt_str or date_el.get_text(strip=True))

            # Location
            loc_el = card.select_one(
                ".tribe-events-venue-location, "
                "[class*='venue'], [class*='location'], "
                ".tribe-venue"
            )
            location = loc_el.get_text(strip=True) if loc_el else "Singapore"

            # Description/excerpt
            desc_el = card.select_one(".tribe-events-schedule, p, [class*='excerpt']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="CFA Society Singapore",
                event_type=self._classify_event_type(name, description),
                location=location,
                city="Singapore",
                description=description,
                event_date=event_date,
                is_free=False,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify_event_type(self, name: str, description: str) -> str:
        text = (name + " " + description).lower()
        if any(w in text for w in ["networking", "mixer", "cocktail", "reception"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion", "debate"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum", "symposium"]):
            return "conference"
        if any(w in text for w in ["roundtable", "round table"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "online", "virtual", "zoom"]):
            return "webinar"
        if any(w in text for w in ["workshop", "training", "course"]):
            return "workshop"
        return "other"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%d/%m/%Y",
        ]:
            try:
                return datetime.strptime(text[:len(fmt) + 2], fmt)
            except ValueError:
                continue
        return None


class CFASydneyScraper(BaseEventScraper):
    """CFA Society Sydney — AM networking and CPD events."""
    source_name = "cfa_australia"
    BASE_URL = "https://www.cfasociety.org"
    # CFA Australia has chapters; Sydney is the primary one
    EVENTS_URL = "https://www.cfasociety.org/sydney/Pages/Events.aspx"
    FALLBACK_URL = "https://www.cfa-sydney.org.au/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            soup = await self._get(self.FALLBACK_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "li.event-item, "
            ".event-listing, "
            "[class*='event'], "
            "article"
        )

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, h4 a, a[href*='event']")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else ""
            if not name:
                return None
            if not url:
                url = self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], span[class*='date']")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get_text(strip=True)
                event_date = self._parse_date(dt_str)

            desc_el = card.select_one("p, [class*='description'], [class*='excerpt']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="CFA Society Sydney",
                event_type=self._classify_event_type(name, description),
                location="Sydney",
                city="Sydney",
                description=description,
                event_date=event_date,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify_event_type(self, name: str, description: str) -> str:
        text = (name + " " + description).lower()
        if any(w in text for w in ["networking", "mixer", "cocktail"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum"]):
            return "conference"
        if any(w in text for w in ["roundtable"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "online", "virtual"]):
            return "webinar"
        return "seminar"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        return None
