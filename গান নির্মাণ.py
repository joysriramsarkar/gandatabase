import json
import re
import os
import time
import google.generativeai as genai
from difflib import get_close_matches
from dotenv import load_dotenv

# .env ফাইল থেকে এনভায়রনমেন্ট ভেরিয়েবল লোড করা
load_dotenv()

# ---------------- কনফিগারেশন ----------------
# সতর্কতা: আপনার নতুন জেনারেট করা API Key টি এখানে বসান
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# এআই ব্যবহার করবেন কি না? (True = হ্যাঁ, False = না)
USE_AI = True 

# ফাইল পাথ (একই ফোল্ডারে থাকলে ফাইলের নাম দিলেই হবে)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LYRICS_FILE = os.path.join(BASE_DIR, 'lyrics1.ts')
SONGS_FILE = os.path.join(BASE_DIR, 'songs1.json')
ARTISTS_FILE = os.path.join(BASE_DIR, 'artists.json')

# ডিফল্ট আইডি (রবীন্দ্রনাথ ঠাকুর)
DEFAULT_ID = "RNT01"
# -------------------------------------------

# গ্লোবাল ভেরিয়েবল
model = None

def setup_ai():
    """এআই সেটআপ এবং মডেল সিলেকশন"""
    global model
    if not USE_AI: return

    genai.configure(api_key=GOOGLE_API_KEY)
    
    print("   AI মডেল যাচাই করা হচ্ছে...")
    try:
        # মডেল খোঁজার লজিক
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # আমরা এই মডেলগুলো খুঁজব (অগ্রাধিকার ভিত্তিতে)
        priority_models = [
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash',
            'models/gemini-pro'
        ]
        
        selected_model = None
        for pm in priority_models:
            if pm in available_models:
                selected_model = pm
                break
        
        # যদি প্রায়োরিটি লিস্টে না থাকে, তবে লিস্টের প্রথমটি নেব
        if not selected_model and available_models:
            selected_model = available_models[0]

        if selected_model:
            print(f"   [সফল] নির্বাচিত মডেল: {selected_model}")
            model = genai.GenerativeModel(selected_model)
        else:
            print("   [ত্রুটি] কোনো উপযুক্ত মডেল পাওয়া যায়নি।")
            
    except Exception as e:
        print(f"   [ত্রুটি] মডেল সেটআপে সমস্যা: {e}")

def load_artists_map(filepath):
    """artists.json থেকে নাম এবং আইডির ম্যাপ তৈরি করে"""
    if not os.path.exists(filepath):
        print(f"   সতর্কতা: '{filepath}' পাওয়া যায়নি।")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f: # utf-8-sig বাদ দেওয়া হলো যদি সমস্যা করে
            data = json.load(f)
    except:
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception as e:
            print(f"   আর্টিস্ট ফাইল পড়তে সমস্যা: {e}")
            return {}
    
    artist_map = {}
    for artist in data:
        if not artist.get('id') or artist.get('id') == "01": continue
        
        norm_name = artist['name'].strip().lower()
        artist_map[norm_name] = artist['id']
        
        if 'alias' in artist:
            aliases = artist['alias'] if isinstance(artist['alias'], list) else [artist['alias']]
            for alias in aliases:
                artist_map[alias.strip().lower()] = artist['id']
    
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

def get_metadata_from_ai(title, lyrics_snippet):
    """জেমিনি এপিআই কল"""
    if not model: return None

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
    If artist is Rabindranath Tagore, use exactly "Rabindranath Tagore".
    """
    
    retries = 3
    for attempt in range(retries):
        try:
            time.sleep(2) # রেট লিমিট এড়াতে
            response = model.generate_content(prompt)
            
            # রেসপন্স ক্লিন করা
            text_resp = response.text
            start = text_resp.find('{')
            end = text_resp.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text_resp[start:end])
            return None
            
        except Exception as e:
            print(f"      (চেষ্টা {attempt+1}/{retries} ব্যর্থ: {e})")
            time.sleep(3)
    
    return None

def main():
    setup_ai()
    artist_map = load_artists_map(ARTISTS_FILE)

    if not os.path.exists(LYRICS_FILE):
        print(f"   '{LYRICS_FILE}' ফাইলটি পাওয়া যায়নি!")
        return

    with open(LYRICS_FILE, 'r', encoding='utf-8') as f: # utf-8 বা utf-8-sig
        content = f.read()

    # Regex: আইডি এবং লিরিক্স
    pattern = re.compile(r'id\s*:\s*["\'](L\d+)["\']\s*,\s*lyrics\s*:\s*`([^`]*)`', re.DOTALL)
    matches = pattern.findall(content)
    
    print(f"২. লিরিক্স এন্ট্রি পাওয়া গেছে: {len(matches)} টি")

    songs_data = []
    seen_titles = set()
    counter = 1
    
    # নতুন এবং ডুপ্লিকেট গানগুলো বাদ দিয়ে প্রসেস করা
    valid_matches = []
    for mid, mtext in matches:
        if mtext.strip(): # খালি লিরিক্স বাদ
            valid_matches.append((mid, mtext))
    
    print(f"   খালি লিরিক্স বাদ দিয়ে বাকি আছে: {len(valid_matches)} টি")
    print("\n   --- প্রসেসিং শুরু ---")

    for lyrics_id, lyrics_text in valid_matches:
        clean_text = lyrics_text.strip()
        
        # টাইটেল প্রসেসিং
        first_line = clean_text.split('\n')[0].strip()
        title = re.sub(r'^.*?[।:]\s*', '', first_line)
        title = title.replace('\\', '').replace('"', '').replace('—', '').strip()
        final_title = title[:100] + "..." if len(title) > 100 else title

        # ডুপ্লিকেট চেক
        check_key = re.sub(r'\s+', '', final_title)
        if check_key in seen_titles:
            print(f"   [বাদ - ডুপ্লিকেট] {final_title}")
            continue
        seen_titles.add(check_key)

        # ডিফল্ট মেটাডাটা
        meta = {
            "artistId": [DEFAULT_ID],
            "lyricistId": DEFAULT_ID,
            "composerId": DEFAULT_ID,
            "genre": ["রবীন্দ্রসংগীত"],
            "tags": ["রবীন্দ্রসংগীত"],
            "releaseYear": 2000
        }

        # এআই কল
        if model:
            print(f"   [{counter}] প্রসেসিং: {final_title}")
            ai_data = get_metadata_from_ai(final_title, clean_text[:200])
            
            if ai_data:
                meta["genre"] = ai_data.get("genre", meta["genre"])
                meta["tags"] = ai_data.get("tags", meta["tags"])
                meta["releaseYear"] = ai_data.get("release_year") or 2000
                
                # আইডি ম্যাপিং
                l_ids = get_ids_from_names(ai_data.get("lyricist_names", []), artist_map)
                if l_ids: meta["lyricistId"] = l_ids[0]

                c_ids = get_ids_from_names(ai_data.get("composer_names", []), artist_map)
                if c_ids: meta["composerId"] = c_ids[0]

                a_ids = get_ids_from_names(ai_data.get("artist_names", []), artist_map)
                if a_ids: meta["artistId"] = a_ids
                elif meta["lyricistId"] != DEFAULT_ID:
                    meta["artistId"] = [meta["lyricistId"]]

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

    # সেভ করা
    try:
        with open(SONGS_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump(songs_data, f, ensure_ascii=False, indent=2)
        print(f"\n   সফল! ফাইল সেভ হয়েছে: {SONGS_FILE}")
    except Exception as e:
        print(f"\n   সেভ করতে সমস্যা: {e}")

if __name__ == "__main__":
    main()