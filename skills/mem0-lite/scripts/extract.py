#!/usr/bin/env python3
"""
mem0-lite: Groq-powered memory extractor
Extrahiert Fakten aus Gesprächen und speichert sie als JSON + Markdown.

Usage:
  echo "Gesprächstext" | python3 extract.py
  python3 extract.py --text "Alex arbeitet an Gisela." --user alex
  python3 extract.py --list                    # Alle Memories anzeigen
  python3 extract.py --search "Gisela"         # Semantisch suchen
"""

import sys
import json
import os
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import ssl

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SSL_CTX = ssl.create_default_context()
DATA_DIR = Path(os.environ.get("MEM0_DATA", "/home/openclaw/.openclaw/workspace/skills/mem0-lite/data"))
MEMORIES_FILE = DATA_DIR / "memories.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_memories():
    if MEMORIES_FILE.exists():
        return json.loads(MEMORIES_FILE.read_text())
    return []


def save_memories(memories):
    MEMORIES_FILE.write_text(json.dumps(memories, indent=2, ensure_ascii=False))


def groq_extract(text: str) -> list[dict]:
    """Ruft Groq API auf, extrahiert strukturierte Fakten."""
    if not GROQ_API_KEY:
        print("FEHLER: GROQ_API_KEY nicht gesetzt", file=sys.stderr)
        return []

    prompt = f"""Analysiere folgenden Text und extrahiere alle relevanten Fakten über Personen, Projekte, Präferenzen, Deadlines und Entscheidungen.

Antworte NUR mit einem JSON-Array. Jedes Objekt hat:
- "fact": der extrahierte Fakt (kurz, präzise, auf Deutsch)
- "entity": Hauptentität (Person/Projekt/Tool/etc.)
- "relation": Beziehungstyp (z.B. "arbeitet_an", "mag", "hat_deadline", "lernt", "entschieden")
- "target": Zielobjekt wenn vorhanden

Text:
{text}

JSON-Array:"""

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1024
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.88.1"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip()
            # JSON aus Antwort parsen
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        print(f"FEHLER bei Groq-Aufruf: {e}", file=sys.stderr)
        return []


def add_memory(text: str, user_id: str = "alex", source: str = "manual"):
    """Extrahiert Fakten und speichert sie."""
    facts = groq_extract(text)
    if not facts:
        print("Keine Fakten extrahiert.")
        return

    memories = load_memories()
    now = datetime.now(timezone.utc).isoformat()
    added = 0

    for fact in facts:
        if not isinstance(fact, dict) or "fact" not in fact:
            continue
        fact_text = fact.get("fact", "")
        # Deduplizierung via Hash
        fact_id = hashlib.md5(fact_text.encode()).hexdigest()[:8]
        if any(m.get("id") == fact_id for m in memories):
            continue

        memories.append({
            "id": fact_id,
            "fact": fact_text,
            "entity": fact.get("entity", ""),
            "relation": fact.get("relation", ""),
            "target": fact.get("target", ""),
            "user_id": user_id,
            "source": source,
            "created_at": now
        })
        print(f"  ✅ {fact_text}")
        added += 1

    save_memories(memories)
    print(f"\n{added} neue Fakten gespeichert ({len(memories)} gesamt).")


def list_memories(user_id: str = None, limit: int = 20):
    """Zeigt alle gespeicherten Memories."""
    memories = load_memories()
    if user_id:
        memories = [m for m in memories if m.get("user_id") == user_id]
    for m in memories[-limit:]:
        entity = f"[{m['entity']}]" if m.get("entity") else ""
        print(f"  {entity} {m['fact']}")
    print(f"\n{len(memories)} Memories total.")


def search_memories(query: str, user_id: str = None) -> list:
    """Einfache Textsuche (qmd für semantisch)."""
    memories = load_memories()
    if user_id:
        memories = [m for m in memories if m.get("user_id") == user_id]
    query_lower = query.lower()
    results = [
        m for m in memories
        if query_lower in m.get("fact", "").lower()
        or query_lower in m.get("entity", "").lower()
        or query_lower in m.get("target", "").lower()
    ]
    return results


def main():
    parser = argparse.ArgumentParser(description="mem0-lite: Groq Memory Extractor")
    parser.add_argument("--text", "-t", help="Text zum Analysieren")
    parser.add_argument("--user", "-u", default="alex", help="User ID")
    parser.add_argument("--list", "-l", action="store_true", help="Memories anzeigen")
    parser.add_argument("--search", "-s", help="Memories suchen")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.list:
        list_memories(args.user, args.limit)
    elif args.search:
        results = search_memories(args.search, args.user)
        for r in results:
            print(f"  [{r['entity']}] {r['fact']}")
        print(f"\n{len(results)} Treffer.")
    elif args.text:
        print(f"Extrahiere Fakten aus Text...\n")
        add_memory(args.text, args.user)
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            print(f"Extrahiere Fakten aus Stdin...\n")
            add_memory(text, args.user)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
