# Lyrics Processor

This project extracts Bengali lyrics from a TypeScript file (`lyrics.ts`), processes them, and generates a JSON database (`songs.json`). It can optionally use Google's Gemini AI to enrich the metadata (Artist, Composer, Genre, Release Year, etc.).

## Prerequisites

- Python 3.8 or higher
- A Google Cloud API Key (for Gemini AI features, optional)

## Installation

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Set up your Google API Key:
   - Create a `.env` file in the project root.
   - Add your API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```

## Usage

Run the script to process the lyrics:

```bash
python "গান নির্মাণ.py"
```

The script will:
1. Read `lyrics.ts`.
2. Extract lyrics and IDs.
3. Check for duplicates.
4. (If API key is present) Query Gemini AI for metadata.
5. Save the result to `songs.json`.

## Files

- `lyrics.ts`: The source file containing lyrics.
- `artists.json`: A database of artists for ID mapping.
- `songs.json`: The output JSON file.
- `গান নির্মাণ.py`: The main processing script.
