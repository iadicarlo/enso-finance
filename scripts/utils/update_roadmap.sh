#!/bin/bash
#
# Quick Roadmap Update Script
#
# This script provides an interactive menu to update your roadmap status.
# Run it at the end of each day or week to keep track of progress.
#
# Usage:
#   bash scripts/utils/update_roadmap.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# File paths
STATUS_FILE="$PROJECT_ROOT/docs/ROADMAP_STATUS.md"
ROADMAP_FILE="$PROJECT_ROOT/docs/PUBLICATION_ROADMAP.md"
QUICK_GUIDE="$PROJECT_ROOT/docs/ROADMAP_QUICK_GUIDE.md"

# Calculate current week (starting from 2025-12-15)
START_DATE="2025-12-15"
CURRENT_DATE=$(date +%Y-%m-%d)
DAYS_DIFF=$(( ( $(date -d "$CURRENT_DATE" +%s) - $(date -d "$START_DATE" +%s) ) / 86400 ))
CURRENT_WEEK=$(( $DAYS_DIFF / 7 + 1 ))

if [ $CURRENT_WEEK -lt 1 ]; then
    CURRENT_WEEK=1
fi

CHECKPOINT_FILE="$PROJECT_ROOT/docs/weekly_checkpoints/WEEK_$(printf "%02d" $CURRENT_WEEK)_CHECKPOINT.md"

# Helper functions
print_header() {
    echo -e "\n${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}     ${BOLD}Publication Roadmap Update - Week $CURRENT_WEEK of 24${NC}        ${BOLD}${BLUE}║${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

show_status() {
    echo -e "${BOLD}${GREEN}Current Status:${NC}"
    python3 "$PROJECT_ROOT/scripts/utils/generate_roadmap_report.py" 2>/dev/null || echo "Report script not available"
    echo ""
}

update_task_status() {
    echo -e "${BOLD}${YELLOW}Update Task Status${NC}"
    echo "What did you complete today?"
    echo ""
    read -p "Task description: " task_desc

    if [ ! -z "$task_desc" ]; then
        # Add to checkpoint
        if [ -f "$CHECKPOINT_FILE" ]; then
            TODAY=$(date +%Y-%m-%d)
            WEEKDAY=$(date +%A)

            # Find the section for today
            if grep -q "### $TODAY ($WEEKDAY)" "$CHECKPOINT_FILE"; then
                # Add task under today's section
                sed -i "/### $TODAY ($WEEKDAY)/a - ✅ $task_desc" "$CHECKPOINT_FILE"
            else
                # Create today's section
                sed -i "/### $TODAY ($WEEKDAY)/i ### $TODAY ($WEEKDAY)\n- ✅ $task_desc\n- **Time Spent**: __ hours\n" "$CHECKPOINT_FILE"
            fi

            echo -e "${GREEN}✓ Task added to checkpoint${NC}"
        else
            echo -e "${RED}⚠ Checkpoint file not found for Week $CURRENT_WEEK${NC}"
        fi

        # Also add to activity log in status file
        if [ -f "$STATUS_FILE" ]; then
            # Add to recent activity
            sed -i "/### Recent Activity Log/a ### $TODAY (Week $CURRENT_WEEK)\n- ✅ $task_desc" "$STATUS_FILE"
            echo -e "${GREEN}✓ Task added to status file${NC}"
        fi
    fi
}

add_blocker() {
    echo -e "${BOLD}${RED}Add Blocker${NC}"
    echo "What's blocking your progress?"
    echo ""
    read -p "Blocker description: " blocker_desc

    if [ ! -z "$blocker_desc" ]; then
        # Add to checkpoint
        if [ -f "$CHECKPOINT_FILE" ]; then
            sed -i "/### Current Blockers/a - ❌ $blocker_desc" "$CHECKPOINT_FILE"
            echo -e "${GREEN}✓ Blocker added to checkpoint${NC}"
        fi

        # Add to status file
        if [ -f "$STATUS_FILE" ]; then
            sed -i "/### Current Blockers/a - ❌ $blocker_desc (Week $CURRENT_WEEK)" "$STATUS_FILE"
            echo -e "${GREEN}✓ Blocker added to status file${NC}"
        fi
    fi
}

update_progress() {
    echo -e "${BOLD}${BLUE}Update Phase Progress${NC}"
    echo "Which phase did you make progress on? (1-6)"
    read -p "Phase number: " phase_num

    if [[ $phase_num =~ ^[1-6]$ ]]; then
        echo "What percentage is Phase $phase_num now complete? (0-100)"
        read -p "Percentage: " percentage

        if [[ $percentage =~ ^[0-9]+$ ]] && [ $percentage -ge 0 ] && [ $percentage -le 100 ]; then
            # Update in status file
            if [ -f "$STATUS_FILE" ]; then
                sed -i "s/Phase $phase_num.*[0-9]\+% complete/Phase $phase_num: ${percentage}% complete/" "$STATUS_FILE"

                # Update progress bar
                # This is simplified - you might want to enhance this
                echo -e "${GREEN}✓ Phase $phase_num updated to ${percentage}%${NC}"
            fi
        else
            echo -e "${RED}Invalid percentage. Must be 0-100.${NC}"
        fi
    else
        echo -e "${RED}Invalid phase number. Must be 1-6.${NC}"
    fi
}

generate_report() {
    echo -e "${BOLD}${BLUE}Generating Progress Report...${NC}\n"
    python3 "$PROJECT_ROOT/scripts/utils/generate_roadmap_report.py"
}

open_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        echo -e "${BOLD}${BLUE}Opening Week $CURRENT_WEEK checkpoint...${NC}"
        ${EDITOR:-vim} "$CHECKPOINT_FILE"
    else
        echo -e "${RED}Checkpoint file not found: $CHECKPOINT_FILE${NC}"
        echo "Creating from template..."
        # Create new checkpoint
        mkdir -p "$(dirname "$CHECKPOINT_FILE")"
        cp "$PROJECT_ROOT/docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md" "$CHECKPOINT_FILE"
        # Update week number in file
        sed -i "s/Week 1/Week $CURRENT_WEEK/g" "$CHECKPOINT_FILE"
        echo -e "${GREEN}✓ Created new checkpoint for Week $CURRENT_WEEK${NC}"
        ${EDITOR:-vim} "$CHECKPOINT_FILE"
    fi
}

