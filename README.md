# 🏛️ Griechisches Wörterbuch

Web-Anwendung zur Analyse und Übersetzung griechischer Wörter mit morphologischen Bestimmungen.

## 📋 Inhaltsverzeichnis

- [Installation](#installation)
- [Verwendung](#verwendung)
- [API](#api)
- [Projektstruktur](#projektstruktur)

## Installation & Deployment

### Online auf Replit (empfohlen) 🚀

1. Dieses Repository auf [Replit importieren](https://replit.com/import)
2. "Run" drücken
3. App läuft unter: `https://dein-projekt.replit.dev`

### Lokal (Linux/macOS)

```bash
chmod +x start.sh
./start.sh
```

Das Skript erstellt eine virtuelle Umgebung, installiert Dependencies und startet die App.

Die App läuft unter `http://localhost:5000`

## Verwendung

1. App starten: `./start.sh` oder `python app.py`
2. Browser öffnen: `http://localhost:5000`
3. Griechisches Wort eingeben und Enter drücken
4. Ergebnisse zeigen Grundform, Morphologie und Übersetzungen

## API

### POST `/api/search`

**Request:**
```json
{
  "word": "κόσμος"
}
```

**Response:**
```json
{
  "results": [
    {
      "grundform": "κόσμος",
      "morphologie": "Nomen Singular Nominativ Maskulinum",
      "übersetzungen": ["Weltordnung", "Weltall", "Schmuck"]
    }
  ]
}
```

## Projektstruktur

```
Griechischwörterbuch/
├── app.py                 # Flask-App mit /api/search Endpoint
├── greek_translator.py    # Übersetzungs- und Analysemodul
├── requirements.txt       # Python-Abhängigkeiten
├── start.sh              # Startup-Skript
├── templates/
│   └── index.html        # Web-Interface
└── README.md
```

Vibecoded with ❤️ by binEpilo