---
name: model-ranking
description: "Personal model ranking for optimal model selection. Tracks performance, rate-limits, and user preferences. Use when: switching models, planning sessions, avoiding dead-ends from rate-limits."
---

# Model Ranking — Personal Learning

**Goal:** Right model for right task. Avoid rate-limit dead-ends.

## User Preferences (learned)

**Preferred models:**
- Opus 4.6 → 10/10 (best quality)
- Kimi 2.5 → 9/10 (1M Context, reliable)
- Sonnet 4.6 → 9/10 (balanced)
- GLM 4 Free → 8/10 (slow but good)

**Budget:** Flexible (€0-20+/month)
**Priority:** Balance (switch based on task)

## Ranking

### 🏆 HIGH CLASS

| Model | User Rating | When to use |
|-------|-------------|-------------|
| **Opus 4.6** | 10/10 | Complex decisions, Architecture, Security |
| **Sonnet 4.6** | 9/10 | Daily driver, Coding, Docs |

### 🛠️ WORKING HORSES

| Model | User Rating | When to use |
|-------|-------------|-------------|
| **Kimi 2.5** | 9/10 | Long sessions (1M context) |
| **Trinity Large** | ?/10 | Testing, Free backup |
| **GLM 4 Free** | 8/10 | Quality over speed |

### 🆓 FREE TIER (Backup)

| Model | User Rating | Warning |
|-------|-------------|---------|
| **Gemini 3 Pro** | ?/10 | Frequent rate-limits |
| **Qwen3 80B** | ?/10 | Frequent rate-limits |

## Auto-Switch Logic

```
1. Try HIGH CLASS
2. If Rate-Limit → WORKING HORSES
3. If Rate-Limit → FREE TIER
4. Issue warning on downgrade
```

## Warning Levels

```
🟢 HIGH CLASS → "All good"
🟡 WORKING HORSE → "Quality okay"
🔴 FREE TIER → "May hit limits"
```

## Logging

Performance is tracked in `model_performance.json`:
- Which models were used
- Success/failure
- Rate-limit events

## Next Questions

Ask in ~5 sessions:
- Most frequent task types?
- Models that DON'T work?

## Learning

> "Collect data iteratively. Ask occasionally. Ranking emerges through experience."
