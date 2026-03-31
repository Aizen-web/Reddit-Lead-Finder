"""config.py — Search queries, scoring weights, and thresholds."""

# ── Reddit-wide search queries ──────────────────────────────────────
# We search ALL of Reddit (not specific subs) with buyer-focused queries.
# Each query is one HTTP request returning up to 100 results.
# These are written to find BUYERS, not sellers.
SEARCH_QUERIES = [
    # Direct buyer intent — someone explicitly needs a website built
    '"need a website" OR "need a new website" OR "build me a website"',
    '"looking for a web developer" OR "looking for a web designer" OR "hire web developer"',
    '"need a developer" website OR "need a designer" website',
    '"website redesign" OR "rebuild my website" OR "revamp my website" OR "redo my website"',
    # Specific platforms / types — strong commercial intent
    '"shopify store" need OR "wordpress website" need OR "ecommerce website" need OR "online store" build',
    '"landing page" need OR "business website" need OR "company website" build',
    # Frustration with existing site — hot leads
    '"fix my website" OR "website not working" OR "website is broken" OR "need help with my website"',
    '"website not converting" OR "need a better website" OR "website looks terrible" OR "website is outdated"',
    # Budget discussions — buyer mindset
    '"how much" website OR "budget" website developer OR "cost" "build a website"',
]

# ── Flair / title patterns that indicate a SELLER (not a buyer) ─────
# Posts matching these in the title are auto-rejected before scoring.
SELLER_TITLE_PATTERNS = [
    "[for hire]",
    "[selling]",
    "[offering]",
    "for hire",
    "i will build",
    "i'll build",
    "i will design",
    "i'll design",
    "i will create",
    "i'll create",
    "i can build",
    "i can design",
    "we build",
    "we design",
    "we create",
    "my services",
    "our services",
    "starting from $",
    "starting at $",
    "$/hr",
    "$/hour",
    "per hour",
    "available for work",
    "available for projects",
    "open for work",
    "open for projects",
    "portfolio included",
    "check out my portfolio",
    "dm me for",
    "here's what i offer",
    "build it for you",
    "build your website",
    "build your digital",
    "get your website",
    "need a website?",
    "want a website?",
    "looking for a website?",
    "websites starting",
    "affordable web",
    "web design services",
    "web development services",
    "introducing ",
    "welcome to r/",
]

# ── Scoring ─────────────────────────────────────────────────────────
# Keywords and their weights — higher = stronger buy signal.
# NOTE: "hire" and "hiring" removed — they trigger on sellers too.
# Instead we score on phrases that only a BUYER would write.

HIGH_INTENT_KEYWORDS = {
    # Buyer-only phrases specifically about web/websites (weight 8-10)
    "looking to hire": 8,
    "want to hire": 8,
    "need to hire": 8,
    "willing to pay": 6,
    "ready to pay": 6,
    "need a quote": 8,
    "send me a quote": 8,
    "looking for a developer": 7,
    "looking for a designer": 7,
    "looking for a web developer": 10,
    "looking for a web designer": 10,
    "need a developer": 7,
    "need a designer": 7,
    "need a web developer": 10,
    "need a web designer": 10,
    "can anyone recommend": 5,
    "who can build": 6,
    "who can help": 4,
    "recommendations for": 4,
    # Project scope — only a buyer describes these (weight 6-9)
    "need a website": 9,
    "need a new website": 10,
    "build my website": 9,
    "build me a website": 9,
    "build a website for": 8,
    "create a website": 7,
    "redesign my": 8,
    "rebuild my": 8,
    "revamp my": 8,
    "redo my website": 9,
    "need an online store": 8,
    "need an ecommerce": 8,
    "need a landing page": 8,
    "need a shopify": 8,
    "need a wordpress": 8,
    "business website": 6,
    "company website": 6,
    "fix my website": 8,
    "website is broken": 7,
    "website not working": 7,
    "website is down": 6,
    "website help": 5,
    # Budget / payment signals (weight 5-8)
    "my budget": 6,
    "budget is": 6,
    "budget of": 6,
    "how much does a website": 8,
    "how much for a website": 8,
    "cost of a website": 6,
    "how much should i pay": 6,
    # Frustration — person with a web problem (weight 5-7)
    "my website is terrible": 7,
    "my website is ugly": 7,
    "my website is outdated": 7,
    "website looks outdated": 6,
    "website is slow": 5,
    "website not converting": 7,
    "not getting leads": 5,
    "losing customers": 5,
    "need it asap": 5,
    "need it done": 5,
    "launch soon": 5,
}

# Phrases in the BODY that disqualify a post (seller / DIY / freebie)
NEGATIVE_KEYWORDS = [
    # Sellers / self-promotion
    "i am a web developer",
    "i'm a web developer",
    "i am a web designer",
    "i'm a web designer",
    "i'm a freelance",
    "i am a freelance",
    "i'm a full-stack",
    "i am a full-stack",
    "i'm a full stack",
    "i am a full stack",
    "i'm a software developer",
    "i'm a frontend",
    "i am a frontend",
    "i'm a front-end",
    "i am a front-end",
    "offering my services",
    "here's my portfolio",
    "here is my portfolio",
    "check out my work",
    "what i can build for you",
    "what i deliver",
    "what i do:",
    "dm me if you need",
    "reach out if you need",
    "available for hire",
    "open to freelance",
    "i run a small website development",
    "i run a web development",
    "i run a web design",
    "custom projects available",
    "fast delivery",
    "affordable price",
    "message me if you need",
    "starting from $",
    # Feedback / showcase (not buying)
    "portfolio review",
    "rate my website",
    "review my website",
    "feedback on my",
    "just finished building",
    "i built this",
    "just launched",
    "roast my",
    # Learning / tutorials
    "self-taught",
    "learning to code",
    "tutorial",
    "beginner question",
    "how do i learn",
    # No-budget signals
    "free website",
    "for free",
    "no budget",
    "$0",
    "volunteer",
    "pro bono",
    "open source",
    # Web dev agency / business owners asking for biz advice (not buyers)
    "getting clients",
    "how to get clients",
    "finding clients",
    "scale my agency",
    "grow my agency",
]

# Minimum score to consider a lead "hot"
MIN_SCORE_HOT = 20      # 🔥  Highly likely to pay
MIN_SCORE_WARM = 12     # 🟡  Worth reaching out
MIN_SCORE_COLD = 6      # ❄️   Low confidence — skip by default

# Maximum post age in hours (48 h = 2 days)
MAX_AGE_HOURS = 48

# How many results per search query (max 100 for Reddit's JSON)
RESULTS_PER_QUERY = 100

# ── Web-relevance gate ──────────────────────────────────────────────
# A post MUST contain at least one of these terms to be considered.
# This prevents scoring posts about concert tickets, hair advice, etc.
WEB_TERMS = [
    "website", "web site", "webpage", "web page", "web app",
    "webapp", "landing page", "online store", "ecommerce", "e-commerce",
    "shopify", "wordpress", "woocommerce", "squarespace", "wix",
    "webflow", "web developer", "web designer", "web design",
    "web development", "frontend", "front-end", "front end",
    "fullstack", "full-stack", "full stack", "html", "css",
    "react", "next.js", "nextjs", "web hosting", "domain name",
    "seo", "ui/ux", "ui ux", "responsive design",
]
