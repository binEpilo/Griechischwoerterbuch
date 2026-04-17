import requests
from bs4 import BeautifulSoup
from typing import List
import re
import unicodedata
from hellenike import translate

# Wörterbuch für Morphologie-Abkürzungen
MORPHOLOGY_TRANSLATIONS = {
    # Kasus
    'nom': 'Nominativ',
    'gen': 'Genitiv',
    'dat': 'Dativ',
    'acc': 'Akkusativ',
    'voc': 'Vokativ',
    
    # Numerus
    'sg': 'Singular',
    'dual': 'Dual',
    'pl': 'Plural',
    
    # Genus
    'masc': 'Maskulinum',
    'fem': 'Femininum',
    'neut': 'Neutrum',
    'masc/fem': 'Maskulinum/Femininum',
    'masc/neut': 'Maskulinum/Neutrum',
    
    # Person
    '1st': '1. Person',
    '2nd': '2. Person',
    '3rd': '3. Person',
    
    # Diathese
    'act': 'Aktiv',
    'mid': 'Medium',
    'pass': 'Passiv',
    'mp': 'Medium/Passiv',
    
    # Tempus
    'pres': 'Präsens',
    'imperf': 'Imperfekt',
    'fut': 'Futur',
    'aor': 'Aorist',
    'perf': 'Perfekt',
    'plup': 'Plusquamperfekt',
    'futperf': 'Futur II',
    
    # Modus / Verbalform
    'ind': 'Indikativ',
    'subj': 'Konjunktiv',
    'opt': 'Optativ',
    'imperat': 'Imperativ',
    'inf': 'Infinitiv',
    'part': 'Partizip',
    
    # Weitere häufige Abkürzungen
    'noun': 'Substantiv',
    'verb': 'Verb',
    'adj': 'Adjektiv',
    'pron': 'Pronomen',
    'attic': 'attisch',
    'doric': 'dorisch',
    'ionic': 'ionisch',
    'epic': 'episch',
    'aeolic': 'aeolisch',
    'homeric': 'homerisch',
    'contr': 'kontrahiert',
    'unaugmented': 'nicht augmentiert',
}


def _translate_morphology(morph_string: str) -> str:
    """
    Übersetzt eine morphologische Bestimmung von Abkürzungen zu deutschen Begriffen.
    
    Args:
        morph_string (str): Die morphologische Bestimmung (z.B. "noun sg fem voc attic")
    
    Returns:
        str: Die übersetzte Bestimmung (z.B. "Nomen Singular Femininum Vokativ attisch")
    """
    
    words = morph_string.split()
    translated_words = []
    
    for word in words:
        # Versuche das Wort im Dictionary zu finden
        if word in MORPHOLOGY_TRANSLATIONS:
            translated_words.append(MORPHOLOGY_TRANSLATIONS[word])
        else:
            # Wenn nicht gefunden, behalte das Original
            translated_words.append(word)
    
    return ' '.join(translated_words)


def get_greek_translations(greek_word: str) -> List[str]:
    """
    Ruft die deutschen Übersetzungen für ein griechisches Wort von der Gottwein-Website ab.
    
    Args:
        greek_word (str): Das gesuchte griechische Wort (z.B. 'χαίρω', 'μῆνις')
    
    Returns:
        List[str]: Eine Liste der möglichen deutschen Übersetzungen, sortiert und ohne Duplikate
    
    Beispiel:
        >>> translations = get_greek_translations('χαίρω')
        >>> for translation in translations:
        ...     print(translation)
    """
    hellenike = translate(greek_word)
    if hellenike:
        return hellenike
    
    # URL der Gottwein-Website
    base_url = "https://www.gottwein.de/GrWk/Gr01.php"
    
    # Parameter für die Suche
    params = {'qu': greek_word, 'ab': 'Hui'}
    
    try:
        # HTTP-Request mit User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # GET-Request zur Website
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
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

                        # Zusätzliche Filter für die Übersetzung
                        # Keine sehr langen Übersetzungen (wahrscheinlich Wendungen)
                        word_count = len(translation.split())
                        if word_count <= 4:
                            # Keine Klammern in der Übersetzung
                            if '(' not in translation and ')' not in translation:
                                translations.add(translation)
        
        # Konvertiere zu sortierter Liste
        result = sorted(list(translations))
        
        if not result:
            return [f"Keine Übersetzungen gefunden für '{greek_word}'"]
        
        return result
    
    except requests.exceptions.RequestException as e:
        return [f"Fehler beim Abrufen der Website: {str(e)}"]
    except Exception as e:
        return [f"Fehler bei der Verarbeitung: {str(e)}"]


