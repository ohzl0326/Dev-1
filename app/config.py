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

GOAL_PROFILE = {
    "name": "User",
    "current_role": "Institutional Client Onboarding Manager",
    "current_seniority": "Associate",
    "years_experience": 5,
    "background": [
        "Investment analyst, private markets fund investments, institutional clients",
        "Institutional client onboarding and relationship management",
        "Sub-fund setup, custodian and counterparty management",
        "Investment solution design and implementation",
        "Multi-stakeholder project management (internal teams + senior client contacts)",
    ],
    "target_deadline": "2026-09-30",
    "target_locations": ["London", "United Kingdom"],
    "target_industries": ["Asset Management", "Fund Management", "Investment Management", "Banking"],
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
        "Client Services",
        "Investor Relations",
        "Client Solutions",
        "Client Director",
    ],
    # Secondary keywords — broader net for adjacent / ambiguously titled roles
    "role_keywords_secondary": [
        "Business Development",
        "Institutional Sales",
        "Distribution",
        "Client Engagement",
        "Investment Consultant",
        "Account Manager",
        "Account Management",
        "Sales Manager",
        "Coverage",
        "Institutional",
        "Fund Distribution",
        "Wholesale",
        "Intermediary",
        "Sales Associate",
        "Associate",       # catches "Associate, Relationship Management" etc.
        "Relationship",    # catches "Relationship" in broader sales/RM team titles
    ],
    # Industry filter — at least one must appear in title or description
    "industry_keywords": [
        "asset management",
        "asset manager",
        "fund management",
        "fund manager",
        "investment management",
        "investment manager",
        "institutional",
        "wealth management",
        "banking",
        "investment bank",
        "private bank",
        "financial services",
    ],
    # Target locations
    "locations": ["London", "United Kingdom", "UK", "England", "City of London", "Canary Wharf"],
    # Seniority to INCLUDE
    "seniority_include": [
        "associate",
        "analyst",
        "senior associate",
        "avp",
        "assistant vice president",
        "manager",
        "senior manager",
        "vice president",
        "vp",
        "director",          # include director level — common AM band
    ],
    # Seniority to EXCLUDE (too senior / irrelevant)
    "seniority_exclude": [
        "managing director",
        "md",
        "chief",
        "ceo",
        "coo",
        "cfo",
        "cio",
        "partner",
        "graduate",
        "intern",
        "internship",
    ],
    # Minimum relevance score to surface a job (relaxed)
    "min_score_threshold": 0.35,
}

# ---------------------------------------------------------------------------
# JOB SOURCES
# ---------------------------------------------------------------------------

JOB_SOURCES = {
    "efinancialcareers": {
        "enabled": True,
        "base_url": "https://www.efinancialcareers.co.uk",
        "search_url": "https://www.efinancialcareers.co.uk/search",
        "description": "Primary source for institutional AM / banking roles in London",
        "locations": ["London"],
        "keywords": ["relationship manager", "institutional client", "asset management"],
    },
    "reed": {
        "enabled": True,
        "base_url": "https://www.reed.co.uk",
        "search_url": "https://www.reed.co.uk/jobs",
        "description": "UK's largest job board — broad London coverage",
        "locations": ["London"],
        "keywords": ["relationship manager", "asset management", "institutional"],
    },
    "totaljobs": {
        "enabled": True,
        "base_url": "https://www.totaljobs.com",
        "search_url": "https://www.totaljobs.com/jobs",
        "description": "Major UK job board",
        "locations": ["London"],
        "keywords": ["relationship manager", "asset management", "institutional"],
    },
    "linkedin": {
        "enabled": True,
        "base_url": "https://www.linkedin.com",
        "search_url": "https://www.linkedin.com/jobs/search",
        "description": "LinkedIn Jobs — broad coverage",
        "locations": ["London, United Kingdom"],
        "keywords": ["institutional relationship manager", "client relationship asset management"],
    },
    "company_sites": {
        "enabled": True,
        "description": "Direct scraping of SIMA member firm career pages for London roles",
    },
}

