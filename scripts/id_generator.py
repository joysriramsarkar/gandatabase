#!/usr/bin/env python3
"""
Centralized ID Generator for Gandatabase V2
Generates sequential display IDs (e.g., ART000001) and UUIDs.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Tuple

PREFIX_MAP = {
    "artist": "ART",
    "work": "WORK",
    "recording": "REC",
    "release": "REL",
    "film": "FILM",
    "lyrics": "LYR",
    "source": "SRC",
    "genre": "GEN",
    "language": "LANG",
    "label": "LAB",
    "alias": "ALIAS",
    "relationship": "RELNSH",
}

DEFAULT_COUNTERS_FILE = Path(__file__).resolve().parent.parent / "id_counters.json"


def load_counters(file_path: Path = DEFAULT_COUNTERS_FILE) -> Dict[str, int]:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {k: 0 for k in PREFIX_MAP}


def save_counters(counters: Dict[str, int], file_path: Path = DEFAULT_COUNTERS_FILE) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(counters, f, indent=2, ensure_ascii=False)


def generate_display_id(entity_type: str, counters: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
    """Generates the next display ID for given entity type."""
    if entity_type not in PREFIX_MAP:
        raise ValueError(f"Unknown entity type: {entity_type}. Valid types: {list(PREFIX_MAP.keys())}")
    
    prefix = PREFIX_MAP[entity_type]
    next_num = counters.get(entity_type, 0) + 1
    counters[entity_type] = next_num
    return f"{prefix}{next_num:06d}", counters


def generate_uuid() -> str:
    """Generate standard RFC 4122 UUID v4."""
    return str(uuid.uuid4())


if __name__ == "__main__":
    counters = load_counters()
    sample_id, counters = generate_display_id("work", counters)
    print(f"Sample generated ID: {sample_id}, UUID: {generate_uuid()}")
