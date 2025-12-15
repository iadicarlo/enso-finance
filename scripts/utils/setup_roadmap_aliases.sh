#!/bin/bash
#
# Setup Roadmap Convenience Aliases
#
# This script adds helpful aliases to your shell for quick roadmap access.
#
# Usage:
#   source scripts/utils/setup_roadmap_aliases.sh
#
# Or add to your ~/.bashrc:
#   source /nethome/abdel042/enso_finance/scripts/utils/setup_roadmap_aliases.sh

PROJECT_ROOT="/nethome/abdel042/enso_finance"

# Set vim as default editor for this session
export EDITOR=vim

# Roadmap management aliases
alias roadmap='bash $PROJECT_ROOT/scripts/utils/update_roadmap.sh'
alias roadmap-status='uv run python $PROJECT_ROOT/scripts/utils/generate_roadmap_report.py'
alias roadmap-view='less $PROJECT_ROOT/docs/ROADMAP_STATUS.md'
alias roadmap-guide='less $PROJECT_ROOT/docs/ROADMAP_QUICK_GUIDE.md'
alias roadmap-plan='less $PROJECT_ROOT/docs/PUBLICATION_ROADMAP.md'

# Quick navigation
alias goto-enso='cd $PROJECT_ROOT'
alias goto-docs='cd $PROJECT_ROOT/docs'
alias goto-scripts='cd $PROJECT_ROOT/scripts'
alias goto-outputs='cd $PROJECT_ROOT/outputs'

# Checkpoint management
alias checkpoint-view='cat $PROJECT_ROOT/docs/weekly_checkpoints/WEEK_$(printf "%02d" $(python3 -c "from datetime import datetime; print((datetime.now()-datetime(2025,12,15)).days//7+1)"))_CHECKPOINT.md'
alias checkpoint-edit='vim $PROJECT_ROOT/docs/weekly_checkpoints/WEEK_$(printf "%02d" $(python3 -c "from datetime import datetime; print((datetime.now()-datetime(2025,12,15)).days//7+1)"))_CHECKPOINT.md'

# Progress tracking
alias roadmap-progress='grep "Overall Progress:" $PROJECT_ROOT/docs/ROADMAP_STATUS.md'
alias roadmap-blockers='grep -A 5 "### Current Blockers" $PROJECT_ROOT/docs/ROADMAP_STATUS.md'
alias roadmap-tasks='grep "\- \[ \]" $PROJECT_ROOT/docs/ROADMAP_STATUS.md | head -10'

# Quick updates
alias roadmap-quick='bash $PROJECT_ROOT/scripts/utils/update_roadmap.sh <<< "1"'  # Quick daily update
alias roadmap-friday='bash $PROJECT_ROOT/scripts/utils/update_roadmap.sh <<< "8"'  # Friday summary

# AI handoff management
alias handoff-create='bash $PROJECT_ROOT/scripts/utils/create_handoff.sh'
alias handoff-to-claude='bash $PROJECT_ROOT/scripts/utils/create_handoff.sh copilot'
alias handoff-to-copilot='bash $PROJECT_ROOT/scripts/utils/create_handoff.sh claude'
alias handoff-view='ls -lt $PROJECT_ROOT/docs/handoffs/ | head -10'
alias handoff-latest='cat $(ls -t $PROJECT_ROOT/docs/handoffs/*.md | head -1)'

echo "✅ Roadmap aliases loaded!"
echo ""
echo "Quick commands:"
echo "  roadmap          - Interactive update menu"
echo "  roadmap-status   - View progress report"
echo "  roadmap-view     - View status file"
echo "  roadmap-guide    - View quick guide"
echo "  roadmap-plan     - View full roadmap"
echo "  goto-enso        - Navigate to project root"
echo "  checkpoint-view  - View current week checkpoint"
echo "  checkpoint-edit  - Edit current week checkpoint"
echo ""
echo "Type 'alias | grep roadmap' to see all roadmap aliases"
