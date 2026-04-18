# Deploying to Render (public, always-on, sim-capable)

This repo is set up to deploy as a single Docker service on Render.com.
Render Starter plan is **$7/month** — the cheapest realistic option for a
public dashboard that lets visitors run simulations on demand.

## Why Render Starter (not free tier)

- **Free tier spins down** after 15 min idle → LinkedIn visitors hit a
  30-60s cold start. Bad first impression.
- **Free tier RAM is 512 MB** with spin-down behavior; the sim subprocess
  loads pandas + the full prospects/teams dataset and can OOM.
- **Starter is always-on** + 512 MB dedicated RAM → sim runs reliably.

## One-time setup (~10 minutes)

### 1. Push this repo to GitHub

```bash
cd C:\Users\colin\nfl-draft-predictor
git init
git add .
git commit -m "Initial commit — 2026 NFL Draft Predictor"
# Create a new repo on github.com (private or public), then:
git remote add origin https://github.com/YOUR-USERNAME/nfl-draft-predictor.git
git branch -M main
git push -u origin main
```

### 2. Sign up at render.com and deploy

1. Go to https://dashboard.render.com and sign up (free to register).
2. Click **New** → **Blueprint**.
3. Connect your GitHub account, pick this repo.
4. Render auto-detects `render.yaml` and proposes the service. Click **Apply**.
5. Render builds the Docker image (~5 min first time) and deploys.
6. You'll get a URL like `https://nfl-draft-predictor-2026.onrender.com`.

Share that URL on LinkedIn. Visitors can browse Teams, Prospects, Trades,
League, and click **Run simulation** to generate a fresh mock. Sims are
capped at 100 per run to keep one visitor from monopolizing the server.

### 3. Update data after new information breaks

Whenever you scrape fresh data or tune the model locally:

```bash
# Run the pipeline locally to regenerate features + sim outputs
python src/data/parse_team_profiles_pdf.py
python src/data/ingest_analyst_mocks.py
python src/data/compute_roster_context.py
python src/data/build_cap_and_coaching.py
python src/data/aggregate_live_intel.py
python src/data/build_team_agents.py
python -m src.models.stage2_game_theoretic

# Commit + push
git add data/
git commit -m "Refresh model data"
git push
```

Render's `autoDeploy: true` picks up the push, rebuilds, and redeploys in ~3 min.

## Cost control knobs

- `DRAFT_MAX_SIMS` (env var) caps the per-request sim count. Default 100
  on Render (set in `render.yaml`), 5000 locally.
- One sim at a time: the API returns 409 Conflict when a sim is already
  running. The frontend handles this gracefully by showing the in-progress
  sim to the second visitor (they see the first person's results).
- Want to temporarily disable sims entirely (pure browse mode)? Add env
  var `DRAFT_READ_ONLY=1` in the Render dashboard → Environment.

## Alternatives ranked by cost

| Host | $ /mo | Always-on | Difficulty |
|---|---|---|---|
| **Render Starter** (recommended) | $7 | ✓ | Easiest — click Deploy from GitHub |
| Railway Hobby | $5 | ✓ | Also easy — similar GitHub deploy |
| Fly.io shared-cpu-1x @ 512 MB | ~$2-4 | ✓ | Moderate — `flyctl` CLI setup |
| Hetzner CX11 VPS | ~$3.50 | ✓ | Advanced — SSH, Docker, Nginx yourself |
| Render free | $0 | ✗ (cold start) | Easy but cold-start is bad for LinkedIn traffic |

## Read-only tunnel sharing (temporary, your PC stays the host)

If you only need to share for an afternoon, skip cloud entirely:

```bash
python run_dashboard.py --share --read-only
```

Prints a `https://xxx.trycloudflare.com` URL. Dies when you close the
terminal. No cloud cost. Requires your PC stay on.
