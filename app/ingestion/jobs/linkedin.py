"""
LinkedIn Jobs scraper — broad coverage, requires careful rate limiting.
Uses LinkedIn's public job search endpoint (no auth required for basic search).
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin, quote

from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com"


class LinkedInScraper(BaseJobScraper):
    source_name = "linkedin"

    # LinkedIn geo IDs
    GEO_IDS = {
        "Singapore": "102454443",
        "Sydney": "105995770",
    }

    SEARCH_CONFIGS = [
        {
            "keywords": "Institutional Relationship Manager Asset Management",
            "geo_id": GEO_IDS["Singapore"],
            "location_name": "Singapore",
        },
        {
            "keywords": "Relationship Manager Institutional Asset Management",
            "geo_id": GEO_IDS["Singapore"],
            "location_name": "Singapore",
        },
        {
            "keywords": "Institutional Relationship Manager Asset Management",
            "geo_id": GEO_IDS["Sydney"],
            "location_name": "Sydney",
        },
        {
            "keywords": "Client Relationship Manager Fund Management",
            "geo_id": GEO_IDS["Sydney"],
            "location_name": "Sydney",
        },
    ]

    # Experience level codes: 1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior, 5=Director
    EXPERIENCE_LEVELS = "3,4,5"  # Associate + Mid-Senior + Director

    async def scrape(self) -> list[ScrapedJob]:
        jobs = []
        seen: set[str] = set()

        for config in self.SEARCH_CONFIGS:
            logger.info(
                f"[{self.source_name}] Searching: '{config['keywords']}' in {config['location_name']}"
            )
            batch = await self._scrape_search(config)
            for job in batch:
                if job.fingerprint not in seen:
                    seen.add(job.fingerprint)
                    jobs.append(job)

        logger.info(f"[{self.source_name}] Total unique jobs: {len(jobs)}")
        return jobs

    async def _scrape_search(self, config: dict) -> list[ScrapedJob]:
        url = f"{BASE_URL}/jobs/search/"
        params = {
            "keywords": config["keywords"],
            "geoId": config["geo_id"],
            "f_E": self.EXPERIENCE_LEVELS,
            "f_TPR": "r2592000",  # Last 30 days
            "position": 1,
            "pageNum": 0,
            "start": 0,
        }

        soup = await self._get(url, params=params)
        if not soup:
            return []

        return self._parse_results(soup, config["location_name"])

    def _parse_results(self, soup, location_hint: str) -> list[ScrapedJob]:
        jobs = []

        # LinkedIn uses multiple possible selectors depending on version
        cards = soup.select(
            "li.jobs-search-results__list-item, "
            "div.job-search-card, "
            "li[class*='result'], "
            ".base-card"
        )

        for card in cards:
            job = self._parse_card(card, location_hint)
            if job:
                jobs.append(job)

        return jobs

    def _parse_card(self, card, location_hint: str) -> Optional[ScrapedJob]:
        try:
            # Title
            title_el = card.select_one(
                "h3.base-search-card__title, "
                "a.job-card-container__link, "
                ".base-card__full-link, "
                "h3 a, h4 a"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)

            # URL
            link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
            if not link_el:
                link_el = title_el
            href = link_el.get("href", "")
            # Strip tracking parameters
            url = href.split("?")[0] if "?" in href else href
            if not url.startswith("http"):
                url = urljoin(BASE_URL, url)

            # Company
            company_el = card.select_one(
                "h4.base-search-card__subtitle a, "
                ".job-card-container__company-name, "
                ".base-search-card__subtitle"
            )
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            # Location
            loc_el = card.select_one(
                ".job-search-card__location, "
                ".job-card-container__metadata-item, "
                ".base-search-card__metadata span"
            )
            location = loc_el.get_text(strip=True) if loc_el else location_hint

            # Date
            date_el = card.select_one("time")
            posted_date = None
            if date_el:
                datetime_attr = date_el.get("datetime", "")
                posted_date = self._parse_date(datetime_attr or date_el.get_text(strip=True))

            return ScrapedJob(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.source_name,
                posted_date=posted_date,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        text_lower = text.lower()
        now = datetime.utcnow()
        if "just" in text_lower or "now" in text_lower or "today" in text_lower:
            return now
        m = re.search(r"(\d+)\s*(minute|hour|day|week|month)", text_lower)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if "minute" in unit:
                return now - timedelta(minutes=n)
            if "hour" in unit:
                return now - timedelta(hours=n)
            if "day" in unit:
                return now - timedelta(days=n)
            if "week" in unit:
                return now - timedelta(weeks=n)
            if "month" in unit:
                return now - timedelta(days=n * 30)
        return None
