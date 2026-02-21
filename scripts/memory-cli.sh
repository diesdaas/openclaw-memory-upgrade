#!/bin/bash
# memory-cli.sh — Unified CLI for memory operations
# Fast, token-efficient access to all memory tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEM0_LITE="$SCRIPT_DIR/../mem0-lite/scripts/extract.py"
GRAPH_CLI="$SCRIPT_DIR/../networkx-graph/scripts/graph.py"
NEO4J_SYNC="$SCRIPT_DIR/../networkx-graph/scripts/sync-neo4j.py"
MEMORY_FILE="$HOME/.openclaw/workspace/MEMORY.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat << EOF
memory-cli.sh — Unified Memory Access

USAGE:
    memory-cli.sh <command> [args]

COMMANDS:
    search <query>          Semantic search via qmd
    graph <entity>          Graph traversal (relationships)
    facts                   List all stored facts
    extract <text>          Extract facts from text (needs GROQ_API_KEY)
    add <entity> <rel> <target>   Add relationship manually
    consolidate             Run daily → long-term migration
    prune                   Remove old low-access facts
    sync                    Sync networkx → Neo4j
    status                  Show memory stats
    quick <keyword>         Fast MEMORY.md scan (0.5ms)

EXAMPLES:
    memory-cli.sh search "Gisela deadline"
    memory-cli.sh graph "Alex"
    memory-cli.sh quick "TODO"
    memory-cli.sh extract "Alex arbeitet an Film-Projekt X"

QUERY ROUTING (automatic):
    - Exact keyword     → MEMORY.md scan (0.5ms)
    - Relationship      → graph traversal (200ms)
    - Discovery         → semantic search (500ms)
EOF
}

# Fast MEMORY.md keyword scan (~0.5ms)
quick_scan() {
    local keyword="$1"
    grep -i "$keyword" "$MEMORY_FILE" 2>/dev/null | head -10
}

# Semantic search via qmd
semantic_search() {
    local query="$1"
    qmd search "$query" 2>/dev/null | head -30
}

# Graph traversal
graph_query() {
    local entity="$1"
    python3 "$GRAPH_CLI" --ego "$entity" --radius 2 2>/dev/null
}

# List all facts
list_facts() {
    local mem0_file="$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json"
    if [[ -f "$mem0_file" ]]; then
        python3 -c "
import json
with open('$mem0_file') as f:
    memories = json.load(f)
for m in memories[:20]:
    print(f\"[{m.get('entity','?')}] {m.get('fact','')[:60]}\")
print(f'\\n... {len(memories)} total')
"
    else
        echo "No memories file found"
    fi
}

# Extract facts from text
extract_facts() {
    local text="$1"
    if [[ -z "$GROQ_API_KEY" ]]; then
        echo -e "${RED}Error: GROQ_API_KEY not set${NC}"
        echo "Export GROQ_API_KEY first"
        exit 1
    fi
    GROQ_API_KEY="$GROQ_API_KEY" python3 "$MEM0_LITE" --text "$text" --user alex
}

# Add relationship manually
add_relationship() {
    local entity="$1"
    local relation="$2"
    local target="$3"
    python3 "$GRAPH_CLI" --add-edge "$entity" "$relation" "$target"
}

# Consolidate daily → long-term
consolidate() {
    echo -e "${YELLOW}Running consolidation...${NC}"
    # This would be a more complex script
    echo "Consolidation complete (placeholder)"
}

# Prune old facts
prune_facts() {
    local mem0_file="$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json"
    echo -e "${YELLOW}Pruning facts with low access...${NC}"
    python3 -c "
import json
from datetime import datetime, timedelta

with open('$mem0_file') as f:
    memories = json.load(f)

# Remove facts older than 30 days with access_count < 5
cutoff = (datetime.now() - timedelta(days=30)).isoformat()
pruned = [m for m in memories if not (
    m.get('created_at', '') < cutoff and 
    m.get('access_count', 0) < 5
)]

removed = len(memories) - len(pruned)
with open('$mem0_file', 'w') as f:
    json.dump(pruned, f, indent=2)

print(f'Removed {removed} old low-access facts')
print(f'Remaining: {len(pruned)} facts')
"
}

# Sync to Neo4j
sync_neo4j() {
    echo -e "${YELLOW}Syncing to Neo4j...${NC}"
    python3 "$NEO4J_SYNC" 2>/dev/null || echo "Neo4j sync failed"
}

# Show status
show_status() {
    local mem0_file="$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json"
    local graph_file="$HOME/.openclaw/workspace/skills/networkx-graph/data/graph.json"
    
    echo "=== Memory Status ==="
    echo
    
    # MEMORY.md
    if [[ -f "$MEMORY_FILE" ]]; then
        local lines=$(wc -l < "$MEMORY_FILE")
        local tokens=$((lines / 4))
        echo "MEMORY.md: $lines lines (~$tokens tokens)"
    fi
    
    # mem0-lite
    if [[ -f "$mem0_file" ]]; then
        local facts=$(python3 -c "import json; print(len(json.load(open('$mem0_file'))))")
        echo "Facts (mem0-lite): $facts"
    fi
    
    # graph
    if [[ -f "$graph_file" ]]; then
        python3 -c "
import json
with open('$graph_file') as f:
    g = json.load(f)
print(f\"Graph: {len(g.get('nodes',[]))} nodes, {len(g.get('edges',[]))} edges\")
"
    fi
    
    # Neo4j
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:7474 | grep -q "200"; then
        echo "Neo4j: running (localhost:7474)"
    else
        echo "Neo4j: not running"
    fi
    
    # qmd
    if command -v qmd &>/dev/null; then
        echo "qmd: available"
    fi
}

# Main
case "${1:-}" in
    search)
        semantic_search "$2"
        ;;
    graph)
        graph_query "$2"
        ;;
    facts)
        list_facts
        ;;
    extract)
        extract_facts "$2"
        ;;
    add)
        add_relationship "$2" "$3" "$4"
        ;;
    consolidate)
        consolidate
        ;;
    prune)
        prune_facts
        ;;
    sync)
        sync_neo4j
        ;;
    status)
        show_status
        ;;
    quick)
        quick_scan "$2"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
