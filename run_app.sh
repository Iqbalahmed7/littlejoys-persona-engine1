#!/bin/bash
cd "/Users/admin/Documents/Simulatte Projects/1. LittleJoys"
# Load .env so ANTHROPIC_API_KEY is available to the app and question engine
set -a
[ -f .env ] && source .env
set +a
exec .venv/bin/streamlit run app/streamlit_app.py --server.port 8501
