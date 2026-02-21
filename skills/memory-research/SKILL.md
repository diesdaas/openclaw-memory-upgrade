---
name: memory-research
description: "Research framework for memory optimization. Token efficiency benchmarks, retrieval accuracy tests, multi-agent security audits. Use when: optimizing memory systems, testing new configurations, security auditing."
---

# Memory Research Framework

Systematic research methodology for AI memory optimization.

## What I Learned

### Token Efficiency

| Finding | Impact |
|---------|--------|
| TSV is 16x more efficient than JSON | Store relationships as entity\trelation\ttarget |
| Markdown is good for human-readable | Use MEMORY.md for curated long-term |
| JSON overhead is 65 tokens/memory | Avoid JSON for high-volume storage |

### Retrieval Methods

| Method | Latency | Best For |
|--------|---------|----------|
| MEMORY.md scan | 0.5ms | Exact keyword lookup |
| NetworkX graph | 200ms | Relationship traversal |
| Neo4j Cypher | 82ms | Multi-hop queries |
| qmd semantic | 500ms | Discovery search |

### Query Routing

```
Query Type → Best Method

"Exact keyword" → MEMORY.md (0.5ms)
"How does X relate?" → Neo4j/Graph (82-200ms)
"Find everything about X" → Hybrid (500ms)
```

### Security Findings

| Vulnerability | Fix |
|---------------|-----|
| Namespace Bypass | verify_access() with token |
| Wildcard Leak | filter_by_category() always |

## Research Tools

### Token Efficiency Test

```bash
python3 tests/test_token_efficiency.py --input test_memories.json
```

### Retrieval Benchmark

```bash
python3 tests/test_retrieval_accuracy.py --benchmark
```

### Multi-Agent Security Test

```bash
python3 tests/test_multi_agent_permissions.py --all
```

## Methodology

1. **Hypothesis** → Define what to test
2. **Test Data** → Generate synthetic or use real data
3. **Benchmark** → Measure with metrics.py
4. **Document** → Update RESEARCH_FINDINGS.md
5. **Implement** → Apply learnings to skills

## Cost Tracking

- Perplexity Research: ~$0.09 total today
- Free tier tools: $0/month

## Files

```
memory-research/
├── SKILL.md              # This file
├── PRD.json              # Research PRD (RALPH format)
├── RESEARCH_FINDINGS.md  # Detailed results
├── SECURITY_AUDIT.md     # Multi-agent security
└── tests/
    ├── test_token_efficiency.py
    ├── test_retrieval_accuracy.py
    └── test_multi_agent_permissions.py
```

## Key Insight

> "Scripts are 100% token-free for retrieval. Use scripts instead of LLM calls whenever possible."
