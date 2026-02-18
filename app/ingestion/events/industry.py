"""
Industry-specific event scrapers:
- Conexus Financial (Australia's #1 institutional investment events platform)
- Investment Magazine (Australian institutional AM)
- AsianInvestor (APAC institutional AM)
- AIMA (alternatives / hedge fund)
- CAIA Association (private markets / alternatives)
- ASIFMA (Asia financial markets)
- Fiduciary Investors Symposium
"""
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseEventScraper, ScrapedEvent

logger = logging.getLogger(__name__)


class ConexusScraper(BaseEventScraper):
    """
    Conexus Financial — Australia's premier institutional investment events.
    Organises: Fiduciary Investors Symposium, Investment Magazine Conference,
    Frontier Forum, etc. Attended by super funds, endowments, family offices.
    """
    source_name = "conexus"
    BASE_URL = "https://conexusfinancial.com.au"
    EVENTS_URL = "https://conexusfinancial.com.au/events/"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            "article.event, "
            ".event-item, "
            "[class*='event-card'], "
            ".wp-block-post, "
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
            title_el = card.select_one("h2 a, h3 a, h4 a, .entry-title a, a.event-link")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else ""
            if not name:
                return None

            date_el = card.select_one("time, .event-date, [class*='date']")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )

            loc_el = card.select_one("[class*='location'], [class*='venue']")
            location = loc_el.get_text(strip=True) if loc_el else "Sydney, Australia"

            desc_el = card.select_one("p, .excerpt, [class*='description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url or self.EVENTS_URL,
                source=self.source_name,
                organiser="Conexus Financial",
                event_type=self._infer_type(name, description),
                location=location,
                city="Sydney",
                description=description,
                event_date=event_date,
                themes=["institutional investment", "asset management", "Australia"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error: {e}")
            return None

    def _infer_type(self, name: str, desc: str) -> str:
        text = (name + " " + desc).lower()
        if "symposium" in text or "conference" in text or "summit" in text:
            return "conference"
        if "forum" in text:
            return "forum"
        if "roundtable" in text:
            return "roundtable"
        if "networking" in text:
            return "networking"
        return "conference"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None


class AsianInvestorScraper(BaseEventScraper):
    """
    AsianInvestor — institutional AM events across APAC / Singapore focus.
    Covers pension funds, sovereign wealth, insurance, endowments in Asia.
    """
    source_name = "asian_investor"
    BASE_URL = "https://www.asianinvestor.net"
    EVENTS_URL = "https://www.asianinvestor.net/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select(
            ".event-listing, "
            "article.event, "
            "[class*='event-item'], "
            ".content-item"
        )

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, h4 a, a.title, .event-title a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .event-date")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )

            loc_el = card.select_one("[class*='location'], [class*='venue']")
            location = loc_el.get_text(strip=True) if loc_el else "Singapore"
            city = "Singapore" if "singapore" in location.lower() else "APAC"

            desc_el = card.select_one("p, .excerpt")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="AsianInvestor",
                event_type="conference",
                location=location,
                city=city,
                description=description,
                event_date=event_date,
                themes=["institutional investment", "asset management", "APAC", "Asia Pacific"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error: {e}")
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None


class AIMAEventScraper(BaseEventScraper):
    """
    AIMA (Alternative Investment Management Association) events.
    Covers hedge funds, private credit, private equity — Singapore chapter active.
    """
    source_name = "aima"
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
                # Only include Asia Pacific / Singapore / Sydney events
                if event.city in ("Singapore", "Sydney", "APAC", "Online") or event.is_online:
                    events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} APAC events")
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
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )

            loc_el = card.select_one("[class*='location'], [class*='venue'], [class*='city']")
            location_text = loc_el.get_text(strip=True).lower() if loc_el else ""

            if "singapore" in location_text:
                city = "Singapore"
            elif "sydney" in location_text or "australia" in location_text:
                city = "Sydney"
            elif "online" in location_text or "virtual" in location_text:
                city = "Online"
            else:
                city = location_text.title() or "Global"

            is_online = "online" in location_text or "virtual" in location_text

            desc_el = card.select_one("p, .excerpt")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="AIMA",
                event_type=self._infer_type(name),
                location=loc_el.get_text(strip=True) if loc_el else "",
                city=city,
                is_online=is_online,
                description=description,
                event_date=event_date,
                themes=["alternatives", "private markets", "hedge fund", "asset management"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error: {e}")
            return None

    def _infer_type(self, name: str) -> str:
        name_lower = name.lower()
        if "roundtable" in name_lower:
            return "roundtable"
        if "networking" in name_lower or "cocktail" in name_lower:
            return "networking"
        if "conference" in name_lower or "summit" in name_lower:
            return "conference"
        if "webinar" in name_lower or "virtual" in name_lower:
            return "webinar"
        return "forum"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None


class CAIAScraper(BaseEventScraper):
    """
    CAIA Association — alternatives / private markets certification body.
    Runs networking and education events in Singapore and Sydney.
    """
    source_name = "caia"
    BASE_URL = "https://caia.org"
    EVENTS_URL = "https://caia.org/events"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select("article, .event-card, [class*='event'], li.views-row")

        for card in cards:
            event = self._parse_card(card)
            if event and (
                event.city in ("Singapore", "Sydney", "Online")
                or event.is_online
                or "apac" in event.description.lower()
                or "asia" in event.description.lower()
                or "australia" in event.description.lower()
            ):
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} relevant events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, h4 a, a.views-field, .event-title a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, [class*='date'], .date-display-single")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )

            loc_el = card.select_one("[class*='location'], [class*='venue'], [class*='city']")
            location = loc_el.get_text(strip=True) if loc_el else ""
            city = self._extract_city(location)
            is_online = any(w in location.lower() for w in ["online", "virtual", "webinar"])

            desc_el = card.select_one("p, .description, .body")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="CAIA Association",
                event_type="networking",
                location=location,
                city=city,
                is_online=is_online,
                description=description,
                event_date=event_date,
                themes=["alternatives", "private markets", "private equity", "private credit"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error: {e}")
            return None

    def _extract_city(self, location: str) -> str:
        loc_lower = location.lower()
        if "singapore" in loc_lower:
            return "Singapore"
        if "sydney" in loc_lower or "australia" in loc_lower:
            return "Sydney"
        if "online" in loc_lower or "virtual" in loc_lower:
            return "Online"
        return location.split(",")[0].strip().title() if location else "Global"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%b %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None


class FiduciaryInvestorsScraper(BaseEventScraper):
    """
    Fiduciary Investors Symposium — top-tier Australian institutional event.
    Attracts CIOs of major super funds, endowments. High-value networking.
    """
    source_name = "fiduciary_investors"
    BASE_URL = "https://fiduciaryinvestors.com.au"
    EVENTS_URL = "https://fiduciaryinvestors.com.au/symposium/"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        # This site typically lists 1-2 upcoming events
        cards = soup.select("article, .event, section.event, .symposium-item, main article")

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        # If no cards found, treat the page itself as one event
        if not events:
            event = self._parse_page(soup)
            if event:
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_page(self, soup) -> Optional[ScrapedEvent]:
        try:
            title_el = soup.select_one("h1, .page-title, .hero-title")
            name = title_el.get_text(strip=True) if title_el else "Fiduciary Investors Symposium"
            date_el = soup.select_one("time, [class*='date'], .event-date")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )
            desc_el = soup.select_one(".hero-text, .intro, p")
            description = desc_el.get_text(strip=True) if desc_el else (
                "Australia's leading institutional investment symposium. "
                "Attended by CIOs of major superannuation funds and institutional investors."
            )
            return ScrapedEvent(
                name=name,
                url=self.EVENTS_URL,
                source=self.source_name,
                organiser="Conexus Financial / Fiduciary Investors",
                event_type="conference",
                location="Sydney, Australia",
                city="Sydney",
                description=description,
                event_date=event_date,
                themes=[
                    "institutional investment", "superannuation", "asset management",
                    "pension", "Australia"
                ],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Page parse error: {e}")
            return None

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h1, h2, h3")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            if not name:
                return None
            date_el = card.select_one("time, [class*='date']")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )
            desc_el = card.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""
            return ScrapedEvent(
                name=name,
                url=self.EVENTS_URL,
                source=self.source_name,
                organiser="Fiduciary Investors",
                event_type="conference",
                location="Sydney, Australia",
                city="Sydney",
                description=description,
                event_date=event_date,
                themes=["institutional investment", "superannuation", "Australia"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card error: {e}")
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None


class InvestmentMagazineScraper(BaseEventScraper):
    """
    Investment Magazine — Australian institutional asset management events.
    """
    source_name = "investment_magazine"
    BASE_URL = "https://investmentmagazine.com.au"
    EVENTS_URL = "https://investmentmagazine.com.au/events/"

    async def scrape(self) -> list[ScrapedEvent]:
        soup = await self._get(self.EVENTS_URL)
        if not soup:
            return []

        events = []
        cards = soup.select("article, .event-item, [class*='event-card'], .post")

        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)

        logger.info(f"[{self.source_name}] Found {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[ScrapedEvent]:
        try:
            title_el = card.select_one("h2 a, h3 a, .entry-title a")
            if not title_el:
                return None
            name = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(self.BASE_URL, href) if href else self.EVENTS_URL

            date_el = card.select_one("time, .date, [class*='date']")
            event_date = self._parse_date(
                date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""
            )
            desc_el = card.select_one("p, .excerpt")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedEvent(
                name=name,
                url=url,
                source=self.source_name,
                organiser="Investment Magazine",
                event_type=self._infer_type(name),
                location="Sydney, Australia",
                city="Sydney",
                description=description,
                event_date=event_date,
                themes=["asset management", "institutional investment", "Australia"],
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error: {e}")
            return None

    def _infer_type(self, name: str) -> str:
        nl = name.lower()
        if "roundtable" in nl:
            return "roundtable"
        if "conference" in nl or "summit" in nl:
            return "conference"
        if "forum" in nl:
            return "forum"
        if "networking" in nl:
            return "networking"
        return "conference"

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text.strip()[:19], fmt)
            except ValueError:
                continue
        return None
