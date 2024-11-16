from .prompts import (
    TEAM_SUPERVISOR_SYSTEM_PROMPT,
    DATA_COLLECTION_AGENT_SYSTEM_PROMPT,
    DATA_SAVE_AGENT_SYSTEM_PROMPT,
    DATA_SEARCH_AGENT_SYSTEM_PROMPT,
    DATA_VISUALIZATION_AGENT_SYSTEM_PROMPT,
    DATA_ANALYSIS_AGENT_SYSTEM_PROMPT,
)

from .analysis import run_analysis
from .collection import run_collection
from .save import run_save
from .search import run_search, load_data
from .visualization import run_visualization

RETRIEVER = load_data()
