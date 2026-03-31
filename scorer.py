"""
scorer.py — Score and qualify Reddit posts as potential paid leads.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from config import (
    HIGH_INTENT_KEYWORDS,
    NEGATIVE_KEYWORDS,
    SELLER_TITLE_PATTERNS,
    WEB_TERMS,
    MIN_SCORE_HOT,
    MIN_SCORE_WARM,
)


@dataclass
class ScoredLead:
    title: str
    url: str
    subreddit: str
    author: str
    body: str
    score: int  # reddit upvotes
    num_comments: int
    created_utc: float
    age_hours: float
    lead_score: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    tier: str = ""  # HOT / WARM / COLD
    generated_reply: str = ""

    @property
    def short_body(self) -> str:
        """First 300 chars of body for display."""
        text = self.body.replace("\n", " ").strip()
        return text[:300] + ("…" if len(text) > 300 else "")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_seller_post(title_lower: str) -> bool:
    """Check if this post is someone OFFERING services, not looking to buy."""
    for pattern in SELLER_TITLE_PATTERNS:
        if pattern in title_lower:
            return True
    return False


def score_post(
    title: str,
    body: str,
    url: str,
    subreddit: str,
    author: str,
    reddit_score: int,
    num_comments: int,
    created_utc: float,
    age_hours: float,
) -> ScoredLead | None:
    """Return a ScoredLead or None if the post is disqualified."""

    title_lower = _normalize(title)
    body_lower = _normalize(body)
    combined = f"{title_lower} {body_lower}"

    # ── Reject seller / service-provider posts ──────────────────────
    if _is_seller_post(title_lower):
        return None

    # ── Web-relevance gate ──────────────────────────────────────────
    # The post MUST mention at least one web-related term.
    # This prevents scoring posts about concert tickets, yoga, etc.
    if not any(term in combined for term in WEB_TERMS):
        return None

    # ── Reject posts with [Hiring] flair that are actually hiring
    #    for non-web roles (content writers, marketers, etc.) ────────
    # (keep [Hiring] posts that mention website/web in title)
    if "[hiring]" in title_lower:
        web_terms = ("website", "web ", "ecommerce", "e-commerce", "shopify",
                     "wordpress", "frontend", "front-end", "fullstack", "full-stack")
        if not any(t in title_lower for t in web_terms):
            return None

    # ── Disqualify by body content ──────────────────────────────────
    for neg in NEGATIVE_KEYWORDS:
        if neg in combined:
            return None

    # ── Keyword scoring ─────────────────────────────────────────────
    lead_score = 0
    matched: list[str] = []

    for keyword, weight in HIGH_INTENT_KEYWORDS.items():
        if keyword in combined:
            lead_score += weight
            matched.append(keyword)

    # ── Engagement bonus ────────────────────────────────────────────
    if num_comments <= 5:
        lead_score += 3        # few replies → less competition
    if reddit_score >= 2:
        lead_score += 2        # some validation from community

    # ── Recency bonus ───────────────────────────────────────────────
    if age_hours <= 6:
        lead_score += 5        # very fresh
    elif age_hours <= 12:
        lead_score += 3
    elif age_hours <= 24:
        lead_score += 1

    # ── Subreddit quality bonus ─────────────────────────────────────
    buyer_subs = {"smallbusiness", "entrepreneur", "ecommerce", "growmybusiness",
                  "startups", "shopify", "squarespace", "wordpress", "woocommerce"}
    if subreddit.lower() in buyer_subs:
        lead_score += 4

    # ── Dollar amount mentioned → real budget ───────────────────────
    if re.search(r"\$\d{3,}", combined):  # $100+
        lead_score += 6

    # ── Tier assignment ─────────────────────────────────────────────
    if lead_score >= MIN_SCORE_HOT:
        tier = "HOT"
    elif lead_score >= MIN_SCORE_WARM:
        tier = "WARM"
    else:
        tier = "COLD"

    return ScoredLead(
        title=title,
        url=url,
        subreddit=subreddit,
        author=author,
        body=body,
        score=reddit_score,
        num_comments=num_comments,
        created_utc=created_utc,
        age_hours=round(age_hours, 1),
        lead_score=lead_score,
        matched_keywords=matched,
        tier=tier,
    )
