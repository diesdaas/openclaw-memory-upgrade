---
name: networkx-graph
description: "Persistent knowledge graph using NetworkX DiGraph. JSON-backed, no server. Use when: traversing entity relationships, finding connections between projects/people/deadlines, building 'what hangs together?' context for agents. Ego-graphs, shortest paths, weakly connected components. Syncs from mem0-lite memories."
---

# networkx-graph — Knowledge Graph für Agenten

Directed graph (DiGraph) mit JSON-Persistenz. Keine Datenbank, kein Server — Nodes und Edges werden als JSON gespeichert und in NetworkX geladen. Ideal für Beziehungsmodellierung zwischen Projekten, Personen, Deadlines, Konzepten.

## When to Use

- *"Was hängt alles mit Gisela zusammen?"* → `--ego "Gisela"`
- *"Wie ist Alex mit diesem Fördertopf verbunden?"* → `--path "Alex" "Fördertopf"`
- *"Welche Entitäten sind isoliert (keine Verbindung)?"* → `--components`
- Nach mem0-lite Extraktion: `--sync` um Fakten zu Nodes/Edges zu konvertieren
- Manuell Beziehungen modellieren die aus Text nicht extrahiert werden

## When NOT to Use

- Für Volltextsuche in Dokumenten → `qmd` Skill
- Für Faktenextraktion aus Gesprächen → `mem0-lite` Skill
- Wenn du nur MEMORY.md schreiben willst → direkt schreiben

## Prerequisites

```bash
# networkx ist system-installiert (3.6.1)
python3 -c "import networkx; print(networkx.__version__)"

# Script
GRAPH=/home/openclaw/.openclaw/workspace/skills/networkx-graph/scripts/graph.py
```

## Operations

### Sync aus mem0-lite

Lädt alle Fakten aus `mem0-lite/data/memories.json` und baut daraus Nodes und Edges:

```bash
python3 $GRAPH --sync
# Graph gespeichert: 6 Nodes, 5 Edges → .../graph.json
```

### Ego-Graph — "Was hängt mit X zusammen?"

```bash
python3 $GRAPH --ego "Gisela" --radius 2
```

Output:
```
Ego-Graph von 'Gisela-Kampagne' (Radius 2):
5 Nodes, 4 Edges

  🔵 Gisela-Kampagne (Zentrum)
    ○ Alex (Hop 1)
    ○ 12. März 2026 (Hop 1)
    ○ Thema Theater und Brandschutz (Hop 1)
      ○ Roland Klick (Hop 2)
```

### Direkte Nachbarn

```bash
python3 $GRAPH --query "Alex"
```

Output:
```
🔵 Alex [entity]
  → ausgehend:
    --[hat_gelernt]--> Roland Klick
       💬 hat bei Roland Klick persönlich gelernt
    --[arbeitet_an]--> Gisela-Kampagne
       💬 arbeitet an der Gisela-Kampagne
  ← eingehend:
    (keine)
```

### Pfad zwischen zwei Nodes

```bash
python3 $GRAPH --path "Roland Klick" "12. März 2026"
```

Output:
```
Pfad (3 Hops): Roland Klick → Alex → Gisela-Kampagne → 12. März 2026
  Roland Klick <--[hat_gelernt]-- Alex (umgekehrt)
  Alex --[arbeitet_an]--> Gisela-Kampagne
  Gisela-Kampagne --[hat_deadline]--> 12. März 2026
```

### Nodes und Edges manuell hinzufügen

```bash
# Node mit Attributen
python3 $GRAPH --add-node "Förderantrag" type=document status=offen

# Gerichtete Edge
python3 $GRAPH --add-edge "Gisela-Kampagne" "braucht" "Förderantrag"

# Beziehung aus Kontext
python3 $GRAPH --add-edge "Alex" "kontaktiert" "90Mail" reason=material
```

### Zusammenhangskomponenten

```bash
python3 $GRAPH --components
```

Zeigt isolierte Cluster — nützlich wenn Fakten aus verschiedenen Sessions keinen gemeinsamen Anker haben.

### Gesamtübersicht

```bash
python3 $GRAPH --viz
```

### Export für externe Tools

```bash
# GML für Gephi / yEd
python3 $GRAPH --export /tmp/graph.gml

# GraphML
python3 $GRAPH --export /tmp/graph.graphml
```

## Graph Schema

**Nodes:**
```json
{ "id": "Gisela-Kampagne", "type": "project", "source": "mem0" }
```

Standard `type` Werte: `entity`, `project`, `person`, `deadline`, `document`, `concept`

**Edges (DiGraph — gerichtet):**
```json
{ "from": "Alex", "to": "Gisela-Kampagne",
  "relation": "arbeitet_an", "fact": "arbeitet an der Gisela-Kampagne" }
```

## NetworkX Algorithmen — Referenz

```python
import networkx as nx

G = nx.DiGraph()

# Nachbarn
list(G.successors("Alex"))      # Wohin zeigt Alex?
list(G.predecessors("Alex"))    # Wer zeigt auf Alex?

# Pfad
nx.shortest_path(G.to_undirected(), "A", "B")
nx.has_path(G.to_undirected(), "A", "B")

# Ego-Graph (n-Hop Nachbarschaft)
ego = nx.ego_graph(G.to_undirected(), "Alex", radius=2)

# Komponenten
nx.weakly_connected_components(G)   # DiGraph
nx.connected_components(G.to_undirected())

# Graph-Metriken
nx.density(G)
nx.number_of_nodes(G), nx.number_of_edges(G)
```

## Daten

- Graph: `data/graph.json` (lesbar, direkt editierbar)
- Source für Sync: `../mem0-lite/data/memories.json`

## Workflow: Vollständige Memory-Pipeline

```bash
# 1. Fakten extrahieren (mem0-lite)
GROQ_API_KEY=... python3 mem0-lite/scripts/extract.py \
  --text "Gesprächszusammenfassung"

# 2. Zu Graph synchronisieren
python3 networkx-graph/scripts/graph.py --sync

# 3. Kontext abrufen
python3 networkx-graph/scripts/graph.py --ego "Alex" --radius 3

# 4. Wichtiges in MEMORY.md eintragen (wenn relevant)
```

## Error Handling

| Error | Fix |
|-------|-----|
| `NodeNotFound` | `--path` braucht **exakte** Node-Namen (case-sensitive). `--viz` zeigt alle gültigen Namen. |
| `NetworkXNoPath` | Nodes nicht verbunden — `--components` prüfen |
| `No module named networkx` | `python3 -c "import networkx"` — system-installiert prüfen |
| Leerer Graph nach `--sync` | mem0-lite Daten haben keine entity/target Felder — extract.py erneut laufen lassen |

## Guardrails

- Nodes sind case-sensitive: "Alex" ≠ "alex" — konsistent halten
- DiGraph speichert Richtung — `--path` nutzt undirected für Pfade (beide Richtungen)
- JSON-Datei ist manuell editierbar — nach manuellen Änderungen `--viz` zur Verifikation
- Kein Lock-Mechanismus — nicht parallel aus mehreren Prozessen schreiben
