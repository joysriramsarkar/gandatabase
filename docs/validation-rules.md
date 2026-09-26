# Validation Rules — Gandatabase v2

> Run automatically on every Pull Request via GitHub Actions.

---

## ১. Schema Validation (Level 1)

Every JSON data file must pass its JSON Schema (in schema/).

- [ ] Required fields present (id, name_bn/title_bn, type, verification_status)
- [ ] Field types correct (string, integer, array, object)
- [ ] String patterns match (IDs ART\\d{6}, dates, language codes)
- [ ] Enum values valid
- [ ] Array items unique (where required)
- [ ] No extra/unknown fields (additionalProperties: false)

---

## ২. Cross-Reference Integrity (Level 2)

All ID references must point to existing entities.

| Field | Must Reference |
|---|---|
| work_id in recording | WORK##### in works |
| lyrics_id in work | WORK##### / LYR##### |
| recording_id in release | REC##### in recordings |
| artist_id/director_ids/actor_ids | ART##### in artists |
| source_ids in any entity | SRC##### in sources |
| external_ids.musicbrainz | Valid MBID format |
| external_ids.wikidata | Valid Q##### format |

**Broken reference → CI fails:** ❌ Broken Reference: REC000100 → WORK999999

---

## ৩. Duplicate Detection (Level 3)

**Titles:** Unicode NFC → punctuation removal → whitespace collapse → lowercase. Fuzzy match (Levenshtein ≤ 3). Transliteration match (bn ↔ en).

Example duplicates:
- এই পথ যদি না শেষ হয়
- এই পথ যদি না শেষ হয়
- Ei Poth Jodi Na Sesh Hoy

All flagged → human review.

---

## ৪. Data Quality Rules (Level 4)

- **Year:** 1700 ≤ year ≤ 2100
- **Source:** Verified entities must have ≥ 1 source_ids
- **AI:** data_origin=ai_suggestion → verification_status MUST be pending
- **ID format:** ART###### (6-digit zero-padded)
- **Language:** Valid ISO 639 code
- **ISRC:** XX-XXX-XXX-XX-X format

---

## ৫. Name & Role Validation

name_bn: not empty, Bengali/English script, no special chars except . - '
Artist roles enum: singer, composer, music_director, lyricist, actor, director, producer, instrumentalist, conductor, dancer, writer, poet
Gender: male, female, other

---

## ৬. Verification Workflow Check

Status: pending → in_review → verified/rejected
AI data origin → MUST be pending (never auto-verified)

---

## ৭. Copyright (Lyrics)

copyright_status required: public/restricted/pending_review/expired
- public: full lyrics visible
- restricted: only metadata + text_preview (2-3 lines max)

---

## ৮. CI Checklist (every PR)

1. JSON Schema Validation (all entities pass)
2. Cross-Reference Check (no broken refs)
3. Duplicate Detection (fuzzy match)
4. Year Range Check (1700-2100)
5. Source Check (verified has sources)
6. AI Data Check (AI-suggested not verified)
7. Alias Uniqueness

---

## ৯. CI Failure Examples

❌ Schema Failed: data/artists/ART000123.json — name_bn is required
❌ Broken Ref: data/recordings/REC000100.json — work_id WORK999999 not found
❌ Duplicate: WORK000145 ≈ WORK000231 — human review required
❌ AI Verified: WORK000456 — data_origin=ai_suggestion but verified
❌ No Source: ART000789 — verified entry missing source_ids
