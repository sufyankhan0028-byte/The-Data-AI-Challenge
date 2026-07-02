"""Global application state shared across services."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd


class AppState:
    """
    Singleton holding loaded data and cached results.
    pandas / numpy are referenced only via string annotations so this module
    can be imported even before those packages are installed.
    """

    candidates_df: Optional[Any] = None       # pd.DataFrame at runtime
    embeddings: Optional[Any] = None          # np.ndarray at runtime
    candidate_ids: Optional[List[str]] = None # ordered list matching embeddings rows
    jd_text: Optional[str] = None
    jd_parsed: Optional[dict] = None
    jd_embedding: Optional[Any] = None        # np.ndarray at runtime
    ranking_results: Optional[list] = None    # list of RankResult dicts
    processing_status: str = "idle"           # idle | loading | embedding | ranking | done | error
    processing_message: str = ""
    total_candidates: int = 0


app_state = AppState()