def get_greek_word_analysis(greek_word: str) -> List[dict]:
    """
    Ruft die morphologischen Analysen für ein griechisches Wort von der Perseus-Website ab.
    Für jede mögliche Grundform werden die Übersetzungen und morphologischen Bestimmungen 
    zurückgegeben.
    
    Args:
        greek_word (str): Das gesuchte griechische Wort (z.B. 'θεά')
    
    Returns:
        List[dict]: Eine Liste von Dictionaries mit folgenden Keys:
            - 'grundform' (str): Die Grundform des Wortes
            - 'übersetzungen' (List[str]): Deutsche Übersetzungen der Grundform
            - 'bestimmungen' (List[str]): Morphologische Bestimmungen (z.B. "noun sg fem voc attic")
    
    Beispiel:
        >>> analyses = get_greek_word_analysis('θεά')
        >>> for analysis in analyses:
        ...     print(f"Grundform: {analysis['grundform']}")
        ...     print(f"Übersetzungen: {analysis['übersetzungen']}")
        ...     for best in analysis['bestimmungen']:
        ...         print(f"  - {best}")
    """
    
    # URL der Perseus-Website
    perseus_url = "https://www.perseus.tufts.edu/hopper/morph"
    
    # Parameter für die Suche
    params = {'l': greek_word}
    
    try:
        # HTTP-Request mit User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # GET-Request zur Website
        response = requests.get(perseus_url, params=params, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        # HTML mit BeautifulSoup parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Finde alle Lemma-Divs
        lemma_divs = soup.find_all('div', class_='lemma')
        
        results = []
        
        for lemma_div in lemma_divs:
            # Extrahiere die Grundform
            lemma_header = lemma_div.find('div', class_='lemma_header')
            if not lemma_header:
                continue
                
            grundform_tag = lemma_header.find('h4', class_='greek')
            if not grundform_tag:
                continue
                
            grundform = grundform_tag.get_text(strip=True)
            
            # Finde alle morphologischen Analysen in diesem Lemma-Block
            # Innerhalb des lemma_div gibt es mehrere Tabellen mit morphologischen Analysen
            morphology_tables = lemma_div.find_all('table')
            
            bestimmungen_set = set()
            
            # Extrahiere Bestimmungen aus allen Tabellen dieses Lemmas
            for table in morphology_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    # Die morphologische Bestimmung ist normalerweise in der zweiten Spalte
                    if len(cols) > 1:
                        morph_text = cols[1].get_text(strip=True)
                        if morph_text and len(morph_text) > 3:
                            bestimmungen_set.add(morph_text)
            
            # Konvertiere zu sortierter Liste
            bestimmungen = sorted(list(bestimmungen_set))
            
            # Übersetze die morphologischen Bestimmungen
            bestimmungen_translated = [_translate_morphology(b) for b in bestimmungen]
            
            # Rufe Übersetzungen ab
            übersetzungen = get_greek_translations(grundform)
            
            # Filtere Error-Meldungen aus den Übersetzungen
            übersetzungen = [ü for ü in übersetzungen if not ü.startswith('Fehler')]
            
            results.append({
                'grundform': grundform,
                'übersetzungen': übersetzungen,
                'bestimmungen': bestimmungen_translated
            })
        
        return results
    
    except requests.exceptions.RequestException as e:
        return [{'grundform': greek_word, 'übersetzungen': [f"Fehler beim Abrufen: {str(e)}"], 'bestimmungen': []}]
    except Exception as e:
        return [{'grundform': greek_word, 'übersetzungen': [f"Fehler bei der Verarbeitung: {str(e)}"], 'bestimmungen': []}]

if __name__ == "__main__":
    test_word = 'θεά'
    print(f"\nMorphologische Analysen für '{test_word}':")
    analyses = get_greek_word_analysis(test_word)
    
    for analysis in analyses:
        print(f"\nGrundform: {analysis['grundform']}")
        print(f"Übersetzungen:")
        for ü in analysis['übersetzungen']:
            print(f"  - {ü}")
        print(f"Bestimmungen ({len(analysis['bestimmungen'])}):")
        for best in analysis['bestimmungen'][:5]:  # Zeige nur erste 5
            print(f"  - {best}")
        if len(analysis['bestimmungen']) > 5:
            print(f"  ... und {len(analysis['bestimmungen']) - 5} weitere")
