from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

MOCK_DIR = Path(__file__).resolve().parent.parent.parent / "sample-data" / "mock-json"


def load_mock(filename: str) -> Union[list, dict]:
    filepath = MOCK_DIR / filename
    if not filepath.exists():
        logger.warning(f"Mock file not found: {filepath}")
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return []
