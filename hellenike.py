#!/usr/bin/env python3
"""
Griechisch-Deutsch Übersetzer für hellenike.de
Parst das interne Markup-Format und gibt cleane Bedeutungslisten aus.
"""

import requests
import json
import re
import html
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote

BASE_URL = "https://hellenike.de/DictGreek?method=search&word="

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def normalize_greek(text: str) -> str:
    """
    Normalisiert griechische Wörter für den Vergleich.
    Entfernt alle diakritischen Zeichen (Akzente, Atemzeichen, etc.)
    
    ἐν -> εν
    εἱς -> εις
    ἔχω -> εχω
    """
    # NFD-Normalisierung: Zerlegt zusammengesetzte Zeichen
    nfd = unicodedata.normalize('NFD', text)
    
    # Filtere alle diakritischen Zeichen (Kategorie 'Mn' = Mark, nonspacing)
    # und alle combining marks
    result = ''.join(
        char for char in nfd 
        if unicodedata.category(char) != 'Mn'
    )
    
    return result.lower()

def extract_greek_tokens(text: str) -> List[str]:
    text = clean_text(text)
    return re.findall(r"[Ͱ-Ͽἀ-῿]+", text)

def normalize_exact_greek(text: str) -> str:
    return unicodedata.normalize('NFC', clean_text(text)).strip().lower()

def fetch_word_data(greek_word: str) -> Optional[Dict]:
    try:
        url = BASE_URL + quote(greek_word)
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        match = re.search(r'\[\{.*\}\]', response.text, re.DOTALL)
        if not match:
            return None

        data = json.loads(match.group(0))
        if not isinstance(data, list) or len(data) == 0:
            return None

        search_exact = normalize_exact_greek(greek_word)
        normalized_search = normalize_greek(greek_word)

        articles = {
            normalize_exact_greek('ὁ'),
            normalize_exact_greek('ἡ'),
            normalize_exact_greek('τό'),
            normalize_exact_greek('το'),
        }

        # 1. Exakter Match mit Akzenten, aber Unicode-normalisiert
        for entry in data:
            h_words = extract_greek_tokens(entry.get('h', ''))
            for word in h_words:
                word_exact = normalize_exact_greek(word)
                if word_exact not in articles and word_exact == search_exact:
                    return entry

        # 2. Fallback über sort
        candidates = [
            entry for entry in data
            if entry.get('sort', '').lower().strip() == normalized_search
        ]

        if len(candidates) == 1:
            return candidates[0]

        return None

    except Exception as e:
        print(f"Fehler beim Abrufen von '{greek_word}': {e}")
        return None
        
def clean_text(text: str) -> str:
    """Entfernt HTML-Tags, Zero-Width-Spaces und andere Artefakte."""
    # HTML-Entities dekodieren
    text = html.unescape(text)
    # HTML-Tags entfernen
    text = re.sub(r'<[^>]+>', '', text)
    # Zero-Width-Spaces entfernen
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\u200c', '')  # Zero-width non-joiner
    text = text.replace('\u200d', '')  # Zero-width joiner
    # Mehrfache Leerzeichen durch einfache ersetzen
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_meaning(text: str) -> str:
    """Entfernt Sonderzeichen am Anfang von Bedeutungen."""
    text = text.strip()
    # Entferne einfache/doppelte Anführungszeichen und Buchstaben-Marker am Anfang
    while text and (text[0] in '\'"ABCDEFGHIJKLMNOPQRSTUVWXYZ' or text[0] in '(){[]}'):
        # Aber nur wenn es ein Marker ist, nicht wenn es das Wort ist
        if len(text) > 1 and text[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and text[1].islower():
            text = text[1:].strip()
        elif text[0] in '\'"{}[]':
            text = text[1:].strip()
        else:
            break
    return text.strip()


def parse_translation_markup(markup_text: str) -> List[str]:
    """
    Parst das spezielle Markup-Format aus hellenike.de
    
    Format: |{ |!Bedeutung1|"Bedeutung2|#Bedeutung3 |} Extra-Info
    
    Symbole:
    ! = Hauptbedeutung
    \", &, ', $, #, % = Alternativen
    """
    meanings = []
    
    # Text bereinigen
    text = clean_text(markup_text).strip()
    
    # Alle Gruppen separieren (|{ ... |})
    # Mit non-greedy matching
    pattern = r'\|\{([^}]*?)\|\}'
    groups = re.findall(pattern, text)
    
    for group in groups:
        # Split nach | und filtere leere Einträge
        parts = [p.strip() for p in group.split('|') if p.strip()]
        
        prefix = ""
        
        # Prüfe auf Präfix (Text ohne Symbol am Anfang)
        if parts and parts[0] and parts[0][0] not in '!"&#$%':
            prefix = parts[0]
            parts = parts[1:]
        
        # Verarbeite jede Bedeutung
        for part in parts:
            if not part:
                continue
                
            # Erstes Zeichen ist Symbol (!, ", &, ', $, #, %)
            if part and part[0] in '!"&#$%':
                meaning = part[1:].strip()
            else:
                meaning = part
            
            # Reinigung
            meaning = clean_meaning(meaning)
            
            if meaning:
                if prefix:
                    meaning = f"{prefix}: {meaning}"
                meanings.append(meaning)
    
    return meanings

def translate(greek_word: str) -> List[str]:
    data = fetch_word_data(greek_word)
    if not data:
        return []

    all_meanings = []
    for trans in data.get('tr', []):
        if trans.get('l') == 'g':
            all_meanings.extend(parse_translation_markup(trans.get('t', '')))

    seen = set()
    unique = []
    for m in all_meanings:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique
