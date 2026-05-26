import sys
from unittest.mock import MagicMock

# Mocking modules that might not be installed in the environment
sys.modules['dotenv'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

from song_generator import get_ids_from_names

def test_get_ids_from_names_empty():
    artist_map = {"rabindranath": "RNT01"}
    assert get_ids_from_names(None, artist_map) == []
    assert get_ids_from_names([], artist_map) == []

def test_get_ids_from_names_single_string():
    artist_map = {"rabindranath": "RNT01"}
    assert get_ids_from_names("rabindranath", artist_map) == ["RNT01"]

def test_get_ids_from_names_exact_match():
    artist_map = {"rabindranath": "RNT01"}
    assert get_ids_from_names(["rabindranath"], artist_map) == ["RNT01"]
    assert get_ids_from_names(["  Rabindranath  "], artist_map) == ["RNT01"]

def test_get_ids_from_names_fuzzy_match():
    artist_map = {"rabindranath tagore": "RNT01"}
    # "rabindranath tagor" is very close to "rabindranath tagore"
    assert get_ids_from_names(["rabindranath tagor"], artist_map) == ["RNT01"]

def test_get_ids_from_names_no_match():
    artist_map = {"rabindranath": "RNT01"}
    assert get_ids_from_names(["unknown"], artist_map) == []

def test_get_ids_from_names_unique_ids():
    artist_map = {"rabindranath": "RNT01", "tagore": "RNT01"}
    assert sorted(get_ids_from_names(["rabindranath", "tagore"], artist_map)) == ["RNT01"]

def test_get_ids_from_names_multiple_ids():
    artist_map = {"rabindranath": "RNT01", "nazrul": "KNI01"}
    assert sorted(get_ids_from_names(["rabindranath", "nazrul"], artist_map)) == ["KNI01", "RNT01"]

def test_get_ids_from_names_bengali():
    artist_map = {"রবীন্দ্রনাথ ঠাকুর": "RNT01"}
    assert get_ids_from_names(["রবীন্দ্রনাথ ঠাকুর"], artist_map) == ["RNT01"]
    # Fuzzy match Bengali (minor typo)
    assert get_ids_from_names(["রবীন্দ্রনাথ ঠাকু"], artist_map) == ["RNT01"]
