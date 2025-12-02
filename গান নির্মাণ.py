import json
import re
import os

def process_lyrics_and_generate_json(input_file, output_file):
    try:
        abs_output_path = os.path.abspath(output_file)
        
        print(f"১. '{input_file}' ফাইলটি পড়ার চেষ্টা করা হচ্ছে...")
        if not os.path.exists(input_file):
            print(f"   ভুল: '{input_file}' ফাইলটি পাওয়া যায়নি!")
            return

        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   ফাইল পড়া হয়েছে। ফাইলের সাইজ: {len(content)} ক্যারেক্টার।")

        # Regex প্যাটার্ন (আগের মতোই)
        pattern = re.compile(r'id\s*:\s*["\'](L\d+)["\']\s*,\s*lyrics\s*:\s*`([^`]*)`', re.DOTALL)
        
        matches = pattern.findall(content)
        
        songs_data = []
        counter = 1
        skipped_count = 0

        print(f"২. মোট এন্ট্রি পাওয়া গেছে: {len(matches)} টি")

        if len(matches) == 0:
            print("   সতর্কতা: কোনো গান পাওয়া যায়নি! ফরম্যাট চেক করুন।")
            return

        # ডেটা প্রসেস করা
        print("\n   --- প্রসেসিং শুরু ---")
        
        for lyrics_id, lyrics_text in matches:
            clean_text = lyrics_text.strip()
            
            # লজিক: যদি লিরিক্স একদম খালি থাকে, তবে সেটা বাদ দেব (Skip)
            if not clean_text:
                skipped_count += 1
                continue

            # গান আইডি তৈরি
            song_id = f"S{counter:05d}"
            
            # টাইটেল বের করা
            first_line = clean_text.split('\n')[0].strip()
            title = first_line.replace('\\', '').replace('"', '').replace('—', '').strip()
            if len(title) > 100:
                    title = title[:100] + "..."

            song_entry = {
                "songId": song_id,
                "title": title,
                "artistId": ["RTS01"],
                "lyricistId": "RTS01",
                "composerId": "RTS01",
                "lyricsId": lyrics_id,
                "parjaay": None,
                "genre": ["রবীন্দ্রসংগীত"],
                "releaseYear": 2000,
                "tags": ["রবীন্দ্রসংগীত"]
            }
            
            songs_data.append(song_entry)
            counter += 1

        # ৫. songs.json ফাইলে সেভ করা (utf-8-sig ব্যবহার করা হয়েছে ভিএস কোডের জন্য)
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            json.dump(songs_data, f, ensure_ascii=False, indent=2)

        print("   -----------------------------------")
        print(f"৩. সফলভাবে ফাইল তৈরি হয়েছে!")
        print(f"   মোট বৈধ গান যুক্ত হয়েছে: {len(songs_data)} টি")
        print(f"   খালি লিরিক্স বাদ দেওয়া হয়েছে: {skipped_count} টি")
        print(f"   ফাইলটি এখানে সেভ হয়েছে: {abs_output_path}")

    except Exception as e:
        print(f"একটি সমস্যা হয়েছে: {e}")

if __name__ == "__main__":
    process_lyrics_and_generate_json('lyrics.ts', 'songs.json')