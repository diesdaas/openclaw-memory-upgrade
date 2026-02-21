---
name: memory-tools
description: "Unified memory access CLI. Fast, token-efficient retrieval via scripts. Routes queries automatically: keywords → MEMORY.md (0.5ms), relationships → graph (200ms), discovery → semantic (500ms). Use for: quick lookups, fact extraction, relationship queries, consolidation."
---

# memory-tools — Unified Memory CLI

Single entry point for all memory operations. Scripts are faster and token-saving.

## Quick Reference

```bash
# FAST: Keyword lookup (0.5ms)
memory-cli.sh quick "project"

# SEMANTIC: Discovery search (500ms)
memory-cli.sh search "deadline project"

# GRAPH: Relationships (200ms)
memory-cli.sh graph "User"

# STATUS
memory-cli.sh status
```

## Commands

| Command | Latency | Use Case |
|---------|---------|----------|
| `quick <keyword>` | **0.5ms** | Exact keyword in MEMORY.md |
| `graph <entity>` | 200ms | Relationship traversal |
| `search <query>` | 500ms | Semantic discovery |
| `facts` | 10ms | List stored facts |
| `extract <text>` | 2s | Extract facts via Groq |
| `add <e> <rel> <t>` | 50ms | Add relationship manually |
| `consolidate` | — | Daily → long-term migration |
| `prune` | 100ms | Remove old low-access facts |
| `sync` | 500ms | Sync networkx → Neo4j |
| `status` | 50ms | Show memory stats |

## Query Routing (Automatic)

```
QUERY TYPE              → BEST METHOD

"What about X?"         → quick (MEMORY.md)
"How does X relate?"    → graph (networkx/Neo4j)
"Find all about X"      → search (qmd semantic)
```

## Integration with Other Skills

### transcription
```bash
# After transcription
memory-cli.sh extract "$(cat transcript.txt)"
```

### film/media
```bash
# After discussion
memory-cli.sh extract "Project X has deadline March 2026"

# Query relationships
memory-cli.sh graph "ProjectX"
```

### github
```bash
# Store repo relationships
memory-cli.sh add "ProjectX" "uses_repo" "github.com/example/repo"
```

## Security Notes

- `extract` requires `GROQ_API_KEY`
- `sync` requires Neo4j running
- `prune` removes facts with: age > 30d AND access_count < 5

## Token Efficiency

Using scripts instead of LLM calls:

| Operation | LLM Method | Script Method | Savings |
|-----------|------------|---------------|---------|
| Keyword lookup | 500 tokens | 0 tokens | 100% |
| Graph query | 800 tokens | 0 tokens | 100% |
| List facts | 300 tokens | 0 tokens | 100% |

**Scripts should be preferred for all retrieval operations.**

## Location

```
skills/memory-tools/
├── SKILL.md
└── scripts/
    └── memory-cli.sh    # Unified CLI
```
