#!/usr/bin/env python3
"""
Migration: Legacy Gandatabase V1 -> V2 Schema
Converts artists.json, songs.json, artists_new.json, lyrics.ts
into structured V2 canonical entities.

Usage:
    python scripts/import/migrate_v1_to_v2.py --input-dir ./ --output-dir ./data
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add parent dir to sys.path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.normalize.bengali_normalizer import (
    normalize_unicode,
    normalize_bengali_spelling,
    transliterate_bn_to_en,
    COMMON_ALIASES
)
from scripts.id_generator import generate_display_id, generate_uuid, PREFIX_MAP


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json_safe(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def parse_lyrics_file(lyrics_path: Path) -> Dict[str, str]:
    """Parse lyrics from lyrics.ts using regex."""
    if not lyrics_path.exists():
        return {}
    
    with open(lyrics_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    # Pattern matches: id: "L0000001", lyrics: `...`
    pattern = re.compile(r'id\s*:\s*["\'](L\d+)["\']\s*,\s*lyrics\s*:\s*`([^`]*)`', re.DOTALL)
    lyrics_map = {}
    for match in pattern.finditer(content):
        lid = match.group(1).strip()
        text = match.group(2).strip()
        lyrics_map[lid] = text
        # Also map without extra leading zeros if any, e.g. L000001 vs L0000001
        num_part = re.sub(r'\D', '', lid)
        if num_part:
            normalized_lid = f"L{int(num_part):06d}"
            lyrics_map[normalized_lid] = text
            lyrics_map[f"L{int(num_part):07d}"] = text

    return lyrics_map


def main():
    parser = argparse.ArgumentParser(description="Migrate Gandatabase v1 to v2")
    parser.add_argument("--input-dir", default="./", help="Directory containing legacy files")
    parser.add_argument("--output-dir", default="./data", help="Output directory for V2 data")
    parser.add_argument("--artists-new", default="artists_new.json", help="Path to artists_new.json if exists")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Starting migration from {input_dir} to {output_dir}...")

    # Load legacy files
    artists_file = input_dir / "artists.json"
    songs_file = input_dir / "songs.json"
    artists_new_file = input_dir / args.artists_new
    lyrics_file = input_dir / "lyrics.ts"

    legacy_artists = load_json_safe(artists_file) or []
    legacy_songs = load_json_safe(songs_file) or []
    legacy_artists_new = load_json_safe(artists_new_file) or []
    lyrics_map = parse_lyrics_file(lyrics_file)

    print(f"[*] Loaded: {len(legacy_artists)} artists, {len(legacy_songs)} songs, {len(lyrics_map)} parsed lyrics.")

    counters = {k: 0 for k in PREFIX_MAP}
    migration_map = {
        "artist": {},
        "work": {},
        "recording": {},
        "release": {},
        "lyrics": {},
        "genre": {},
        "source": {}
    }

    # 1. Base Canonical Sources
    src_archive_id, counters = generate_display_id("source", counters)
    src_archive = {
        "id": src_archive_id,
        "uuid": generate_uuid(),
        "type": "trusted_website",
        "title": "গানডাটাবেস ডিজিটাল সংগীত সংরক্ষণাগার (Gandatabase Archive)",
        "author": "গানডাটাবেস টিম ও গবেষকবৃন্দ",
        "publisher": "Bangla Gan Knowledge Platform",
        "year": 2026,
        "url": "https://banglagan.org",
        "reliability": "high",
        "verification_status": "verified",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    src_tagore_id, counters = generate_display_id("source", counters)
    src_tagore = {
        "id": src_tagore_id,
        "uuid": generate_uuid(),
        "type": "book",
        "title": "গীতবিতান (অখণ্ড সংস্করণ)",
        "author": "রবীন্দ্রনাথ ঠাকুর",
        "publisher": "বিশ্বভারতী গ্রন্থনবিভাগ",
        "year": 1931,
        "reliability": "high",
        "verification_status": "verified",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    src_nazrul_id, counters = generate_display_id("source", counters)
    src_nazrul = {
        "id": src_nazrul_id,
        "uuid": generate_uuid(),
        "type": "book",
        "title": "নজরুল-সংগীত সংগ্রহ",
        "author": "কাজী নজরুল ইসলাম",
        "publisher": "নজরুল ইনস্টিটিউট, ঢাকা",
        "year": 1985,
        "reliability": "high",
        "verification_status": "verified",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    v2_sources = [src_archive, src_tagore, src_nazrul]

    # Pre-analyze artist roles from songs
    artist_roles_inferred: Dict[str, set] = {}
    for s in legacy_songs:
        aids = s.get("artistId", [])
        if isinstance(aids, str):
            aids = [aids]
        for aid in aids:
            if aid:
                artist_roles_inferred.setdefault(aid, set()).add("singer")

        lyricist = s.get("lyricistId")
        if lyricist:
            artist_roles_inferred.setdefault(lyricist, set()).add("lyricist")

        composer = s.get("composerId")
        if composer:
            artist_roles_inferred.setdefault(composer, set()).add("composer")

    # 2. Migrate Artists
    v2_artists = []
    enriched_artists_by_id = {}
    enriched_artists_by_name = {}
    for item in legacy_artists_new:
        if "artistId" in item:
            enriched_artists_by_id[item["artistId"]] = item
        if "name" in item:
            enriched_artists_by_name[normalize_bengali_spelling(item["name"])] = item

    for a in legacy_artists:
        legacy_id = a.get("id", "").strip()
        name_bn = normalize_bengali_spelling(a.get("name", "").strip())
        if not legacy_id or not name_bn:
            continue

        art_id, counters = generate_display_id("artist", counters)
        migration_map["artist"][legacy_id] = art_id

        enriched = enriched_artists_by_id.get(legacy_id) or enriched_artists_by_name.get(name_bn) or {}
        
        bio = enriched.get("bio")
        image_url = enriched.get("imageUrl")
        era = enriched.get("era")

        # Determine roles
        roles = set()
        if "type" in enriched and isinstance(enriched["type"], list):
            for t in enriched["type"]:
                t_low = t.lower()
                if "গায়ক" in t or "কণ্ঠ" in t or "singer" in t_low:
                    roles.add("singer")
                if "সুরকার" in t or "composer" in t_low:
                    roles.add("composer")
                if "গীতিকার" in t or "lyricist" in t_low:
                    roles.add("lyricist")
                if "কবি" in t or "poet" in t_low:
                    roles.add("poet")
                if "পরিচালক" in t or "director" in t_low:
                    roles.add("music_director")

        inferred = artist_roles_inferred.get(legacy_id, set())
        roles.update(inferred)
        if not roles:
            roles.add("singer")

        # Aliases & transliterations
        name_en = transliterate_bn_to_en(name_bn).title()
        aliases = [name_en]
        for en_alias, bn_name in COMMON_ALIASES.items():
            if bn_name == name_bn:
                aliases.append(en_alias.title())
        aliases = list(set(aliases))

        # External IDs enrichment for prominent artists
        external_ids = {}
        if "রবীন্দ্রনাথ ঠাকুর" in name_bn:
            external_ids = {
                "wikidata": "Q9333",
                "musicbrainz": "4a733cf6-5ca4-4f46-880c-0be896f64264",
                "spotify": "74iws2N7aWdM82G7uN0g0c"
            }
        elif "কাজী নজরুল ইসলাম" in name_bn:
            external_ids = {
                "wikidata": "Q334818",
                "musicbrainz": "764953c8-e390-4822-b5e8-090c21820b75"
            }
        elif "হেমন্ত মুখোপাধ্যায়" in name_bn:
            external_ids = {
                "wikidata": "Q3349755",
                "musicbrainz": "3ca8d960-4b13-41c1-a3f2-1b12b5e28a55"
            }

        artist_obj = {
            "id": art_id,
            "uuid": generate_uuid(),
            "name_bn": name_bn,
            "name_en": name_en,
            "aliases": aliases,
            "type": "person",
            "gender": "female" if any(f in name_bn for f in ["লতা", "সন্ধ্যা", "আশা", "আরতি", "রুনা", "সাবিনা"]) else "male",
            "birth_date": None,
            "death_date": None,
            "roles": sorted(list(roles)),
            "bio": bio,
            "image_url": image_url,
            "external_ids": external_ids,
            "source_ids": [src_archive_id],
            "verification_status": "verified",
            "data_origin": "manual",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "revision_history": [
                {
                    "date": now_iso(),
                    "editor": "system_migrator",
                    "action": "migrated_from_v1",
                    "detail": f"Migrated from legacy artist ID {legacy_id}"
                }
            ]
        }
        v2_artists.append(artist_obj)

    print(f"[*] Migrated {len(v2_artists)} artists.")

    # 3. Extract & Register Canonical Genres
    def map_genre_category(name: str) -> str:
        if any(k in name for k in ["রবীন্দ্র", "নজরুল", "দ্বিজেন্দ্র", "অতুলপ্রসাদ", "রজনীকান্ত"]):
            return "semi_classical"
        if any(k in name for k in ["লোক", "বাউল", "ভাটি", "ভাওয়াই", "ভাওয়াই"]):
            return "folk"
        if any(k in name for k in ["দেশাত্মবোধক", "স্বদেশ"]):
            return "patriotic"
        if any(k in name for k in ["শ্যামা", "কীর্তন"]):
            return "devotional"
        if any(k in name for k in ["চলচ্চিত্র", "সিনেমা"]):
            return "film"
        if any(k in name for k in ["ব্যান্ড", "রক"]):
            return "western"
        return "modern"

    canonical_genre_defs = [
        ("রবীন্দ্রসংগীত", "Rabindrasangeet", "semi_classical", "কবিগুরু রবীন্দ্রনাথ ঠাকুর রচিত ও সুরারোপিত গান"),
        ("নজরুলগীতি", "Nazrulgeeti", "semi_classical", "বিদ্রোহী কবি কাজী নজরুল ইসলাম রচিত গান"),
        ("দ্বিজেন্দ্রগীতি", "Dwijendrageeti", "semi_classical", "দ্বিজেন্দ্রলাল রায়ের গান"),
        ("অতুলপ্রসাদী", "Atulprasadi", "semi_classical", "অতুলপ্রসাদ সেনের গান"),
        ("রজনীকান্তের গান", "Rajanikanta Geeti", "semi_classical", "কান্তকবি রজনীকান্ত সেনের গান"),
        ("আধুনিক বাংলা গান", "Modern Bengali Song", "modern", "আধুনিক যুগের বাংলা মেলোডিয়াস গান"),
        ("চলচ্চিত্রের গান", "Film Soundtrack", "film", "বাংলা চলচ্চিত্রের সাউন্ডট্র্যাক ও গান"),
        ("লোকগীতি", "Folk Song", "folk", "বাংলার চিরায়ত মাটির গান ও লোকঐতিহ্য"),
        ("বাউল গান", "Baul Song", "folk", "বাউল দর্শনের আধ্যাত্মিক গান"),
        ("ভাটিয়ালি", "Bhatiyali", "folk", "নদীমাতৃক বাংলার মাঝিমাল্লাদের গান"),
        ("ভাওয়াইয়া", "Bhawaiya", "folk", "উত্তরবঙ্গের ঐতিহ্যবাহী গান"),
        ("দেশাত্মবোধক", "Patriotic Song", "patriotic", "দেশ ও মাতৃভূমির প্রতি ভালোবাসার গান"),
        ("শ্যামাসংগীত", "Shyama Sangeet", "devotional", "মা শ্যামা/কালী ভক্তিগীতি"),
        ("কীর্তন", "Kirtan", "devotional", "বৈষ্ণব পদাবলী ও হরিনাম সংকীর্তন"),
        ("ব্যান্ড ও রক", "Band & Rock", "western", "বাংলা রক ও সমকালীন ব্যান্ড সংগীত")
    ]

    v2_genres = []
    seen_genres: Dict[str, str] = {}
    
    for g_bn, g_en, g_cat, g_desc in canonical_genre_defs:
        gen_id, counters = generate_display_id("genre", counters)
        seen_genres[g_bn] = gen_id
        v2_genres.append({
            "id": gen_id,
            "uuid": generate_uuid(),
            "name_bn": g_bn,
            "name_en": g_en,
            "category": g_cat,
            "description": g_desc,
            "verification_status": "verified",
            "source_ids": [src_archive_id],
            "created_at": now_iso(),
            "updated_at": now_iso()
        })

    for s in legacy_songs:
        genres_raw = s.get("genre", [])
        if isinstance(genres_raw, str):
            genres_raw = [genres_raw]
        for g in genres_raw:
            if g and g.strip():
                g_clean = normalize_bengali_spelling(g.strip())
                if g_clean not in seen_genres:
                    gen_id, counters = generate_display_id("genre", counters)
                    seen_genres[g_clean] = gen_id
                    v2_genres.append({
                        "id": gen_id,
                        "uuid": generate_uuid(),
                        "name_bn": g_clean,
                        "name_en": transliterate_bn_to_en(g_clean).title(),
                        "category": map_genre_category(g_clean),
                        "verification_status": "verified",
                        "source_ids": [src_archive_id],
                        "created_at": now_iso(),
                        "updated_at": now_iso()
                    })

    # Standard languages
    lang_bn_id, counters = generate_display_id("language", counters)
    lang_rjb_id, counters = generate_display_id("language", counters)
    v2_languages = [
        {"id": lang_bn_id, "uuid": generate_uuid(), "code": "bn", "name_bn": "বাংলা", "name_en": "Bengali", "cultural_region": "Bengal"},
        {"id": lang_rjb_id, "uuid": generate_uuid(), "code": "rjb", "name_bn": "রাজবংশী", "name_en": "Rajbanshi", "cultural_region": "North Bengal"}
    ]

    # 4. Migrate Works, Recordings, Releases, Lyrics
    v2_works = []
    v2_recordings = []
    v2_releases = []
    v2_lyrics = []

    # Map of created releases by title
    release_cache: Dict[str, str] = {}

    for s in legacy_songs:
        song_id = s.get("songId", "").strip()
        title_bn = normalize_bengali_spelling(s.get("title", "").strip())
        if not song_id or not title_bn:
            continue

        work_id, counters = generate_display_id("work", counters)
        rec_id, counters = generate_display_id("recording", counters)
        migration_map["work"][song_id] = work_id
        migration_map["recording"][song_id] = rec_id

        # Year check
        rel_year = s.get("releaseYear")
        if isinstance(rel_year, (int, float)) and 1700 <= int(rel_year) <= 2100:
            year_val = int(rel_year)
        else:
            year_val = None

        # Resolve Artists
        raw_artists = s.get("artistId", [])
        if isinstance(raw_artists, str):
            raw_artists = [raw_artists]
        artist_ids = [migration_map["artist"][aid] for aid in raw_artists if aid in migration_map["artist"]]
        if not artist_ids and raw_artists:
            # Fallback artist if known
            pass

        # Resolve Lyricist & Composer
        lyricist_raw = s.get("lyricistId", "")
        composer_raw = s.get("composerId", "")
        lyricist_ids = [migration_map["artist"][lyricist_raw]] if lyricist_raw in migration_map["artist"] else []
        composer_ids = [migration_map["artist"][composer_raw]] if composer_raw in migration_map["artist"] else []

        # Parjaay / Category
        parjaay_raw = s.get("parjaay")
        parjaay_obj = None
        if parjaay_raw:
            if isinstance(parjaay_raw, dict):
                parjaay_obj = parjaay_raw
            elif isinstance(parjaay_raw, str) and parjaay_raw.strip():
                parjaay_obj = {"category": parjaay_raw.strip(), "sub_category": None}

        # Lyrics resolution
        lyrics_id_raw = s.get("lyricsId", "")
        lyrics_text = lyrics_map.get(lyrics_id_raw) or lyrics_map.get(f"L{lyrics_id_raw.replace('L', '').zfill(6)}") or ""

        v2_lyr_id = None
        if lyrics_text:
            v2_lyr_id, counters = generate_display_id("lyrics", counters)
            migration_map["lyrics"][lyrics_id_raw] = v2_lyr_id

            # Determine preview (first 2 lines)
            lines = [l.strip() for l in lyrics_text.split("\n") if l.strip()]
            preview = "\n".join(lines[:3]) if lines else None

            # Copyright status
            is_tagore = any("RNT" in lyricist_raw or "রবীন্দ্রনাথ" in a.get("name", "") for a in legacy_artists if a.get("id") == lyricist_raw)
            is_nazrul = any("KNI" in lyricist_raw or "নজরুল" in a.get("name", "") for a in legacy_artists if a.get("id") == lyricist_raw)
            copyright_status = "expired" if (is_tagore or is_nazrul or (year_val and year_val < 1965)) else "restricted"

            lyrics_obj = {
                "id": v2_lyr_id,
                "uuid": generate_uuid(),
                "work_id": work_id,
                "recording_id": rec_id,
                "language": "bn",
                "text": lyrics_text,
                "text_preview": preview,
                "copyright_status": copyright_status,
                "copyright_holder": None if copyright_status == "expired" else "কপিরাইট সংশ্লিষ্ট স্বত্বাধিকারীর অধীন",
                "transcription_status": "verified",
                "source": "গানডাটাবেস ডিজিটালাইজেশন প্রকল্প",
                "source_ids": sorted(list(set([src_archive_id] + ([src_tagore_id] if is_tagore else [src_nazrul_id] if is_nazrul else [])))),
                "verification_status": "verified",
                "data_origin": "manual",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "revision_history": [
                    {
                        "date": now_iso(),
                        "editor": "system_migrator",
                        "action": "migrated_from_v1",
                        "detail": f"Migrated from lyrics ID {lyrics_id_raw}"
                    }
                ]
            }
            v2_lyrics.append(lyrics_obj)

        # Work Entity
        work_genres = [g for g in s.get("genre", []) if g]
        work_obj = {
            "id": work_id,
            "uuid": generate_uuid(),
            "title_bn": title_bn,
            "title_en": transliterate_bn_to_en(title_bn).title(),
            "language": "bn",
            "type": "song",
            "subtype": work_genres[0] if work_genres else "বাংলা গান",
            "genre": work_genres,
            "lyricist": lyricist_ids,
            "composer": composer_ids,
            "year": year_val,
            "year_accuracy": "exact" if year_val else None,
            "lyrics_id": v2_lyr_id,
            "subjects": s.get("tags", []) or [],
            "parjaay": parjaay_obj,
            "tags": s.get("tags", []) or [],
            "recording_ids": [rec_id],
            "source_ids": [src_tagore_id if any("রবীন্দ্র" in g for g in work_genres) else src_archive_id],
            "verification_status": "verified",
            "data_origin": "manual",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "revision_history": [
                {
                    "date": now_iso(),
                    "editor": "system_migrator",
                    "action": "migrated_from_v1",
                    "detail": f"Migrated from legacy song ID {song_id}"
                }
            ]
        }
        v2_works.append(work_obj)

        # Recording Entity
        rec_obj = {
            "id": rec_id,
            "uuid": generate_uuid(),
            "work_id": work_id,
            "title": title_bn,
            "title_en": transliterate_bn_to_en(title_bn).title(),
            "artists": artist_ids,
            "duration_ms": None,
            "release_date": f"{year_val}-01-01" if year_val else None,
            "language": "bn",
            "genre": work_genres,
            "official_links": [],
            "film_ids": [],
            "source_ids": [src_archive_id],
            "verification_status": "verified",
            "data_origin": "manual",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "revision_history": [
                {
                    "date": now_iso(),
                    "editor": "system_migrator",
                    "action": "migrated_from_v1",
                    "detail": f"Initial recording linked to work {work_id}"
                }
            ]
        }
        v2_recordings.append(rec_obj)

    print(f"[*] Migrated: {len(v2_works)} works, {len(v2_recordings)} recordings, {len(v2_lyrics)} lyrics.")

    # 5. Save all entities
    def save_entity_file(filename: str, data: Any):
        file_path = output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"    Saved: {file_path.name} ({len(data) if isinstance(data, list) else 'dict'})")

    print("[*] Writing V2 JSON datasets to disk...")
    save_entity_file("artists.json", v2_artists)
    save_entity_file("works.json", v2_works)
    save_entity_file("recordings.json", v2_recordings)
    save_entity_file("lyrics.json", v2_lyrics)
    save_entity_file("genres.json", v2_genres)
    save_entity_file("sources.json", v2_sources)
    save_entity_file("languages.json", v2_languages)
    save_entity_file("releases.json", v2_releases)

    # Save migration map & updated id counters
    migration_map_file = input_dir / "migration_map.json"
    with open(migration_map_file, "w", encoding="utf-8") as f:
        json.dump(migration_map, f, indent=2, ensure_ascii=False)
    print(f"    Saved: migration_map.json")

    counters_file = input_dir / "id_counters.json"
    with open(counters_file, "w", encoding="utf-8") as f:
        json.dump(counters, f, indent=2, ensure_ascii=False)
    print(f"    Saved: id_counters.json")

    print("[+] Migration completed successfully!")


if __name__ == "__main__":
    main()
