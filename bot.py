"""
bot.py — Reddit Lead Finder
Searches ALL of Reddit (no API key needed) for people looking to pay
for website help, then hands the CSV to Codex CLI to generate replies
and prune bad leads.

Strategy: 7 buyer-focused search queries across all of Reddit.
7 HTTP requests total → ~15 seconds.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from rich.console import Console

from config import (
    MAX_AGE_HOURS,
    MIN_SCORE_WARM,
    RESULTS_PER_QUERY,
    SEARCH_QUERIES,
    PAGES_PER_QUERY,
    LEAD_SUBREDDITS,
    POSTS_PER_SUBREDDIT,
)
from reply_generator import fill_replies_with_codex
from scorer import ScoredLead, score_post

# ── Setup ───────────────────────────────────────────────────────────
load_dotenv()
console = Console()

OUTPUT_DIR = Path("leads_output")
OUTPUT_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
})

REQUEST_DELAY = 2.0


# ── Search all of Reddit ────────────────────────────────────────────
def _fetch_json(url: str) -> list[dict]:
    """Fetch a single Reddit JSON listing page and return its children."""
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code == 429:
            console.print("  [dim red]⚠ Rate-limited, waiting 10s…[/]")
            time.sleep(10)
            resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            console.print(f"  [dim red]⚠ HTTP {resp.status_code}[/]")
            return []
        data = resp.json().get("data", {})
        return data.get("children", [])
    except requests.RequestException as exc:
        console.print(f"  [dim red]⚠ {exc}[/]")
        return []
    except (ValueError, KeyError):
        return []


def search_reddit(query: str) -> list[dict]:
    """Run a paginated search query against all of Reddit's public JSON.
    Fetches up to PAGES_PER_QUERY pages (100 results each)."""
    all_children: list[dict] = []
    after: str | None = None

    for page in range(PAGES_PER_QUERY):
        url = (
            f"https://www.reddit.com/search.json"
            f"?q={quote_plus(query)}&sort=new&t=week&type=link&limit={RESULTS_PER_QUERY}"
        )
        if after:
            url += f"&after={after}"

        children = _fetch_json(url)
        if not children:
            break

        all_children.extend(children)

        # Get the "after" cursor for the next page
        last_name = children[-1].get("data", {}).get("name")
        if not last_name:
            break
        after = last_name
        time.sleep(REQUEST_DELAY)

    return all_children


def fetch_subreddit_new(subreddit: str) -> list[dict]:
    """Pull the newest posts from a subreddit (no keyword search needed)."""
    url = (
        f"https://www.reddit.com/r/{subreddit}/new.json"
        f"?limit={POSTS_PER_SUBREDDIT}"
    )
    return _fetch_json(url)


def _process_post(post: dict, seen_ids: set[str], now: float) -> ScoredLead | None:
    """Score a single post dict. Returns a ScoredLead or None."""
    post_id = post.get("id", "")
    if post_id in seen_ids:
        return None
    seen_ids.add(post_id)

    created_utc = post.get("created_utc", 0)
    age_hours = (now - created_utc) / 3600
    if age_hours > MAX_AGE_HOURS:
        return None

    subreddit = post.get("subreddit", "unknown")
    permalink = post.get("permalink", "")
    lead = score_post(
        title=post.get("title", ""),
        body=post.get("selftext", ""),
        url=f"https://reddit.com{permalink}",
        subreddit=subreddit,
        author=post.get("author", "[deleted]"),
        reddit_score=post.get("score", 0),
        num_comments=post.get("num_comments", 0),
        created_utc=created_utc,
        age_hours=age_hours,
    )
    if lead and lead.lead_score >= MIN_SCORE_WARM:
        return lead
    return None


def run_full_scan() -> list[ScoredLead]:
    """Run all buyer-focused queries + scrape lead subreddits."""
    seen_ids: set[str] = set()
    all_leads: list[ScoredLead] = []
    now = time.time()
    total_posts = 0

    # ── Phase 1: Keyword search across all of Reddit (paginated) ────
    console.print("[bold]Phase 1:[/] Keyword search across all of Reddit\n")
    for i, query in enumerate(SEARCH_QUERIES, 1):
        short_q = query[:60] + ("…" if len(query) > 60 else "")
        console.print(f"  [dim][{i}/{len(SEARCH_QUERIES)}] {short_q}[/]")

        posts = search_reddit(query)
        for item in posts:
            post = item.get("data", {})
            total_posts += 1
            lead = _process_post(post, seen_ids, now)
            if lead:
                all_leads.append(lead)

        if i < len(SEARCH_QUERIES):
            time.sleep(REQUEST_DELAY)

    console.print(f"\n  [dim]Search phase: {total_posts} posts from {len(SEARCH_QUERIES)} queries[/]\n")

    # ── Phase 2: Scrape newest posts from known lead subreddits ─────
    console.print(f"[bold]Phase 2:[/] Scraping newest posts from {len(LEAD_SUBREDDITS)} subreddits\n")
    sub_posts = 0
    for i, sub in enumerate(LEAD_SUBREDDITS, 1):
        console.print(f"  [dim][{i}/{len(LEAD_SUBREDDITS)}] r/{sub}[/]")

        posts = fetch_subreddit_new(sub)
        for item in posts:
            post = item.get("data", {})
            sub_posts += 1
            lead = _process_post(post, seen_ids, now)
            if lead:
                all_leads.append(lead)

        if i < len(LEAD_SUBREDDITS):
            time.sleep(REQUEST_DELAY)

    total_posts += sub_posts
    console.print(f"\n  [dim]Subreddit phase: {sub_posts} posts from {len(LEAD_SUBREDDITS)} subreddits[/]")
    console.print(f"  [dim]Total scanned: {total_posts} posts[/]")

    # Deduplicate by URL and keep highest score
    best: dict[str, ScoredLead] = {}
    for lead in all_leads:
        if lead.url not in best or lead.lead_score > best[lead.url].lead_score:
            best[lead.url] = lead

    return sorted(best.values(), key=lambda l: l.lead_score, reverse=True)


# ── Output ──────────────────────────────────────────────────────────
def print_leads(leads: list[ScoredLead]) -> None:
    if not leads:
        console.print("\n[yellow]No qualifying leads found. Try again later.[/]")
        return

    hot = [l for l in leads if l.tier == "HOT"]
    warm = [l for l in leads if l.tier == "WARM"]

    console.print(f"\n[bold green]Found {len(leads)} leads[/]  "
                  f"(🔥 {len(hot)} hot · 🟡 {len(warm)} warm)\n")

    for lead in leads:
        icon = "🔥" if lead.tier == "HOT" else "🟡"
        tier_color = "red" if lead.tier == "HOT" else "yellow"

        # ── Header ──────────────────────────────────────────────────
        header = (
            f"{icon}  [bold {tier_color}]{lead.tier}[/] "
            f"(score {lead.lead_score})  ·  "
            f"r/{lead.subreddit}  ·  "
            f"{lead.age_hours:.0f}h ago  ·  "
            f"u/{lead.author}"
        )
        console.print(header)
        console.print(f"  [bold]{lead.title}[/]")
        console.print(f"  [dim]{lead.url}[/]")

        if lead.body:
            body_preview = lead.short_body
            console.print(f"  [dim italic]{body_preview}[/]\n")

        # ── Keywords matched ────────────────────────────────────────
        if lead.matched_keywords:
            kw = ", ".join(lead.matched_keywords)
            console.print(f"  [cyan]Keywords:[/] {kw}")

        console.print("─" * 80 + "\n")


def save_json(leads: list[ScoredLead]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUTPUT_DIR / f"leads_{ts}.json"
    
    data = []
    for lead in leads:
        data.append({
            "tier": lead.tier,
            "lead_score": lead.lead_score,
            "age_hours": lead.age_hours,
            "subreddit": lead.subreddit,
            "author": lead.author,
            "title": lead.title,
            "body_preview": lead.short_body,
            "keywords": lead.matched_keywords,
            "reddit_score": lead.score,
            "comments": lead.num_comments,
            "url": lead.url,
            "generated_reply": lead.generated_reply,
        })
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    return path


# ── Entrypoint ──────────────────────────────────────────────────────
def main() -> None:
    console.print("[bold cyan]━━━ Reddit Lead Finder ━━━[/]\n")
    console.print(f"Searching ALL of Reddit with {len(SEARCH_QUERIES)} queries × {PAGES_PER_QUERY} pages "
                  f"+ {len(LEAD_SUBREDDITS)} subreddits  (≤ {MAX_AGE_HOURS}h old)\n")

    leads = run_full_scan()

    print_leads(leads)

    if leads:
        # Step 1: Save JSON with empty generated_reply field
        json_path = save_json(leads)
        console.print(f"\n[green]✔ Saved {len(leads)} leads to {json_path}[/]")

        # Step 2: Hand the JSON to Codex CLI to fill in all replies at once
        success = fill_replies_with_codex(str(json_path.resolve()))
        if success:
            console.print(f"[green]✔ Replies written into {json_path}[/]")
        else:
            console.print(f"[yellow]JSON saved without replies. You can fill them in manually or re-run Codex:[/]")
            console.print(f'  [dim]codex -p "Fill the generated_reply key in {json_path.resolve()}"[/]')

    console.print()


if __name__ == "__main__":
    main()
