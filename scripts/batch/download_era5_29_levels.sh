#!/bin/bash
#SBATCH --job-name=download_era5_29lev
#SBATCH --output=logs/download_era5_29lev_%j.out
#SBATCH --error=logs/download_era5_29lev_%j.err
#SBATCH --time=30:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --partition=normal

# Download ERA5 Monthly Data with 29 Pressure Levels (1980-2020)
# For accurate PI calculation using tcpyPI

set -e

# Change to project directory
cd /nethome/abdel042/enso_finance

# Activate virtual environment (check both .venv and venv)
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "ERROR: No virtual environment found (.venv or venv)"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Log start time
START_TIME=$(date +%s)
START_DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "======================================================================"
echo "DOWNLOADING ERA5 MONTHLY DATA (29 PRESSURE LEVELS)"
echo "======================================================================"
echo "Started: $START_DATE"
echo "Period: 1980-2020 (41 years × 12 months = 492 files)"
echo "Pressure levels: 29 levels (1000-50 hPa)"
echo "Variables: temperature, u/v winds, specific humidity"
echo "Single-level: SST, surface pressure"
echo "======================================================================"
echo ""
echo "Monitor progress with:"
echo "  ./scripts/batch/monitor_download_era5.sh $SLURM_JOB_ID"
echo "  tail -f logs/download_era5_29lev_${SLURM_JOB_ID}.out"
echo ""

# Run download script
# Note: Script defaults to 29 pressure levels (ERA5_PI_PRESSURE_LEVELS) and all required variables
python scripts/tc_intensity/download_monthly_training_data.py \
    --start-year 1980 \
    --end-year 2020 \
    --era5-only

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
HOURS=$((ELAPSED / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))
SECONDS=$((ELAPSED % 60))

# Count downloaded files
if [ -d "data/tc_intensity/monthly/era5/pressure_levels" ]; then
    FILE_COUNT=$(find data/tc_intensity/monthly/era5/pressure_levels -name "*.nc" 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh data/tc_intensity/monthly/era5/pressure_levels 2>/dev/null | cut -f1)
else
    FILE_COUNT=0
    TOTAL_SIZE="N/A"
fi

echo ""
echo "======================================================================"
echo "DOWNLOAD COMPLETE"
echo "======================================================================"
echo "Ended: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Elapsed time: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Files downloaded: $FILE_COUNT / 492 expected"
echo "Total size: $TOTAL_SIZE"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Verify downloaded files: ls -lh data/tc_intensity/monthly/era5/pressure_levels/"
echo "  2. Re-extract training data with updated PI calculation"
echo "  3. Validate PI values are in correct range (30-90 m/s)"
echo ""

