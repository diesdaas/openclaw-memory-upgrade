# OpenClaw Memory Upgrade

**Upgrade your OpenClaw bot with a production-ready, token-efficient memory system.**

- **94% token savings** vs JSON-based memory
- **0.5ms - 82ms retrieval** (vs 500ms+ LLM calls)
- **Multi-agent isolation** with namespace security
- **$0/month** running costs (all free-tier tools)

---

## Quick Start

```bash
# 1. Clone into your OpenClaw workspace
cd ~/.openclaw/workspace/skills
git clone https://github.com/YOUR_USERNAME/openclaw-memory-upgrade.git memory-tools

# 2. Run setup
cd memory-tools
./scripts/setup.sh

# 3. Test
./scripts/memory-cli.sh status
```

---

## What You Get

### Unified Memory CLI

```bash
memory-cli.sh quick "keyword"     # 0.5ms, 0 tokens
memory-cli.sh graph "entity"      # 200ms, 0 tokens
memory-cli.sh search "query"      # 500ms, 0 tokens
memory-cli.sh extract "text..."   # Auto-extract facts
memory-cli.sh status              # Memory overview
```

### Multi-Layer Architecture

```
Layer 0: MEMORY.md      → Long-term, curated (0.5ms)
Layer 1: mem0-lite      → Auto-extracted facts (JSON)
Layer 2: networkx-graph → Relationships (TSV, 4.1 tok/mem)
Layer 3: Neo4j          → Multi-hop traversal (82ms)
Index:   qmd            → Semantic search (500ms)
```

### Query Routing (Automatic)

```
"Wie hängt X mit Y?"  → Graph (200ms)
"Was über X?"         → MEMORY.md (0.5ms)
"Finde alles über X"  → Hybrid (500ms)
```

---

## Requirements

- OpenClaw installed
- Python 3.10+
- Docker (for Neo4j)
- Groq API key (free tier)
- ~1GB RAM for Neo4j
- ~5GB disk

---

## Installation

### Step 1: Install Dependencies

```bash
# Python packages (already included in most OpenClaw setups)
pip3 install networkx

# qmd for semantic search
npm install -g qmd

# Neo4j (optional, for graph DB)
docker run -d --name neo4j \
  -p 127.0.0.1:7474:7474 \
  -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword \
  neo4j:community
```

### Step 2: Configure API Keys

Add to `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "groq-whisper": {
        "apiKey": "gsk_your_groq_key"
      }
    }
  }
}
```

### Step 3: Initialize Memory System

```bash
./scripts/setup.sh --init
```

---

## Usage Examples

### After a Conversation

```bash
# Extract facts from discussion
memory-cli.sh extract "Alex arbeitet an Gisela-Kampagne. Deadline 12. März 2026."

# Sync to graph
memory-cli.sh sync
```

### Query Memory

```bash
# Quick keyword lookup
memory-cli.sh quick "Gisela"
# → MEMORY.md scan (0.5ms)

# Relationship query
memory-cli.sh graph "Gisela"
# → Shows: Gisela → has_deadline → 12. März
#          Gisela → hat_task → TODO: ...

# Semantic discovery
memory-cli.sh search "film project deadline"
# → qmd semantic search (500ms)
```

### Maintenance

```bash
# Weekly: Remove old low-access facts
memory-cli.sh prune

# Daily → Long-term consolidation
memory-cli.sh consolidate
```

---

## Architecture

```
skills/memory-tools/
├── SKILL.md                    # Documentation
├── scripts/
│   ├── memory-cli.sh           # Unified CLI
│   ├── setup.sh                # Installation
│   ├── extract.py              # Fact extraction (Groq)
│   └── graph.py                # NetworkX operations
├── docs/
│   ├── ARCHITECTURE.md         # Deep dive
│   ├── SECURITY.md             # Multi-agent isolation
│   └── BENCHMARKS.md           # Performance data
└── data/                       # Memory storage
    ├── memories.json           # Facts
    └── graph.json              # Relationships
```

---

## Benchmarks

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Tokens/memory | 65.3 | 4.1 | **16x better** |
| Keyword lookup | 500ms | 0.5ms | **1000x faster** |
| Relationship query | N/A | 82ms | New capability |
| Multi-agent support | No | Yes | Security added |

---

## Security

### Multi-Agent Isolation

Each agent has isolated memory via `user_id` + `agent_id`:

```python
# Agent A cannot see Agent B's memories
memory.search(query, user_id="alice", agent_id="film-producer")
```

### Known Vulnerabilities (documented)

1. **Namespace Bypass** — Requires server-side agent_id verification
2. **Wildcard Leak** — Requires category-based RBAC

See `docs/SECURITY.md` for mitigations.

---

## Contributing

1. Fork this repo
2. Make improvements
3. Submit PR with benchmarks

---

## License

MIT — Use freely, credit appreciated.

---

## Credits

- Research: Ullrich (OpenClaw AI Agent)
- Framework: OpenClaw
- Tools: Groq, Neo4j, NetworkX, qmd, Mem0 (inspiration)
