#!/usr/bin/env python3
"""
Bengali Normalizer & Transliteration Engine
Provides Unicode normalization, spelling variant canonicalization,
Bengali <-> English phonetic transliteration, and similarity calculation.
"""

import unicodedata
import re
from typing import Set

# Phonetic character mapping for Bengali -> English
BN_VOWEL_MAP = {
    'অ': 'o', 'আ': 'a', 'ই': 'i', 'ঈ': 'i', 'উ': 'u', 'ঊ': 'u',
    'ঋ': 'ri', 'এ': 'e', 'ঐ': 'oi', 'ও': 'o', 'ঔ': 'ou',
    'া': 'a', 'ি': 'i', 'ী': 'i', 'ু': 'u', 'ূ': 'u', 'ৃ': 'ri',
    'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou', '্': '',
}

BN_CONSONANT_MAP = {
    'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'ঙ': 'ng',
    'চ': 'ch', 'ছ': 'chh', 'জ': 'j', 'ঝ': 'jh', 'ঞ': 'n',
    'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh', 'ণ': 'n',
    'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n',
    'প': 'p', 'ফ': 'f', 'ব': 'b', 'ভ': 'bh', 'ম': 'm',
    'য': 'y', 'র': 'r', 'ল': 'l', 'শ': 'sh', 'ষ': 'sh', 'স': 's', 'হ': 'h',
    'ড়': 'r', 'ঢ়': 'rh', 'য়': 'y', 'ৎ': 't',
    'ং': 'ng', 'ঃ': 'h', 'ঁ': 'n'
}

COMMON_ALIASES = {
    "rabindranath tagore": "রবীন্দ্রনাথ ঠাকুর",
    "rabindranath thakur": "রবীন্দ্রনাথ ঠাকুর",
    "rabi tagore": "রবীন্দ্রনাথ ঠাকুর",
    "kazi nazrul islam": "কাজী নজরুল ইসলাম",
    "nazrul": "কাজী নজরুল ইসলাম",
    "hemanta mukherjee": "হেমন্ত মুখোপাধ্যায়",
    "hemanta mukhopadhyay": "হেমন্ত মুখোপাধ্যায়",
    "manna dey": "মান্না দে",
    "salil chowdhury": "সলিল চৌধুরী",
    "kishore kumar": "কিশোর কুমার",
    "lata mangeshkar": "লতা মঙ্গেশকর",
    "asha bhosle": "আশা ভোঁসলে",
    "bhupen hazarika": "ভূপেন হাজারিকা",
    "rd burman": "আর ডি বর্মন",
    "sd burman": "এস ডি বর্মন",
    "sandhya mukherjee": "সন্ধ্যা মুখোপাধ্যায়",
    "shyamal mitra": "শ্যামল মিত্র",
    "aroti mukherjee": "আরতি মুখোপাধ্যায়",
}


def normalize_unicode(text: str) -> str:
    """Normalize text using Unicode NFC form."""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)


def normalize_bengali_spelling(text: str) -> str:
    """
    Standardize Bengali spelling variations:
    - Normalizes composite characters (ড + ় -> ড়, etc.)
    - Removes Zero-Width non-joiner/joiner
    - Standardizes common variant representations
    """
    if not text:
        return ""
    
    t = normalize_unicode(text)
    
    # Remove ZWNJ and ZWJ
    t = t.replace('\u200c', '').replace('\u200d', '')
    
    # Normalize nukta combinations
    t = t.replace('ড\u09BC', 'ড়')
    t = t.replace('ঢ\u09BC', 'ঢ়')
    t = t.replace('য\u09BC', 'য়')
    
    # Collapse multiple whitespaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def strip_punctuation(text: str) -> str:
    """Removes punctuation and converts to lowercase for indexing."""
    if not text:
        return ""
    t = normalize_bengali_spelling(text).lower()
    t = re.sub(r'[^\w\s\u0980-\u09FF]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


COMMON_WORD_MAP = {
    "একলা": "ekla",
    "চলো": "cholo",
    "চল": "cholo",
    "রে": "re",
    "আমার": "amar",
    "সোনার": "sonar",
    "বাংলা": "bangla",
    "বাঙলা": "bangla",
    "আমি": "ami",
    "তোমায়": "tomay",
    "তোমায়": "tomay",
    "ভালোবাসি": "bhalobasi",
    "রবীন্দ্রনাথ": "rabindranath",
    "ঠাকুর": "tagore",
    "কাজী": "kazi",
    "নজরুল": "nazrul",
    "ইসলাম": "islam",
    "হেমন্ত": "hemanta",
    "মুখোপাধ্যায়": "mukherjee",
    "মুখোপাধ্যায়": "mukherjee",
    "মান্না": "manna",
    "দে": "dey",
    "কিশোর": "kishore",
    "কুমার": "kumar"
}


def transliterate_bn_to_en(text: str) -> str:
    """
    Transliterates Bengali text to phonetic English using canonical word mapping
    with character-level phonetic fallback.
    Example: 'একলা চলো রে' -> 'ekla cholo re'
    """
    if not text:
        return ""
    
    t = normalize_bengali_spelling(text)
    words = t.split()
    res_words = []
    
    for w in words:
        # Check clean word in dictionary
        clean_w = strip_punctuation(w)
        if clean_w in COMMON_WORD_MAP:
            res_words.append(COMMON_WORD_MAP[clean_w])
            continue
            
        # Character-level fallback
        chars = list(w)
        n = len(chars)
        ch_res = []
        for i, ch in enumerate(chars):
            if ch in BN_VOWEL_MAP:
                ch_res.append(BN_VOWEL_MAP[ch])
            elif ch in BN_CONSONANT_MAP:
                ch_res.append(BN_CONSONANT_MAP[ch])
            elif ch.isascii():
                ch_res.append(ch.lower())
            else:
                ch_res.append(ch)
        res_words.append("".join(ch_res))
        
    return re.sub(r'\s+', ' ', " ".join(res_words)).strip()


def get_search_tokens(text: str) -> Set[str]:
    """Generates normalized search tokens in both Bengali and English."""
    if not text:
        return set()
    
    normalized = normalize_bengali_spelling(text)
    stripped = strip_punctuation(text)
    transliterated = transliterate_bn_to_en(normalized)
    
    tokens = set()
    for word in stripped.split():
        if len(word) > 1:
            tokens.add(word)
            tokens.add(transliterate_bn_to_en(word))
            
    if transliterated:
        tokens.add(transliterated)
        for w in transliterated.split():
            tokens.add(w)
            
    return tokens


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute standard Levenshtein distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Returns similarity score between 0.0 and 1.0."""
    n1 = strip_punctuation(s1)
    n2 = strip_punctuation(s2)
    if n1 == n2:
        return 1.0
    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(n1, n2)
    return 1.0 - (dist / max_len)


if __name__ == "__main__":
    test_str = "আমার সোনার বাংলা, আমি তোমায় ভালোবাসি!"
    print("Original:", test_str)
    print("Normalized:", normalize_bengali_spelling(test_str))
    print("Transliterated:", transliterate_bn_to_en(test_str))
    print("Tokens:", get_search_tokens(test_str))
    print("Similarity ('আমার সোনার বাংলা', 'আমার সোনার বাংলা!'):", similarity_ratio("আমার সোনার বাংলা", "আমার সোনার বাংলা!"))
