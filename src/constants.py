"""
Project-wide constants. No magic numbers anywhere else in the codebase.

All numeric thresholds, limits, and fixed values are defined here.
"""

# --- Population Generation ---
MAX_POPULATION_SIZE = 10_000
MIN_POPULATION_SIZE = 1
DEFAULT_POPULATION_SIZE = 300
DEFAULT_DEEP_PERSONA_COUNT = 30
DEFAULT_SEED = 42

# --- Persona Attributes ---
ATTRIBUTE_MIN = 0.0
ATTRIBUTE_MAX = 1.0
TOTAL_ATTRIBUTE_COUNT = 145

# --- Age Ranges ---
PARENT_AGE_MIN = 22
PARENT_AGE_MAX = 45
CHILD_AGE_MIN = 2
CHILD_AGE_MAX = 14
MIN_PARENT_CHILD_AGE_GAP = 18

# --- City Tiers ---
CITY_TIERS = ("Tier1", "Tier2", "Tier3")

# --- Decision Engine ---
FUNNEL_STAGES = ("need_recognition", "awareness", "consideration", "purchase")
DECISION_OUTCOMES = ("adopt", "reject")

# --- Simulation ---
MAX_SIMULATION_MONTHS = 24
DEFAULT_SIMULATION_MONTHS = 12
WOM_TRANSMISSION_DECAY = 0.85

# --- Correlation Validation ---
CORRELATION_TOLERANCE = 0.15
DISTRIBUTION_P_VALUE_THRESHOLD = 0.05

# --- LLM ---
LLM_CACHE_DIR = "data/.llm_cache"
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0

# --- Code Coverage ---
MIN_CODE_COVERAGE_PERCENT = 80

# --- Performance Targets ---
STATIC_SIM_MAX_DURATION_SECONDS = 30
TIER2_MAX_DURATION_SECONDS = 600
INTERVIEW_MAX_RESPONSE_SECONDS = 5
