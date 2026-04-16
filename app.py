"""
Flask-Web-App für das Griechische Wörterbuch
Stellt die API-Endpoints für das Web-Frontend bereit
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from greek_translator import get_greek_word_analysis
import threading
import time
import os

app = Flask(__name__)
CORS(app)

# Cache für wiederholte Anfragen
cache = {}
cache_timeout = 3600  # 1 Stunde


@app.route('/')
def index():
    """Gibt die Hauptseite aus"""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search():
    """
    API-Endpoint für die Wortsuche
    Request: JSON mit 'word' (griechisches Wort)
    Response: JSON mit Liste von Analyses
    """
    data = request.get_json()
    greek_word = data.get('word', '').strip()
    
    if not greek_word:
        return jsonify({'error': 'Bitte geben Sie ein Wort ein'}), 400
    
    # Cache prüfen
    if greek_word in cache:
        cached_data, timestamp = cache[greek_word]
        if time.time() - timestamp < cache_timeout:
            return jsonify({'results': cached_data})
    
    try:
        # Führe die Analyse durch
        results = get_greek_word_analysis(greek_word)
        
        # Filtere Grundformen mit Zahlen
        results = [r for r in results if not any(char.isdigit() for char in r.get('grundform', ''))]
        
        # Speichere im Cache
        cache[greek_word] = (results, time.time())
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': f'Fehler bei der Verarbeitung: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
