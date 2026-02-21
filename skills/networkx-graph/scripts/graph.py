#!/usr/bin/env python3
"""
networkx-graph: Knowledge Graph for AI Agents
Persistent DiGraph (JSON-backed) with Traversal, Ego-Graphs, Path Search.

Usage:
  python3 graph.py --sync               # Load from mem0-lite memories.json
  python3 graph.py --add-node "ProjectX" type=project
  python3 graph.py --add-edge "User" "works_on" "ProjectX"
  python3 graph.py --query "ProjectX"   # Direct neighbors
  python3 graph.py --ego "User" --radius 2  # Ego-graph (N hops)
  python3 graph.py --path "User" "Deadline"
  python3 graph.py --components         # Connected components
  python3 graph.py --viz                # ASCII overview
  python3 graph.py --export graph.gml   # Export for external tools
"""

import json
import argparse
import os
import sys
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    print("networkx nicht installiert. Systemweit verfügbar unter Python 3.x")
    sys.exit(1)

# --- Konfiguration ---
# Use environment variables or relative paths for portability
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "data"

DATA_DIR = Path(os.environ.get("GRAPH_DATA", str(DEFAULT_DATA_DIR)))
GRAPH_FILE = DATA_DIR / "graph.json"

DEFAULT_MEM0_DIR = SCRIPT_DIR.parent.parent / "mem0-lite" / "data"
MEM0_FILE = Path(os.environ.get("MEM0_DATA", str(DEFAULT_MEM0_DIR))) / "memories.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# --- Persistenz ---

def load_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    if not GRAPH_FILE.exists():
        return G
    data = json.loads(GRAPH_FILE.read_text())
    for node in data.get("nodes", []):
        attrs = {k: v for k, v in node.items() if k != "id"}
        G.add_node(node["id"], **attrs)
    for edge in data.get("edges", []):
        attrs = {k: v for k, v in edge.items() if k not in ("from", "to")}
        G.add_edge(edge["from"], edge["to"], **attrs)
    return G


