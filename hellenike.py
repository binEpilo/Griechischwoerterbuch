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

try:
    from spellchecker import SpellChecker
    SPELL_CHECKER = SpellChecker(language='de')
except ImportError:
    SPELL_CHECKER = None

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

def has_accents(text: str) -> bool:
    """
    Prüft ob ein griechisches Wort Akzente/Diakriten enthält.
    """
    # Normalisiere zu NFD (decomposed form) um separate Diakriten zu sehen
    nfd = unicodedata.normalize('NFD', text)
    # Prüfe ob es Combining Diacritical Marks gibt (Kategorie 'Mn')
    for char in nfd:
        if unicodedata.category(char) == 'Mn':
            return True
    return False

def has_matching_accents(word1: str, word2: str) -> bool:
    """
    Prüft ob zwei griechische Wörter die gleichen Akzente an den gleichen Positionen haben.
    
    Dies verhindert falsche Matches wie:
    - θέρμος (suche) vs θερμός (API) - unterschiedliche Akzent-Position
    
    Wir vergleichen die Strings direkt nach Unicode-Normalisierung (NFC).
    Wenn die Struktur der Akzente unterschiedlich ist, wird ein Mismatch erkannt.
    """
    # Normalisiere beide Wörter zu NFC (standard Unicode form)
    # Dies stellt sicher, dass Akzente konsistent behandelt werden
    w1_clean = clean_text(word1).strip().lower()
    w2_clean = clean_text(word2).strip().lower()
    
    w1_nfc = unicodedata.normalize('NFC', w1_clean)
    w2_nfc = unicodedata.normalize('NFC', w2_clean)
    
    # Direkter Vergleich der normalisierten Strings
    # Wenn Akzente an unterschiedlichen Positionen sind, werden die Strings unterschiedlich sein
    return w1_nfc == w2_nfc

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
                    # Zusätzliche Prüfung: Akzente müssen exakt übereinstimmen
                    if has_matching_accents(greek_word, word):
                        return entry

        # WICHTIG: Falls der Suchtext Akzente hat und kein Match mit Akzenten gefunden wurde,
        # nicht weiter mit dem akzentlosen Fallback suchen.
        if has_accents(greek_word):
            return None

        # 2. Fallback über sort - nur wenn der Suchtext KEINE Akzente hat
        # ABER: Auch hier müssen die Akzente exakt passen!
        candidates = []
        for entry in data:
            if entry.get('sort', '').lower().strip() == normalized_search:
                # Prüfe dass Akzente passen - wenn die API das Wort mit Akzenten speichert,
                # sollte ein Suchtext ohne Akzent auch nichts finden
                h_words = extract_greek_tokens(entry.get('h', ''))
                for word in h_words:
                    if has_matching_accents(greek_word, word):
                        candidates.append(entry)
                        break

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
                    # Zusätzliche Prüfung: Akzente müssen exakt übereinstimmen
                    if has_matching_accents(greek_word, word):
                        exact_matches.append(entry)
                        break  # Nicht mehrmals hinzufügen für das gleiche Entry

        # WICHTIG: Falls der Suchtext Akzente hat und kein Match mit Akzenten gefunden wurde,
        # nicht weiter mit dem akzentlosen Fallback suchen. Der Nutzer wollte ein spezifisches Wort.
        if has_accents(greek_word):
            return exact_matches

        # 2. Fallback über sort - nur wenn der Suchtext KEINE Akzente hat
        # ABER: Auch hier müssen die Akzente exakt passen!
        # Das verhindert, dass "θερμος" (ohne Akzent) "θερμός" (mit Akzent) findet
        candidates = []
        for entry in data:
            if entry.get('sort', '').lower().strip() == normalized_search:
                # Prüfe dass Akzente passen - wenn die API das Wort mit Akzenten speichert,
                # sollte ein Suchtext ohne Akzent auch nichts finden
                h_words = extract_greek_tokens(entry.get('h', ''))
                for word in h_words:
                    if has_matching_accents(greek_word, word):
                        candidates.append(entry)
                        break

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
    
    Die hellenike.de API nutzt drei Buchstaben-Marker: A, B, C, D
    Diese sind Kategorie-Marker, z.B. "Bder Schmuck", "Cdie Welt", "Ablind"
    
    Strategie: 
    1. Entferne Symbol-Marker (!, ", &, etc.) - diese sind eindeutig
    2. Für A, B, C Marker: Überprüfe ob das folgende Wort im deutschen Wörterbuch existiert
       - Falls ja (z.B. "blind", "der"): Marker entfernen
       - Falls nein oder SPELL_CHECKER nicht verfügbar: Marker behalten (könnte echte Bedeutung sein)
    """
    text = text.strip()
    
    # Entferne Symbol-Marker am Anfang
    while text and text[0] in '\'"(){}[]!&#$%':
        if text[0] == '(' and text.endswith(')') and text[1:-1].count('(') == 0:
            break
        if text[0] == '[' and text.endswith(']') and text[1:-1].count('[') == 0:
            break
        if text[0] == '{' and text.endswith('}') and text[1:-1].count('{') == 0:
            break
        text = text[1:].strip()
    
    # Entferne A, B, C, D Marker wenn das folgende Wort im Deutschen existiert
    if SPELL_CHECKER and len(text) > 1 and text[0] in 'ABCD' and text[1].islower():
        # Finde das nächste Leerzeichen um das erste Wort zu extrahieren
        space_idx = text.find(' ', 1)
        if space_idx == -1:
            space_idx = len(text)
        
        # Das erste Wort NACH dem Marker
        first_word = text[1:space_idx].lower()
        
        # Wenn das Wort im deutschen Wörterbuch existiert, entferne den Marker
        if first_word in SPELL_CHECKER:
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
