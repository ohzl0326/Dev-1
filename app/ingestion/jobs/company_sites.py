"""
Company career page scraper — directly scrapes SIMA member firm career pages
for London-based relationship management / client roles.

Strategy:
- Uses the curated URL list from config.SIMA_COMPANY_CAREERS
- Each URL is pre-configured to search for relevant roles in London
- Generic parser handles common ATS HTML patterns (Workday, Greenhouse,
  Lever, and direct career pages)
- Falls back to broad link scanning if structured selectors find nothing
- Filters results by checking for London in the location field
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.config import SIMA_COMPANY_CAREERS
from app.ingestion.base_scraper import BaseJobScraper, ScrapedJob

logger = logging.getLogger(__name__)

# Keywords that indicate a job is relevant (title-level check)
RELEVANT_TITLE_WORDS = [
    "relationship", "client", "institutional", "distribution", "sales",
    "coverage", "associate", "business development", "investor relations",
    "wholesale", "intermediary", "account manager", "consultant",
]

# London signals in location text
LONDON_SIGNALS = ["london", "uk", "united kingdom", "england", "ec", "wc", "e1", "sw", "se"]


def _is_london(location: str) -> bool:
    loc = location.lower()
    return any(sig in loc for sig in LONDON_SIGNALS)


def _is_relevant_title(title: str) -> bool:
    tl = title.lower()
    return any(w in tl for w in RELEVANT_TITLE_WORDS)


class CompanySitesScraper(BaseJobScraper):
    """
    Scrapes curated career page URLs for SIMA member firms.
    Each firm's URL is pre-parameterised to filter for London / relationship roles.
    """
    source_name = "company_sites"

    async def scrape(self) -> list[ScrapedJob]:
        all_jobs: list[ScrapedJob] = []
        seen: set[str] = set()

        for firm_name, url, ats_hint in SIMA_COMPANY_CAREERS:
            logger.info(f"[{self.source_name}] Scraping {firm_name}")
            try:
                jobs = await self._scrape_firm(firm_name, url, ats_hint)
                for job in jobs:
                    if job.fingerprint not in seen:
                        seen.add(job.fingerprint)
                        all_jobs.append(job)
                if jobs:
                    logger.info(f"[{self.source_name}] {firm_name}: {len(jobs)} jobs found")
            except Exception as e:
                logger.warning(f"[{self.source_name}] {firm_name} failed: {e}")
            # Extra delay between company sites to be respectful
            await asyncio.sleep(1.0)

        logger.info(f"[{self.source_name}] Total: {len(all_jobs)} jobs from company sites")
        return all_jobs

    async def _scrape_firm(self, firm_name: str, url: str, ats_hint: str) -> list[ScrapedJob]:
        soup = await self._get(url)
        if not soup:
            return []

        jobs = []

        if ats_hint == "workday":
            jobs = self._parse_workday(soup, firm_name, url)

        if not jobs:
            # Greenhouse pattern
            jobs = self._parse_greenhouse(soup, firm_name, url)

        if not jobs:
            # Lever pattern
            jobs = self._parse_lever(soup, firm_name, url)

        if not jobs:
            # Generic career page
            jobs = self._parse_generic(soup, firm_name, url)

        if not jobs:
            # Last resort: scan all links for job-like URLs
            jobs = self._parse_links(soup, firm_name, url)

        return jobs

    def _parse_workday(self, soup, firm_name: str, base_url: str) -> list[ScrapedJob]:
        jobs = []
        cards = soup.select(
            "li[class*='css-'][role='listitem'], "
            "[data-automation-id='jobFoundText'] + ul li, "
            "[class*='job-posting-card'], "
            "li[class*='WGST']"
        )
        for card in cards:
            job = self._parse_workday_card(card, firm_name, base_url)
            if job:
                jobs.append(job)
        return jobs

    def _parse_workday_card(self, card, firm_name: str, base_url: str) -> Optional[ScrapedJob]:
        try:
            title_el = card.select_one(
                "a[data-automation-id='jobPostingTitle'], "
                "a[class*='jobTitle'], "
                "h2 a, h3 a, a"
            )
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            if not _is_relevant_title(title):
                return None

            href = title_el.get("href", "")
            url = urljoin(base_url, href) if href else base_url

            loc_el = card.select_one(
                "[data-automation-id='locations'], "
                "[class*='location'], "
                ".jobLocation"
            )
            location = loc_el.get_text(strip=True) if loc_el else "London"
            if not _is_london(location) and location != "London":
                return None

            return ScrapedJob(
                title=title,
                company=firm_name,
                location=location,
                url=url,
                source=self.source_name,
            )
        except Exception:
            return None

    def _parse_greenhouse(self, soup, firm_name: str, base_url: str) -> list[ScrapedJob]:
        jobs = []
        # Greenhouse uses <div class="job"> or <section class="level-0"> patterns
        cards = soup.select(
            ".job, "
            "[class*='opening'], "
            "tr.job-post, "
            "li.job-post"
        )
        for card in cards:
            try:
                title_el = card.select_one("a, h3, .title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _is_relevant_title(title):
                    continue

                href = title_el.get("href", "") if title_el.name == "a" else ""
                url = urljoin(base_url, href) if href else base_url

                loc_el = card.select_one(".location, [class*='location']")
                location = loc_el.get_text(strip=True) if loc_el else "London"
                if not _is_london(location) and location != "London":
                    continue

                jobs.append(ScrapedJob(
                    title=title,
                    company=firm_name,
                    location=location,
                    url=url,
                    source=self.source_name,
                ))
            except Exception:
                continue
        return jobs

    def _parse_lever(self, soup, firm_name: str, base_url: str) -> list[ScrapedJob]:
        jobs = []
        # Lever uses <div class="posting"> with location as separate span
        cards = soup.select(".posting, [class*='posting-title']")
        for card in cards:
            try:
                title_el = card.select_one("h5, h4, h3, .posting-title, a[data-qa='posting-name']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not _is_relevant_title(title):
                    continue

                link_el = card.select_one("a[href*='lever.co'], a[href*='/apply']")
                href = link_el.get("href", "") if link_el else ""
                url = urljoin(base_url, href) if href else base_url

                loc_el = card.select_one(".location, [class*='location'], [data-qa='posting-location']")
                location = loc_el.get_text(strip=True) if loc_el else "London"
                if not _is_london(location) and location != "London":
                    continue

                jobs.append(ScrapedJob(
                    title=title,
                    company=firm_name,
                    location=location,
                    url=url,
                    source=self.source_name,
                ))
            except Exception:
                continue
        return jobs

    def _parse_generic(self, soup, firm_name: str, base_url: str) -> list[ScrapedJob]:
        jobs = []
        cards = soup.select(
            "li.job, "
            "article.job, "
            "[class*='job-card'], "
            "[class*='vacancy'], "
            "[class*='position'], "
            "[class*='opening'], "
            "tr[class*='job']"
        )
        for card in cards:
            try:
                title_el = card.select_one(
                    "h2 a, h3 a, h4 a, "
                    "[class*='title'] a, "
                    "[class*='job-title'] a, "
                    "a"
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or not _is_relevant_title(title):
                    continue

                href = title_el.get("href", "")
                url = urljoin(base_url, href) if href else base_url

                loc_el = card.select_one(
                    "[class*='location'], [class*='venue'], "
                    "[class*='city'], span.location"
                )
                location = loc_el.get_text(strip=True) if loc_el else "London"
                if not _is_london(location) and location != "London":
                    continue

                jobs.append(ScrapedJob(
                    title=title,
                    company=firm_name,
                    location=location,
                    url=url,
                    source=self.source_name,
                ))
            except Exception:
                continue
        return jobs

    def _parse_links(self, soup, firm_name: str, base_url: str) -> list[ScrapedJob]:
        """
        Last-resort: scan all anchor tags for job-like links containing
        relevant title words. Useful for bespoke career pages.
        """
        jobs = []
        seen_titles: set[str] = set()

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 5 or len(text) > 200:
                continue
            if not _is_relevant_title(text):
                continue
            if text in seen_titles:
                continue
            seen_titles.add(text)

            href = a.get("href", "")
            url = urljoin(base_url, href) if href else base_url

            # Try to find a sibling/parent location element
            parent = a.parent
            location = "London"
            if parent:
                loc_el = parent.find(
                    class_=re.compile(r"location|city|venue", re.I)
                )
                if loc_el:
                    location = loc_el.get_text(strip=True)

            jobs.append(ScrapedJob(
                title=text,
                company=firm_name,
                location=location,
                url=url,
                source=self.source_name,
            ))

        return jobs[:10]  # Cap at 10 per firm from link scan to avoid noise
