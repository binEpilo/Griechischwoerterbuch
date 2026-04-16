#!/bin/bash

# Startup-Skript für die Griechisches Wörterbuch App

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Griechisches Wörterbuch - Startup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

# Wechsel zum App-Verzeichnis
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Prüfe ob venv existiert, wenn nicht erstelle es
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Erstelle virtuelle Umgebung...${NC}"
    python3 -m venv .venv
fi

# Installiere Dependencies
echo -e "${BLUE}Installiere/aktualisiere Abhängigkeiten...${NC}"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Starte die App in einer screen-Session
SESSION_NAME="griechisch"

# Prüfe ob Session bereits existiert
if screen -list | grep -q "$SESSION_NAME"; then
    echo -e "${BLUE}Session '$SESSION_NAME' existiert bereits${NC}"
    echo -e "${GREEN}Verbinde mit: screen -r $SESSION_NAME${NC}"
else
    echo -e "${GREEN}✓ Starte App in screen-Session...${NC}"
    echo -e "${GREEN}Die App läuft unter: http://localhost:5000${NC}"
    echo -e "${GREEN}Session-Name: $SESSION_NAME${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo ""
    
    # Starte App in screen mit direktem Python-Pfad
    screen -dmS "$SESSION_NAME" .venv/bin/python app.py
    
    echo -e "${GREEN}✓ App läuft im Hintergrund${NC}"
    echo -e "${GREEN}Verbinde mit: screen -r $SESSION_NAME${NC}"
fi
