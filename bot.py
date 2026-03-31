"""
bot.py — Reddit Lead Finder
Searches ALL of Reddit (no API key needed) for people looking to pay
for website help, then hands the CSV to Codex CLI to generate replies
and prune bad leads.

Strategy: 7 buyer-focused search queries across all of Reddit.
7 HTTP requests total → ~15 seconds.
"""

from __future__ import annotations

import csv
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
def search_reddit(query: str) -> list[dict]:
    """Run a single search query against all of Reddit's public JSON."""
    url = (
        f"https://www.reddit.com/search.json"
        f"?q={quote_plus(query)}&sort=new&t=week&type=link&limit={RESULTS_PER_QUERY}"
    )
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code == 429:
            console.print("  [dim red]⚠ Rate-limited, waiting 10s…[/]")
            time.sleep(10)
            resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            console.print(f"  [dim red]⚠ Search returned {resp.status_code}[/]")
            return []
        return resp.json().get("data", {}).get("children", [])
    except requests.RequestException as exc:
        console.print(f"  [dim red]⚠ {exc}[/]")
        return []
    except (ValueError, KeyError):
        return []


def run_full_scan() -> list[ScoredLead]:
    """Run all buyer-focused queries across all of Reddit."""
    seen_ids: set[str] = set()
    all_leads: list[ScoredLead] = []
    now = time.time()
    total_posts = 0

    for i, query in enumerate(SEARCH_QUERIES, 1):
        short_q = query[:60] + ("…" if len(query) > 60 else "")
        console.print(f"  [dim][{i}/{len(SEARCH_QUERIES)}] {short_q}[/]")

        posts = search_reddit(query)
        for item in posts:
            post = item.get("data", {})
            post_id = post.get("id", "")

            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)
            total_posts += 1

            created_utc = post.get("created_utc", 0)
            age_hours = (now - created_utc) / 3600
            if age_hours > MAX_AGE_HOURS:
                continue

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
                all_leads.append(lead)

        if i < len(SEARCH_QUERIES):
            time.sleep(REQUEST_DELAY)

    console.print(f"\n  [dim]Scanned {total_posts} posts from {len(SEARCH_QUERIES)} queries across all of Reddit[/]")

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


def save_csv(leads: list[ScoredLead]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUTPUT_DIR / f"leads_{ts}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "tier", "lead_score", "age_hours", "subreddit", "author",
            "title", "body_preview", "keywords", "reddit_score",
            "comments", "url", "generated_reply",
        ])
        for lead in leads:
            writer.writerow([
                lead.tier,
                lead.lead_score,
                lead.age_hours,
                lead.subreddit,
                lead.author,
                lead.title,
                lead.short_body,
                "; ".join(lead.matched_keywords),
                lead.score,
                lead.num_comments,
                lead.url,
                lead.generated_reply,
            ])
    return path


# ── Entrypoint ──────────────────────────────────────────────────────
def main() -> None:
    console.print("[bold cyan]━━━ Reddit Lead Finder ━━━[/]\n")
    console.print(f"Searching ALL of Reddit with {len(SEARCH_QUERIES)} buyer-focused queries "
                  f"(≤ {MAX_AGE_HOURS}h old)  —  no API key needed\n")

    leads = run_full_scan()

    print_leads(leads)

    if leads:
        # Step 1: Save CSV with empty generated_reply column
        csv_path = save_csv(leads)
        console.print(f"\n[green]✔ Saved {len(leads)} leads to {csv_path}[/]")

        # Step 2: Hand the CSV to Codex CLI to fill in all replies at once
        success = fill_replies_with_codex(str(csv_path.resolve()))
        if success:
            console.print(f"[green]✔ Replies written into {csv_path}[/]")
        else:
            console.print(f"[yellow]CSV saved without replies. You can fill them in manually or re-run Codex:[/]")
            console.print(f'  [dim]codex -p "Fill the generated_reply column in {csv_path.resolve()}"[/]')

    console.print()


if __name__ == "__main__":
    main()
