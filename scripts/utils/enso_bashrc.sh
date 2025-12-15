# ENSO Finance Project - Bash Configuration
# Add this to your ~/.bashrc to make aliases and settings permanent
#
# Usage:
#   cat scripts/utils/enso_bashrc.sh >> ~/.bashrc
#   source ~/.bashrc
#
# Or add this line to ~/.bashrc:
#   source /nethome/abdel042/enso_finance/scripts/utils/setup_roadmap_aliases.sh

# Set vim as default editor
export EDITOR=vim

# Load project aliases
source /nethome/abdel042/enso_finance/scripts/utils/setup_roadmap_aliases.sh

# Optional: Auto-navigate to project on login
# cd /nethome/abdel042/enso_finance

# Optional: Show roadmap status on login
# echo ""
# echo "ENSO Finance Project - Quick Status:"
# python3 /nethome/abdel042/enso_finance/scripts/utils/generate_roadmap_report.py 2>/dev/null || echo "Run 'goto-enso' to navigate to project"
# echo ""
