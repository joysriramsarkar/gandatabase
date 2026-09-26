# গান ডেটাবেস (Gandatabase v2) — স্কিমা ডকুমেন্টেশন

> **লালি:** V2 schema এখন **Source of Truth** হিসেবে কাজ করবে। পুরনো songs.json + artists.json ভান্ডার হলো **legacy**।

---

## ১. Entity Overview

| Entity | ID | Folder | Description |
|---|---|---|---|
| Artist | ART000001 | data/artists/ | গায়ক, সুরকার, গীতিকার, পরিচালক |
| Work | WORK000001 | data/works/ | সৃষ্টিকর্ম (গান/কবিতা/বাদ্য) |
| Recording | REC000001 | data/recordings/ | নির্দিষ্ট recording |
| Release | REL000001 | data/releases/ | Album/Film/Single/Compilation |
| Film | FILM000001 | data/films/ | চলচ্চিত্র |
| Lyrics | LYR000001 | data/lyrics/ | গানের কথা (rights-dependent) |
| Genre | GEN000001 | data/genres/ | সংগীত ধারা |
| Language | LANG000001 | data/languages/ | ভাষা ও সাংস্কৃতিক অঞ্চল |
| Label | LAB000001 | — | Record label / Studio |
| Source | SRC000001 | — | তথ্যের উৎস |
| Alias | ALIAS000001 | — | Transliteration / normalization |
| Relationship | RELNSH000001 | — | Entity relationship |

---

## ২. Core Relationship Graph

`	ext
Artist ─ composed ──→ Work
Artist ─ wrote_lyrics → Work
Artist ─ performed ──→ Recording
Artist ─ directed ───→ Film
Work ─ has_recording → Recording
Work ─ has_lyrics ──→ Lyrics
Recording ─ part_of → Release
Recording ─ featured_in → Film
Release ─ contains → Recording
Release ─ label → Label
Film ─ has_work → Work
`

---

## ৩. Entity Details

### 3.1-3.12
See schema/ folder for full JSON Schema. Summary:
- **Artist**: name_bn, type, roles, bio, external_ids, verification_status, data_origin
- **Work**: title_bn/en, lyricist[], composer[], year, genre[], lyrics_id, recording_ids
- **Recording**: work_id, artists[], duration_ms, isrc, official_links (no audio), film_ids
- **Release**: type (album/film/single), year, track_list, label_id, barcode
- **Film**: type, year, director_ids, actor_ids, music_director_ids, work_ids, recording_ids
- **Lyrics**: copyright_status, transcription_status, text_preview, text
- **Genre**: name_bn/en, category, parent_genre_id (open-ended taxonomy)
- **Language**: code (ISO639), name_bn/en, cultural_region
- **Label**: name, type, external_ids
- **Source**: type, title, author, publisher, year, url, reliability
- **Alias**: entity_type, entity_id, alias_text, alias_type, language
- **Relationship**: entity_a, entity_b, relationship_type, source_id

---

## ৪. Universal Fields

Every entity has: id, uuid, verification_status, data_origin, source_ids, created_at, updated_at, revision_history.

---

## ৫. Verification Workflow

raw data → Parser → AI suggestion → Validation → Human review → Verified
AI data ALWAYS stays pending until human verifies.

---

## ৬. REST API

GET /api/artists /api/works /api/recordings /api/releases /api/films
GET /api/artists/:id /api/works/:id /api/recordings/:id /api/films/:id
GET /api/lyrics/:id /api/genres /api/languages /api/sources
GET /api/search /api/timeline /api/contributions

---

## ৭. Validation

Full rules: docs/validation-rules.md
- All IDs match pattern | No broken refs | No duplicate aliases
- Year 1700-2100 | Verified needs sources | AI never auto-verified

---

## ৮. Files

**Schemas:** schema/*.schema.json (12 files)
**Docs:** docs/schema.md, docs/id-strategy.md, docs/validation-rules.md
**Scripts:** scripts/import/migrate_v1_to_v2.py, scripts/validate/validate.py
