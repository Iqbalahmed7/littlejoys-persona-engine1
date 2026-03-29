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
