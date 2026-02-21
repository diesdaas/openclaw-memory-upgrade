# Memory Benchmarks & Performance Data

**Research Date:** February 2026

---

## Token Efficiency Results

### Test Methodology
Compared 6 storage formats with 50 synthetic memories of various types (facts, relationships, episodes, preferences).

### Results

| Format | Tokens/Memory | Efficiency Rating |
|--------|---------------|-------------------|
| **TSV (Graph Edges)** | **4.1** | 🏆 **Best** |
| Markdown | 10.2 | Good for readability |
| Key-Value | 11.0 | Good balance |
| Summarized JSON | 18.8 | Moderate |
| JSON (compact) | 54.7 | Poor |
| JSON (pretty) | 65.3 | ❌ Worst |

### Compression Analysis

| Format | Original Bytes | Gzipped | Ratio |
|--------|---------------|---------|-------|
| TSV | 820 | 423 | 51.6% |
| Markdown | 2,108 | 857 | 40.7% |
| JSON (pretty) | 13,074 | 2,131 | 16.3% |

**Conclusion:** For LLM context windows, uncompressed tokens matter. TSV remains most efficient.

---

## Retrieval Accuracy Results

### Test Methodology
Benchmarked 5 retrieval methods across 4 test queries with ground truth data.

### Latency Results

| Method | Avg Latency | Notes |
|--------|-------------|-------|
| **MEMORY.md scan** | **0.5ms** | File read only |
| **Neo4j Cypher** | 82ms | Network + query |
| **networkx-graph** | 175ms | Python startup + traversal |
| **qmd semantic** | 522ms | Embedding + vector search |
| **Hybrid** | 523ms | Combined methods |

### Accuracy Results (Precision@5 / Recall@5)

| Method | P@5 | R@5 | F1 |
|--------|-----|-----|-----|
| **Neo4j** | **0.33** | **0.56** | 0.42 |
| networkx-graph | 0.13 | 0.22 | 0.16 |
| Hybrid | 0.13 | 0.22 | 0.16 |
| MEMORY.md | - | - | keyword only |
| qmd | - | - | needs indexed data |

### Query Type Analysis

| Query Type | Best Method | Latency | Accuracy |
|------------|-------------|---------|----------|
| Exact keyword | MEMORY.md | 0.5ms | High |
| Relationship | Neo4j | 82ms | Highest |
| Multi-hop | Neo4j | 82ms | High |
| Discovery | Hybrid | 523ms | Medium |
| Offline query | networkx-graph | 175ms | Medium |

---

## Multi-Agent Security Test Results

### Test Setup

3 simulated agents with different permission levels:
- **Agent A (producer)**: Access to project category only
- **Agent B (admin)**: Access to all categories
- **Agent C (guest)**: Access to public category only

### Test Results

| Test | Result | Notes |
|------|--------|-------|
| Isolation | ✅ PASS | Agents only see their own memories |
| Cross-namespace read | ✅ PASS | No leakage between user_ids |
| **Cross-namespace write** | ⚠️ VULNERABILITY | No server-side enforcement |
| **Wildcard leak** | ⚠️ LEAK | agent_id="*" shows all for user |

### Vulnerability Details

**1. Namespace Bypass (HIGH)**
- Any agent can set `agent_id="admin"` when writing
- No verification that writer owns the namespace
- Impact: Data contamination, privilege escalation

**2. Wildcard Leak (MEDIUM)**
- Querying with `agent_id="*"` returns all user's memories
- Category-based access control not enforced
- Impact: Lower-privilege agents see sensitive data

---

## Token Savings Calculation

### For 100 Memories

| Storage | Total Tokens | % of Context (100k) |
|---------|--------------|---------------------|
| JSON (pretty) | 6,530 | 6.5% |
| JSON (compact) | 5,470 | 5.5% |
| Markdown | 1,020 | 1.0% |
| **TSV** | **410** | **0.4%** |

**Savings:** TSV uses **94% fewer tokens** than JSON.

### For 1,000 Memories

| Storage | Total Tokens | % of Context |
|---------|--------------|--------------|
| JSON (pretty) | 65,300 | 65% |
| **TSV** | **4,100** | **4%** |

**Impact:** With JSON, you'd use 65% of your context on memory alone. With TSV, only 4%.

---

## Recommendations Summary

1. **Use TSV for relationships** — 16x better than JSON
2. **Use Neo4j for relationship queries** — Best accuracy
3. **Use MEMORY.md for keywords** — Fastest (0.5ms)
4. **Use scripts instead of LLM** — 100% token savings
5. **Implement query routing** — Match method to query type
