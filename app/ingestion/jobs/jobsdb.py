"""
JobsDB Singapore scraper — primary Singapore job board.
Uses JobsDB/SEEK API (same parent company, similar API structure).
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://sg.jobsdb.com"


class JobsDBScraper(BaseJobScraper):
    source_name = "jobsdb"

    SEARCH_CONFIGS = [
        {"keywords": "relationship manager asset management", "location": "Singapore"},
        {"keywords": "institutional client manager", "location": "Singapore"},
        {"keywords": "institutional relationship manager", "location": "Singapore"},
        {"keywords": "client coverage asset management", "location": "Singapore"},
        {"keywords": "business development asset manager", "location": "Singapore"},
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
        # JobsDB uses a GraphQL-based API
        api_url = "https://xapi.supercharge-srp.co/job-search/graphql"
        headers = {
            "Content-Type": "application/json",
            "X-Site-Url": "https://sg.jobsdb.com",
        }
        query = """
        query getJobs($keyword: String, $locationId: String, $pageSize: Int) {
          jobs(
            keyword: $keyword
            locationId: $locationId
            pageSize: $pageSize
            jobFunctionIds: ["bank-fin-svc"]
          ) {
            total
            jobs {
              id
              title
              advertiser { description }
              location { label }
              workTypes { label }
              salary { label minimum maximum }
              listingDate
              teaser
              url
            }
          }
        }
        """
        payload = {
            "query": query,
            "variables": {
                "keyword": config["keywords"],
                "locationId": "DB-SG-3a53c66e-3468-11e1-8513-000000000000",  # Singapore
                "pageSize": 20,
            },
        }

        try:
            resp = await self._client.post(api_url, json=payload, headers=headers)
            data = resp.json()
            listings = data.get("data", {}).get("jobs", {}).get("jobs", [])
            if listings:
                return self._parse_graphql_response(listings)
        except Exception as e:
            logger.warning(f"[{self.source_name}] GraphQL failed: {e}, falling back to HTML")

        # Fallback to HTML scraping
        params = {
            "q": config["keywords"],
            "l": "Singapore",
            "sp": "salary",
        }
        soup = await self._get(f"{BASE_URL}/jobs-in-banking-financial-services", params=params)
        return self._parse_html(soup) if soup else []

    def _parse_graphql_response(self, listings: list) -> list[ScrapedJob]:
        jobs = []
        for item in listings:
            try:
                title = item.get("title", "")
                company = item.get("advertiser", {}).get("description", "Unknown")
                location = item.get("location", {}).get("label", "Singapore")
                url = item.get("url", "")
                if not url:
                    job_id = item.get("id", "")
                    url = f"{BASE_URL}/job/{job_id}" if job_id else ""
                if not title or not url:
                    continue

                salary = item.get("salary", {}) or {}
                salary_min = salary.get("minimum")
                salary_max = salary.get("maximum")

                posted_str = item.get("listingDate", "")
                posted_date = self._parse_date(posted_str)
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
                    salary_currency="SGD",
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[{self.source_name}] Parse error: {e}")
        return jobs

    def _parse_html(self, soup) -> list[ScrapedJob]:
        jobs = []
        cards = soup.select("article, [data-job-id], [class*='job-card'], [class*='jobCard']")
        for card in cards:
            try:
                title_el = card.select_one("h1 a, h2 a, h3 a, [class*='title'] a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                url = urljoin(BASE_URL, href)
                company_el = card.select_one("[class*='company'], [class*='employer']")
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                jobs.append(ScrapedJob(
                    title=title,
                    company=company,
                    location="Singapore",
                    url=url,
                    source=self.source_name,
                    salary_currency="SGD",
                ))
            except Exception as e:
                logger.debug(f"[{self.source_name}] HTML card error: {e}")
        return jobs

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        text_lower = text.lower()
        now = datetime.utcnow()
        if "today" in text_lower or "just" in text_lower:
            return now
        m = re.search(r"(\d+)\s*(day|hour|week|month)", text_lower)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if "hour" in unit:
                return now - timedelta(hours=n)
            if "day" in unit:
                return now - timedelta(days=n)
            if "week" in unit:
                return now - timedelta(weeks=n)
            if "month" in unit:
                return now - timedelta(days=n * 30)
        return None
