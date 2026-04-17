"""Pape (Griechisch–Deutsch) über dieselbe API wie https://logeion.uchicago.edu/ ."""

from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

_DETAIL = "https://anastrophe.uchicago.edu/logeion-api/detail"
# Wie in der öffentlichen Logeion-Web-App (TokenInterceptor / gebündelte Skripte).
_DEFAULT_API_KEY = "AIzaSyCT5aVzk3Yx-m8FH8rmTpEgfVyVA3pYbqg"


def _plain_one_line(html_fragment: str) -> str:
    t = html.unescape(html_fragment)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,;.!?])", r"\1", t)
    return t


def _pape_meaning_segments(html_block: str) -> list[str]:
    """
    Zerlegt Pape-HTML an <br>. Zeilen, die keine neue Gliederung mit <b>… einleiten
    (z. B. Absatz mitten in einer Bedeutung), an die vorherige Bedeutung anhängen.
    """
    raw = re.split(r"<br\s*/?>\s*", html_block, flags=re.IGNORECASE)
    merged: list[str] = []
    for seg in raw:
        if not seg.strip():
            continue
        if merged and not re.match(r"^\s*<b", seg):
            merged[-1] = merged[-1] + "<br>" + seg
        else:
            merged.append(seg)
    return merged


def _strip_lemma_lead(line: str, headword: str) -> str:
    """Entfernt typischen Pape-Kopf «Lemma, Artikel,» am Zeilenanfang."""
    if not headword or not line:
        return line
    t = line.lstrip()
    if not t.startswith(headword):
        return line
    rest = t[len(headword) :].lstrip()
    if rest.startswith(","):
        rest = rest[1:].lstrip()
    m = re.match(r"[^\s,]+,\s*", rest)
    if m:
        rest = rest[m.end() :]
    return rest.lstrip()


def pape(
    lemma: str,
    *,
    api_key: str | None = None,
    wheel_type: str = "normal",
    timeout: float = 60.0,
) -> list[str]:
    """
    Liefert den Pape-Artikel als Liste einzelner **Bedeutungsabschnitte** (jeweils
    eine Gliederungseinheit wie ``A.``, ``1)``, ``a)`` … laut ``<b>``-Markup).
    Der API-``headword``-Kopf (Lemma + Artikel) wird im ersten Eintrag nicht
    wiederholt.

    *api_key*: Google-API-Key (Query-Parameter ``key``). Bei *None*: zuerst
    ``LOGEION_API_KEY``, sonst eingebetteter Standard wie in der Logeion-Web-App.
    """
    key = (
        api_key
        if api_key is not None
        else os.environ.get("LOGEION_API_KEY") or _DEFAULT_API_KEY
    )

    q = urllib.parse.urlencode({"key": key, "w": lemma, "type": wheel_type}, safe="")
    req = urllib.request.Request(
        f"{_DETAIL}?{q}",
        headers={"User-Agent": "logeion.py/1 (+https://logeion.uchicago.edu/)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(str(e.reason)) from e

    dicos = (data.get("detail") or {}).get("dicos") or []
    pape = next((d for d in dicos if d.get("dname") == "Pape"), None)
    if not pape:
        if not dicos:
            raise LookupError(f"Kein Eintrag für «{lemma}».")
        names = ", ".join(d.get("dname", "?") for d in dicos)
        raise LookupError(f"Kein Pape für «{lemma}». Verfügbar: {names}")

    headword = (data.get("detail") or {}).get("headword") or lemma
    lines: list[str] = []
    for block in pape.get("es") or []:
        if not block:
            continue
        for seg in _pape_meaning_segments(block):
            plain = _plain_one_line(seg)
            if plain:
                lines.append(plain)
    if lines:
        lines[0] = _strip_lemma_lead(lines[0], headword)
        if not lines[0]:
            lines.pop(0)
    
    # Split at semicolons into separate items
    final_lines: list[str] = []
    for line in lines:
        parts = [p.strip() for p in line.split(";")]
        final_lines.extend([p for p in parts if p])
    
    return final_lines
