"""
Central configuration: user goal profile, matching criteria, and app settings.
Edit this file to update your job search criteria, target roles, and event preferences.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://appuser:apppassword@db:5432/career_tracker",
        env="DATABASE_URL",
    )

    # --- Redis / Celery ---
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")

    # --- OpenAI ---
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")

    # --- Notifications ---
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, env="TELEGRAM_CHAT_ID")
    notify_email: Optional[str] = Field(default=None, env="NOTIFY_EMAIL")
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")

    # --- Scraping ---
    scrape_interval_hours: int = Field(default=12, env="SCRAPE_INTERVAL_HOURS")
    playwright_headless: bool = Field(default=True, env="PLAYWRIGHT_HEADLESS")
    request_delay_seconds: float = Field(default=2.0, env="REQUEST_DELAY_SECONDS")

    # --- App ---
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


# ---------------------------------------------------------------------------
# USER GOAL PROFILE
# ---------------------------------------------------------------------------
# This is the core configuration that drives all matching, scoring, and
# AI recommendations. Modify these values as your search evolves.
# ---------------------------------------------------------------------------

GOAL_PROFILE = {
    "name": "User",
    "current_role": "Institutional Client Onboarding Manager",
    "current_seniority": "Associate",
    "years_experience": 5,  # ~2 years investment analyst + ~3 years current role
    "background": [
        "Investment analyst, private markets fund investments, institutional clients",
        "Institutional client onboarding and relationship management",
        "Sub-fund setup, custodian and counterparty management",
        "Investment solution design and implementation",
        "Multi-stakeholder project management (internal teams + senior client contacts)",
    ],
    "target_deadline": "2026-09-30",  # End of Q3 2026
    "target_locations": ["Singapore", "Sydney", "Australia"],
    "target_industries": ["Asset Management", "Fund Management", "Investment Management"],
    "target_markets": ["Public Markets", "Private Markets", "Multi-Asset"],
}

# ---------------------------------------------------------------------------
# JOB MATCHING CRITERIA
# ---------------------------------------------------------------------------

JOB_CRITERIA = {
    # Primary role keywords — any of these in title = strong match
    "role_keywords_primary": [
        "Institutional Relationship Manager",
        "Relationship Manager",
        "Institutional Client Manager",
        "Client Relationship Manager",
        "Institutional Client Services",
        "Client Coverage",
        "Client Management",
    ],
    # Secondary keywords — broaden the net for adjacent roles
    "role_keywords_secondary": [
        "Business Development",
        "Client Solutions",
        "Institutional Sales",
        "Distribution",
        "Client Engagement",
        "Investment Consultant",
        "Client Director",
    ],
    # Must appear somewhere in description (industry filter)
    "industry_keywords": [
        "asset management",
        "asset manager",
        "fund management",
        "fund manager",
        "investment management",
        "investment manager",
        "institutional",
    ],
    # At least one target location must be present
    "locations": ["Singapore", "Sydney", "Australia", "NSW", "SG"],
    # Seniority filter: titles or levels to INCLUDE
    "seniority_include": [
        "associate",
        "analyst",
        "senior associate",
        "avp",
        "assistant vice president",
        "manager",
        "senior manager",
        "vice president",
    ],
    # Seniority filter: titles to EXCLUDE (too senior)
    "seniority_exclude": [
        "managing director",
        "md",
        "executive director",
        "head of",
        "chief",
        "ceo",
        "coo",
        "partner",
        "principal",
    ],
    # Minimum relevance score to surface a job (0.0–1.0)
    "min_score_threshold": 0.45,
}

# ---------------------------------------------------------------------------
# JOB SOURCES
# ---------------------------------------------------------------------------

JOB_SOURCES = {
    "efinancialcareers": {
        "enabled": True,
        "base_url": "https://www.efinancialcareers.com",
        "search_url": "https://www.efinancialcareers.com/search",
        "description": "Primary source for institutional AM roles globally",
        "locations": ["Singapore", "Sydney"],
        "keywords": ["relationship manager", "institutional client", "asset management"],
    },
    "seek": {
        "enabled": True,
        "base_url": "https://www.seek.com.au",
        "search_url": "https://www.seek.com.au/jobs",
        "description": "Primary Australian job board",
        "locations": ["Sydney NSW"],
        "keywords": ["relationship manager", "asset management", "institutional"],
    },
    "jobsdb": {
        "enabled": True,
        "base_url": "https://sg.jobsdb.com",
        "search_url": "https://sg.jobsdb.com/jobs",
        "description": "Primary Singapore job board",
        "locations": ["Singapore"],
        "keywords": ["relationship manager", "asset management", "institutional"],
    },
    "linkedin": {
        "enabled": True,
        "base_url": "https://www.linkedin.com",
        "search_url": "https://www.linkedin.com/jobs/search",
        "description": "LinkedIn Jobs — broad coverage",
        "locations": ["Singapore", "Sydney, New South Wales, Australia"],
        "keywords": ["institutional relationship manager", "client relationship asset management"],
    },
    "cfa_institute": {
        "enabled": True,
        "base_url": "https://www.cfainstitute.org",
        "search_url": "https://careers.cfainstitute.org/jobs",
        "description": "CFA Institute career board — finance-specific",
        "locations": ["Singapore", "Sydney"],
        "keywords": ["relationship manager", "client management"],
    },
}

# ---------------------------------------------------------------------------
# EVENT MATCHING CRITERIA
# ---------------------------------------------------------------------------

EVENT_CRITERIA = {
    # Event types to actively track
    "types_include": [
        "networking",
        "panel",
        "conference",
        "roundtable",
        "forum",
        "symposium",
        "summit",
        "webinar",
        "workshop",
    ],
    # Theme keywords — events must relate to one of these
    "theme_keywords": [
        # Industry / product
        "asset management",
        "investment management",
        "fund management",
        "institutional investor",
        "institutional investment",
        "private markets",
        "private equity",
        "private credit",
        "alternatives",
        "multi-asset",
        "public markets",
        # Functional / strategic
        "client trends",
        "product trends",
        "distribution",
        "investor relations",
        "wealth management",
        "endowment",
        "sovereign wealth",
        "pension",
        "superannuation",
        # Geo focus
        "Asia Pacific",
        "APAC",
        "Australia",
        "Singapore",
    ],
    "locations": ["Singapore", "Sydney", "Australia", "Online", "Virtual", "APAC"],
    # Minimum relevance score to surface an event
    "min_score_threshold": 0.40,
}

# ---------------------------------------------------------------------------
# EVENT SOURCES
# ---------------------------------------------------------------------------

EVENT_SOURCES = {
    "cfa_singapore": {
        "enabled": True,
        "url": "https://cfasingapore.org.sg/events/",
        "description": "CFA Society Singapore — premier networking for AM professionals",
        "location": "Singapore",
    },
    "cfa_australia": {
        "enabled": True,
        "url": "https://www.cfasociety.org/sydney/Pages/Events.aspx",
        "description": "CFA Society Sydney — AM networking and CPD",
        "location": "Sydney",
    },
    "caia": {
        "enabled": True,
        "url": "https://caia.org/events",
        "description": "CAIA Association — alternatives / private markets focus",
        "location": "Global/APAC",
    },
    "aima": {
        "enabled": True,
        "url": "https://www.aima.org/events.html",
        "description": "AIMA — alternatives and hedge fund industry",
        "location": "Singapore/Global",
    },
    "conexus": {
        "enabled": True,
        "url": "https://conexusfinancial.com.au/events/",
        "description": "Conexus Financial — institutional investment events in Australia",
        "location": "Sydney",
    },
    "investment_magazine": {
        "enabled": True,
        "url": "https://investmentmagazine.com.au/events/",
        "description": "Investment Magazine — Australian institutional AM events",
        "location": "Sydney",
    },
    "asian_investor": {
        "enabled": True,
        "url": "https://www.asianinvestor.net/events",
        "description": "AsianInvestor — institutional AM events across Asia",
        "location": "Singapore/APAC",
    },
    "asifma": {
        "enabled": True,
        "url": "https://www.asifma.org/events/",
        "description": "ASIFMA — Asia financial markets association events",
        "location": "Singapore",
    },
    "fiduciary_investors": {
        "enabled": True,
        "url": "https://fiduciaryinvestors.com.au/symposium/",
        "description": "Fiduciary Investors Symposium — top-tier Australian pension/AM event",
        "location": "Sydney",
    },
    "pere": {
        "enabled": True,
        "url": "https://www.perenews.com/events/",
        "description": "PERE — private equity real estate conferences",
        "location": "Global/APAC",
    },
    "superreturn": {
        "enabled": True,
        "url": "https://informaconnect.com/superreturn-international/",
        "description": "SuperReturn — private equity and private credit",
        "location": "Global",
    },
    "eventbrite_finance": {
        "enabled": True,
        "url": "https://www.eventbrite.com",
        "description": "Eventbrite finance/investment events in target cities",
        "location": "Singapore/Sydney",
    },
}
