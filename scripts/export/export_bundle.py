#!/usr/bin/env python3
"""
Export Bundle Script for Gandatabase V2
Packages canonical V2 data for the Web Platform (banglagan) and Mobile App (banglagan_android_app).
Generates precomputed search indexes, slugs, and fast lookup maps.

Usage:
    python scripts/export/export_bundle.py --source-dir data/ --web-target ../banglagan/src/data/v2/
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.normalize.bengali_normalizer import (
    normalize_bengali_spelling,
    strip_punctuation,
    transliterate_bn_to_en,
    get_search_tokens
)


def create_slug(title: str, uid: str) -> str:
    """Generate clean URL-friendly slug from title and ID."""
    translit = transliterate_bn_to_en(title)
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', translit).strip().lower()
    clean = re.sub(r'[\s-]+', '-', clean)
    clean = clean[:60].strip('-')
    if not clean:
        clean = "song"
    return f"{clean}-{uid.lower()}"


def main():
    parser = argparse.ArgumentParser(description="Export V2 bundle for Web and Mobile")
    parser.add_argument("--source-dir", default="data", help="Directory containing canonical v2 data")
    parser.add_argument("--web-target", default="../banglagan/src/data/v2", help="Web target directory")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    web_target = Path(args.web_target).resolve()
    web_target.mkdir(parents=True, exist_ok=True)

    print(f"[*] Packaging V2 data from {source_dir} -> {web_target}...")

    def read_json(name: str):
        p = source_dir / f"{name}.json"
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    artists = read_json("artists")
    works = read_json("works")
    recordings = read_json("recordings")
    lyrics = read_json("lyrics")
    genres = read_json("genres")
    sources = read_json("sources")
    languages = read_json("languages")

    artist_map = {a["id"]: a for a in artists}
    lyrics_map = {l["id"]: l for l in lyrics}

    # Enrich works with slug and primary artist names for instant display
    enriched_works = []
    search_index = []
    timeline_map: Dict[str, List[str]] = {}

    for w in works:
        wid = w["id"]
        title_bn = w.get("title_bn", "")
        slug = create_slug(title_bn, wid)
        w["slug"] = slug

        # Primary lyricist and composer names
        lyricist_names = [artist_map[lid]["name_bn"] for lid in w.get("lyricist", []) if lid in artist_map]
        composer_names = [artist_map[cid]["name_bn"] for cid in w.get("composer", []) if cid in artist_map]
        
        w["lyricist_name"] = ", ".join(lyricist_names) if lyricist_names else "অজানা গীতিকার"
        w["composer_name"] = ", ".join(composer_names) if composer_names else "অজানা সুরকার"

        # Attached lyrics preview
        lyr_id = w.get("lyrics_id")
        if lyr_id and lyr_id in lyrics_map:
            w["lyrics_preview"] = lyrics_map[lyr_id].get("text_preview")
            w["copyright_status"] = lyrics_map[lyr_id].get("copyright_status")

        enriched_works.append(w)

        # Timeline bucket
        year = w.get("year")
        if year:
            decade = f"{(year // 10) * 10}s"
            timeline_map.setdefault(decade, []).append(wid)

        # Precompute search tokens for instant indexing
        tokens = get_search_tokens(title_bn)
        for name in lyricist_names + composer_names:
            tokens.update(get_search_tokens(name))
        for g in w.get("genre", []):
            tokens.update(get_search_tokens(g))

        search_index.append({
            "id": wid,
            "title_bn": title_bn,
            "title_en": w.get("title_en", ""),
            "slug": slug,
            "lyricist": w["lyricist_name"],
            "composer": w["composer_name"],
            "year": year,
            "genres": w.get("genre", []),
            "tokens": list(tokens)
        })

    # Stats summary
    stats = {
        "total_works": len(enriched_works),
        "total_artists": len(artists),
        "total_recordings": len(recordings),
        "total_lyrics": len(lyrics),
        "total_genres": len(genres),
        "total_sources": len(sources),
        "decades": {k: len(v) for k, v in sorted(timeline_map.items())}
    }

    def write_json(target_path: Path, data: Any):
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"    Exported: {target_path.name}")

    write_json(web_target / "works.json", enriched_works)
    write_json(web_target / "artists.json", artists)
    write_json(web_target / "recordings.json", recordings)
    write_json(web_target / "lyrics.json", lyrics)
    write_json(web_target / "genres.json", genres)
    write_json(web_target / "sources.json", sources)
    write_json(web_target / "languages.json", languages)
    write_json(web_target / "search-index.json", search_index)
    write_json(web_target / "stats.json", stats)

    print(f"[+] Successfully exported {len(enriched_works)} works to {web_target}!")


if __name__ == "__main__":
    main()
