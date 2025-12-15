#!/bin/bash
#
# Create AI Assistant Handoff Document
#
# Quickly create a handoff document when switching between AI assistants
# (GitHub Copilot <-> Claude Code)
#
# Usage:
#   bash scripts/utils/create_handoff.sh
#   bash scripts/utils/create_handoff.sh copilot  # From Copilot to Claude
#   bash scripts/utils/create_handoff.sh claude    # From Claude to Copilot
#

set -e

PROJECT_ROOT="/nethome/abdel042/enso_finance"
HANDOFF_DIR="$PROJECT_ROOT/docs/handoffs"
TEMPLATE="$PROJECT_ROOT/docs/HANDOFF_TEMPLATE.md"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Determine AI assistant
if [ "$1" == "copilot" ]; then
    FROM="GitHub Copilot"
    TO="Claude Code"
elif [ "$1" == "claude" ]; then
    FROM="Claude Code"
    TO="GitHub Copilot"
else
    echo -e "${YELLOW}From which AI? (copilot/claude):${NC} "
    read ai_from
    if [ "$ai_from" == "copilot" ]; then
        FROM="GitHub Copilot"
        TO="Claude Code"
    else
        FROM="Claude Code"
        TO="GitHub Copilot"
    fi
fi

# Create handoffs directory if needed
mkdir -p "$HANDOFF_DIR"

# Generate filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="$HANDOFF_DIR/handoff_${TIMESTAMP}.md"

echo -e "\n${BOLD}${BLUE}Creating AI Handoff Document${NC}\n"

# Get current week
START_DATE="2025-12-15"
CURRENT_DATE=$(date +%Y-%m-%d)
DAYS_DIFF=$(( ( $(date -d "$CURRENT_DATE" +%s) - $(date -d "$START_DATE" +%s) ) / 86400 ))
CURRENT_WEEK=$(( $DAYS_DIFF / 7 + 1 ))
if [ $CURRENT_WEEK -lt 1 ]; then
    CURRENT_WEEK=1
fi

# Get current phase from ROADMAP_STATUS.md
CURRENT_PHASE=$(grep "Current Phase:" "$PROJECT_ROOT/docs/ROADMAP_STATUS.md" | sed 's/\*\*Current Phase\*\*: //' || echo "Unknown")

# Copy template
cp "$TEMPLATE" "$FILENAME"

# Replace placeholders
sed -i "s/\[DATE\]/$(date +'%Y-%m-%d %H:%M')/g" "$FILENAME"
sed -i "s/\[GitHub Copilot \/ Claude Code\]/$FROM/g" "$FILENAME"
sed -i "s/\[GitHub Copilot \/ Claude Code\]/$TO/g" "$FILENAME"
sed -i "s/YYYY-MM-DD HH:MM/$(date +'%Y-%m-%d %H:%M')/g" "$FILENAME"
sed -i "s/\[e.g., Phase 1, Week 1\]/Phase 1, Week $CURRENT_WEEK/g" "$FILENAME"

echo -e "${GREEN}✓${NC} Handoff template created: ${BLUE}$FILENAME${NC}\n"

# Collect context
echo -e "${BOLD}Let's fill in the details:${NC}\n"

# Current task
echo -e "${YELLOW}What task are you currently working on?${NC}"
read -p "> " current_task
sed -i "s/\[Specific task being worked on\]/$current_task/g" "$FILENAME"

# Last action
echo -e "\n${YELLOW}What was the last thing completed/attempted?${NC}"
read -p "> " last_action
sed -i "s/\[What was just done\]/$last_action/g" "$FILENAME"

# Next priority
echo -e "\n${YELLOW}What should the next AI do first (immediate priority)?${NC}"
read -p "> " next_priority
# This will need manual editing for the numbered list

# Add git status
echo -e "\n${BLUE}Collecting git status...${NC}"
cd "$PROJECT_ROOT"
GIT_STATUS=$(git status --short 2>/dev/null || echo "Not in git repo")

# Add to file
cat >> "$FILENAME" << EOF

---

## 🔄 Auto-Collected Info

### Git Status
\`\`\`
$GIT_STATUS
\`\`\`

### Environment
- Working Directory: $PROJECT_ROOT
- Date: $(date +'%Y-%m-%d %H:%M:%S')
- Week: $CURRENT_WEEK of 24

### Recent Commands (from history)
\`\`\`bash
$(history | tail -10)
\`\`\`

---

**Note**: Please edit this file to add:
- Specific next steps
- Technical details
- Blockers/issues
- Open questions

Then share this file with the next AI assistant.
EOF

echo -e "\n${GREEN}✓${NC} Handoff document created!\n"
echo -e "${BOLD}Next steps:${NC}"
echo -e "  1. Edit the file: ${BLUE}vim $FILENAME${NC}"
echo -e "  2. Fill in remaining sections"
echo -e "  3. When resuming with $TO:"
echo -e "     - Attach this file in the conversation"
echo -e "     - Say: 'Please read the handoff document and continue from there'\n"

# Ask if user wants to edit now
echo -e "${YELLOW}Open for editing now? (y/n):${NC} "
read edit_now
if [ "$edit_now" == "y" ]; then
    ${EDITOR:-vim} "$FILENAME"
fi

echo -e "\n${GREEN}✓${NC} Handoff ready at: ${BLUE}$FILENAME${NC}\n"
