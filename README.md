# বাংলা গানের ডেটাবেস (Gandatabase v2)

> **Source of Truth** — বাংলা সংগীতের structured knowledge base।

---

## Schema Overview

Core chain: **Artist → Work → Recording → Release → Film**

---

## Repository Structure

`
gandatabase/
├── data/                         # Entity data
│   ├── artists/ works/ recordings/
│   ├── releases/ films/ lyrics/
│   ├── genres/ languages/
│   ├── sources/ aliases/
│   └── relationships/
├── schema/                       # 12 JSON Schema files
├── scripts/                      # import, validate, normalize, etc.
├── docs/                         # schema.md, id-strategy.md, validation-rules.md
├── tests/
├── .github/workflows/validate.yml
├── .gitignore
└── README.md
`

---

## Legacy Files

Kept for migration reference:
- songs.json, artists.json, lyrics.ts, artists_new.json
- song_generator.py, ID_generator.html (deprecated)

`ash
python scripts/import/migrate_v1_to_v2.py --input-dir ./ --output-dir ./v2_output
`

---

## Validation (Every PR)

1. JSON Schema Validation
2. Cross-Reference Check
3. Duplicate Detection (fuzzy match)
4. Year Range (1700-2100)
5. Source Check (verified needs sources)
6. AI Data Check (AI NEVER auto-verified)

---

## AI Policy

AI is a research assistant only:

✅ Can: suggest metadata, detect duplicates, transliterate, generate tokens, suggest relations
❌ Cannot: auto-verify, write final data, set verified status, override human review, create sources

All AI data: data_origin=ai_suggestion, verification_status=pending

---

## Verification Workflow

raw data → Parser → AI suggestion → Validation → Human review → Verified
                                         ↑
                               AI stays PENDING

---

## Related Repos

| Repository | Role |
|---|---|
| gandatabase | Source of Truth |
| banglagan | Web platform |
| banglagan_android_app | Android client |
| banglagan-api (future) | REST API |

---

## Contributing

- Never submit AI data as verified
- Always cite sources (source_ids)
- Check for duplicates
- Use proper ID format (ART000001)
- See অবদান.md for full guidelines

---

## License

Educational/research use. Song lyrics subject to copyright.
