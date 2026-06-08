#!/bin/bash
# sync_test.sh — Verifies all MCP servers are reachable before running the sync
 
set -e
 
# ─── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
 
# ─── MCP → Port mapping ────────────────────────────────────────────────────────
declare -A MCP_PORTS=(
    ["google_calendar"]="8001"
    ["notion"]="8002"
    ["files"]="8003"
    ["github"]="8004"
)
 
# ─── Global result ─────────────────────────────────────────────────────────────
ALL_OK=true
 
echo ""
echo "🔍 Checking MCP server connectivity..."
echo "────────────────────────────────────────────────"
 
for MCP in "${!MCP_PORTS[@]}"; do
    PORT="${MCP_PORTS[$MCP]}"
    URL="http://localhost:${PORT}/mcp-server/mcp"
 
    # A simple GET is enough — MCP servers respond even with 405
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$URL" 2>/dev/null || echo "000")
 
    if [ "$STATUS" = "000" ]; then
        echo -e "  ${RED}✗${NC}  ${MCP} (port ${PORT}) — ${RED}NOT RESPONDING${NC}"
        ALL_OK=false
    else
        echo -e "  ${GREEN}✓${NC}  ${MCP} (port ${PORT}) — ${GREEN}OK${NC} (HTTP ${STATUS})"
    fi
done
 
echo "────────────────────────────────────────────────"
 
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✅ All MCP servers are up. You can run the sync.${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  One or more servers are not responding. Start them before running sync_mcps.py${NC}"
    echo ""
    exit 1
fi