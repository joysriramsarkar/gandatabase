# ID Strategy — Centralized

> **Note:** `ID_generator.html` (legacy) is being deprecated. All IDs are now programmatically generated.

---

## ১. Two-Layer ID System

### Display ID (Human-readable)
```text
ART000001     — Artist
WORK000001    — Work
REC000001     — Recording
REL000001     — Release/Film
FILM000001    — Film
LYR000001     — Lyrics
SRC000001     — Source
GEN000001     — Genre
LANG000001    — Language
LAB000001     — Label
ALIAS000001   — Alias
RELNSH000001  — Relationship
```

### Internal UUID (System)
Every entity also has a `uuid` field for system-level operations (merging duplicates, cross-system references, etc.):
```json
{
  "id": "ART000001",
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Why both?**
- Display ID: Human-friendly, sortable, database-index friendly
- UUID: System-friendly, merge-safe, external-system compatible

---

## ২. ID Generation Rules

### Sequential Counter (Per Entity)

```text
Entity     Prefix     Example
Artist     ART        ART000001
Work       WORK       WORK000001
Recording  REC        REC000001
Release    REL        REL000001
Film       FILM       FILM000001
Lyrics     LYR        LYR000001
Source     SRC        SRC000001
Genre      GEN        GEN000001
Language   LANG       LANG000001
Label      LAB        LAB000001
Alias      ALIAS      ALIAS000001
Relationship RELNSH   RELNSH000001
```

### ID Counter Storage

A centralized `id_counters.json` (or database auto-increment) tracks the latest ID per entity:

```json
{
  "artist": 1247,
  "work": 5832,
  "recording": 12041,
  "release": 3201,
  "film": 891,
  "lyrics": 7821,
  "source": 412,
  "genre": 45,
  "language": 28,
  "label": 178,
  "alias": 15630,
  "relationship": 28400
}
```

### Programmatic Generation (Python)

```python
def generate_id(entity_type: str, counter_file: str = "id_counters.json") -> str:
    """Generate a new sequential display ID."""
    prefix_map = {
        "artist": "ART", "work": "WORK", "recording": "REC",
        "release": "REL", "film": "FILM", "lyrics": "LYR",
        "source": "SRC", "genre": "GEN", "language": "LANG",
        "label": "LAB", "alias": "ALIAS", "relationship": "RELNSH"
    }
    prefix = prefix_map[entity_type]

    with open(counter_file, 'r') as f:
        counters = json.load(f)

    next_num = counters[entity_type] + 1
    counters[entity_type] = next_num

    with open(counter_file, 'w') as f:
        json.dump(counters, f, indent=2)

    return f"{prefix}{next_num:06d}"
```

```python
import uuid
def generate_uuid():
    """Generate internal UUID."""
    return str(uuid.uuid4())
```

---

## ৩. ID Convention Reference

| Purpose | Format | Example |
|---|---|---|
| Artist ID | `ART######` | `ART000123` |
| Work ID | `WORK######` | `WORK000456` |
| Recording ID | `REC######` | `REC000789` |
| Release ID | `REL######` | `REL000321` |
| Film ID | `FILM######` | `FILM000654` |
| Lyrics ID | `LYR######` | `LYR000987` |
| Source ID | `SRC######` | `SRC000111` |
| Genre ID | `GEN######` | `GEN000042` |
| Language ID | `LANG######` | `LANG000028` |
| Label ID | `LAB######` | `LAB000178` |
| Alias ID | `ALIAS######` | `ALIAS000001` |
| Relationship ID | `RELNSH######` | `RELNSH000001` |

---

## ৪. Legacy ID Migration

Old IDs from v1:
- `RNT01`, `KNI01`, `DLR01` → Artist (artists.json)
- `S00001`, `S00002` → Song (songs.json)
- `L000001`, `L000002` → Lyrics (lyrics.ts / songs.json)

Migration mapping stored in `migration_map.json`:
```json
{
  "artist": {
    "RNT01": "ART000001",
    "KNI01": "ART000002",
    "DLR01": "ART000003"
  },
  "work": {
    "S00001": "WORK000001",
    "S00002": "WORK000002"
  },
  "lyrics": {
    "L000001": "LYR000001",
    "L000002": "LYR000002"
  }
}
```

---

## ৫. External ID Mapping

External system IDs stored within entities:

```json
{
  "id": "ART000001",
  "external_ids": {
    "musicbrainz": "a1b2c3d4-...",
    "wikidata": "Q12345",
    "isni": "0000000000000",
    "spotify": "6K...",
    "youtube_music": "UC..."
  }
}
```

**No external ID is treated as authoritative.** External IDs are enrichment only. All data still requires local verification.

---

## ৬. Anti-patterns

❌ **DON'T:** Use sequential integers (1, 2, 3)
❌ **DON'T:** Use auto-generated names (Song1, Artist2)
❌ **DON'T:** Share ID space across entity types
❌ **DON'T:** Keep `ID_generator.html` as the source of truth
✅ **DO:** Use prefix + 6-digit zero-padded number
✅ **DO:** Also store UUID for internal operations
✅ **DO:** Keep migration map when migrating legacy data
