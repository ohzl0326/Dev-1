"""
Matching engine — scores scraped jobs and events against the user's goal profile.

Scoring approach:
- Each factor contributes a weighted score (0.0–1.0)
- Final score is a weighted sum, clamped to [0.0, 1.0]
- Scores above JOB_CRITERIA['min_score_threshold'] are surfaced to the user

Job scoring weights:
  title_match    0.35  — role title is the strongest signal
  industry       0.20  — must be AM / banking / financial services
  location       0.25  — London is the target (high weight)
  seniority      0.15  — associate to director level
  description    0.05  — secondary keyword match in body

Event scoring weights:
  theme          0.40  — topic relevance to institutional AM / banking
  location       0.35  — London-first (higher weight than before)
  event_type     0.15  — networking / panel > webinar
  organiser      0.10  — known high-value organisers get a boost
"""
import re
from typing import Optional

from app.config import JOB_CRITERIA, EVENT_CRITERIA
from app.ingestion.base_scraper import ScrapedJob, ScrapedEvent


# ---------------------------------------------------------------------------
# JOB SCORER
# ---------------------------------------------------------------------------

class JobScorer:
    """Score a ScrapedJob against the user's job criteria."""

    WEIGHTS = {
        "title": 0.35,
        "industry": 0.20,
        "location": 0.25,
        "seniority": 0.15,
        "description": 0.05,
    }

    def score(self, job: ScrapedJob) -> tuple[float, dict]:
        """Return (final_score, breakdown_dict)."""
        breakdown = {
            "title": self._score_title(job.title),
            "industry": self._score_industry(job.title, job.description),
            "location": self._score_location(job.location),
            "seniority": self._score_seniority(job.title),
            "description": self._score_description(job.description),
        }
        final = sum(breakdown[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        final = round(min(max(final, 0.0), 1.0), 4)
        return final, breakdown

    def _score_title(self, title: str) -> float:
        tl = title.lower()
        # Primary: direct role match
        for kw in JOB_CRITERIA["role_keywords_primary"]:
            if kw.lower() in tl:
                return 1.0
        # Secondary: adjacent roles
        for kw in JOB_CRITERIA["role_keywords_secondary"]:
            if kw.lower() in tl:
                return 0.6
        # Partial: any single important word that suggests the right function
        partial_words = [
            "relationship", "institutional", "client", "distribution",
            "coverage", "sales", "wholesale", "intermediary",
        ]
        if any(w in tl for w in partial_words):
            return 0.35
        return 0.0

    def _score_industry(self, title: str, description: str) -> float:
        text = (title + " " + (description or "")).lower()
        matches = sum(1 for kw in JOB_CRITERIA["industry_keywords"] if kw in text)
        if matches >= 3:
            return 1.0
        if matches == 2:
            return 0.8
        if matches == 1:
            return 0.5
        # If no explicit industry keyword but job is from a company careers scraper,
        # give a neutral score rather than zero (company already filtered by sector)
        return 0.2

    def _score_location(self, location: str) -> float:
        loc_lower = location.lower()
        # Exact London targets
        for target in JOB_CRITERIA["locations"]:
            if target.lower() in loc_lower:
                return 1.0
        # UK outside London — still useful, partial credit
        if any(r in loc_lower for r in ["united kingdom", "uk", "england", "britain", "gb"]):
            return 0.7
        # EMEA / Europe — remote possibility
        if any(r in loc_lower for r in ["europe", "emea", "remote"]):
            return 0.4
        return 0.0

    def _score_seniority(self, title: str) -> float:
        tl = title.lower()
        # Hard exclude
        for excl in JOB_CRITERIA["seniority_exclude"]:
            if excl in tl:
                return 0.0
        # Match target seniority
        for incl in JOB_CRITERIA["seniority_include"]:
            if incl in tl:
                return 1.0
        # No seniority signal — neutral, don't penalise (many AM jobs omit levels)
        return 0.7

    def _score_description(self, description: str) -> float:
        if not description:
            return 0.4  # neutral: no info
        desc_lower = description.lower()
        positive = [
            "institutional", "asset management", "client relationship",
            "fund", "investment", "aum", "mandate", "portfolio",
            "private markets", "private equity", "alternatives",
            "london", "uk", "banking", "financial services",
            "wealth management", "relationship management",
        ]
        matches = sum(1 for kw in positive if kw in desc_lower)
        return min(matches / 5.0, 1.0)

    def infer_market_type(self, job: ScrapedJob) -> str:
        text = (job.title + " " + (job.description or "")).lower()
        if any(w in text for w in ["private equity", "private credit", "private markets",
                                    "private debt", "infrastructure", "real assets",
                                    "alternatives", "hedge fund"]):
            return "private"
        if any(w in text for w in ["equity", "fixed income", "bonds", "multi-asset",
                                    "listed", "public markets"]):
            return "public"
        return "multi-asset"


# ---------------------------------------------------------------------------
# EVENT SCORER
# ---------------------------------------------------------------------------

class EventScorer:
    """Score a ScrapedEvent against the user's event criteria."""

    WEIGHTS = {
        "theme": 0.40,
        "location": 0.35,
        "event_type": 0.15,
        "organiser": 0.10,
    }

    # Known high-value London AM/banking organisers
    HIGH_VALUE_ORGANISERS = {
        "cfa society uk", "cfa uk",
        "investment association", "the ia",
        "aima",
        "caia", "caia association",
        "pimfa",
        "aic", "association of investment companies",
        "institutional investor",
        "pere", "superreturn",
        "city of london",
        "financial times", "ft",
        "bloomberg",
        "the economist",
        "ipe", "investment & pensions europe",
    }

    TYPE_SCORES = {
        "networking": 1.0,
        "roundtable": 0.95,
        "panel": 0.85,
        "conference": 0.80,
        "forum": 0.80,
        "symposium": 0.80,
        "summit": 0.75,
        "workshop": 0.60,
        "webinar": 0.45,
        "seminar": 0.45,
        "other": 0.30,
    }

    def score(self, event: ScrapedEvent) -> tuple[float, float]:
        """Return (final_score, networking_value)."""
        theme_score = self._score_theme(event.name, event.description, event.themes or [])
        location_score = self._score_location(event.city, event.location, event.is_online)
        type_score = self.TYPE_SCORES.get(event.event_type or "other", 0.3)
        organiser_score = self._score_organiser(event.organiser, event.source)

        final = (
            theme_score * self.WEIGHTS["theme"]
            + location_score * self.WEIGHTS["location"]
            + type_score * self.WEIGHTS["event_type"]
            + organiser_score * self.WEIGHTS["organiser"]
        )
        final = round(min(max(final, 0.0), 1.0), 4)
        networking_value = round(type_score * location_score, 4)
        return final, networking_value

    def _score_theme(self, name: str, description: str, themes: list) -> float:
        text = (name + " " + (description or "") + " " + " ".join(themes)).lower()
        matches = sum(
            1 for kw in EVENT_CRITERIA["theme_keywords"]
            if kw.lower() in text
        )
        if matches >= 4:
            return 1.0
        if matches == 3:
            return 0.85
        if matches == 2:
            return 0.65
        if matches == 1:
            return 0.40
        return 0.0

    def _score_location(self, city: str, location: str, is_online: bool) -> float:
        combined = ((city or "") + " " + (location or "")).lower()
        # London is the target — full score
        if "london" in combined:
            return 1.0
        # Wider UK
        if any(w in combined for w in ["united kingdom", " uk", "england", "britain"]):
            return 0.75
        # EMEA / Europe — relevant but not primary
        if any(w in combined for w in ["europe", "emea"]):
            return 0.5
        # Online events — still valuable for content/networking
        if is_online or any(w in combined for w in ["online", "virtual"]):
            return 0.5
        return 0.1

    def _score_organiser(self, organiser: str, source: str) -> float:
        check = (organiser or "").lower() + " " + (source or "").lower()
        for hvo in self.HIGH_VALUE_ORGANISERS:
            if hvo in check:
                return 1.0
        return 0.4  # Unknown organiser — neutral


# ---------------------------------------------------------------------------
# Module-level convenience instances
# ---------------------------------------------------------------------------

job_scorer = JobScorer()
event_scorer = EventScorer()


def score_job(job: ScrapedJob) -> tuple[float, dict]:
    return job_scorer.score(job)


def score_event(event: ScrapedEvent) -> tuple[float, float]:
    return event_scorer.score(event)