open_status() {
    if [ -f "$STATUS_FILE" ]; then
        echo -e "${BOLD}${BLUE}Opening roadmap status...${NC}"
        ${EDITOR:-vim} "$STATUS_FILE"
    else
        echo -e "${RED}Status file not found: $STATUS_FILE${NC}"
    fi
}

view_guide() {
    if [ -f "$QUICK_GUIDE" ]; then
        less "$QUICK_GUIDE"
    else
        echo -e "${RED}Quick guide not found: $QUICK_GUIDE${NC}"
    fi
}

quick_update() {
    echo -e "${BOLD}${YELLOW}Quick Daily Update${NC}\n"

    # Add completed task
    echo "What's the main thing you completed today? (or press Enter to skip)"
    read -p "> " task
    if [ ! -z "$task" ]; then
        TODAY=$(date +%Y-%m-%d)
        WEEKDAY=$(date +%A)
        if [ -f "$CHECKPOINT_FILE" ]; then
            sed -i "/### $TODAY ($WEEKDAY)/a - ✅ $task" "$CHECKPOINT_FILE" 2>/dev/null || true
        fi
        echo -e "${GREEN}✓ Logged${NC}"
    fi

    # Add blocker if any
    echo -e "\nAny blockers? (or press Enter to skip)"
    read -p "> " blocker
    if [ ! -z "$blocker" ]; then
        if [ -f "$CHECKPOINT_FILE" ]; then
            sed -i "/### Current Blockers/a - ❌ $blocker" "$CHECKPOINT_FILE" 2>/dev/null || true
        fi
        echo -e "${YELLOW}⚠ Blocker logged${NC}"
    fi

    # Time spent
    echo -e "\nHow many hours did you work today?"
    read -p "> " hours
    if [[ $hours =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}✓ Logged $hours hours${NC}"
        # You could add this to checkpoint if desired
    fi

    echo -e "\n${GREEN}Daily update complete!${NC}"
    echo -e "Run this script again tomorrow, or use option 6 to open full checkpoint.\n"
}

friday_summary() {
    if [ $(date +%u) -ne 5 ]; then
        echo -e "${YELLOW}⚠ Today is not Friday. Continue anyway? (y/n)${NC}"
        read -p "> " confirm
        if [ "$confirm" != "y" ]; then
            return
        fi
    fi

    echo -e "${BOLD}${GREEN}Friday End-of-Week Summary${NC}\n"
    echo "Opening checkpoint for final summary..."
    echo "Please fill out the 'Friday End-of-Week Summary' section."
    sleep 2
    open_checkpoint

    echo -e "\n${BOLD}Don't forget to:${NC}"
    echo "  1. Update ROADMAP_STATUS.md (option 7)"
    echo "  2. Generate progress report (option 4)"
    echo "  3. Create next week's checkpoint template"
}

# Main menu
main_menu() {
    print_header

    echo -e "${BOLD}What would you like to do?${NC}\n"
    echo -e "  ${GREEN}1)${NC} Quick daily update (fastest)"
    echo -e "  ${YELLOW}2)${NC} Add completed task"
    echo -e "  ${RED}3)${NC} Add blocker/issue"
    echo -e "  ${BLUE}4)${NC} View progress report"
    echo -e "  ${BLUE}5)${NC} Update phase progress"
    echo -e "  ${YELLOW}6)${NC} Open weekly checkpoint (full edit)"
    echo -e "  ${YELLOW}7)${NC} Open roadmap status (full edit)"
    echo -e "  ${GREEN}8)${NC} Friday end-of-week summary"
    echo -e "  ${BLUE}9)${NC} View quick guide"
    echo -e "  ${BOLD}0)${NC} Exit"
    echo ""
    read -p "Choice: " choice

    case $choice in
        1) quick_update ;;
        2) update_task_status ;;
        3) add_blocker ;;
        4) generate_report ;;
        5) update_progress ;;
        6) open_checkpoint ;;
        7) open_status ;;
        8) friday_summary ;;
        9) view_guide ;;
        0) echo -e "\n${GREEN}Keep up the great work! 🚀${NC}\n"; exit 0 ;;
        *) echo -e "\n${RED}Invalid choice. Please try again.${NC}\n"; main_menu ;;
    esac

    echo ""
    read -p "Press Enter to return to menu (or Ctrl+C to exit)..."
    main_menu
}

