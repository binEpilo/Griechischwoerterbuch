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

def fetch_all_word_data(greek_word: str) -> List[Dict]:
    """
    Ruft ALLE Einträge für ein griechisches Wort ab.
    Dies ist besonders wichtig für Wörter wie Präpositionen, die mehrere grammatikalische Formen haben.
    Z.B. παρά gibt es als "Präp. m. Gen.", "Präp. m. Dat." und "Präp. m. Akk."
    
    Args:
        greek_word (str): Das griechische Wort zu suchen
    
    Returns:
        List[Dict]: Eine Liste von ALL matching Einträgen (nicht nur der erste)
    """
    try:
        url = BASE_URL + quote(greek_word)
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        match = re.search(r'\[\{.*\}\]', response.text, re.DOTALL)
        if not match:
            return []

        data = json.loads(match.group(0))
        if not isinstance(data, list):
            return []

        search_exact = normalize_exact_greek(greek_word)
        normalized_search = normalize_greek(greek_word)

        articles = {
            normalize_exact_greek('ὁ'),
            normalize_exact_greek('ἡ'),
            normalize_exact_greek('τό'),
            normalize_exact_greek('το'),
        }

        # 1. Sammle ALLE exakten Matches mit Akzenten, aber Unicode-normalisiert
        exact_matches = []
        for entry in data:
            h_words = extract_greek_tokens(entry.get('h', ''))
            for word in h_words:
                word_exact = normalize_exact_greek(word)
                if word_exact not in articles and word_exact == search_exact:
                    exact_matches.append(entry)
                    break  # Nicht mehrmals hinzufügen für das gleiche Entry

        if exact_matches:
            return exact_matches

        # 2. Fallback über sort - sammle ALLE Kandidaten
        candidates = [
            entry for entry in data
            if entry.get('sort', '').lower().strip() == normalized_search
        ]

        return candidates

    except Exception as e:
        print(f"Fehler beim Abrufen von '{greek_word}': {e}")
        return []
        
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
    """
    Entfernt nur bekannte Marker am Anfang von Bedeutungen.
    
    Die hellenike.de API nutzt verschiedene Marker-Symbole und Buchstaben:
    - Symbol-Marker: !, ", &, ', $, #, %
    - Buchstaben-Marker: A-Z (als Kategorien, z.B. "Bder Schmuck", "Cdie Welt")
    
    Heuristic für Buchstaben-Marker:
    - Marker sind IMMER ein Großbuchstabe direkt gefolgt von einem Kleinbuchstaben
    - Dann folgt ein Wort (typischerweise ein deutsches Artikel oder Präposition)
    - Diese Wörter sind KURZ (1-4 Zeichen): der, die, das, den, etc.
    
    Echte Wörter wie "Verderben" hätten das Wort DIREKT nach dem Marker sehr lang
    (8+ Zeichen), daher entfernen wir nur wenn Wort-Länge <= 4 ist.
    """
    text = text.strip()
    
    # Entferne Symbol-Marker am Anfang
    while text and text[0] in '\'"(){}[]!&#$%':
        text = text[1:].strip()
    
    # Entferne Buchstaben-Marker am Anfang (A-Z)
    # Aber nur wenn das folgende Wort kurz ist (typischerweise Artikel)
    if len(text) > 1 and text[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and text[1].islower():
        # Finde das nächste Leerzeichen um die Wort-Länge zu bestimmen
        space_idx = text.find(' ', 1)
        if space_idx == -1:
            space_idx = len(text)
        
        # Wort-Länge NACH dem Marker (also text[1:space_idx])
        word_length = space_idx - 1
        
        # Marker-Wörter sind typischerweise kurz (deutsche Artikel, Präpositionen)
        # Echte Wörter wie "Verderben" sind länger
        if word_length <= 4:
            text = text[1:].strip()
    
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
    """
    Übersetzt ein griechisches Wort ins Deutsche.
    Für Wörter mit mehreren grammatikalischen Formen (z.B. Präpositionen mit verschiedenen Fällen)
    werden ALLE Einträge verarbeitet und die Bedeutungen mit ihrer Grammatik kombiniert.
    
    Args:
        greek_word (str): Das griechische Wort
    
    Returns:
        List[str]: Liste von Übersetzungen, optional mit grammatikalischer Info
    """
    # Hole ALLE Einträge für dieses Wort
    all_entries = fetch_all_word_data(greek_word)
    if not all_entries:
        return []

    all_meanings = []
    
    for data in all_entries:
        # Hole die grammatikalische Information (z.B. "Präp. m. Gen.", "Präp. m. Dat.", etc.)
        grammar = data.get('g', '').strip()
        
        # Verarbeite alle Übersetzungen in diesem Eintrag
        entry_meanings = []
        for trans in data.get('tr', []):
            if trans.get('l') == 'g':
                entry_meanings.extend(parse_translation_markup(trans.get('t', '')))
        
        # Kombiniere Bedeutungen mit Grammatik
        # Wenn es eine Grammatik gibt (besonders für Präpositionen), hänge sie an
        if grammar and entry_meanings:
            for meaning in entry_meanings:
                # Format: "Bedeutung (Grammatik)"
                combined = f"{meaning} ({grammar})"
                all_meanings.append(combined)
        else:
            all_meanings.extend(entry_meanings)

    # Entferne Duplikate (behalte Reihenfolge)
    seen = set()
    unique = []
    for m in all_meanings:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique
