"""
Seek.com.au scraper — primary Australian job board for Sydney AM roles.
Uses Seek's JSON API endpoint where possible for reliability.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.seek.com.au"


class SeekScraper(BaseJobScraper):
    source_name = "seek"

    # Seek classification IDs for Finance / Asset Management
    CLASSIFICATION_IDS = {
        "banking_finance": "1200",  # Banking & Financial Services
        "investment": "6043",        # Fund Management / Investment
    }

    SEARCH_CONFIGS = [
        {
            "keywords": "relationship manager asset management",
            "location": "Sydney NSW 2000",
            "locationId": "3002",  # Sydney metro
        },
        {
            "keywords": "institutional client manager",
            "location": "Sydney NSW 2000",
            "locationId": "3002",
        },
        {
            "keywords": "institutional relationship manager",
            "location": "Sydney NSW 2000",
            "locationId": "3002",
        },
        {
            "keywords": "client relationship manager fund management",
            "location": "Sydney NSW 2000",
            "locationId": "3002",
        },
    ]

    async def scrape(self) -> list[ScrapedJob]:
        jobs = []
        seen: set[str] = set()

        for config in self.SEARCH_CONFIGS:
            logger.info(f"[{self.source_name}] Searching: {config['keywords']}")
            batch = await self._scrape_search(config)
            for job in batch:
                if job.fingerprint not in seen:
                    seen.add(job.fingerprint)
                    jobs.append(job)

        logger.info(f"[{self.source_name}] Total unique jobs: {len(jobs)}")
        return jobs

    async def _scrape_search(self, config: dict) -> list[ScrapedJob]:
        # Try the Seek API first (more reliable)
        api_url = "https://www.seek.com.au/api/chalice-search/v4/search"
        params = {
            "siteKey": "AU-Main",
            "sourcesystem": "houston",
            "userqueryid": "",
            "keywords": config["keywords"],
            "locationId": config.get("locationId", "3002"),
            "classification": self.CLASSIFICATION_IDS["banking_finance"],
            "pageSize": 22,
            "page": 1,
            "locale": "en-AU",
        }

        data = await self._get_json(api_url, params=params)
        if data and "data" in data:
            return self._parse_api_response(data["data"])

        # Fallback: HTML scraping
        soup = await self._get(f"{BASE_URL}/jobs", params={
            "keywords": config["keywords"],
            "location": config["location"],
            "classification": self.CLASSIFICATION_IDS["banking_finance"],
        })
        return self._parse_html(soup) if soup else []

    def _parse_api_response(self, listings: list) -> list[ScrapedJob]:
        jobs = []
        for item in listings:
            try:
                title = item.get("title", "")
                company = item.get("advertiser", {}).get("description", "Unknown")
                location_parts = [
                    item.get("suburb", ""),
                    item.get("area", ""),
                    item.get("state", ""),
                ]
                location = ", ".join(p for p in location_parts if p) or "Sydney"
                job_id = item.get("id", "")
                url = f"{BASE_URL}/job/{job_id}" if job_id else ""
                if not url or not title:
                    continue

                # Salary
                salary_min = item.get("salary", {}).get("minimum")
                salary_max = item.get("salary", {}).get("maximum")

                # Date
                posted_str = item.get("listingDate", "")
                posted_date = self._parse_iso_date(posted_str)

                description = item.get("teaser", "")

                jobs.append(ScrapedJob(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source=self.source_name,
                    description=description,
                    salary_min=int(salary_min) if salary_min else None,
                    salary_max=int(salary_max) if salary_max else None,
                    salary_currency="AUD",
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[{self.source_name}] Error parsing API item: {e}")
        return jobs

    def _parse_html(self, soup) -> list[ScrapedJob]:
        jobs = []
        cards = soup.select("article[data-card-type='JobCard'], [data-automation='normalJob']")
        for card in cards:
            job = self._parse_card(card)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, card) -> Optional[ScrapedJob]:
        try:
            title_el = card.select_one("[data-automation='jobTitle'] a, h1 a, h2 a")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href)

            company_el = card.select_one("[data-automation='jobCompany'], .company")
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            loc_el = card.select_one("[data-automation='jobLocation'], .location")
            location = loc_el.get_text(strip=True) if loc_el else "Sydney"

            listed_el = card.select_one("[data-automation='jobListingDate']")
            posted_date = self._parse_relative_date(
                listed_el.get_text(strip=True) if listed_el else ""
            )

            return ScrapedJob(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.source_name,
                salary_currency="AUD",
                posted_date=posted_date,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _parse_iso_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        text = text.lower().strip()
        now = datetime.utcnow()
        if not text or "just" in text or "today" in text:
            return now
        if "yesterday" in text:
            return now - timedelta(days=1)
        m = re.search(r"(\d+)\s*(d|day|hour|h|min|week|w|month|m)", text)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("h") or unit == "min":
                return now - timedelta(hours=n)
            if unit.startswith("d"):
                return now - timedelta(days=n)
            if unit.startswith("w"):
                return now - timedelta(weeks=n)
            if unit.startswith("m"):
                return now - timedelta(days=n * 30)
        return None