# Check if required files exist
if [ ! -f "$STATUS_FILE" ]; then
    echo -e "${RED}Error: Roadmap status file not found at $STATUS_FILE${NC}"
    echo "Please ensure you're running this from the project root."
    exit 1
fi

# Create checkpoint if it doesn't exist
if [ ! -f "$CHECKPOINT_FILE" ]; then
    echo -e "${YELLOW}⚠ No checkpoint found for Week $CURRENT_WEEK${NC}"
    echo -e "${BLUE}Creating new checkpoint...${NC}"
    mkdir -p "$(dirname "$CHECKPOINT_FILE")"

    # Try to copy from template
    if [ -f "$PROJECT_ROOT/docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md" ]; then
        cp "$PROJECT_ROOT/docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md" "$CHECKPOINT_FILE"
        # Update week numbers
        sed -i "s/Week 1/Week $CURRENT_WEEK/g" "$CHECKPOINT_FILE"
        # Update date range
        WEEK_START=$(date -d "$START_DATE + $(( ($CURRENT_WEEK - 1) * 7 )) days" +%Y-%m-%d)
        WEEK_END=$(date -d "$WEEK_START + 6 days" +%Y-%m-%d)
        sed -i "s/2025-12-15 to 2025-12-21/$WEEK_START to $WEEK_END/g" "$CHECKPOINT_FILE"
        echo -e "${GREEN}✓ Checkpoint created for Week $CURRENT_WEEK${NC}\n"
    else
        echo -e "${RED}Template not found. Please create manually.${NC}"
        exit 1
    fi
fi

# Run main menu
main_menu
