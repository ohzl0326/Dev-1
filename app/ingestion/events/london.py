"""
London-focused event scrapers for institutional AM / banking professionals.

Sources:
- CFA Society UK          — premier AM networking in London
- Investment Association  — UK's AM industry body (theia.org)
- AIMA                    — alternatives/hedge fund events, filter London
- PIMFA                   — wealth management / private investment
- AIC                     — Association of Investment Companies
- Institutional Investor  — global AM conferences with London focus
- CAIA                    — alternatives/private markets, filter London/UK
- Eventbrite London       — finance/investment networking events in London
"""
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseEventScraper, ScrapedEvent

logger = logging.getLogger(__name__)

LONDON_SIGNALS = ["london", "uk", "united kingdom", "england", "city of london"]


def _is_london_event(city: str, location: str) -> bool:
    combined = (city + " " + location).lower()
    return any(sig in combined for sig in LONDON_SIGNALS)


# ---------------------------------------------------------------------------
# CFA Society UK
# ---------------------------------------------------------------------------

class CFAUKScraper(BaseEventScraper):
    """CFA Society UK — the primary professional body for AM in London."""
    source_name = "cfa_uk"
    BASE_URL = "https://www.cfauk.org"
    EVENTS_URL = "https://www.cfauk.org/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "article[class*='event'], "
            ".event-item, "
            "[class*='event-card'], "
            ".tribe-event, "
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
            title_el = card.select_one("h2 a, h3 a, h4 a, .event-title a, [class*='title'] a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .event-date, abbr[title]")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get("title", "")
                event_date = self._parse_date(dt_str or date_el.get_text(strip=True))

            loc_el = card.select_one("[class*='location'], [class*='venue'], .event-location")
            location = loc_el.get_text(strip=True) if loc_el else "London"

            desc_el = card.select_one("p, .excerpt, [class*='description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="CFA Society UK",
                event_type=self._classify(name, description),
                location=location,
                city="London",
                description=description,
                event_date=event_date,
                themes=["asset management", "investment management", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify(self, name: str, desc: str) -> str:
        text = (name + " " + desc).lower()
        if any(w in text for w in ["networking", "mixer", "reception", "drinks"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion", "debate"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum", "symposium"]):
            return "conference"
        if any(w in text for w in ["roundtable", "round table"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "online", "virtual"]):
            return "webinar"
        if any(w in text for w in ["workshop", "training", "course"]):
            return "workshop"
        return "seminar"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
            "%d/%m/%Y",
            "%d %b %Y",
        ]:
            try:
                return datetime.strptime(text[:len(fmt) + 5], fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# Investment Association (The IA / theia.org)
# ---------------------------------------------------------------------------

class InvestmentAssociationScraper(BaseEventScraper):
    """
    The Investment Association — UK's trade body for asset management.
    Events are aimed at AM professionals; conference / roundtable heavy.
    """
    source_name = "investment_association"
    BASE_URL = "https://www.theia.org"
    EVENTS_URL = "https://www.theia.org/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "[class*='event-item'], "
            "article[class*='event'], "
            ".event-listing, "
            "li.event, "
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
            title_el = card.select_one("h2 a, h3 a, h4 a, a[href*='event'], [class*='title'] a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .event-date")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get_text(strip=True)
                event_date = self._parse_date(dt_str)

            desc_el = card.select_one("p, .summary, [class*='description'], [class*='excerpt']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="Investment Association",
                event_type=self._classify(name, description),
                location="London",
                city="London",
                description=description,
                event_date=event_date,
                themes=["asset management", "fund management", "UK", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify(self, name: str, desc: str) -> str:
        text = (name + " " + desc).lower()
        if "roundtable" in text:
            return "roundtable"
        if "conference" in text or "summit" in text:
            return "conference"
        if "forum" in text:
            return "forum"
        if "panel" in text:
            return "panel"
        if "webinar" in text or "virtual" in text:
            return "webinar"
        if "networking" in text:
            return "networking"
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


# ---------------------------------------------------------------------------
# PIMFA (Personal Investment Management & Financial Advice Association)
# ---------------------------------------------------------------------------

class PIMFAScraper(BaseEventScraper):
    """PIMFA — wealth management and private investment events in London."""
    source_name = "pimfa"
    BASE_URL = "https://www.pimfa.co.uk"
    EVENTS_URL = "https://www.pimfa.co.uk/events/"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "article.type-tribe_events, "
            "[class*='tribe-event'], "
            ".event-item, "
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
            title_el = card.select_one("h2 a, h3 a, h4 a, [class*='title'] a, .tribe-event-url")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, .tribe-event-date-start, [class*='date'], abbr[title]")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get("title", "")
                event_date = self._parse_date(dt_str or date_el.get_text(strip=True))

            loc_el = card.select_one("[class*='venue'], [class*='location'], .tribe-venue")
            location = loc_el.get_text(strip=True) if loc_el else "London"

            desc_el = card.select_one("p, [class*='excerpt'], [class*='description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="PIMFA",
                event_type=self._classify(name, description),
                location=location,
                city="London",
                description=description,
                event_date=event_date,
                themes=["wealth management", "financial services", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify(self, name: str, desc: str) -> str:
        text = (name + " " + desc).lower()
        if "networking" in text or "reception" in text:
            return "networking"
        if "conference" in text or "summit" in text:
            return "conference"
        if "roundtable" in text:
            return "roundtable"
        if "webinar" in text:
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


# ---------------------------------------------------------------------------
# AIC (Association of Investment Companies)
# ---------------------------------------------------------------------------

class AICScraper(BaseEventScraper):
    """AIC — investment companies / investment trust sector events."""
    source_name = "aic"
    BASE_URL = "https://www.theaic.co.uk"
    EVENTS_URL = "https://www.theaic.co.uk/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "[class*='event-item'], "
            "article, "
            "li.event, "
            "[class*='event-card']"
        )

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, h4 a, a[href*='event'], [class*='title'] a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .event-date")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get_text(strip=True)
                event_date = self._parse_date(dt_str)

            desc_el = card.select_one("p, [class*='description'], [class*='summary']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="Association of Investment Companies",
                event_type="seminar",
                location="London",
                city="London",
                description=description,
                event_date=event_date,
                themes=["investment companies", "asset management", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

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


# ---------------------------------------------------------------------------
# Institutional Investor Events
# ---------------------------------------------------------------------------

class InstitutionalInvestorScraper(BaseEventScraper):
    """
    Institutional Investor — global AM conferences; filter for London/Europe.
    High-prestige events, good for networking with senior allocators.
    """
    source_name = "institutional_investor"
    BASE_URL = "https://www.institutionalinvestor.com"
    EVENTS_URL = "https://www.institutionalinvestor.com/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "[class*='event-card'], "
            "[class*='event-item'], "
            "article, "
            ".event"
        )

        for card in cards:
            event = self._parse_card(card)
            if event and (_is_london_event(event.city, event.location) or event.is_online):
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} London/online events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one(
                "h2 a, h3 a, h4 a, [class*='title'] a, [class*='event-title'] a"
            )
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .date")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get_text(strip=True)
                event_date = self._parse_date(dt_str)

            loc_el = card.select_one("[class*='location'], [class*='venue'], .city")
            location_text = loc_el.get_text(strip=True) if loc_el else ""
            city = self._extract_city(location_text)
            is_online = "virtual" in location_text.lower() or "online" in location_text.lower()

            desc_el = card.select_one("p, .summary, [class*='description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="Institutional Investor",
                event_type="conference",
                location=location_text or "London",
                city=city,
                is_online=is_online,
                description=description,
                event_date=event_date,
                themes=["institutional investment", "asset management", "EMEA"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _extract_city(self, location: str) -> str:
        loc_lower = location.lower()
        if "london" in loc_lower:
            return "London"
        if "uk" in loc_lower or "united kingdom" in loc_lower or "england" in loc_lower:
            return "London"
        if "virtual" in loc_lower or "online" in loc_lower:
            return "Online"
        if "europe" in loc_lower or "emea" in loc_lower:
            return "EMEA"
        return location.split(",")[0].strip().title() if location else "Global"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%b %d, %Y"]:
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# AIMA London filter (wraps existing AIMA scraper with London filter)
# ---------------------------------------------------------------------------

class AIMALondonScraper(BaseEventScraper):
    """
    AIMA events filtered for London/UK.
    AIMA runs many London events for alternatives professionals.
    """
    source_name = "aima_london"
    BASE_URL = "https://www.aima.org"
    EVENTS_URL = "https://www.aima.org/events.html"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "[class*='event-item'], "
            "li.event, "
            ".events-list li, "
            "article"
        )

        for card in cards:
            event = self._parse_card(card)
            if event:
                # Keep London, UK, online, and global events
                if (
                    _is_london_event(event.city, event.location)
                    or event.city in ("Online", "Global")
                    or event.is_online
                ):
                    events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} London/online AIMA events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, h4 a, a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date']")
            event_date = None
            if date_el:
                dt_str = date_el.get("datetime", "") or date_el.get_text(strip=True)
                event_date = self._parse_date(dt_str)

            loc_el = card.select_one("[class*='location'], [class*='venue'], [class*='city']")
            location_text = loc_el.get_text(strip=True) if loc_el else ""
            loc_lower = location_text.lower()

            if "london" in loc_lower or "uk" in loc_lower or "united kingdom" in loc_lower:
                city = "London"
            elif "online" in loc_lower or "virtual" in loc_lower:
                city = "Online"
            else:
                city = location_text.split(",")[0].strip().title() if location_text else "Global"

            is_online = "online" in loc_lower or "virtual" in loc_lower

            desc_el = card.select_one("p, .excerpt")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="AIMA",
                event_type=self._classify(name),
                location=location_text,
                city=city,
                is_online=is_online,
                description=description,
                event_date=event_date,
                themes=["alternatives", "hedge fund", "private credit", "asset management"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _classify(self, name: str) -> str:
        nl = name.lower()
        if "roundtable" in nl:
            return "roundtable"
        if "networking" in nl or "cocktail" in nl or "reception" in nl:
            return "networking"
        if "conference" in nl or "summit" in nl:
            return "conference"
        if "webinar" in nl or "virtual" in nl:
            return "webinar"
        if "forum" in nl:
            return "forum"
        return "seminar"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# Eventbrite London
# ---------------------------------------------------------------------------

class EventbriteLondonScraper(BaseEventScraper):
    """
    Eventbrite London — finance and investment networking events.
    Covers smaller, niche events not on specialist platforms.
    """
    source_name = "eventbrite_london"
    BASE_URL = "https://www.eventbrite.co.uk"

    SEARCH_CONFIGS = [
        {"query": "asset management networking London", "city": "London"},
        {"query": "investment banking networking London", "city": "London"},
        {"query": "institutional investment London", "city": "London"},
        {"query": "CFA networking London finance", "city": "London"},
        {"query": "private equity networking London", "city": "London"},
    ]

    async def scrape(self) -> list[ScrapedEvent]:
        events = []
        seen: set[str] = set()

        for config in self.SEARCH_CONFIGS:
            batch = await self._scrape_search(config)
            for event in batch:
                if event.fingerprint not in seen:
                    seen.add(event.fingerprint)
                    events.append(event)

        logger.info(f"[{self.source_name}] Total unique events: {len(events)}")
        return events

    async def _scrape_search(self, config: dict) -> list[ScrapedEvent]:
        from urllib.parse import quote_plus
        search_url = (
            f"https://www.eventbrite.co.uk/d/united-kingdom--london/"
            f"finance--investment/"
        )
        soup = await self._get(search_url)
        if not soup:
            # Fallback to generic search
            soup = await self._get(
                f"{self.BASE_URL}/e/",
                params={"q": config["query"], "location": "London"},
            )
        if not soup:
            return []
        return self._parse_results(soup, config["city"])

    def _parse_results(self, soup, city: str) -> list[ScrapedEvent]:
        events = []
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
                "h2, h3, [class*='EventCard__Title']"
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
                themes=["networking", "finance", "investment", "London"],
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
