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
    quick <keyword>         Fast MEMORY.md scan (0.5ms)
    search <query>          Search facts by keyword
    graph <entity>          Graph traversal (relationships)
    facts [--limit N]       List stored facts
    extract <text>          Extract facts from text (needs GROQ_API_KEY)
    add <e> <rel> <t>       Add relationship manually
    delete <id>             Delete memory by ID
    prune [--days N]        Remove old facts
    sync                    Sync networkx → Neo4j
    status                  Show memory stats

AUTHENTICATION:
    Set environment variables:
      export GROQ_API_KEY="gsk_..."
      export OPENCLAW_USER_ID="your_user"
      export MEM0_DEV_MODE=true    # For development without JWT
    
    Or use JWT (more secure):
      export JWT_SECRET="your-secret"
      export OPENCLAW_TOKEN="eyJhbGc..."

EXAMPLES:
    memory-cli.sh quick "deadline"
    memory-cli.sh search "project"
    memory-cli.sh graph "User"
    memory-cli.sh extract "Project X deadline is March 15"
    memory-cli.sh delete fact_a1b2c3d4
    memory-cli.sh prune --days 30

QUERY ROUTING:
    - Exact keyword     → MEMORY.md scan (0.5ms)
    - Relationship      → graph traversal (200ms)
    - Fact search       → JSON keyword search (10ms)
    - Discovery         → qmd semantic (500ms)
EOF
}

# Check authentication
check_auth() {
    if [[ -z "$GROQ_API_KEY" ]]; then
        echo -e "${RED}Error: GROQ_API_KEY not set${NC}"
        echo "Export GROQ_API_KEY first:"
        echo "  export GROQ_API_KEY=\$(python3 -c \"import json; d=json.load(open('\$HOME/.openclaw/openclaw.json')); print(d['skills']['entries']['groq-whisper']['apiKey'])\")"
        exit 1
    fi
    
    if [[ -z "$OPENCLAW_TOKEN" ]] && [[ -z "$MEM0_DEV_MODE" ]]; then
        echo -e "${YELLOW}Warning: No authentication configured${NC}"
        echo "Set MEM0_DEV_MODE=true for development or OPENCLAW_TOKEN for production"
        export MEM0_DEV_MODE=true
    fi
}

# Fast MEMORY.md keyword scan (~0.5ms)
quick_scan() {
    local keyword="$1"
    if [[ -f "$MEMORY_FILE" ]]; then
        grep -i "$keyword" "$MEMORY_FILE" 2>/dev/null | head -10
    else
        echo "MEMORY.md not found"
    fi
}

# Semantic search via qmd
semantic_search() {
    local query="$1"
    if command -v qmd &>/dev/null; then
        qmd search "$query" 2>/dev/null | head -30
    else
        echo "qmd not installed. Install with: npm install -g qmd"
    fi
}

# Graph traversal
graph_query() {
    local entity="$1"
    python3 "$GRAPH_CLI" --ego "$entity" --radius 2 2>/dev/null
}

# List all facts
list_facts() {
    local limit="${1:-20}"
    check_auth
    python3 "$MEM0_LITE" --list --limit "$limit"
}

# Search facts by keyword
search_facts() {
    local query="$1"
    check_auth
    python3 "$MEM0_LITE" --search "$query"
}

# Extract facts from text
extract_facts() {
    local text="$1"
    check_auth
    python3 "$MEM0_LITE" --text "$text"
}

# Add relationship manually
add_relationship() {
    local entity="$1"
    local relation="$2"
    local target="$3"
    python3 "$GRAPH_CLI" --add-edge "$entity" "$relation" "$target"
}

# Delete memory
delete_memory() {
    local memory_id="$1"
    check_auth
    python3 "$MEM0_LITE" --delete "$memory_id"
}

# Prune old facts
prune_facts() {
    local days="${1:-30}"
    check_auth
    python3 "$MEM0_LITE" --prune --days "$days"
}

# Sync to Neo4j
sync_neo4j() {
    if [[ -f "$NEO4J_SYNC" ]]; then
        echo -e "${YELLOW}Syncing to Neo4j...${NC}"
        python3 "$NEO4J_SYNC" 2>/dev/null || echo "Neo4j sync failed"
    else
        echo "Neo4j sync script not found"
    fi
}

# Show status
show_status() {
    local mem0_file="$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json"
    local graph_file="$HOME/.openclaw/workspace/skills/networkx-graph/data/graph.json"
    local audit_file="$HOME/.openclaw/workspace/skills/mem0-lite/data/audit.log"
    
    echo "=== Memory Status ==="
    echo
    
    # MEMORY.md
    if [[ -f "$MEMORY_FILE" ]]; then
        local lines=$(wc -l < "$MEMORY_FILE")
        local tokens=$((lines / 4))
        echo "MEMORY.md: $lines lines (~$tokens tokens)"
    else
        echo "MEMORY.md: not found"
    fi
    
    # mem0-lite
    if [[ -f "$mem0_file" ]]; then
        local facts=$(python3 -c "import json; print(len(json.load(open('$mem0_file'))))" 2>/dev/null || echo "0")
        echo "Facts (mem0-lite): $facts"
    else
        echo "Facts (mem0-lite): not found"
    fi
    
    # graph
    if [[ -f "$graph_file" ]]; then
        python3 -c "
import json
with open('$graph_file') as f:
    g = json.load(f)
print(f\"Graph: {len(g.get('nodes',[]))} nodes, {len(g.get('edges',[]))} edges\")
" 2>/dev/null || echo "Graph: error reading"
    else
        echo "Graph: not found"
    fi
    
    # Neo4j
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:7474 2>/dev/null | grep -q "200"; then
        echo "Neo4j: running (localhost:7474)"
    else
        echo "Neo4j: not running"
    fi
    
    # qmd
    if command -v qmd &>/dev/null; then
        echo "qmd: available"
    else
        echo "qmd: not installed"
    fi
    
    # Auth status
    echo
    echo "=== Authentication ==="
    if [[ -n "$OPENCLAW_TOKEN" ]]; then
        echo "Mode: JWT (secure)"
    elif [[ "$MEM0_DEV_MODE" == "true" ]]; then
        echo "Mode: Development (MEM0_DEV_MODE)"
    else
        echo "Mode: Not configured"
    fi
    
    if [[ -n "$GROQ_API_KEY" ]]; then
        echo "GROQ_API_KEY: set (${#GROQ_API_KEY} chars)"
    else
        echo "GROQ_API_KEY: not set"
    fi
    
    # Audit log
    if [[ -f "$audit_file" ]]; then
        local entries=$(wc -l < "$audit_file")
        echo "Audit log: $entries entries"
    fi
}

# Main
case "${1:-}" in
    quick)
        quick_scan "$2"
        ;;
    search)
        search_facts "$2"
        ;;
    semantic)
        semantic_search "$2"
        ;;
    graph)
        graph_query "$2"
        ;;
    facts)
        list_facts "${3:-20}"
        ;;
    extract)
        extract_facts "$2"
        ;;
    add)
        add_relationship "$2" "$3" "$4"
        ;;
    delete)
        delete_memory "$2"
        ;;
    prune)
        prune_facts "${3:-30}"
        ;;
    sync)
        sync_neo4j
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
