#!/usr/bin/env python3
"""
Generate Weekly Roadmap Progress Report

Automatically generates a summary report of roadmap progress,
including completed tasks, current blockers, and next steps.

Usage:
    python scripts/utils/generate_roadmap_report.py
    python scripts/utils/generate_roadmap_report.py --format markdown
    python scripts/utils/generate_roadmap_report.py --format slack
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from typing import Dict, List, Tuple

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def parse_roadmap_status(status_file: Path) -> Dict:
    """Parse ROADMAP_STATUS.md and extract key metrics."""

    with open(status_file, 'r') as f:
        content = f.read()

    # Extract overall progress
    overall_match = re.search(r'Overall Progress: (\d+)%', content)
    overall_progress = int(overall_match.group(1)) if overall_match else 0

    # Extract current week
    week_match = re.search(r'Current Week: Week (\d+) of (\d+)', content)
    current_week = int(week_match.group(1)) if week_match else 0
    total_weeks = int(week_match.group(2)) if week_match else 24

    # Extract current phase
    phase_match = re.search(r'Current Phase: (.+)', content)
    current_phase = phase_match.group(1) if phase_match else "Unknown"

    # Extract blockers
    blockers_section = re.search(r'### Current Blockers\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    blockers = []
    if blockers_section:
        blocker_text = blockers_section.group(1).strip()
        if "None currently" not in blocker_text:
            blockers = [line.strip('- ').strip() for line in blocker_text.split('\n') if line.strip().startswith('-')]

    # Extract phase progress
    phase_progress = {}
    for i in range(1, 7):
        phase_pattern = f'Phase {i}.*?(\d+)% complete'
        phase_match = re.search(phase_pattern, content)
        if phase_match:
            phase_progress[f'Phase {i}'] = int(phase_match.group(1))

    # Extract completed tasks this week (from activity log)
    activity_match = re.search(r'### \d{4}-\d{2}-\d{2}.*?\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    recent_activity = []
    if activity_match:
        activity_text = activity_match.group(1).strip()
        recent_activity = [line.strip('- ').strip() for line in activity_text.split('\n') if '✅' in line]

    # Extract next milestones
    milestone_pattern = rf'\| {current_week+1} \| .+ \| (.+?) \|'
    next_milestone_match = re.search(milestone_pattern, content)
    next_milestone = next_milestone_match.group(1) if next_milestone_match else "See roadmap"

    return {
        'overall_progress': overall_progress,
        'current_week': current_week,
        'total_weeks': total_weeks,
        'current_phase': current_phase,
        'blockers': blockers,
        'phase_progress': phase_progress,
        'recent_activity': recent_activity,
        'next_milestone': next_milestone
    }

def generate_terminal_report(data: Dict) -> str:
    """Generate colorful terminal report."""

    report = []

    # Header
    report.append(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    report.append(f"{Colors.BOLD}{Colors.BLUE}   PUBLICATION ROADMAP - WEEKLY PROGRESS REPORT{Colors.END}")
    report.append(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

    # Date
    report.append(f"{Colors.BOLD}Report Date:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"{Colors.BOLD}Current Week:{Colors.END} Week {data['current_week']} of {data['total_weeks']}\n")

    # Overall progress
    progress_bar = create_progress_bar(data['overall_progress'], 50)
    report.append(f"{Colors.BOLD}Overall Progress:{Colors.END} {progress_bar} {data['overall_progress']}%\n")

    # Phase progress
    report.append(f"{Colors.BOLD}Phase Progress:{Colors.END}")
    for phase, progress in data['phase_progress'].items():
        phase_bar = create_progress_bar(progress, 30)
        color = Colors.GREEN if progress == 100 else Colors.YELLOW if progress > 0 else Colors.RED
        report.append(f"  {color}{phase}:{Colors.END} {phase_bar} {progress}%")
    report.append("")

    # Current phase
    report.append(f"{Colors.BOLD}Current Phase:{Colors.END}")
    report.append(f"  {Colors.YELLOW}→{Colors.END} {data['current_phase']}\n")

    # Recent activity
    if data['recent_activity']:
        report.append(f"{Colors.BOLD}Recent Activity:{Colors.END}")
        for activity in data['recent_activity']:
            report.append(f"  {Colors.GREEN}✅{Colors.END} {activity}")
        report.append("")

    # Blockers
    if data['blockers']:
        report.append(f"{Colors.BOLD}{Colors.RED}⚠ Blockers:{Colors.END}")
        for blocker in data['blockers']:
            report.append(f"  {Colors.RED}•{Colors.END} {blocker}")
        report.append("")
    else:
        report.append(f"{Colors.BOLD}{Colors.GREEN}✓ No Current Blockers{Colors.END}\n")

    # Next milestone
    report.append(f"{Colors.BOLD}Next Milestone (Week {data['current_week'] + 1}):{Colors.END}")
    report.append(f"  {Colors.BLUE}→{Colors.END} {data['next_milestone']}\n")

    # Timeline
    weeks_remaining = data['total_weeks'] - data['current_week']
    report.append(f"{Colors.BOLD}Timeline:{Colors.END}")
    report.append(f"  {Colors.BLUE}•{Colors.END} {weeks_remaining} weeks remaining until target submission")

    expected_completion = datetime.now() + timedelta(weeks=weeks_remaining)
    report.append(f"  {Colors.BLUE}•{Colors.END} Expected completion: {expected_completion.strftime('%Y-%m-%d')}\n")

    # Footer
    report.append(f"{Colors.BLUE}{'='*80}{Colors.END}")
    report.append(f"{Colors.BOLD}Next Update:{Colors.END} {(datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')}")
    report.append(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    return '\n'.join(report)

def generate_markdown_report(data: Dict) -> str:
    """Generate markdown report for documentation."""

    report = []

    # Header
    report.append("# Weekly Progress Report")
    report.append(f"\n**Report Date**: {datetime.now().strftime('%Y-%m-%d')}")
    report.append(f"**Week**: {data['current_week']} of {data['total_weeks']}")
    report.append(f"**Overall Progress**: {data['overall_progress']}%\n")

    # Progress bars
    report.append("## Phase Progress")
    report.append("")
    for phase, progress in data['phase_progress'].items():
        status = "🟢" if progress == 100 else "🟡" if progress > 0 else "⚪"
        report.append(f"- {status} **{phase}**: {progress}%")
    report.append("")

    # Current work
    report.append("## Current Focus")
    report.append(f"\n**Phase**: {data['current_phase']}\n")

    # Recent activity
    if data['recent_activity']:
        report.append("## Completed This Week")
        report.append("")
        for activity in data['recent_activity']:
            report.append(f"- ✅ {activity}")
        report.append("")

    # Blockers
    if data['blockers']:
        report.append("## ⚠️ Blockers")
        report.append("")
        for blocker in data['blockers']:
            report.append(f"- {blocker}")
        report.append("")
    else:
        report.append("## ✅ No Current Blockers\n")

    # Next steps
    report.append("## Next Milestone")
    report.append(f"\n**Week {data['current_week'] + 1}**: {data['next_milestone']}\n")

    # Timeline
    weeks_remaining = data['total_weeks'] - data['current_week']
    expected_completion = datetime.now() + timedelta(weeks=weeks_remaining)
    report.append("## Timeline")
    report.append(f"\n- **Weeks Remaining**: {weeks_remaining}")
    report.append(f"- **Expected Completion**: {expected_completion.strftime('%Y-%m-%d')}\n")

    return '\n'.join(report)

def generate_slack_report(data: Dict) -> str:
    """Generate Slack-formatted report."""

    report = []

    # Header
    report.append("📊 *Weekly Roadmap Report*")
    report.append(f"Week {data['current_week']}/{data['total_weeks']} • {data['overall_progress']}% Complete\n")

    # Current phase
    report.append(f"🎯 *Current Phase:* {data['current_phase']}\n")

    # Recent activity
    if data['recent_activity']:
        report.append("✅ *Completed This Week:*")
        for activity in data['recent_activity'][:3]:  # Limit to 3 for brevity
            report.append(f"  • {activity}")
        report.append("")

    # Blockers
    if data['blockers']:
        report.append("⚠️ *Blockers:*")
        for blocker in data['blockers']:
            report.append(f"  • {blocker}")
        report.append("")
    else:
        report.append("✓ No blockers\n")

    # Next steps
    report.append(f"🎯 *Next Milestone:* {data['next_milestone']}")

    return '\n'.join(report)

def create_progress_bar(progress: int, width: int = 30) -> str:
    """Create ASCII progress bar."""
    filled = int(width * progress / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"

def main():
    parser = argparse.ArgumentParser(description='Generate roadmap progress report')
    parser.add_argument(
        '--format',
        choices=['terminal', 'markdown', 'slack'],
        default='terminal',
        help='Report format (default: terminal)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Find status file
    project_root = Path(__file__).parent.parent.parent
    status_file = project_root / 'docs' / 'ROADMAP_STATUS.md'

    if not status_file.exists():
        print(f"Error: Status file not found at {status_file}")
        return 1

    # Parse status
    data = parse_roadmap_status(status_file)

    # Generate report
    if args.format == 'terminal':
        report = generate_terminal_report(data)
    elif args.format == 'markdown':
        report = generate_markdown_report(data)
    else:  # slack
        report = generate_slack_report(data)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
    else:
        print(report)

    return 0

if __name__ == '__main__':
    exit(main())
