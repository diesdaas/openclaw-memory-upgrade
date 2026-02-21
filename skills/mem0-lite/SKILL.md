---
name: mem0-lite
description: "Groq-powered memory extraction and search for AI agents without heavy ML dependencies (no PyTorch). Use when: capturing facts from conversations, searching stored memories, managing per-user knowledge. Lightweight alternative to full Mem0/ChromaDB stack. Requires GROQ_API_KEY."
---

# mem0-lite — Groq Memory Extractor

Extracts structured facts from conversation text via Groq LLM and stores them as JSON for fast retrieval. No vector DB, no PyTorch, no persistent service — just Groq API + file storage.

## When to Use

- After a session with Alex: extract and persist important facts
- Before generating a response: search stored memories for relevant context
- When building on prior knowledge: retrieve what you know about a person/project
- As an alternative to manually updating MEMORY.md

## When NOT to Use

- For semantic vector search (use `qmd` skill instead)
- For relationship traversal between entities (use `networkx-graph` skill instead)
- When disk or network is unavailable (Groq API required)

## Prerequisites

```bash
# GROQ_API_KEY (from openclaw.json)
export GROQ_API_KEY=$(python3 -c "
import json
d = json.load(open('/home/openclaw/.openclaw/openclaw.json'))
print(d['skills']['entries']['groq-whisper']['apiKey'])
")

# Scripts location
SCRIPTS=/home/openclaw/.openclaw/workspace/skills/mem0-lite/scripts

# Data location (auto-created)
# /home/openclaw/.openclaw/workspace/skills/mem0-lite/data/memories.json
```

**Known quirk:** Groq API blocks Python's default `urllib` User-Agent. Scripts set `User-Agent: curl/7.88.1` — do not remove this header.

## Operations

### 1. Add Memory — Extract Facts from Text

```bash
GROQ_API_KEY=$GROQ_KEY python3 $SCRIPTS/extract.py \
  --text "Alex arbeitet an Gisela-Kampagne. Deadline: 12. März 2026." \
  --user alex
```

Output:
```
Extrahiere Fakten aus Text...
  ✅ Alex arbeitet an der Gisela-Kampagne
  ✅ Deadline Gisela-Kampagne: 12. März 2026
2 neue Fakten gespeichert (11 gesamt).
```

**From stdin** (pipe a conversation summary):
```bash
echo "Alex lernt Spanisch." | GROQ_API_KEY=$GROQ_KEY python3 $SCRIPTS/extract.py
```

### 2. Search Memories

```bash
# Keyword search (fast, local)
GROQ_API_KEY=$GROQ_KEY python3 $SCRIPTS/extract.py --search "Gisela" --user alex
```

Output:
```
  [Alex] Alex arbeitet an der Gisela-Kampagne
  [Gisela-Kampagne] Deadline Gisela-Kampagne: 12. März 2026
  [Gisela-Kampagne] Thema Theater und Brandschutz
3 Treffer.
```

### 3. List All Memories

```bash
python3 $SCRIPTS/extract.py --list --user alex --limit 30
```

### 4. Deduplication

Built-in: Facts are hashed (MD5 of fact text). Identical facts silently skipped.
Groq's LLM handles semantic deduplication during extraction (infer=True equivalent).

## Memory Schema

Each memory in `data/memories.json`:

```json
{
  "id": "a3f1c2b4",          // MD5 hash of fact text (8 chars)
  "fact": "Alex arbeitet an der Gisela-Kampagne",
  "entity": "Alex",          // Main subject
  "relation": "arbeitet_an", // Relationship type
  "target": "Gisela-Kampagne", // Object of relation
  "user_id": "alex",
  "source": "manual",
  "created_at": "2026-02-21T18:00:00+00:00"
}
```

## Integration: After-Session Workflow

After an important session with Alex, run:

```bash
export GROQ_API_KEY=$(python3 -c "import json; d=json.load(open('/home/openclaw/.openclaw/openclaw.json')); print(d['skills']['entries']['groq-whisper']['apiKey'])")

# Extract from session summary
python3 /home/openclaw/.openclaw/workspace/skills/mem0-lite/scripts/extract.py \
  --text "[Gesprächszusammenfassung hier]" \
  --user alex

# Sync to knowledge graph
python3 /home/openclaw/.openclaw/workspace/skills/networkx-graph/scripts/graph.py --sync
```

## Compared to Full Mem0 OSS

| Feature | mem0-lite | Full Mem0 OSS |
|---------|-----------|---------------|
| LLM extraction | ✅ Groq | ✅ OpenAI/Groq/Ollama |
| Vector search | ❌ keyword only | ✅ ChromaDB/Qdrant |
| RAM | ~0MB (no service) | ~200MB+ |
| Disk | ~5MB | ~500MB (PyTorch) |
| Conflict resolution | hash dedup | full semantic merge |
| API | Python script | Python SDK |

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `403 Forbidden` | Wrong User-Agent or bad key | Check GROQ_API_KEY; scripts must set `User-Agent: curl/7.88.1` |
| `No module named ssl` | Python env issue | Use system Python3, not venv |
| `Keine Fakten extrahiert` | Empty text or API failure | Check input text is not empty; verify GROQ_API_KEY |
| Disk full | Large memories.json | `python3 extract.py --list` and manually prune old entries |

## Guardrails

- Never store raw API keys in memories.json
- Never call extract.py without GROQ_API_KEY set — fails silently
- Search is keyword-only (not semantic) — use `qmd` for semantic search over the memory files
- max_tokens=1024 for extraction; very long texts may get truncated facts — chunk if needed
