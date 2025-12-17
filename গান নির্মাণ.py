import json
import re
import os
import time
from difflib import get_close_matches
from dotenv import load_dotenv
import warnings

# Suppress warnings if we fall back to deprecated usage, or from other libs
warnings.filterwarnings("ignore", category=FutureWarning)

# Try importing the new library
try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False
    try:
        import google.generativeai as old_genai
        HAS_OLD_GENAI = True
    except ImportError:
        HAS_OLD_GENAI = False

# .env ফাইল থেকে এনভায়রনমেন্ট ভেরিয়েবল লোড করা
load_dotenv()

# ---------------- কনফিগারেশন ----------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# এআই ব্যবহার করবেন কি না? (Key থাকলেই কেবল True)
USE_AI = bool(GOOGLE_API_KEY)

# ফাইল পাথ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LYRICS_FILE = os.path.join(BASE_DIR, 'lyrics.ts')
SONGS_FILE = os.path.join(BASE_DIR, 'songs.json')
ARTISTS_FILE = os.path.join(BASE_DIR, 'artists.json')

# ডিফল্ট আইডি (রবীন্দ্রনাথ ঠাকুর)
DEFAULT_ID = "RNT01"
# -------------------------------------------

def setup_ai():
    """এআই সেটআপ এবং ক্লায়েন্ট রিটার্ন"""
    if not USE_AI:
        return None

    print("   AI সংযোগ স্থাপন করা হচ্ছে...")
    try:
        if HAS_NEW_GENAI:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            return {'client': client, 'type': 'new'}
        elif HAS_OLD_GENAI:
            old_genai.configure(api_key=GOOGLE_API_KEY)
            return {'client': old_genai, 'type': 'old'}
        else:
            print("   [ত্রুটি] 'google-genai' বা 'google-generativeai' লাইব্রেরি পাওয়া যায়নি।")
            return None
    except Exception as e:
        print(f"   [ত্রুটি] AI সেটআপে সমস্যা: {e}")
        return None

def load_artists_map(filepath):
    """artists.json থেকে নাম এবং আইডির ম্যাপ তৈরি করে"""
    if not os.path.exists(filepath):
        print(f"   সতর্কতা: '{filepath}' পাওয়া যায়নি।")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"   আর্টিস্ট ফাইল '{filepath}' পড়তে সমস্যা: {e}")
        return {}

    artist_map = {}
    for artist in data:
        artist_id = artist.get('id')
        artist_name = artist.get('name')
        if artist_id and artist_name and artist_id != "01":
            norm_name = artist_name.strip().lower()
            artist_map[norm_name] = artist_id
            
            aliases = artist.get('alias', [])
            if isinstance(aliases, str):
                aliases = [aliases]
            for alias in aliases:
                artist_map[alias.strip().lower()] = artist_id
    return artist_map

def get_ids_from_names(names, artist_map):
    """নাম থেকে আইডি খুঁজে বের করা"""
    ids = []
    if not names: return ids
    if isinstance(names, str): names = [names]
    
    for name in names:
        norm_name = name.strip().lower()
        if norm_name in artist_map:
            ids.append(artist_map[norm_name])
        else:
            matches = get_close_matches(norm_name, artist_map.keys(), n=1, cutoff=0.85)
            if matches:
                ids.append(artist_map[matches[0]])
    
    return list(set(ids))

def get_metadata_from_ai(ai_obj, title, lyrics_snippet):
    """জেমিনি এপিআই কল"""
    if not ai_obj: return None

    prompt = f"""
    Analyze this Bengali song. Return ONLY JSON.
    Title: "{title}"
    Lyrics: "{lyrics_snippet}..."
    
    JSON Schema:
    {{
        "genre": ["String"],
        "lyricist_names": ["String"],
        "composer_names": ["String"],
        "artist_names": ["String"],
        "release_year": Integer,
        "tags": ["String"]
    }}
    IMPORTANT: Return names in BENGALI script (e.g. "কাজী নজরুল ইসলাম", "রবীন্দ্রনাথ ঠাকুর") matching standard spelling.
    If artist is Rabindranath Tagore, use "রবীন্দ্রনাথ ঠাকুর".
    """
    
    retries = 3
    model_name = "gemini-2.0-flash"

    for attempt in range(retries):
        try:
            time.sleep(1) # রেট লিমিট এড়াতে

            text_resp = ""
            
            if ai_obj['type'] == 'new':
                client = ai_obj['client']
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                text_resp = response.text
            else:
                # Fallback to old library
                model = ai_obj['client'].GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                text_resp = response.text

            # রেসপন্স ক্লিন করা
            if not text_resp: return None

            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_resp, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = text_resp.find('{')
                end = text_resp.rfind('}') + 1
                json_str = text_resp[start:end] if start != -1 and end != -1 else None

            if json_str:
                return json.loads(json_str)
            return None
        except Exception as e:
            print(f"      (চেষ্টা {attempt+1}/{retries} ব্যর্থ: {e})")
            time.sleep(2 * (attempt + 1))
    return None

