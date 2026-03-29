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

In the Streamlit Cloud dashboard, go to your app -> Settings -> Secrets and paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-real-key-here"
LLM_MOCK_ENABLED = "false"
```

### 3. First Boot

- The app installs dependencies from `requirements.txt`
- On first load, click "Generate Population" to create the 300-persona synthetic population
- Streamlit Cloud uses an ephemeral filesystem; population and cache are regenerated after app restarts/redeploys
- Typical first-time population generation takes about ~10 seconds

### 4. Local Development

For local development with real LLM:

1. Copy `.env.example` to `.env.local`
2. Set `ANTHROPIC_API_KEY` to your real key
3. Set `LLM_MOCK_ENABLED=false`
4. Run: `uv run streamlit run app/streamlit_app.py`

Alternatively, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the key.

### 5. Cost Estimates

| Action | Estimated Cost |
| --- | --- |
| Generate population | $0.00 (pure computation) |
| Run scenario simulation | $0.00 (pure computation) |
| Run auto-scenario explorer | $0.00 (pure computation) |
| One interview turn | ~$0.02-0.05 (Claude Sonnet) |
| Full demo session (20 turns) | ~$0.50-1.00 |

Session spend caps are enforced at 50 calls / $2.00 per session.

## Architecture Notes

- Population data is stored in `data/population/` - ephemeral on cloud
- LLM response cache is stored in `data/.llm_cache/` - ephemeral on cloud
- All simulation (funnel, counterfactual, explorer) is pure computation - no LLM cost
- Only interviews use the LLM API

