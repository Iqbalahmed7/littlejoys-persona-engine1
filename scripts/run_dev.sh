#!/bin/bash
# Start the Streamlit dashboard in development mode.
export ENVIRONMENT=development
uv run streamlit run app/streamlit_app.py --server.port 8502 --server.runOnSave true
