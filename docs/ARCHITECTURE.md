# Memory System Architecture

A production-ready, multi-layer memory system for AI agents.

---

## Overview

This architecture addresses the key challenges of AI agent memory:
- **Token efficiency** — Minimize context window usage
- **Fast retrieval** — Sub-100ms for most queries
- **Relationship modeling** — Entity connections, not just facts
- **Multi-agent isolation** — Namespace security
- **Offline capability** — Works without network

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MEMORY STACK                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 0: MEMORY.md                                   │   │
│  │ • Manually curated long-term memory                  │   │
│  │ • Fastest access: 0.5ms                              │   │
│  │ • Max ~10k tokens                                    │   │
│  │ • Human-readable, git-trackable                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 1: mem0-lite (Facts)                           │   │
│  │ • Auto-extracted facts from conversations            │   │
│  │ • Groq-powered LLM extraction                        │   │
│  │ • JSON storage with deduplication                    │   │
│  │ • Namespace: user_id + agent_id                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 2: networkx-graph (Relationships)              │   │
│  │ • Entity → Relation → Target triples                 │   │
│  │ • TSV format: 4.1 tokens/memory                      │   │
│  │ • Offline-capable, no server needed                  │   │
│  │ • Python NetworkX DiGraph                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Layer 3: Neo4j (Graph Database)                      │   │
│  │ • Multi-hop traversal                                │   │
│  │ • Best accuracy for relationship queries             │   │
│  │ • Cypher query language                              │   │
│  │ • 82ms average latency                               │   │
│  │ • Optional (requires Docker)                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Index: qmd (Semantic Search)                         │   │
│  │ • BM25 + Vector embeddings                           │   │
│  │ • Discovery queries, semantic similarity             │   │
│  │ • ~500ms latency                                     │   │
│  │ • Optional (requires npm install)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Query Routing

Different query types are routed to optimal methods:

```
                    QUERY
                      │
                      ▼
        ┌─────────────────────────┐
        │ Is it a known keyword?   │
        └────────────┬────────────┘
               YES │     │ NO
                   ▼     ▼
            MEMORY.md   ┌─────────────────────┐
            (0.5ms)     │ Relationship words?  │
                        └──────────┬──────────┘
                              YES │     │ NO
                                  ▼     ▼
                             Neo4j   ┌─────────────────┐
                            (82ms)   │ Discovery query? │
                                     └────────┬────────┘
                                        YES │     │ NO
                                            ▼     ▼
                                       Hybrid  networkx
                                      (523ms)  (175ms)
```

---

## Data Flow

### Writing Memory

```
Conversation
     │
     ▼
mem0-lite extract (Groq API)
     │
     ├── Extract: "User works on Project X"
     ├── Entity: User
     ├── Relation: works_on
     └── Target: Project X
     │
     ▼
memories.json (JSON)
     │
     ▼
graph.py --sync
     │
     ▼
graph.json (TSV)
     │
     ▼
Neo4j sync (optional)
```

### Reading Memory

```
Query: "What about Project X?"
              │
              ▼
     Route to optimal method
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
MEMORY.md  Graph    Semantic
(0.5ms)   (200ms)   (500ms)
    │         │         │
    └─────────┴─────────┘
              │
              ▼
         Combined result
```

---

## Token Comparison

| Storage | 100 memories | 1000 memories |
|---------|-------------|---------------|
| JSON | 6,530 tokens | 65,300 tokens |
| **TSV** | **410 tokens** | **4,100 tokens** |
| Savings | **94%** | **94%** |

---

## Latency Comparison

| Operation | LLM Call | Script | Speedup |
|-----------|----------|--------|---------|
| Keyword search | 500ms | 0.5ms | **1000x** |
| Graph query | 800ms | 200ms | **4x** |
| List facts | 300ms | 10ms | **30x** |

---

## Security Model

```
┌────────────────────────────────────────┐
│           USER ISOLATION               │
│  user_id: Completely separate tenants  │
└────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│          AGENT ISOLATION               │
│  agent_id: Agents within user isolated │
│  (requires server-side verification)   │
└────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│          CATEGORY ACCESS               │
│  category: Content-based permissions   │
│  (admin: *, producer: project, etc.)   │
└────────────────────────────────────────┘
```

---

## Cost Model

| Component | Cost |
|-----------|------|
| Groq API (extraction) | Free tier: 7,200s/day |
| Neo4j Community | Free |
| networkx | Free |
| qmd | Free |
| **Monthly total** | **$0** |

---

## Scaling

| Memories | Recommended Setup |
|----------|-------------------|
| < 100 | Just MEMORY.md + mem0-lite |
| 100 - 1,000 | Add networkx-graph |
| 1,000 - 10,000 | Add Neo4j |
| 10,000+ | Add qmd index |

---

## Files Structure

```
~/.openclaw/
├── workspace/
│   ├── MEMORY.md              # Layer 0
│   └── memory/
│       └── YYYY-MM-DD.md      # Daily logs
└── skills/
    ├── mem0-lite/
    │   ├── data/memories.json # Layer 1
    │   └── scripts/extract.py
    ├── networkx-graph/
    │   ├── data/graph.json    # Layer 2
    │   └── scripts/graph.py
    ├── neo4j/                 # Layer 3
    │   └── SKILL.md
    └── memory-tools/
        └── scripts/memory-cli.sh
```
