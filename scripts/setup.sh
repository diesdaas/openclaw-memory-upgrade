#!/bin/bash
# setup.sh — Initialize OpenClaw Memory Upgrade

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.openclaw/workspace/skills/memory-tools"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== OpenClaw Memory Upgrade Setup ==="
echo

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 required"
    exit 1
fi
echo "  ✓ Python3: $(python3 --version)"

if ! command -v docker &>/dev/null; then
    echo "⚠️  Docker not found — Neo4j will not be available"
else
    echo "  ✓ Docker: $(docker --version)"
fi

if ! command -v qmd &>/dev/null; then
    echo "⚠️  qmd not found — semantic search will not work"
    echo "     Install: npm install -g qmd"
else
    echo "  ✓ qmd: available"
fi

# Check for Groq API key
if [[ -z "$GROQ_API_KEY" ]]; then
    echo "⚠️  GROQ_API_KEY not set"
    echo "     Extract it from openclaw.json:"
    echo "     export GROQ_API_KEY=\$(python3 -c \"import json; d=json.load(open('\$HOME/.openclaw/openclaw.json')); print(d['skills']['entries']['groq-whisper']['apiKey'])\")"
else
    echo "  ✓ GROQ_API_KEY: set"
fi

# Create directories
echo
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$INSTALL_DIR/scripts"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$HOME/.openclaw/workspace/memory"

# Copy files
echo -e "${YELLOW}Installing files...${NC}"
cp "$SCRIPT_DIR/memory-cli.sh" "$INSTALL_DIR/scripts/"
cp -r "$SCRIPT_DIR/../skills/mem0-lite" "$HOME/.openclaw/workspace/skills/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/../skills/networkx-graph" "$HOME/.openclaw/workspace/skills/" 2>/dev/null || true

chmod +x "$INSTALL_DIR/scripts/memory-cli.sh"

echo "  ✓ Installed to $INSTALL_DIR"

# Initialize memory files
echo
echo -e "${YELLOW}Initializing memory files...${NC}"

# Create empty memories.json
if [[ ! -f "$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json" ]]; then
    mkdir -p "$HOME/.openclaw/workspace/skills/mem0-lite/data"
    echo "[]" > "$HOME/.openclaw/workspace/skills/mem0-lite/data/memories.json"
    echo "  ✓ Created memories.json"
fi

# Create empty graph.json
if [[ ! -f "$HOME/.openclaw/workspace/skills/networkx-graph/data/graph.json" ]]; then
    mkdir -p "$HOME/.openclaw/workspace/skills/networkx-graph/data"
    echo '{"nodes": [], "edges": []}' > "$HOME/.openclaw/workspace/skills/networkx-graph/data/graph.json"
    echo "  ✓ Created graph.json"
fi

# Create MEMORY.md if not exists
if [[ ! -f "$HOME/.openclaw/workspace/MEMORY.md" ]]; then
    echo "# MEMORY.md — Long-Term Memory" > "$HOME/.openclaw/workspace/MEMORY.md"
    echo "" >> "$HOME/.openclaw/workspace/MEMORY.md"
    echo "This file stores curated, long-term memories." >> "$HOME/.openclaw/workspace/MEMORY.md"
    echo "  ✓ Created MEMORY.md"
fi

# Install Python dependencies
echo
echo -e "${YELLOW}Checking Python packages...${NC}"
python3 -c "import networkx; print('  ✓ networkx:', networkx.__version__)" 2>/dev/null || {
    echo "  Installing networkx..."
    pip3 install networkx --quiet
}

# Initialize qmd index
if command -v qmd &>/dev/null; then
    echo
    echo -e "${YELLOW}Indexing memory files with qmd...${NC}"
    qmd collection add "$HOME/.openclaw/workspace/memory" --name memory --mask "*.md" 2>/dev/null || true
    qmd update 2>/dev/null | tail -3
fi

# Summary
echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Memory system installed. Test with:"
echo
echo "  ~/openclaw-memory-upgrade/scripts/memory-cli.sh status"
echo
echo "Or add to your PATH:"
echo
echo "  export PATH=\"\$HOME/openclaw-memory-upgrade/scripts:\$PATH\""
echo "  memory-cli.sh status"
echo

# Optional: Start Neo4j
if command -v docker &>/dev/null; then
    echo "To start Neo4j (optional):"
    echo
    echo "  docker run -d --name neo4j \\"
    echo "    -p 127.0.0.1:7474:7474 \\"
    echo "    -p 127.0.0.1:7687:7687 \\"
    echo "    -e NEO4J_AUTH=neo4j/yourpassword \\"
    echo "    neo4j:community"
    echo
fi
