"""
Totaljobs.com scraper — major UK job board with strong London financial services coverage.
Uses HTML scraping of search results.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.totaljobs.com"


class JobsDBScraper(BaseJobScraper):
    """Renamed to TotalJobsScraper internally; kept as JobsDBScraper for import compatibility."""
    source_name = "totaljobs"

    SEARCH_CONFIGS = [
        {"keywords": "relationship manager asset management", "location": "London"},
        {"keywords": "institutional client manager", "location": "London"},
        {"keywords": "institutional sales investment management", "location": "London"},
        {"keywords": "associate relationship management", "location": "London"},
        {"keywords": "client coverage investment bank", "location": "London"},
        {"keywords": "fund distribution sales", "location": "London"},
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
        params = {
            "q": config["keywords"],
            "l": config["location"],
            "radius": "10",
            "s": "date",
        }
        soup = await self._get(f"{BASE_URL}/jobs", params=params)
        if not soup:
            return []

        return self._parse_results(soup, config["location"])

    def _parse_results(self, soup, location_hint: str) -> list[ScrapedJob]:
        jobs = []
        cards = soup.select(
            "article.job-ft, "
            "[class*='job-card'], "
            "[data-at='job-item'], "
            ".job-item"
        )
        for card in cards:
            job = self._parse_card(card, location_hint)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, card, location_hint: str) -> Optional[ScrapedJob]:
        try:
            title_el = card.select_one(
                "h2 a, h3 a, [data-at='job-title'] a, .job-title a, [class*='title'] a"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href) if href else ""
            if not url:
                return None

            company_el = card.select_one(
                "[data-at='job-item-company-name'], .company, [class*='company'], [class*='employer']"
            )
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            loc_el = card.select_one(
                "[data-at='job-item-location'], .location, [class*='location']"
            )
            location = loc_el.get_text(strip=True) if loc_el else location_hint

            salary_el = card.select_one(
                "[data-at='job-item-salary'], .salary, [class*='salary']"
            )
            salary_text = salary_el.get_text(strip=True) if salary_el else ""
            salary_min, salary_max = self._parse_salary(salary_text)

            date_el = card.select_one("time, [data-at='job-item-date'], .date, [class*='date']")
            posted_date = None
            if date_el:
                posted_date = self._parse_date(
                    date_el.get("datetime", "") or date_el.get_text(strip=True)
                )

            desc_el = card.select_one("p, .job-intro, [class*='description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            return ScrapedJob(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.source_name,
                description=description,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency="GBP",
                posted_date=posted_date,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Card parse error: {e}")
            return None

    def _parse_salary(self, text: str) -> tuple[Optional[int], Optional[int]]:
        if not text:
            return None, None
        numbers = re.findall(r"[\d,]+", text)
        cleaned = [int(n.replace(",", "")) for n in numbers if len(n.replace(",", "")) >= 4]
        if len(cleaned) >= 2:
            return min(cleaned), max(cleaned)
        if len(cleaned) == 1:
            return cleaned[0], None
        return None, None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        text_lower = text.lower()
        now = datetime.utcnow()
        if "today" in text_lower or "just" in text_lower:
            return now
        if "yesterday" in text_lower:
            return now - timedelta(days=1)
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