def parse_lyrics_file(filepath, artist_map):
    """lyrics.ts ফাইল পার্স করে আর্টিস্ট অনুযায়ী লিরিক্স বের করা"""
    if not os.path.exists(filepath):
        print(f"   '{filepath}' ফাইলটি পাওয়া যায়নি!")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by comments /* ... */
    # This regex captures the comment content in odd indices
    parts = re.split(r'/\*(.*?)\*/', content, flags=re.DOTALL)

    parsed_entries = []

    # ডিফল্ট আর্টিস্ট (রবীন্দ্রনাথ)
    current_artist_id = DEFAULT_ID

    # প্রথম অংশ (যদি ফাইলের শুরুতে কোনো কমেন্ট না থাকে)
    if parts[0].strip():
       # শুরুতে কিছু থাকলে ডিফল্ট আর্টিস্ট দিয়ে পার্স করা হবে
       pass

    # parts[0] is content before first comment
    # parts[1] is first comment
    # parts[2] is content after first comment
    # ...

    # Process the first chunk (before any comment)
    # Usually lyrics.ts starts with [ then maybe a comment.
    # If the first comment is Rabindranath, then subsequent objects belong to him.

    # Let's iterate through parts
    # If we find a comment that matches an artist name, we update current_artist_id
    # Then we parse the following content block for lyrics
    
    # Regex to find id and lyrics within a block
    # Note: Using ` ` for lyrics content as in the file
    entry_pattern = re.compile(r'id\s*:\s*["\'](L\d+)["\']\s*,\s*lyrics\s*:\s*`([^`]*)`', re.DOTALL)

    # First block (index 0)
    if parts[0]:
        matches = entry_pattern.findall(parts[0])
        for mid, mtext in matches:
            if mtext.strip():
                parsed_entries.append({
                    'id': mid,
                    'text': mtext,
                    'artist_id': current_artist_id # Default
                })

    for i in range(1, len(parts), 2):
        comment = parts[i].strip()
        content_block = parts[i+1] if i+1 < len(parts) else ""

        # Check if comment is an artist
        # Try exact match or partial match in map
        # Also clean up "এখান থেকে ... লিখেছেন" type comments

        # Simple lookup
        artist_key = comment.lower().strip()

        found_id = None
        if artist_key in artist_map:
            found_id = artist_map[artist_key]
        else:
            # Try to find if any artist name is IN the comment
            # e.g. "কাজী নজরুল ইসলাম" in "/* কাজী নজরুল ইসলাম */" (already stripped)
            # or "এখান থেকে বুব্ধদেব মহন্ত লিখেছেন" -> "বুব্ধদেব মহন্ত" ?? Typo in file?
            # "বুব্ধদেব মহন্ত" is not in artists.json? Let's check artists.json

            # Let's try closest match for the whole comment string against keys
            matches = get_close_matches(artist_key, artist_map.keys(), n=1, cutoff=0.8)
            if matches:
                found_id = artist_map[matches[0]]

        if found_id:
            current_artist_id = found_id
            # print(f"   [আর্টিস্ট পরিবর্তন] {comment} -> {found_id}")
        else:
            # If comment is not an artist (e.g. "এই লিরিক্সের..."), keep previous artist
            pass

        # Parse content block
        matches = entry_pattern.findall(content_block)
        for mid, mtext in matches:
            if mtext.strip():
                parsed_entries.append({
                    'id': mid,
                    'text': mtext,
                    'artist_id': current_artist_id
                })

    return parsed_entries

