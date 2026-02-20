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
- Luma (lu.ma)            — modern event platform popular in finance/tech circles
- Meetup London           — finance/investment networking meetup groups
"""
import json
import logging
import re
from datetime import datetime, timedelta
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
# Eventbrite London  (rewritten — JSON-LD primary, CSS fallback)
# ---------------------------------------------------------------------------

class EventbriteLondonScraper(BaseEventScraper):
    """
    Eventbrite London — finance/investment networking events.

    Uses varied search URLs (one per config, not a hardcoded URL) and parses
    event data from JSON-LD <script> tags embedded in the page.  Falls back
    to CSS selectors when JSON-LD is absent.
    """
    source_name = "eventbrite_london"
    BASE_URL = "https://www.eventbrite.co.uk"

    # Each config hits a DIFFERENT URL — queries are actually varied now.
    SEARCH_CONFIGS = [
        {
            "url": "https://www.eventbrite.co.uk/d/united-kingdom--london/networking/?q=finance+investment",
            "city": "London",
        },
        {
            "url": "https://www.eventbrite.co.uk/d/united-kingdom--london/networking/?q=asset+management",
            "city": "London",
        },
        {
            "url": "https://www.eventbrite.co.uk/d/united-kingdom--london/business/?q=finance+networking",
            "city": "London",
        },
        {
            "url": "https://www.eventbrite.co.uk/d/united-kingdom--london/finance-investment/",
            "city": "London",
        },
        {
            "url": "https://www.eventbrite.co.uk/d/united-kingdom--london/networking/?q=private+equity+investment",
            "city": "London",
        },
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
        today = datetime.utcnow().date()
        end = today + timedelta(days=90)
        sep = "&" if "?" in config["url"] else "?"
        url = f"{config['url']}{sep}start_date={today}&end_date={end}"

        soup = await self._get(url)
        if not soup:
            return []

        # Primary: JSON-LD embedded by Eventbrite in SSR output
        events = self._extract_from_json_ld(soup, config["city"])
        if events:
            return events

        # Secondary: server-data blob injected into the page
        events = self._extract_from_server_data(soup, config["city"])
        if events:
            return events

        # Fallback: CSS selectors (works if Eventbrite SSR includes card HTML)
        return self._parse_cards(soup, config["city"])

    # ------------------------------------------------------------------ JSON-LD

    def _extract_from_json_ld(self, soup, city: str) -> list[ScrapedEvent]:
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Event", "SocialEvent", "BusinessEvent"):
                        event = self._parse_jsonld_item(item, city)
                        if event:
                            events.append(event)
            except Exception:
                continue
        return events

    def _parse_jsonld_item(self, item: dict, city: str) -> Optional[ScrapedEvent]:
        try:
            name = item.get("name", "").strip()
            if not name:
                return None
            url = item.get("url", "").split("?")[0]
            if not url:
                return None

            start_date = self._parse_date(item.get("startDate", ""))
            end_date = self._parse_date(item.get("endDate", ""))

            # Location
            loc = item.get("location", {})
            if isinstance(loc, dict):
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    parts = [
                        addr.get("streetAddress", ""),
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                    ]
                    location_text = ", ".join(p for p in parts if p)
                else:
                    location_text = str(addr)
                venue_name = loc.get("name", "")
                if venue_name and venue_name not in location_text:
                    location_text = f"{venue_name}, {location_text}" if location_text else venue_name
            else:
                location_text = str(loc) if loc else city

            is_online = any(w in location_text.lower() for w in ["online", "virtual"])

            description = item.get("description", "")

            # Offers / price
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = str(offers.get("price", "")).strip()
            is_free = price in ("0", "0.00", "") or offers.get("availability") == "Free"
            cost = f"£{price}" if price and price not in ("0", "0.00", "") else ("Free" if is_free else "")

            organiser = item.get("organizer", {})
            if isinstance(organiser, dict):
                organiser = organiser.get("name", "")
            else:
                organiser = str(organiser) if organiser else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser=organiser,
                event_type=self._classify(name, description),
                location=location_text or city,
                city=city,
                is_online=is_online,
                description=description[:2000],
                event_date=start_date,
                event_end_date=end_date,
                is_free=is_free,
                cost=cost,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] JSON-LD parse error: {e}")
            return None

    # ------------------------------------------------- embedded server-data JSON

    def _extract_from_server_data(self, soup, city: str) -> list[ScrapedEvent]:
        """Try to pull events from window.__SERVER_DATA__ or similar blobs."""
        events = []
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__SERVER_DATA__" not in text and "window.__data" not in text:
                continue
            # Extract the JSON blob
            m = re.search(r'(?:window\.__SERVER_DATA__|window\.__data)\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
                          text, re.DOTALL)
            if not m:
                continue
            try:
                blob = json.loads(m.group(1))
                # Eventbrite typically nests events under search_data.events.results
                results = (
                    blob.get("search_data", {}).get("events", {}).get("results")
                    or blob.get("events", {}).get("results")
                    or []
                )
                for raw in results:
                    event = self._parse_server_event(raw, city)
                    if event:
                        events.append(event)
            except Exception:
                continue
        return events

    def _parse_server_event(self, raw: dict, city: str) -> Optional[ScrapedEvent]:
        try:
            name = raw.get("name", "").strip()
            url = raw.get("url", "").split("?")[0]
            if not name or not url:
                return None

            start = raw.get("start", {})
            event_date = self._parse_date(start.get("utc", "") or start.get("local", ""))

            venue = raw.get("venue") or {}
            location_text = venue.get("name", "") or city
            is_online = raw.get("online_event", False)

            ticket_availability = raw.get("ticket_availability") or {}
            is_free = ticket_availability.get("is_free", False)

            description = (raw.get("description") or {}).get("text", "")

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="",
                event_type=self._classify(name, description),
                location=location_text,
                city=city,
                is_online=is_online,
                description=description[:2000],
                event_date=event_date,
                is_free=is_free,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Server-data event parse error: {e}")
            return None

    # ------------------------------------------------------------ CSS fallback

    def _parse_cards(self, soup, city: str) -> list[ScrapedEvent]:
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
            date_text = date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
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
                event_type=self._classify(name, ""),
                location=location,
                city=city,
                is_online=is_online,
                event_date=event_date,
                is_free=is_free,
                cost=price_text,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    # ---------------------------------------------------------------- helpers

    def _classify(self, name: str, desc: str = "") -> str:
        text = (name + " " + desc).lower()
        if any(w in text for w in ["networking", "mixer", "reception", "drinks", "social"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion", "debate"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum", "symposium"]):
            return "conference"
        if any(w in text for w in ["roundtable", "round table"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "virtual", "online", "zoom"]):
            return "webinar"
        if any(w in text for w in ["workshop", "training", "course"]):
            return "workshop"
        return "seminar"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%A, %B %d · %I:%M %p",
            "%a, %b %d",
        ]:
            try:
                return datetime.strptime(text[:25], fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# Luma (lu.ma) London
# ---------------------------------------------------------------------------

class LumaLondonScraper(BaseEventScraper):
    """
    Lu.ma — modern event platform popular for finance/fintech networking in London.
    Parses __NEXT_DATA__ JSON from their SSR pages; falls back to JSON-LD.
    """
    source_name = "luma_london"
    BASE_URL = "https://lu.ma"

    SEARCH_URLS = [
        "https://lu.ma/discover?q=finance+networking+london&start=2026-01-01",
        "https://lu.ma/discover?q=investment+networking+london",
        "https://lu.ma/discover?q=asset+management+london",
        "https://lu.ma/discover?q=fintech+networking+london",
    ]

    async def scrape(self) -> list[ScrapedEvent]:
        events = []
        seen: set[str] = set()
        for url in self.SEARCH_URLS:
            batch = await self._scrape_url(url)
            for event in batch:
                if event.fingerprint not in seen:
                    seen.add(event.fingerprint)
                    events.append(event)
        logger.info(f"[{self.source_name}] Total unique events: {len(events)}")
        return events

    async def _scrape_url(self, url: str) -> list[ScrapedEvent]:
        soup = await self._get(url)
        if not soup:
            return []

        # Primary: __NEXT_DATA__ SSR JSON blob
        events = self._extract_from_next_data(soup)
        if events:
            return events

        # Fallback: JSON-LD
        return self._extract_from_json_ld(soup)

    def _extract_from_next_data(self, soup) -> list[ScrapedEvent]:
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return []
        try:
            data = json.loads(script.string or "")
            page_props = data.get("props", {}).get("pageProps", {})
            # Lu.ma uses various nested paths depending on page type
            raw_events = (
                page_props.get("events")
                or page_props.get("initialData", {}).get("events")
                or page_props.get("initialEvents")
                or page_props.get("data", {}).get("events")
                or []
            )
            results = []
            for item in raw_events:
                event = self._parse_luma_item(item)
                if event:
                    results.append(event)
            return results
        except Exception as e:
            logger.debug(f"[{self.source_name}] __NEXT_DATA__ parse error: {e}")
            return []

    def _extract_from_json_ld(self, soup) -> list[ScrapedEvent]:
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Event", "SocialEvent"):
                        event = self._parse_jsonld_item(item)
                        if event:
                            events.append(event)
            except Exception:
                continue
        return events

    def _parse_luma_item(self, item: dict) -> Optional[ScrapedEvent]:
        try:
            # Lu.ma wraps events in {"event": {...}} or exposes fields directly
            ev = item.get("event", item)
            name = (ev.get("name") or ev.get("title", "")).strip()
            if not name:
                return None

            slug = ev.get("url") or ev.get("slug", "")
            if not slug:
                return None
            url = slug if slug.startswith("http") else f"https://lu.ma/{slug}"

            event_date = self._parse_date(ev.get("start_at", ""))
            event_end_date = self._parse_date(ev.get("end_at", ""))

            geo = ev.get("geo_address_info") or {}
            location = (
                geo.get("full_address")
                or geo.get("city_state")
                or ev.get("location", "London")
            )
            city_raw = geo.get("city", "")
            city = city_raw if city_raw else "London"

            description = (ev.get("description") or "")[:2000]

            ticket_info = ev.get("ticket_info") or {}
            min_price = ticket_info.get("min_ticket_price")
            is_free = min_price == 0 or min_price is None

            host = ev.get("hosts") or []
            organiser = host[0].get("name", "") if host and isinstance(host[0], dict) else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser=organiser,
                event_type=self._classify(name, description),
                location=location,
                city=city,
                is_online="online" in location.lower() or "virtual" in location.lower(),
                description=description,
                event_date=event_date,
                event_end_date=event_end_date,
                is_free=is_free,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Luma item parse error: {e}")
            return None

    def _parse_jsonld_item(self, item: dict) -> Optional[ScrapedEvent]:
        try:
            name = item.get("name", "").strip()
            url = item.get("url", "").split("?")[0]
            if not name or not url:
                return None
            event_date = self._parse_date(item.get("startDate", ""))
            loc = item.get("location", {})
            if isinstance(loc, dict):
                addr = loc.get("address", {})
                location_text = addr.get("addressLocality", "") if isinstance(addr, dict) else str(addr)
            else:
                location_text = "London"
            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="",
                event_type=self._classify(name, ""),
                location=location_text or "London",
                city="London",
                event_date=event_date,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] JSON-LD parse error: {e}")
            return None

    def _classify(self, name: str, desc: str = "") -> str:
        text = (name + " " + desc).lower()
        if any(w in text for w in ["networking", "mixer", "reception", "drinks", "social"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion", "debate"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum", "symposium"]):
            return "conference"
        if any(w in text for w in ["roundtable", "round table"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "virtual", "online", "zoom"]):
            return "webinar"
        if any(w in text for w in ["workshop", "training", "course"]):
            return "workshop"
        return "seminar"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                return datetime.strptime(text[:26], fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# Meetup London (finance / investment groups)
# ---------------------------------------------------------------------------

class MeetupLondonScraper(BaseEventScraper):
    """
    Meetup.com — London finance and investment professional networking groups.
    Scrapes the Meetup search results page (SSR) and extracts __NEXT_DATA__ JSON.
    """
    source_name = "meetup_london"
    BASE_URL = "https://www.meetup.com"

    SEARCH_URLS = [
        "https://www.meetup.com/find/?q=finance+networking+investment&location=London%2C+GB&source=EVENTS&eventType=inPerson",
        "https://www.meetup.com/find/?q=asset+management+networking&location=London%2C+GB&source=EVENTS&eventType=inPerson",
        "https://www.meetup.com/find/?q=investment+professionals+london&location=London%2C+GB&source=EVENTS",
        "https://www.meetup.com/find/?q=CFA+finance+london&location=London%2C+GB&source=EVENTS",
    ]

    async def scrape(self) -> list[ScrapedEvent]:
        events = []
        seen: set[str] = set()
        for url in self.SEARCH_URLS:
            batch = await self._scrape_url(url)
            for event in batch:
                if event.fingerprint not in seen:
                    seen.add(event.fingerprint)
                    events.append(event)
        logger.info(f"[{self.source_name}] Total unique events: {len(events)}")
        return events

    async def _scrape_url(self, url: str) -> list[ScrapedEvent]:
        soup = await self._get(url)
        if not soup:
            return []

        # Primary: __NEXT_DATA__ JSON (Meetup uses Next.js)
        events = self._extract_from_next_data(soup)
        if events:
            return events

        # Fallback: JSON-LD
        events = self._extract_from_json_ld(soup)
        if events:
            return events

        # Last resort: CSS selectors
        return self._parse_cards(soup)

    def _extract_from_next_data(self, soup) -> list[ScrapedEvent]:
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return []
        try:
            data = json.loads(script.string or "")
            page_props = data.get("props", {}).get("pageProps", {})
            # Meetup nests events in various paths
            raw_events = (
                page_props.get("events")
                or page_props.get("searchResults", {}).get("events")
                or page_props.get("data", {}).get("rankedEvents", {}).get("edges", [])
                or []
            )
            results = []
            for item in raw_events:
                # Meetup may wrap in {node: {...}}
                ev_data = item.get("node", item)
                event = self._parse_meetup_event(ev_data)
                if event:
                    results.append(event)
            return results
        except Exception as e:
            logger.debug(f"[{self.source_name}] __NEXT_DATA__ parse error: {e}")
            return []

    def _extract_from_json_ld(self, soup) -> list[ScrapedEvent]:
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Event", "SocialEvent"):
                        event = self._parse_jsonld_item(item)
                        if event:
                            events.append(event)
            except Exception:
                continue
        return events

    def _parse_meetup_event(self, ev: dict) -> Optional[ScrapedEvent]:
        try:
            name = (ev.get("title") or ev.get("name", "")).strip()
            if not name:
                return None
            url = ev.get("eventUrl") or ev.get("url", "")
            if not url:
                return None

            # Meetup timestamps are epoch milliseconds or ISO strings
            time_val = ev.get("dateTime") or ev.get("time")
            if isinstance(time_val, (int, float)):
                event_date = datetime.utcfromtimestamp(time_val / 1000)
            else:
                event_date = self._parse_date(str(time_val) if time_val else "")

            venue = ev.get("venue") or {}
            location_parts = [
                venue.get("name", ""),
                venue.get("address", ""),
                venue.get("city", ""),
            ]
            location_text = ", ".join(p for p in location_parts if p) or "London"

            description = (ev.get("description") or "")[:2000]
            # Strip HTML tags from Meetup descriptions
            description = re.sub(r"<[^>]+>", " ", description).strip()

            group = ev.get("group") or {}
            organiser = group.get("name", "")

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser=organiser,
                event_type=self._classify(name, description),
                location=location_text,
                city="London",
                is_online=ev.get("isOnline", False),
                description=description,
                event_date=event_date,
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Meetup event parse error: {e}")
            return None

    def _parse_jsonld_item(self, item: dict) -> Optional[ScrapedEvent]:
        try:
            name = item.get("name", "").strip()
            url = item.get("url", "").split("?")[0]
            if not name or not url:
                return None
            event_date = self._parse_date(item.get("startDate", ""))
            loc = item.get("location", {})
            if isinstance(loc, dict):
                addr = loc.get("address", {})
                location_text = addr.get("addressLocality", "") if isinstance(addr, dict) else str(addr)
            else:
                location_text = "London"
            description = item.get("description", "")
            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="",
                event_type=self._classify(name, description),
                location=location_text or "London",
                city="London",
                event_date=event_date,
                description=description[:2000],
                themes=["financial services", "investment management", "networking", "London"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] JSON-LD parse error: {e}")
            return None

    def _parse_cards(self, soup) -> list[ScrapedEvent]:
        """CSS fallback for Meetup search results."""
        events = []
        cards = soup.select(
            "[data-testid='event-card'], "
            ".eventCard, "
            "article[class*='event'], "
            "li[class*='event']"
        )
        for card in cards:
            try:
                title_el = card.select_one("h2, h3, [class*='title'], [class*='name']")
                if not title_el:
                    continue
                name = title_el.get_text(strip=True)
                link_el = card.select_one("a[href*='/events/']")
                if not link_el:
                    continue
                url = urljoin(self.BASE_URL, link_el.get("href", ""))
                date_el = card.select_one("time, [class*='date']")
                event_date = self._parse_date(
                    date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
                )
                events.append(ScrapedEvent(
                    name=name,
                    url=url,
                    source=self.source_name,
                    event_type=self._classify(name, ""),
                    location="London",
                    city="London",
                    event_date=event_date,
                    themes=["financial services", "investment management", "networking", "London"],
                ))
            except Exception:
                continue
        return events

    def _classify(self, name: str, desc: str = "") -> str:
        text = (name + " " + desc).lower()
        if any(w in text for w in ["networking", "mixer", "reception", "drinks", "social"]):
            return "networking"
        if any(w in text for w in ["panel", "discussion", "debate"]):
            return "panel"
        if any(w in text for w in ["conference", "summit", "forum", "symposium"]):
            return "conference"
        if any(w in text for w in ["roundtable", "round table"]):
            return "roundtable"
        if any(w in text for w in ["webinar", "virtual", "online", "zoom"]):
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
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]:
            try:
                return datetime.strptime(text[:25], fmt)
            except ValueError:
                continue
        return None
