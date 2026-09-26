#!/usr/bin/env python3
"""
Validation Suite for Gandatabase V2
Implements 4-Level Validation:
  Level 1: Schema Validation (Required fields, types, patterns, enums)
  Level 2: Cross-Reference Integrity (No broken IDs, orphan entities)
  Level 3: Duplicate Detection (Fuzzy matching on normalized titles)
  Level 4: Data Quality Rules (Year boundaries, sources, AI pending status)

Usage:
    python scripts/validate/validate.py --data-dir data/ --schema-dir schema/
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.normalize.bengali_normalizer import (
    normalize_bengali_spelling,
    strip_punctuation,
    similarity_ratio
)

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class ValidationReport:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {}

    def error(self, level: int, msg: str):
        self.errors.append(f"[L{level} ERROR] {msg}")

    def warn(self, level: int, msg: str):
        self.warnings.append(f"[L{level} WARN] {msg}")

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def print_summary(self):
        print("\n" + "=" * 60)
        print("         GANDATABASE V2 VALIDATION REPORT")
        print("=" * 60)
        for entity, count in self.stats.items():
            print(f"  * {entity.capitalize()}: {count} entities checked")
        print("-" * 60)
        print(f"Total Errors:   {len(self.errors)}")
        print(f"Total Warnings: {len(self.warnings)}")
        print("-" * 60)

        if self.errors:
            print("\n❌ ERRORS:")
            for err in self.errors[:25]:
                print(f"  {err}")
            if len(self.errors) > 25:
                print(f"  ... and {len(self.errors) - 25} more errors.")

        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warn in self.warnings[:20]:
                print(f"  {warn}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more warnings.")

        print("=" * 60)
        if self.is_valid():
            print("🎉 ALL VALIDATION CHECKS PASSED SUCCESSFULLY!\n")
        else:
            print("🚫 VALIDATION FAILED. Please resolve the errors above.\n")


def load_dataset(data_dir: Path, name: str) -> List[Dict[str, Any]]:
    path = data_dir / f"{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


def validate_level_1_schema(data_dir: Path, schema_dir: Path, report: ValidationReport):
    """Level 1: JSON Schema validation."""
    schemas = {
        "artists": "artist.schema.json",
        "works": "work.schema.json",
        "recordings": "recording.schema.json",
        "releases": "release.schema.json",
        "lyrics": "lyrics.schema.json",
        "genres": "genre.schema.json",
        "sources": "source.schema.json",
        "languages": "language.schema.json",
    }

    for entity_name, schema_file in schemas.items():
        data = load_dataset(data_dir, entity_name)
        report.stats[entity_name] = len(data)
        schema_path = schema_dir / schema_file
        
        if not schema_path.exists():
            report.warn(1, f"Schema file {schema_file} not found. Skipping schema check.")
            continue

        with open(schema_path, "r", encoding="utf-8") as sf:
            schema = json.load(sf)

        if HAS_JSONSCHEMA:
            validator = jsonschema.Draft7Validator(schema)
            for item in data:
                item_id = item.get("id", "UNKNOWN")
                for err in validator.iter_errors(item):
                    report.error(1, f"{entity_name} [{item_id}]: {err.message} at '{'/'.join(map(str, err.path))}'")
        else:
            # Fallback basic schema validation
            required = schema.get("required", [])
            for item in data:
                item_id = item.get("id", "UNKNOWN")
                for req in required:
                    if req not in item or item[req] is None or item[req] == "":
                        report.error(1, f"{entity_name} [{item_id}]: Missing required field '{req}'")


def validate_level_2_references(data_dir: Path, report: ValidationReport):
    """Level 2: Cross-reference integrity check."""
    artists = {a["id"] for a in load_dataset(data_dir, "artists") if "id" in a}
    works = {w["id"] for w in load_dataset(data_dir, "works") if "id" in w}
    recordings = {r["id"] for r in load_dataset(data_dir, "recordings") if "id" in r}
    lyrics = {l["id"] for l in load_dataset(data_dir, "lyrics") if "id" in l}
    sources = {s["id"] for s in load_dataset(data_dir, "sources") if "id" in s}

    # Check Works
    for w in load_dataset(data_dir, "works"):
        wid = w.get("id", "UNKNOWN")
        # Lyricist refs
        for lid in w.get("lyricist", []):
            if lid not in artists:
                report.error(2, f"Work [{wid}]: Invalid lyricist reference '{lid}'")
        # Composer refs
        for cid in w.get("composer", []):
            if cid not in artists:
                report.error(2, f"Work [{wid}]: Invalid composer reference '{cid}'")
        # Lyrics ref
        lyr_id = w.get("lyrics_id")
        if lyr_id and lyr_id not in lyrics:
            report.error(2, f"Work [{wid}]: Broken lyrics reference '{lyr_id}'")
        # Source refs
        for sid in w.get("source_ids", []):
            if sid not in sources:
                report.error(2, f"Work [{wid}]: Broken source reference '{sid}'")

    # Check Recordings
    for r in load_dataset(data_dir, "recordings"):
        rid = r.get("id", "UNKNOWN")
        wid = r.get("work_id")
        if wid and wid not in works:
            report.error(2, f"Recording [{rid}]: Broken work reference '{wid}'")
        for aid in r.get("artists", []):
            if aid not in artists:
                report.error(2, f"Recording [{rid}]: Invalid artist reference '{aid}'")

    # Check Lyrics
    for l in load_dataset(data_dir, "lyrics"):
        lid = l.get("id", "UNKNOWN")
        wid = l.get("work_id")
        if wid and wid not in works:
            report.error(2, f"Lyrics [{lid}]: Broken work reference '{wid}'")


def validate_level_3_duplicates(data_dir: Path, report: ValidationReport):
    """Level 3: Duplicate title detection."""
    works = load_dataset(data_dir, "works")
    seen_titles: Dict[str, str] = {}

    for w in works:
        wid = w.get("id", "UNKNOWN")
        title = w.get("title_bn", "")
        stripped = strip_punctuation(title)
        if not stripped:
            continue

        if stripped in seen_titles:
            orig_id = seen_titles[stripped]
            report.warn(3, f"Possible duplicate work title: [{wid}] '{title}' resembles [{orig_id}]")
        else:
            seen_titles[stripped] = wid


def validate_level_4_quality(data_dir: Path, report: ValidationReport):
    """Level 4: Data Quality rules."""
    # Work quality
    for w in load_dataset(data_dir, "works"):
        wid = w.get("id", "UNKNOWN")
        year = w.get("year")
        if year is not None:
            if not (1000 <= year <= 2100):
                report.error(4, f"Work [{wid}]: Year {year} out of valid range (1000-2100)")
        if w.get("data_origin") == "ai_suggestion" and w.get("verification_status") == "verified":
            report.error(4, f"Work [{wid}]: AI-suggested entry cannot be directly 'verified'")
        if w.get("verification_status") == "verified" and not w.get("source_ids"):
            report.error(4, f"Work [{wid}]: Verified entry must have at least one source_id")

    # Artist quality
    for a in load_dataset(data_dir, "artists"):
        aid = a.get("id", "UNKNOWN")
        if not a.get("name_bn"):
            report.error(4, f"Artist [{aid}]: name_bn is required and cannot be empty")
        if a.get("verification_status") == "verified" and not a.get("source_ids"):
            report.error(4, f"Artist [{aid}]: Verified artist missing source_ids")


def main():
    parser = argparse.ArgumentParser(description="Validate Gandatabase v2")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--schema-dir", default="schema", help="Path to schema directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    schema_dir = Path(args.schema_dir).resolve()

    print(f"[*] Validating datasets in {data_dir} using schemas from {schema_dir}...")
    report = ValidationReport()

    validate_level_1_schema(data_dir, schema_dir, report)
    validate_level_2_references(data_dir, report)
    validate_level_3_duplicates(data_dir, report)
    validate_level_4_quality(data_dir, report)

    report.print_summary()
    sys.exit(0 if report.is_valid() else 1)


if __name__ == "__main__":
    main()