# ---------------------------------------------------------------------------
# SIMA MEMBER FIRMS — career page URLs for London scraping
# ---------------------------------------------------------------------------
# These are global asset managers that are Singapore IM Association members
# but all have significant London offices / European operations.

SIMA_COMPANY_CAREERS = [
    # Firm name, careers page URL, ATS hint
    ("Aberdeen Investments", "https://careers.aberdeengroup.com/search?q=relationship+manager&location=London", "workday"),
    ("AllianceBernstein", "https://careers.alliancebernstein.com/search/?q=relationship+manager&locationsearch=London", "workday"),
    ("Allianz Global Investors", "https://www.allianzgi.com/en/careers", "generic"),
    ("Amundi", "https://jobs.amundi.com/search/?q=relationship+manager&locationsearch=London", "workday"),
    ("AXA Investment Managers", "https://careers.axa-im.com/search/?q=relationship&locationsearch=London", "workday"),
    ("BlackRock", "https://careers.blackrock.com/job-search-results/?keyword=relationship+manager&location=London&country=United+Kingdom", "workday"),
    ("BNP Paribas Asset Management", "https://group.bnpparibas/en/careers/job-offers?location=London", "generic"),
    ("BNY Mellon Investment Management", "https://bnymellon.eightfold.ai/careers?query=relationship+manager&location=London", "generic"),
    ("Capital Group", "https://careers.capitalgroup.com/search/?q=relationship&locationsearch=London", "workday"),
    ("DWS", "https://careers.dws.com/search/?q=relationship+manager&locationsearch=London", "workday"),
    ("Eastspring Investments", "https://www.eastspring.com/about-us/careers", "generic"),
    ("Federated Hermes", "https://www.hermes-investment.com/ukw/about-us/careers/", "generic"),
    ("FIL Investment Management", "https://jobs.fil.com/search/?q=relationship&locationsearch=London", "workday"),
    ("First Sentier Investors", "https://www.firstsentierinvestors.com/uk/en/individual/about-us/careers.html", "generic"),
    ("Goldman Sachs Asset Management", "https://www.goldmansachs.com/careers/search#q=asset+management&location=London", "generic"),
    ("HSBC Global Asset Management", "https://www.hsbc.com/careers/jobs?q=relationship+manager&location=London", "generic"),
    ("Invesco", "https://careers.invesco.com/search/?q=relationship+manager&locationsearch=London", "workday"),
    ("Janus Henderson Investors", "https://careers.janushenderson.com/search/?q=relationship&locationsearch=London", "workday"),
    ("JPMorgan Asset Management", "https://careers.jpmorgan.com/us/en/jobs/search?q=relationship+manager&location=London", "workday"),
    ("Lazard Asset Management", "https://lazard.wd1.myworkdayjobs.com/en-US/LazardCareers/jobs?q=relationship&locations=London", "workday"),
    ("M&G Investments", "https://careers.mandg.com/search/?q=relationship+manager&locationsearch=London", "workday"),
    ("Manulife Investment Management", "https://manulife.wd3.myworkdayjobs.com/en-US/manulife_careers/jobs?q=relationship&locations=London", "workday"),
    ("Morgan Stanley Investment Management", "https://www.morganstanley.com/careers/career-opportunities-search#q=relationship+manager&location=London", "generic"),
    ("Neuberger Berman", "https://www.nb.com/pages/public/en-us/about-us/careers.aspx", "generic"),
    ("Ninety One", "https://www.ninetyone.com/en/about-us/careers", "generic"),
    ("Nordea Asset Management", "https://www.nordea.com/en/careers", "generic"),
    ("PGIM", "https://pgim.wd1.myworkdayjobs.com/en-US/pgim/jobs?q=relationship&locations=London", "workday"),
    ("Pictet Asset Management", "https://careers.group.pictet/search/?q=relationship&locationsearch=London", "workday"),
    ("PIMCO", "https://pimco.wd1.myworkdayjobs.com/en-US/PIMCO_Careers/jobs?q=relationship&locations=London", "workday"),
    ("Principal Asset Management", "https://careers.principal.com/search/?q=relationship&locationsearch=London", "workday"),
    ("Robeco", "https://careers.robeco.com/vacancies/?query=relationship+manager&location=London", "generic"),
    ("Schroders", "https://www.schroders.com/en/global/individual/our-firm/careers/", "generic"),
    ("State Street Global Advisors", "https://statestreet.wd1.myworkdayjobs.com/en-US/External/jobs?q=relationship&locations=London", "workday"),
    ("T. Rowe Price", "https://troweprice.wd5.myworkdayjobs.com/en-US/TRP_Careers/jobs?q=relationship&locations=London", "workday"),
    ("UBS Asset Management", "https://jobs.ubs.com/TGWebHost/home.aspx?partnerid=25008", "generic"),
    ("Wellington Management", "https://wellington.wd5.myworkdayjobs.com/en-US/Wellington_Careers/jobs?q=relationship&locations=London", "workday"),
    ("Western Asset Management", "https://jobs.westernasset.com/search/?q=relationship&locationsearch=London", "workday"),
    ("Vontobel", "https://www.vontobel.com/en/careers/", "generic"),
    ("William Blair", "https://williamblair.wd1.myworkdayjobs.com/en-US/WilliamBlair/jobs?q=relationship&locations=London", "workday"),
]

