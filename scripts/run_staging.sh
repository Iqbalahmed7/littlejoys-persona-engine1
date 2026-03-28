#!/bin/bash
# Start the Streamlit dashboard in staging mode.
export ENVIRONMENT=staging
uv run streamlit run app/streamlit_app.py --server.port 8501