def save_graph(G: nx.DiGraph):
    data = {
        "nodes": [{"id": n, **dict(G.nodes[n])} for n in G.nodes()],
        "edges": [{"from": u, "to": v, **dict(G[u][v])} for u, v in G.edges()]
    }
    GRAPH_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Graph gespeichert: {G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges → {GRAPH_FILE}")


# --- Sync ---

def sync_from_mem0(G: nx.DiGraph) -> nx.DiGraph:
    """Lädt alle Fakten aus mem0-lite memories.json und baut DiGraph auf."""
    if not MEM0_FILE.exists():
        print(f"Keine memories.json unter {MEM0_FILE}")
        print("Erst: cd mem0-lite/scripts && python3 extract.py --text '...'")
        return G

    memories = json.loads(MEM0_FILE.read_text())
    added_nodes, added_edges = 0, 0

    for m in memories:
        entity = m.get("entity", "").strip()
        target = m.get("target", "").strip()
        relation = m.get("relation", "").strip()
        fact = m.get("fact", "")

        if not entity:
            continue

        # Node anlegen
        if entity not in G:
            G.add_node(entity, type="entity", source="mem0")
            added_nodes += 1

        # Edge anlegen wenn Target vorhanden
        if target:
            if target not in G:
                G.add_node(target, type="entity", source="mem0")
                added_nodes += 1
            if not G.has_edge(entity, target):
                G.add_edge(entity, target, relation=relation, fact=fact)
                added_edges += 1

    print(f"Sync: +{added_nodes} Nodes, +{added_edges} Edges")
    print(f"Gesamt: {G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges")
    return G


# --- CRUD ---

def add_node(G: nx.DiGraph, name: str, attrs: dict) -> nx.DiGraph:
    if name in G:
        G.nodes[name].update(attrs)
        print(f"Node aktualisiert: {name} {attrs}")
    else:
        G.add_node(name, **attrs)
        print(f"Node hinzugefügt: {name} {attrs}")
    return G


def add_edge(G: nx.DiGraph, source: str, relation: str, target: str, **attrs) -> nx.DiGraph:
    for node in [source, target]:
        if node not in G:
            G.add_node(node, type="entity")
    G.add_edge(source, target, relation=relation, **attrs)
    print(f"Edge: {source} --[{relation}]--> {target}")
    return G


def remove_node(G: nx.DiGraph, name: str) -> nx.DiGraph:
    if name in G:
        G.remove_node(name)
        print(f"Node gelöscht: {name}")
    else:
        print(f"Node nicht gefunden: {name}")
    return G


# --- Abfragen ---

def query_node(G: nx.DiGraph, entity: str):
    """Direkte Nachbarn (1 Hop) einer Entität."""
    matches = [n for n in G.nodes() if entity.lower() in n.lower()]
    if not matches:
        print(f"Nicht gefunden: '{entity}'")
        return

    for node in matches:
        attrs = dict(G.nodes[node])
        type_label = f"[{attrs.get('type', 'entity')}]"
        print(f"\n🔵 {node} {type_label}")

        out_edges = list(G.out_edges(node, data=True))
        in_edges = list(G.in_edges(node, data=True))

        if out_edges:
            print("  → ausgehend:")
            for _, t, d in out_edges:
                rel = d.get("relation", "→")
                print(f"    --[{rel}]--> {t}")
                if d.get("fact"):
                    print(f"       💬 {d['fact']}")
        if in_edges:
            print("  ← eingehend:")
            for s, _, d in in_edges:
                rel = d.get("relation", "←")
                print(f"    <--[{rel}]-- {s}")


def ego_graph_query(G: nx.DiGraph, center: str, radius: int = 2):
    """
    Ego-Graph: Alle Nodes und Edges im Umkreis von `radius` Hops.
    Nützlich für 'Was hängt alles mit X zusammen?'
    """
    matches = [n for n in G.nodes() if center.lower() in n.lower()]
    if not matches:
        print(f"Node '{center}' nicht gefunden.")
        return

    node = matches[0]
    # ego_graph auf dem undirected Graph (ignoriert Richtung)
    ego = nx.ego_graph(G.to_undirected(), node, radius=radius)
    print(f"\nEgo-Graph von '{node}' (Radius {radius}):")
    print(f"{ego.number_of_nodes()} Nodes, {ego.number_of_edges()} Edges\n")

    for n in ego.nodes():
        if n == node:
            print(f"  🔵 {n} (Zentrum)")
        else:
            # Hop-Distanz berechnen
            try:
                dist = nx.shortest_path_length(ego, node, n)
                print(f"  {'  ' * dist}○ {n} (Hop {dist})")
            except Exception:
                print(f"  ○ {n}")

    print(f"\nEdges in diesem Subgraph:")
    for u, v in ego.edges():
        # Richtung aus DiGraph holen
        if G.has_edge(u, v):
            rel = G[u][v].get("relation", "→")
            print(f"  {u} --[{rel}]--> {v}")
        elif G.has_edge(v, u):
            rel = G[v][u].get("relation", "←")
            print(f"  {v} --[{rel}]--> {u}")


def find_path(G: nx.DiGraph, source: str, target: str):
    """Kürzester Pfad zwischen zwei Nodes (undirected für maximale Reichweite)."""
    try:
        path = nx.shortest_path(G.to_undirected(), source, target)
        print(f"Pfad ({len(path)-1} Hops): {' → '.join(path)}")

        # Edge-Labels für den Pfad
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if G.has_edge(u, v):
                rel = G[u][v].get("relation", "")
                print(f"  {u} --[{rel}]--> {v}")
            elif G.has_edge(v, u):
                rel = G[v][u].get("relation", "")
                print(f"  {v} --[{rel}]--> {u} (umgekehrt)")
    except nx.NetworkXNoPath:
        print(f"Kein Pfad: '{source}' → '{target}'")
    except nx.NodeNotFound as e:
        print(f"Node nicht gefunden: {e}")


def show_components(G: nx.DiGraph):
    """Zeigt schwach zusammenhängende Komponenten — findet isolierte Cluster."""
    components = list(nx.weakly_connected_components(G))
    print(f"\n{len(components)} Komponenten:\n")
    for i, comp in enumerate(sorted(components, key=len, reverse=True)):
        nodes = sorted(comp)
        print(f"  Komponente {i+1} ({len(nodes)} Nodes): {', '.join(nodes[:5])}")
        if len(nodes) > 5:
            print(f"    ... (+{len(nodes)-5} weitere)")


def visualize(G: nx.DiGraph, limit: int = 50):
    """ASCII-Übersicht aller Edges."""
    print(f"\nKnowledge Graph ({G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges):\n")
    count = 0
    for u, v, data in G.edges(data=True):
        rel = data.get("relation", "→")
        print(f"  {u} --[{rel}]--> {v}")
        count += 1
        if count >= limit:
            remaining = G.number_of_edges() - limit
            if remaining > 0:
                print(f"  ... (+{remaining} weitere Edges)")
            break

    print(f"\nNodes ohne Edges ({sum(1 for n in G.nodes() if G.degree(n) == 0)}):")
    isolated = [n for n in G.nodes() if G.degree(n) == 0]
    if isolated:
        print(f"  {', '.join(isolated)}")


def export_graph(G: nx.DiGraph, path: str):
    """Export als GML (für Gephi, yEd) oder GraphML."""
    p = Path(path)
    if p.suffix == ".gml":
        nx.write_gml(G, str(p))
    elif p.suffix == ".graphml":
        nx.write_graphml(G, str(p))
    else:
        nx.write_gml(G, str(p))
    print(f"Graph exportiert: {p}")


# --- CLI ---

def parse_key_value(items: list) -> dict:
    """Parst key=value Paare aus CLI-Args."""
    result = {}
    for item in items or []:
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
    return result


def main():
    parser = argparse.ArgumentParser(
        description="networkx-graph: Knowledge Graph für Agenten",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sync", action="store_true",
        help="Aus mem0-lite memories.json synchronisieren")
    parser.add_argument("--add-node", metavar="NAME",
        help="Node hinzufügen (optionale key=value Attribute folgen)")
    parser.add_argument("--add-edge", nargs=3, metavar=("FROM", "REL", "TO"),
        help="Gerichtete Edge hinzufügen")
    parser.add_argument("--remove-node", metavar="NAME",
        help="Node und alle Edges entfernen")
    parser.add_argument("--query", "-q", metavar="ENTITY",
        help="Direkte Nachbarn einer Entität")
    parser.add_argument("--ego", metavar="CENTER",
        help="Ego-Graph (Subgraph um Zentrum)")
    parser.add_argument("--radius", type=int, default=2,
        help="Hop-Radius für --ego (default: 2)")
    parser.add_argument("--path", nargs=2, metavar=("FROM", "TO"),
        help="Kürzester Pfad zwischen zwei Nodes")
    parser.add_argument("--components", action="store_true",
        help="Zusammenhangskomponenten anzeigen")
    parser.add_argument("--viz", action="store_true",
        help="Alle Edges anzeigen")
    parser.add_argument("--export", metavar="FILE",
        help="Export als .gml oder .graphml")
    parser.add_argument("attrs", nargs="*",
        help="key=value Attribute für --add-node")
    args = parser.parse_args()

    G = load_graph()
    modified = False

    if args.sync:
        G = sync_from_mem0(G)
        modified = True
    elif args.add_node:
        attrs = parse_key_value(args.attrs)
        G = add_node(G, args.add_node, attrs)
        modified = True
    elif args.add_edge:
        G = add_edge(G, args.add_edge[0], args.add_edge[1], args.add_edge[2])
        modified = True
    elif args.remove_node:
        G = remove_node(G, args.remove_node)
        modified = True
    elif args.query:
        query_node(G, args.query)
    elif args.ego:
        ego_graph_query(G, args.ego, args.radius)
    elif args.path:
        find_path(G, args.path[0], args.path[1])
    elif args.components:
        show_components(G)
    elif args.viz:
        visualize(G)
    elif args.export:
        export_graph(G, args.export)
    else:
        parser.print_help()

    if modified:
        save_graph(G)


if __name__ == "__main__":
    main()
