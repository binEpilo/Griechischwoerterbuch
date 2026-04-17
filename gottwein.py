#!/usr/bin/env python3
"""
Griechisch-Deutsch Übersetzer für gottwein.de
Extrahiert Übersetzungen aus dem Gottwein-Wörterbuch.
"""

import requests
from bs4 import BeautifulSoup
from typing import List
import re
import unicodedata

BASE_URL = "https://www.gottwein.de/GrWk/Gr01.php"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def translate(greek_word: str) -> List[str]:
    """
    Ruft die deutschen Übersetzungen für ein griechisches Wort von der Gottwein-Website ab.
    
    Args:
        greek_word (str): Das gesuchte griechische Wort (z.B. 'χαίρω', 'μῆνις')
    
    Returns:
        List[str]: Eine Liste der möglichen deutschen Übersetzungen, sortiert und ohne Duplikate.
                   Returns empty list if no translations found.
    
    Beispiel:
        >>> translations = translate('χαίρω')
        >>> for translation in translations:
        ...     print(translation)
    """
    
    # Parameter für die Suche
    params = {'qu': greek_word, 'ab': 'Hui'}
    
    try:
        # GET-Request zur Website
        response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'  # Stelle sicher, dass UTF-8 verwendet wird
        response.raise_for_status()
        
        # HTML mit BeautifulSoup parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Übersetzungen extrahieren aus den onClick="gowo(...)" Attributen
        # Strategie: Nur Übersetzungen nehmen, deren griechisches Wort (linke Spalte)
        # mit dem gesuchten Wort anfängt (Flexionsformen sind OK, aber nicht Wendungen)
        translations = set()
        
        # Normalisiere das Suchword für Vergleich
        search_word_nfc = unicodedata.normalize('NFC', greek_word)
        
        # Finde alle TDs mit width:190px die "griechische Synonyme" enthalten
        for td in soup.find_all('td', style=re.compile(r'width:190px')):
            img = td.find('img', alt=re.compile(r'griechische Synonyme', re.IGNORECASE))
            
            if img:
                # Extrahiere die Übersetzung aus dem onclick-Attribut
                onclick = img.get('onclick', '')
                match = re.search(r'gowo\("([^"]+)"\)', onclick)
                
                if match:
                    translation = match.group(1).strip()
                    
                    # Extrahiere das griechische Wort aus der TD
                    greek_word_in_cell = td.get_text(strip=True)
                    
                    # Normalisiere auch das griechische Wort für Vergleich (NFC)
                    greek_word_cell_nfc = unicodedata.normalize('NFC', greek_word_in_cell)
                    
                    # WICHTIG: Akzeptiere nur das EXAKTE Wort oder mit grammatischen Anmerkungen (Komma)
                    # Grammatische Anmerkungen sind z.B. ", ἡ" für Artikel
                    # NICHT akzeptieren: Wendungen mit Leerzeichen wie "χαίρω ἐᾶν" oder "χαίρω ποιῶν"
                    
                    is_exact_match = (greek_word_cell_nfc == search_word_nfc)
                    is_grammar_variant = (greek_word_cell_nfc.startswith(search_word_nfc + ',') or 
                                         greek_word_cell_nfc.startswith(search_word_nfc + ' '))
                    
                    # Nur akzeptieren wenn:
                    # 1. Exakt gleich (z.B. χαίρω = χαίρω)
                    # 2. Mit Komma-Grammatik (z.B. μῆνις, ἡ = μῆνις)
                    # NICHT akzeptieren wenn: Mit Leerzeichen (= Wendung)
                    if is_exact_match or (is_grammar_variant and greek_word_cell_nfc.startswith(search_word_nfc + ',')):
                        translations.add(translation)
        
        # Konvertiere zu sortierter Liste
        result = sorted(list(translations))
        
        return result
    
    except requests.exceptions.RequestException as e:
        # Auf Fehler mit leerer Liste antworten, nicht mit Fehlermeldung
        return []
    except Exception as e:
        # Auf Fehler mit leerer Liste antworten, nicht mit Fehlermeldung
        return []
