# Reddit Lead Finder 🔥

Automatically scans Reddit for people **actively looking to pay** for website design/development help. Returns scored, tiered leads from the last 48 hours.

## How It Works

1. **Searches 21 subreddits** (r/smallbusiness, r/forhire, r/Entrepreneur, etc.) across 30+ intent-based queries
2. **Scores every post** using weighted keyword matching — "willing to pay", "hire", "budget", dollar amounts, urgency signals
3. **Filters out noise** — self-promoters, learners, people wanting free work
4. **Ranks leads** as 🔥 HOT (very likely to pay) or 🟡 WARM (worth reaching out)
5. **Exports to CSV** for easy tracking

---

## Quick Start

### 1. Get Reddit API Credentials (free, takes 2 minutes)

1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"create another app…"**
3. Choose **"script"** as the type
4. Set redirect URI to `http://localhost:8080`
5. Copy the **client ID** (under the app name) and **secret**

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your credentials:

```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=LeadFinder/1.0 by YourRedditUsername
```

### 3. Install & Run

```bash
pip install -r requirements.txt
python bot.py
```

---

## Output

The bot prints a color-coded table in your terminal:

| Tier | Score | Age | Subreddit       | Title                              | Keywords              |
|------|-------|-----|-----------------|------------------------------------|-----------------------|
| 🔥   | 34    | 2h  | r/smallbusiness | Need someone to build my website   | hire, budget, new website |
| 🟡   | 16    | 18h | r/Entrepreneur  | Website redesign recommendations?  | redesign, business website |

Results are also saved to `leads_output/leads_YYYY-MM-DD_HHMM.csv`.

---

## Tuning

All settings live in `config.py`:

| Setting | What it does |
|---------|-------------|
| `SUBREDDITS` | List of subreddits to scan |
| `SEARCH_QUERIES` | Search terms sent to Reddit |
| `HIGH_INTENT_KEYWORDS` | Keywords + weights used for scoring |
| `NEGATIVE_KEYWORDS` | Phrases that disqualify a post |
| `MIN_SCORE_HOT` | Minimum score for 🔥 tier (default: 20) |
| `MIN_SCORE_WARM` | Minimum score for 🟡 tier (default: 12) |
| `MAX_AGE_HOURS` | Maximum post age in hours (default: 48) |

---

## Tips

- **Run it daily** — leads go stale fast. The freshest posts (< 6h) get a bonus score.
- **Low comment count = less competition** — posts with ≤ 3 comments get a bonus.
- **Dollar amounts get boosted** — any post mentioning `$XXX+` gets +6 points.
- **Add your own subreddits** — niche industry subs (r/realtors, r/restaurants, etc.) can be goldmines.