def main():
    ai_obj = setup_ai()
    artist_map = load_artists_map(ARTISTS_FILE)

    print("১. লিরিক্স ফাইল পড়া হচ্ছে...")
    lyrics_entries = parse_lyrics_file(LYRICS_FILE, artist_map)

    print(f"২. মোট লিরিক্স এন্ট্রি: {len(lyrics_entries)} টি")

    songs_data = []
    seen_titles = set()
    counter = 1
    
    print("\n   --- প্রসেসিং শুরু ---")

    for entry in lyrics_entries:
        lyrics_id = entry['id']
        lyrics_text = entry['text']
        artist_id = entry['artist_id']

        clean_text = lyrics_text.strip()
        
        # টাইটেল প্রসেসিং (প্রথম লাইন)
        first_line = clean_text.split('\n')[0].strip()
        # Remove common prefixes like numbers or bullets if any (regex can be improved)
        title = re.sub(r'^.*?[।:]\s*', '', first_line)
        title = title.replace('\\', '').replace('"', '').replace('—', '').strip()
        final_title = title[:100] + "..." if len(title) > 100 else title

        # ডুপ্লিকেট চেক (টাইটেল দিয়ে)
        check_key = re.sub(r'\s+', '', final_title)
        if check_key in seen_titles:
            # print(f"   [বাদ - ডুপ্লিকেট] {final_title}")
            continue
        seen_titles.add(check_key)

        # ডিফল্ট মেটাডাটা
        # এখানে আমরা আর্টিস্ট আইডি সেট করছি পার্সিং থেকে পাওয়া আইডি দিয়ে
        meta = {
            "artistId": [artist_id],
            "lyricistId": artist_id if artist_id != DEFAULT_ID else DEFAULT_ID, # Assuming singer/writer same often
            "composerId": artist_id if artist_id != DEFAULT_ID else DEFAULT_ID,
            "genre": ["রবীন্দ্রসংগীত"] if artist_id == DEFAULT_ID else ["আধুনিক"],
            "tags": [],
            "releaseYear": 2000
        }

        # Specific fix for Nazrul
        if artist_id == "KNI01": # Kazi Nazrul Islam
             meta["genre"] = ["নজরুল গীতি"]

        # এআই কল (যদি থাকে)
        if ai_obj:
            print(f"   [{counter}] AI প্রসেসিং: {final_title}")
            ai_data = get_metadata_from_ai(ai_obj, final_title, clean_text[:200])
            
            if ai_data:
                meta["genre"] = ai_data.get("genre", meta["genre"])
                meta["tags"] = ai_data.get("tags", meta["tags"])
                meta["releaseYear"] = ai_data.get("release_year") or 2000
                
                # আইডি ম্যাপিং আপডেট
                l_ids = get_ids_from_names(ai_data.get("lyricist_names", []), artist_map)
                if l_ids: meta["lyricistId"] = l_ids[0]

                c_ids = get_ids_from_names(ai_data.get("composer_names", []), artist_map)
                if c_ids: meta["composerId"] = c_ids[0]

                a_ids = get_ids_from_names(ai_data.get("artist_names", []), artist_map)
                if a_ids: meta["artistId"] = a_ids
        
        # Fallbacks logic
        if not meta["lyricistId"]: meta["lyricistId"] = artist_id
        if not meta["composerId"]: meta["composerId"] = artist_id
        
        # গানের অবজেক্ট
        song_entry = {
            "songId": f"S{counter:05d}",
            "title": final_title,
            "artistId": meta["artistId"],
            "lyricistId": meta["lyricistId"],
            "composerId": meta["composerId"],
            "lyricsId": lyrics_id,
            "parjaay": None,
            "genre": meta["genre"],
            "releaseYear": meta["releaseYear"],
            "tags": meta["tags"]
        }
        
        songs_data.append(song_entry)
        counter += 1

        if counter % 100 == 0:
            print(f"   ... {counter} টি গান প্রসেস হয়েছে ...")

    # সেভ করা
    try:
        with open(SONGS_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump(songs_data, f, ensure_ascii=False, indent=2)
        print(f"\n   সফল! ফাইল সেভ হয়েছে: {SONGS_FILE}")
        print(f"   মোট গান: {len(songs_data)}")
    except Exception as e:
        print(f"\n   সেভ করতে সমস্যা: {e}")

if __name__ == "__main__":
    main()
