# Codex — Sprint 11 Track B: Deployment Configuration

**Branch:** `sprint-11-track-b-deployment`
**Base:** `main`

## Context

We're deploying LittleJoys to Streamlit Community Cloud so the co-founder can access it via URL. The app already works locally — this track prepares the deployment configuration, secrets management, and ensures the app boots correctly on a fresh cloud instance with no pre-existing data.

## Deliverables

### 1. Create `.streamlit/config.toml` (NEW)

```toml
[server]
headless = true
port = 8501
enableCORS = false
maxUploadSize = 10

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8F9FA"
textColor = "#1A1A2E"
font = "sans serif"
```

### 2. Create `.streamlit/secrets.toml.example` (NEW)

```toml
# Copy this to .streamlit/secrets.toml (local) or paste into Streamlit Cloud secrets panel.
# NEVER commit secrets.toml — it's in .gitignore.

ANTHROPIC_API_KEY = "sk-ant-REPLACE_ME"
LLM_MOCK_ENABLED = "false"
```

Verify that `.streamlit/secrets.toml` is already in `.gitignore` (it is — line 59).

### 3. Create `requirements.txt` (NEW)

Streamlit Cloud reads `requirements.txt` by default. Extract runtime deps from `pyproject.toml`:

```
pydantic>=2.0
pydantic-settings>=2.0
numpy>=1.26
scipy>=1.12
pandas>=2.2
scikit-learn>=1.4
shap>=0.44
anthropic>=0.40
plotly>=5.18
streamlit>=1.30
structlog>=24.1
httpx>=0.27
beautifulsoup4>=4.12
pytrends>=4.9
pyarrow>=15.0
```

**Important:** These must match `pyproject.toml` `[project.dependencies]` exactly. Read `pyproject.toml` to verify.

### 4. Verify Cold-Start Population Generation

On Streamlit Cloud, `data/population/` won't exist on first boot. Verify that `app/streamlit_app.py` handles this correctly:

```python
# This already exists in streamlit_app.py — verify it works:
if "population" not in st.session_state:
    if pop_path.exists():
        st.session_state.population = Population.load(pop_path)
    else:
        st.info("No population data found. Generate a synthetic baseline population to begin.")
        if st.button("Generate Population", type="primary"):
            # ... generates and saves
```

This is fine for local, but on Streamlit Cloud the filesystem is ephemeral. Each reboot regenerates. That's acceptable for a demo — just document it.

**However**, we need to ensure the `data/` directory is writable. Add a check at the top of `app/streamlit_app.py`:

```python
# After imports, before set_page_config:
from pathlib import Path
Path("data/population").mkdir(parents=True, exist_ok=True)
```

If this line already exists or the directory is created elsewhere, no change needed. Read the file to verify.

### 5. Create `docs/DEPLOYMENT.md` (NEW)

```markdown
# Deploying LittleJoys to Streamlit Community Cloud

## Prerequisites

- GitHub repo with the codebase pushed
- Anthropic API key (get one at https://console.anthropic.com)

## Steps

### 1. Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository, branch `main`, and main file path `app/streamlit_app.py`

### 2. Configure Secrets

In the Streamlit Cloud dashboard, go to your app → Settings → Secrets and paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-real-key-here"
LLM_MOCK_ENABLED = "false"
```

### 3. First Boot

- The app will install dependencies from `requirements.txt`
- On first load, click "Generate Population" to create the 300-persona synthetic population
- Population is regenerated on each cloud reboot (ephemeral filesystem) — this takes ~10 seconds

### 4. Local Development

For local development with real LLM:

1. Copy `.env.example` to `.env.local`
2. Set `ANTHROPIC_API_KEY` to your real key
3. Set `LLM_MOCK_ENABLED=false`
4. Run: `uv run streamlit run app/streamlit_app.py`

Alternatively, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the key.

### 5. Cost Estimates

| Action | Estimated Cost |
|--------|---------------|
| Generate population | $0.00 (pure computation) |
| Run scenario simulation | $0.00 (pure computation) |
| Run auto-scenario explorer | $0.00 (pure computation) |
| One interview turn | ~$0.02-0.05 (Claude Sonnet) |
| Full demo session (20 turns) | ~$0.50-1.00 |

Session spend caps are enforced at 50 calls / $2.00 per session.

## Architecture Notes

- Population data is stored in `data/population/` — ephemeral on cloud
- LLM response cache is stored in `data/.llm_cache/` — ephemeral on cloud
- All simulation (funnel, counterfactual, explorer) is pure computation — no LLM cost
- Only interviews use the LLM API
```

### 6. Add Python Version File

Streamlit Cloud reads `.python-version` or `runtime.txt` for Python version:

Create `runtime.txt`:
```
python-3.11
```

Or create `.python-version`:
```
3.11
```

Use `runtime.txt` — it's the standard for Streamlit Cloud.

## Files to Read Before Starting

1. `pyproject.toml` — **full file** — dependencies list
2. `app/streamlit_app.py` — **full file** — cold-start population flow
3. `.env.example` — env var documentation
4. `.gitignore` — verify secrets.toml is excluded

## Constraints

- Do NOT modify any Python source files
- Do NOT commit any real API keys or secrets
- `requirements.txt` must exactly match `pyproject.toml` runtime dependencies
- `.streamlit/secrets.toml` must remain gitignored
- No new pip dependencies

## Feedback from Sprint 10

Your Sprint 10 delivery was excellent — best test isolation on the team. Two things:
1. Watch for cosmetic spec details (you used `->` instead of `→` in format_modification).
2. When you touch files outside your track scope, flag it prominently in your report.

## Acceptance Criteria

- [ ] `.streamlit/config.toml` created with theme and server settings
- [ ] `.streamlit/secrets.toml.example` created with placeholder key
- [ ] `requirements.txt` matches `pyproject.toml` dependencies
- [ ] `runtime.txt` specifies Python 3.11
- [ ] `docs/DEPLOYMENT.md` has step-by-step cloud deployment guide
- [ ] Cold-start flow verified — `data/population/` created if missing
- [ ] No real secrets committed anywhere
- [ ] All existing tests still pass
