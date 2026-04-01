# Security & Privacy

## No Credentials Required for Core Bot

✅ **Reddit scraping** — Uses public JSON endpoints, no API key needed  
✅ **No database** — CSV output, no server dependencies  
✅ **No hardcoded secrets** — All config in `.env`

---

## Environment Variables

### Optional: OPENAI_API_KEY

If you use **Codex CLI** to auto-generate replies:

```bash
OPENAI_API_KEY=sk-...your_key...
OPENAI_MODEL=gpt-4o-mini  # or your preferred model
```

**Security Best Practices:**
- Never commit `.env` to git (already in `.gitignore`)
- Use `.env.example` as a template for setup docs
- Rotate your API key regularly
- Use environment-variable-specific API keys when possible (most providers support this)
- Run Codex CLI locally or on a trusted machine

---

## Data Privacy

### What the Bot Collects
- **Public Reddit post data**: Title, body, subreddit, author, URL, scores
- **Your OpenAI API key** (if using Codex) — passed to Codex CLI subprocess, never logged

### Where Data Goes
- **Local CSV file** (`leads_output/`) — on your machine only
- **OpenAI API** (if using Codex) — via the Codex CLI; review [OpenAI's privacy policy](https://openai.com/privacy)
- **Nowhere else** — this bot has no network calls beyond Reddit + optional OpenAI

### What NOT to Do
❌ Don't commit `.env` files to git (it's in `.gitignore`)  
❌ Don't share `leads_output/` CSVs containing Reddit author data  
❌ Don't hard-code API keys anywhere  

---

## Safety Checks

The `.gitignore` prevents accidental leaks:

```
.env                   # Prevent env var exposure
__pycache__/          # Prevent bytecode commits
*.pyc                 # Prevent compiled Python
leads_output/         # Prevent CSV with Reddit author data
```

---

## Auditing

To verify no secrets are committed:

```bash
# Check git history for secrets
git log -p | grep -i "api_key\|secret\|password"

# Check current staged files
git diff --cached | grep -i "api_key\|secret\|password"

# Check .gitignore is working
git check-ignore .env  # Should return .env

# Verify no env vars in Python files
grep -r "OPENAI_API_KEY\|REDDIT" *.py  # Should only match config references
```

---

## Deployment

If running this on a server:

1. Use your platform's **secrets manager** (AWS Secrets, GitHub Actions secrets, etc.)
2. Never store secrets in `~/.bashrc` or `/etc/environment`
3. Use IAM roles / service accounts when possible
4. Rotate API keys quarterly
5. Monitor API usage for unusual spikes
