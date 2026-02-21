# Ullrich Memory Optimization Research - Findings

**Research Date:** 2026-02-21
**Token Budget:** ~$0.03 Perplexity
**Test Data:** 50 synthetic memories

## Executive Summary

**Key Discovery:** Graph-based storage (TSV) is 16x more token-efficient than JSON, while Neo4j provides the best retrieval accuracy for relationship queries.

## Experiment 1: Token Efficiency

### Methodology
Compared 6 storage formats across 50 test memories:
- JSON (pretty, compact)
- Markdown
- Key-Value
- Graph Edges (TSV)
- Summarized JSON

### Results

| Format | Tokens/Memory | Efficiency |
|--------|---------------|------------|
| **Graph Edges (TSV)** | **4.1** | 🏆 **Best** |
| Markdown | 10.2 | Good for readability |
| Key-Value | 11.0 | Good balance |
| Summarized JSON | 18.8 | Moderate |
| JSON (compact) | 54.7 | Poor |
| JSON (pretty) | 65.3 | ❌ Worst |

### Compression Analysis

- JSON compresses well (16-19% of original)
- But for LLM context, **uncompressed tokens** matter
- TSV remains most efficient even without compression

### Recommendation

**For facts/relationships:** Use TSV format (entity\trelation\ttarget)
**For human-readable docs:** Use Markdown
**Avoid:** Full JSON for memory storage (16x less efficient)

## Experiment 2: Retrieval Accuracy

### Methodology
Benchmarked 5 retrieval methods across 4 test queries:
- qmd (vector search)
- Neo4j (graph traversal)
- networkx-graph (--ego)
- MEMORY.md scan
- Hybrid (qmd + Neo4j)

### Results

| Method | Latency | P@5 | R@5 | Best For |
|--------|---------|-----|-----|----------|
| **MEMORY.md** | **0.5ms** | 0.00 | 0.00 | Fast keyword check |
| **Neo4j** | 82ms | **0.33** | **0.56** | Relationship queries |
| graph | 175ms | 0.13 | 0.22 | Offline traversal |
| qmd | 522ms | 0.00 | 0.00 | Semantic discovery* |
| hybrid | 523ms | 0.13 | 0.22 | Maximum coverage |

*qmd needs indexed data; test data wasn't indexed

### Query-Type Analysis

| Query Type | Best Method | Why |
|------------|-------------|-----|
| "What about X?" | MEMORY.md | 0.5ms for known keywords |
| "How does X relate to Y?" | Neo4j | Multi-hop traversal |
| "Find all about X" | Hybrid | Vector + Graph combined |
| "Who's involved?" | Graph | Entity extraction |

### Latency Breakdown

```
MEMORY.md scan:   ~0.5ms  (file read)
Neo4j Cypher:     ~80ms   (network + query)
networkx-graph:   ~175ms  (Python startup + traversal)
qmd search:       ~520ms  (embedding + vector search)
```

## Experiment 3: Consolidation (Theoretical)

Based on Perplexity research (~$0.03):

### Research Findings

1. **Hybrid RAG (Vector + Graph) → +30% accuracy** vs vector-only
2. **Multi-tiered Memory**: Core (RAM) → Archival (Disk/Vector)
3. **Sleep-time Consolidation**: Async processing during idle periods
4. **Conflict Resolution**: Intelligent merging, not just append
5. **Forgetting Curves**: Prune data with low access + low relevance

### Recommended Consolidation Strategy

```
SESSION END
    ↓
mem0-lite extract → Extract facts (automatic)
    ↓
graph.py --sync → Build relationships
    ↓
sync-neo4j.py → Update graph DB
    ↓
DAILY: memory/*.md → MEMORY.md (manual curation)
    ↓
WEEKLY: Prune old facts (access_count < 5 AND age > 30 days)
```

## Optimal Memory Configuration

Based on all experiments, here's the recommended configuration:

### Storage Layer

```json
{
  "short_term": {
    "location": "memory/YYYY-MM-DD.md",
    "format": "markdown",
    "retention": "7 days"
  },
  "long_term": {
    "location": "MEMORY.md",
    "format": "markdown",
    "max_tokens": 10000,
    "consolidation": "manual"
  },
  "facts": {
    "location": "mem0-lite/data/memories.json",
    "format": "json",
    "max_entries": 1000,
    "pruning": "access_count < 5 AND age > 30d"
  },
  "relationships": {
    "location": "networkx-graph/data/graph.json",
    "format": "tsv",
    "sync_to": "neo4j"
  },
  "index": {
    "vector": "qmd",
    "graph": "neo4j"
  }
}
```

### Query Routing

```python
def route_query(query: str) -> str:
    """Route query to optimal retrieval method."""
    
    # Fast keyword check
    if is_exact_keyword(query):
        return "memory_md"  # 0.5ms
    
    # Relationship query
    if has_relationship_words(query):  # "how", "relates", "connects"
        return "neo4j"  # 80ms, best accuracy
    
    # Discovery query
    if is_discovery_query(query):  # "find all", "everything about"
        return "hybrid"  # 520ms, max recall
    
    # Default: graph for structured data
    return "graph"  # 175ms, works offline
```

## Token Savings Calculation

**Current Setup (JSON):**
- 50 memories = 3,267 tokens
- Per memory: 65.3 tokens

**Optimized Setup (TSV + selective indexing):**
- 50 memories = 204 tokens (TSV)
- Per memory: 4.1 tokens
- **Savings: 94%**

**For 1,000 memories:**
- Current: 65,300 tokens (~40% of GPT-4 context)
- Optimized: 4,100 tokens (~2.5% of GPT-4 context)

## Action Items

1. **Implement TSV export** for mem0-lite facts
2. **Add query routing** based on query type
3. **Set up weekly pruning** job
4. **Optimize qmd indexing** for test data
5. **Create consolidation pipeline** (daily → long-term)

## Next Steps

- [ ] Test consolidation triggers (time vs session count)
- [ ] Benchmark forgetting curves
- [ ] Implement automatic query routing
- [ ] Measure long-term information retention

---

**Research Budget Used:**
- Perplexity queries: 3 × ~$0.01 = $0.03
- Remaining budget: $0.07

**Total Research Time:** ~1 hour