# ---------------------------------------------------------------------------
# EVENT MATCHING CRITERIA
# ---------------------------------------------------------------------------

EVENT_CRITERIA = {
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
    # Theme keywords — event must relate to at least one
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
        "fixed income",
        "equities",
        "hedge fund",
        # Functional / strategic
        "client relations",
        "distribution",
        "investor relations",
        "wealth management",
        "endowment",
        "sovereign wealth",
        "pension",
        "banking",
        "financial services",
        "capital markets",
        "securities",
        # Geo focus
        "London",
        "United Kingdom",
        "UK",
        "EMEA",
        "Europe",
    ],
    "locations": ["London", "United Kingdom", "UK", "Online", "Virtual", "EMEA"],
    # Minimum relevance score
    "min_score_threshold": 0.35,
}

# ---------------------------------------------------------------------------
# EVENT SOURCES
# ---------------------------------------------------------------------------

EVENT_SOURCES = {
    "cfa_uk": {
        "enabled": True,
        "url": "https://www.cfauk.org/events",
        "description": "CFA Society UK — premier networking for AM professionals in London",
        "location": "London",
    },
    "investment_association": {
        "enabled": True,
        "url": "https://www.theia.org/events",
        "description": "Investment Association — UK asset management industry body events",
        "location": "London",
    },
    "aima": {
        "enabled": True,
        "url": "https://www.aima.org/events.html",
        "description": "AIMA — alternatives and hedge fund industry events",
        "location": "London/Global",
    },
    "pimfa": {
        "enabled": True,
        "url": "https://www.pimfa.co.uk/events/",
        "description": "PIMFA — Personal Investment Management & Financial Advice Association",
        "location": "London",
    },
    "aic": {
        "enabled": True,
        "url": "https://www.theaic.co.uk/events",
        "description": "Association of Investment Companies — London events",
        "location": "London",
    },
    "institutional_investor": {
        "enabled": True,
        "url": "https://www.institutionalinvestor.com/events",
        "description": "Institutional Investor — global AM conferences, London focus",
        "location": "London/Global",
    },
    "caia_uk": {
        "enabled": True,
        "url": "https://caia.org/events",
        "description": "CAIA — alternatives / private markets, filter for London/UK",
        "location": "London/Global",
    },
    "eventbrite_london": {
        "enabled": True,
        "url": "https://www.eventbrite.co.uk",
        "description": "Eventbrite London finance/investment networking events",
        "location": "London",
    },
}
