---
name: model-ranking
description: "Personal model ranking for optimal model selection. Tracks performance, rate-limits, and Alex's preferences. Use when: switching models, planning sessions, avoiding dead-ends from rate-limits."
---

# Model Ranking — Personal Learning

**Ziel:** Richtiges Modell für richtige Aufgabe. Rate-Limit Dead-Ends vermeiden.

## Alex's Preferences (gelernt)

**Mag ich:**
- Opus 4.6 → 10/10 (beste Qualität)
- Kimi 2.5 → 9/10 (1M Context, zuverlässig)
- Sonnet 4.6 → 9/10 (ausgewogen)
- GLM 4 Free → 8/10 (langsam aber gut)

**Budget:** Flexibel (€0-20+/Monat)
**Priorität:** Balance (wechseln je nach Task)

## Ranking

### 🏆 HIGH CLASS

| Model | Alex-Rating | Wann nutzen |
|-------|-------------|-------------|
| **Opus 4.6** | 10/10 | Complex decisions, Architecture, Security |
| **Sonnet 4.6** | 9/10 | Daily driver, Coding, Docs |

### 🛠️ WORKING HORSES

| Model | Alex-Rating | Wann nutzen |
|-------|-------------|-------------|
| **Kimi 2.5** | 9/10 | Long sessions (1M context) |
| **Trinity Large** | ?/10 | Testing, Free backup |
| **GLM 4 Free** | 8/10 | Quality over speed |

### 🆓 FREE TIER (Backup)

| Model | Alex-Rating | Warnung |
|-------|-------------|---------|
| **Gemini 3 Pro** | ?/10 | Häufig Rate-limits |
| **Qwen3 80B** | ?/10 | Rate-limits häufig |

## Auto-Switch Logik

```
1. HIGH CLASS versuchen
2. Falls Rate-Limit → WORKING HORSES
3. Falls Rate-Limit → FREE TIER
4. Warnung ausgeben bei Abstufung
```

## Warn-Level

```
🟢 HIGH CLASS → "Alles gut"
🟡 WORKING HORSE → "Qualität okay"
🔴 FREE TIER → "Könnte limitieren"
```

## Logging

Performance wird in `model_performance.json` getrackt:
- Welche Modelle genutzt
- Erfolg/Misserfolg
- Rate-Limit-Events

## Nächste Fragen

In ~5 Sessions fragen:
- Häufigste Task-Typen?
- Modelle die NICHT funktionieren?

## Lernen

> "Sammle Daten iterativ. Frage ab und zu. Ranking entsteht durch Erfahrung."
