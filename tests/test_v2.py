#!/usr/bin/env python3
"""
Unit and Integration Tests for Gandatabase V2
"""

import pytest
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.id_generator import generate_display_id, generate_uuid, PREFIX_MAP
from scripts.normalize.bengali_normalizer import (
    normalize_unicode,
    normalize_bengali_spelling,
    transliterate_bn_to_en,
    strip_punctuation,
    similarity_ratio,
    get_search_tokens
)
from scripts.validate.validate import ValidationReport, validate_level_2_references, validate_level_4_quality


def test_id_generator():
    counters = {}
    art_id, counters = generate_display_id("artist", counters)
    assert art_id == "ART000001"
    work_id, counters = generate_display_id("work", counters)
    assert work_id == "WORK000001"
    
    uid = generate_uuid()
    assert len(uid) == 36
    assert uid.count("-") == 4


def test_bengali_normalizer():
    # Punctuation & spelling normalization
    raw = "আমার সোনার বাংলা, আমি তোমায় ভালোবাসি!"
    norm = normalize_bengali_spelling(raw)
    assert "সোনার" in norm
    assert "বাংলা" in norm
    
    # Transliteration
    translit = transliterate_bn_to_en("একলা চলো রে")
    assert "ekla" in translit.lower()
    assert "cholo" in translit.lower()
    
    # Search tokens
    tokens = get_search_tokens("রবীন্দ্রনাথ ঠাকুর")
    assert any("rabindranath" in t.lower() for t in tokens)
    
    # Similarity
    sim = similarity_ratio("আমার সোনার বাংলা", "আমার সোনার বাংলা!")
    assert sim == 1.0


def test_v2_datasets_integrity():
    data_dir = BASE_DIR / "data"
    assert (data_dir / "artists.json").exists()
    assert (data_dir / "works.json").exists()
    assert (data_dir / "recordings.json").exists()
    assert (data_dir / "lyrics.json").exists()
    assert (data_dir / "genres.json").exists()

    with open(data_dir / "works.json", "r", encoding="utf-8-sig") as f:
        works = json.load(f)
    assert len(works) >= 1800

    with open(data_dir / "artists.json", "r", encoding="utf-8-sig") as f:
        artists = json.load(f)
    assert len(artists) >= 800

    # Cross-reference check
    report = ValidationReport()
    validate_level_2_references(data_dir, report)
    assert len(report.errors) == 0

    # Quality check
    validate_level_4_quality(data_dir, report)
    assert len(report.errors) == 0
