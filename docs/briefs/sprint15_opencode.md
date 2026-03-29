# Sprint 15 Brief — OpenCode (GPT 5.4 Nano)
## Streamlit Cloud Deployment Config

### Context
The app needs to be deployable to Streamlit Cloud for a co-founder demo. This task creates the deployment configuration and ensures the app runs cleanly in a cloud environment.

### Task 1: Create `.streamlit/config.toml`

If it doesn't already exist, create `.streamlit/config.toml`:

```toml
[server]
headless = true
port = 8501
enableCORS = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#333333"
font = "sans serif"
```

### Task 2: Create/Verify `requirements.txt`

Streamlit Cloud uses `requirements.txt`. Check if one exists. If not, generate it from the project's dependencies. The app needs at minimum:

```
streamlit>=1.30.0
plotly>=5.18.0
pandas>=2.0.0
pydantic>=2.0.0
structlog>=23.0.0
anthropic>=0.40.0
python-dotenv>=1.0.0
scikit-learn>=1.3.0
shap>=0.43.0
```

If the project uses `pyproject.toml` or `uv`, extract the actual dependency versions from there rather than guessing. Run:
```bash
uv pip compile pyproject.toml -o requirements.txt
```
Or manually extract from `pyproject.toml`'s `[project.dependencies]`.

### Task 3: Create `.streamlit/secrets.toml.example`

Template for users to create their own secrets file:

```toml
# Copy this to .streamlit/secrets.toml and fill in your API key
# DO NOT commit secrets.toml to git

ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"
```

Verify `.streamlit/secrets.toml` is in `.gitignore`. If not, add it.

### Task 4: Verify Cloud Readiness

Run these checks:
```bash
# Verify the app starts without errors
uv run streamlit run app/streamlit_app.py --server.headless true &
sleep 5
curl -s http://localhost:8501 | head -20
# Kill the server
pkill -f "streamlit run"
```

If there are import errors or missing dependencies, fix them.

### Task 5: Create `DEPLOY.md`

**New file:** `docs/DEPLOY.md` — short deployment guide:

```markdown
# Deploying LittleJoys to Streamlit Cloud

## Quick Start

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file path: `app/streamlit_app.py`
5. Add secret `ANTHROPIC_API_KEY` in the app's Secrets settings
6. Deploy

## Local Development

```bash
uv run streamlit run app/streamlit_app.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | For real LLM mode | Anthropic API key for interviews and reports |

Without an API key, the app runs in mock mode (all features work with synthetic responses).
```

### Deliverables
1. `.streamlit/config.toml` — theme + server config
2. `requirements.txt` — pinned dependencies for Streamlit Cloud
3. `.streamlit/secrets.toml.example` — API key template
4. `.gitignore` updated if needed
5. `docs/DEPLOY.md` — deployment guide
6. App starts cleanly with `streamlit run app/streamlit_app.py`

### Do NOT
- Modify source modules in `src/`
- Modify page files in `app/pages/`
- Add new Python dependencies
- Commit real API keys
