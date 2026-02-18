"""
eFinancialCareers scraper — best source for institutional AM roles in SG and AU.
Searches for RM / client management roles in Singapore and Sydney.
"""
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.config import JOB_SOURCES
from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

SOURCE = JOB_SOURCES["efinancialcareers"]
BASE_URL = SOURCE["base_url"]


class EFinancialCareersScraper(BaseJobScraper):
    source_name = "efinancialcareers"

    SEARCH_CONFIGS = [
        {
            "keywords": "relationship manager asset management",
            "location": "Singapore",
            "locationId": "242",  # Singapore location ID
        },
        {
            "keywords": "institutional client manager asset management",
            "location": "Singapore",
            "locationId": "242",
        },
        {
            "keywords": "relationship manager asset management",
            "location": "Sydney",
            "locationId": "36",  # Sydney location ID
        },
        {
            "keywords": "institutional client services asset management",
            "location": "Sydney",
            "locationId": "36",
        },
    ]

    async def scrape(self) -> list[ScrapedJob]:
        jobs = []
        seen_fingerprints: set[str] = set()

        for config in self.SEARCH_CONFIGS:
            logger.info(
                f"[{self.source_name}] Searching: {config['keywords']} in {config['location']}"
            )
            batch = await self._scrape_search(config)
            for job in batch:
                if job.fingerprint not in seen_fingerprints:
                    seen_fingerprints.add(job.fingerprint)
                    jobs.append(job)

        logger.info(f"[{self.source_name}] Total unique jobs found: {len(jobs)}")
        return jobs

    async def _scrape_search(self, config: dict) -> list[ScrapedJob]:
        """Scrape a single search result page."""
        params = {
            "q": config["keywords"],
            "location": config["location"],
            "locationId": config.get("locationId", ""),
            "page": 1,
            "pageSize": 25,
            "type": "permanent,contract",
        }

        soup = await self._get(f"{BASE_URL}/search", params=params)
        if not soup:
            return []

        jobs = []
        # eFinancialCareers job cards
        cards = soup.select("article.job-item, div.job-card, li[data-job-id]")

        if not cards:
            # Fallback: look for any job listing structure
            cards = soup.select("[class*='job'][class*='item'], [class*='jobCard']")

        for card in cards:
            job = self._parse_card(card, config["location"])
            if job:
                jobs.append(job)

        return jobs

    def _parse_card(self, card, location_hint: str) -> Optional[ScrapedJob]:
        try:
            # Title
            title_el = card.select_one(
                "a[data-test='job-title'], h2 a, h3 a, .job-title a, [class*='jobTitle'] a"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)

            # URL
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href) if href else ""
            if not url:
                return None

            # Company
            company_el = card.select_one(
                "[data-test='company-name'], .company-name, [class*='employer']"
            )
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            # Location
            loc_el = card.select_one(
                "[data-test='location'], .location, [class*='location']"
            )
            location = loc_el.get_text(strip=True) if loc_el else location_hint

            # Salary
            salary_el = card.select_one("[data-test='salary'], .salary, [class*='salary']")
            salary_text = salary_el.get_text(strip=True) if salary_el else ""
            salary_min, salary_max, currency = self._parse_salary(salary_text)

            # Posted date
            date_el = card.select_one("[data-test='date'], time, .date, [class*='date']")
            posted_date = None
            if date_el:
                posted_date = self._parse_date(
                    date_el.get("datetime", "") or date_el.get_text(strip=True)
                )

            # Description snippet
            desc_el = card.select_one(".description, [class*='description'], [class*='summary']")
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
                salary_currency=currency,
                posted_date=posted_date,
            )
        except Exception as e:
            logger.debug(f"[{self.source_name}] Error parsing card: {e}")
            return None

    def _parse_salary(self, text: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
        if not text:
            return None, None, None
        currency = "SGD" if "S$" in text or "SGD" in text else "AUD" if "A$" in text or "AUD" in text else "USD"
        numbers = re.findall(r"[\d,]+", text.replace(",", ""))
        cleaned = [int(n.replace(",", "")) for n in numbers if len(n) >= 4]
        if len(cleaned) >= 2:
            return min(cleaned), max(cleaned), currency
        if len(cleaned) == 1:
            return cleaned[0], None, currency
        return None, None, None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        # "X days ago" / "today" / "yesterday"
        text_lower = text.lower()
        now = datetime.utcnow()
        if "today" in text_lower or "just now" in text_lower:
            return now
        if "yesterday" in text_lower:
            from datetime import timedelta
            return now - timedelta(days=1)
        m = re.search(r"(\d+)\s+day", text_lower)
        if m:
            from datetime import timedelta
            return now - timedelta(days=int(m.group(1)))
        return None
