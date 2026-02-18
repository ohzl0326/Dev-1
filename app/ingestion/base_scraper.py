"""
Base scraper class with shared utilities: HTTP client, rate limiting,
deduplication, and Playwright support for JS-rendered pages.
"""
import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


class ScrapedJob:
    """Raw job data before scoring and persistence."""
    def __init__(
        self,
        title: str,
        company: str,
        location: str,
        url: str,
        source: str,
        description: str = "",
        requirements: str = "",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        salary_currency: Optional[str] = None,
        employment_type: Optional[str] = None,
        seniority_level: Optional[str] = None,
        posted_date: Optional[datetime] = None,
    ):
        self.title = title.strip()
        self.company = company.strip()
        self.location = location.strip()
        self.url = url.strip()
        self.source = source
        self.description = description
        self.requirements = requirements
        self.salary_min = salary_min
        self.salary_max = salary_max
        self.salary_currency = salary_currency
        self.employment_type = employment_type
        self.seniority_level = seniority_level
        self.posted_date = posted_date

    @property
    def fingerprint(self) -> str:
        """Deduplication key based on normalised title + company."""
        raw = f"{self.title.lower().strip()}{self.company.lower().strip()}{self.location.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()


class ScrapedEvent:
    """Raw event data before scoring and persistence."""
    def __init__(
        self,
        name: str,
        url: str,
        source: str,
        organiser: str = "",
        event_type: str = "",
        location: str = "",
        city: str = "",
        is_online: bool = False,
        description: str = "",
        speakers: Optional[list] = None,
        event_date: Optional[datetime] = None,
        event_end_date: Optional[datetime] = None,
        registration_deadline: Optional[datetime] = None,
        is_free: Optional[bool] = None,
        cost: Optional[str] = None,
    ):
        self.name = name.strip()
        self.url = url.strip()
        self.source = source
        self.organiser = organiser
        self.event_type = event_type
        self.location = location
        self.city = city
        self.is_online = is_online
        self.description = description
        self.speakers = speakers or []
        self.event_date = event_date
        self.event_end_date = event_end_date
        self.registration_deadline = registration_deadline
        self.is_free = is_free
        self.cost = cost

    @property
    def fingerprint(self) -> str:
        raw = f"{self.name.lower().strip()}{self.url.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()


class BaseJobScraper(ABC):
    """Abstract base for all job scrapers."""

    source_name: str = "unknown"

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str, params: Optional[dict] = None) -> Optional[BeautifulSoup]:
        """Fetch a URL and return parsed HTML. Respects rate limiting."""
        await asyncio.sleep(settings.request_delay_seconds)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except httpx.HTTPStatusError as e:
            logger.warning(f"[{self.source_name}] HTTP {e.response.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"[{self.source_name}] Error fetching {url}: {e}")
            return None

    async def _get_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Fetch a URL expecting JSON response."""
        await asyncio.sleep(settings.request_delay_seconds)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[{self.source_name}] Error fetching JSON from {url}: {e}")
            return None

    @abstractmethod
    async def scrape(self) -> list[ScrapedJob]:
        """Run the scraper and return a list of ScrapedJob objects."""
        ...


class BaseEventScraper(ABC):
    """Abstract base for all event scrapers."""

    source_name: str = "unknown"

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str, params: Optional[dict] = None) -> Optional[BeautifulSoup]:
        await asyncio.sleep(settings.request_delay_seconds)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.error(f"[{self.source_name}] Error fetching {url}: {e}")
            return None

    async def _get_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        await asyncio.sleep(settings.request_delay_seconds)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[{self.source_name}] Error fetching JSON from {url}: {e}")
            return None

    @abstractmethod
    async def scrape(self) -> list[ScrapedEvent]:
        """Run the scraper and return a list of ScrapedEvent objects."""
        ...
