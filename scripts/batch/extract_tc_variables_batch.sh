#!/bin/bash
#SBATCH --job-name=extract_tc_vars
#SBATCH --output=logs/extract_tc_variables_%j.out
#SBATCH --error=logs/extract_tc_variables_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=abdel042@uu.nl

# Extract Environmental Variables at TC Locations by Basin (Batch Job)
# Parallelized extraction with debugging and monitoring features
# Features: Parallel processing, progress monitoring, detailed logging

set -e  # Exit on error
set -u  # Exit on undefined variable

# Set working directory
cd /nethome/abdel042/enso_finance

# Create directories
mkdir -p logs
mkdir -p outputs/tc_intensity/training_data

# Log function with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a logs/extract_tc_variables_${SLURM_JOB_ID}.log
}

# Error function
error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a logs/extract_tc_variables_${SLURM_JOB_ID}.log >&2
    exit 1
}

log "======================================================================"
log "TC VARIABLE EXTRACTION - BATCH JOB (PARALLEL)"
log "======================================================================"
log "Job ID: $SLURM_JOB_ID"
log "Node: $SLURM_NODELIST"
log "Started: $(date '+%Y-%m-%d %H:%M:%S')"
log "Working directory: $(pwd)"
log ""
log "Features enabled:"
log "  ✓ Parallel extraction (threading)"
log "  ✓ Progress monitoring with ETA"
log "  ✓ Detailed debugging output"
log "  ✓ Thread-safe logging"
log ""

# Parse arguments
BASIN=${1:-NA}
START_YEAR=${2:-1980}
END_YEAR=${3:-2020}
TEST_MODE=${4:-true}
MAX_TEST_OBS=${5:-50}
MAX_WORKERS=${6:-8}
MIN_WIND_MS=${7:-17.0}

log "[1] Configuration:"
log "   Basin: $BASIN"
log "   Period: $START_YEAR-$END_YEAR"
log "   Test mode: $TEST_MODE"
log "   Max test observations: $MAX_TEST_OBS"
log "   Max workers (parallel): $MAX_WORKERS"
log "   Minimum wind speed: $MIN_WIND_MS m/s"
log ""

# Check Python environment
log "[2] Checking Python environment..."
if ! uv run python3 -c "import pandas, numpy, xarray; print('OK')" 2>/dev/null; then
    error "Required Python packages not available"
fi
log "✅ Python environment OK"
log ""

# Check data availability
log "[3] Checking data availability..."
ERA5_PLEV_COUNT=$(find data/tc_intensity/monthly/era5/pressure_levels -name "*.nc" 2>/dev/null | wc -l)
ERA5_SL_COUNT=$(find data/tc_intensity/monthly/era5/single_level -name "*.nc" 2>/dev/null | wc -l)
ORAS5_COUNT=$(find data/tc_intensity/monthly/oras5 -name "*.nc" 2>/dev/null | wc -l)

log "   ERA5 pressure-level files: $ERA5_PLEV_COUNT"
log "   ERA5 single-level files: $ERA5_SL_COUNT"
log "   ORAS5 files: $ORAS5_COUNT"

if [ "$ERA5_PLEV_COUNT" -lt 100 ] || [ "$ERA5_SL_COUNT" -lt 100 ] || [ "$ORAS5_COUNT" -lt 100 ]; then
    error "Insufficient data files found. Run download scripts first!"
fi
log "✅ Data availability OK"
log ""

# Check monthly data catalog
log "[4] Checking monthly data catalog..."
if [ ! -f "data/tc_intensity/monthly/monthly_data_catalog.json" ]; then
    error "Monthly data catalog not found. Run download scripts first!"
fi
log "✅ Monthly data catalog exists"
log ""

# Start extraction
log "[5] Starting parallel extraction..."
log "   This may take 30-60 minutes for test mode, 6-12 hours for full basin."
log ""

START_TIME=$(date +%s)

# Build Python command arguments
PYTHON_ARGS=(
    scripts/tc_intensity/extract_tc_variables_by_basin_parallel.py
    --basin $BASIN
    --start-year $START_YEAR
    --end-year $END_YEAR
    --min-wind-ms $MIN_WIND_MS
    --max-workers $MAX_WORKERS
)

if [ "$TEST_MODE" = "true" ]; then
    PYTHON_ARGS+=(--test)
    PYTHON_ARGS+=(--max-test-obs $MAX_TEST_OBS)
fi

# Run extraction script - write directly to log file with unbuffered output
PYTHONUNBUFFERED=1 uv run python3 -u "${PYTHON_ARGS[@]}" \
    >> logs/extract_tc_variables_${SLURM_JOB_ID}.log 2>&1

EXIT_CODE=${PIPESTATUS[0]}
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_HOURS=$((ELAPSED / 3600))
ELAPSED_MINUTES=$(((ELAPSED % 3600) / 60))

log ""
log "======================================================================"
log "EXTRACTION COMPLETED"
log "======================================================================"
log "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
log "Elapsed time: ${ELAPSED_HOURS}h ${ELAPSED_MINUTES}m"
log "Exit code: $EXIT_CODE"
log ""

# Final status check and auto-cleaning
if [ $EXIT_CODE -eq 0 ]; then
    log "[6] Final status check..."
    
    # Check output file
    if [ "$TEST_MODE" = "true" ]; then
        OUTPUT_FILE="outputs/tc_intensity/training_data/tc_training_data_${BASIN}_test.csv"
    else
        OUTPUT_FILE="outputs/tc_intensity/training_data/tc_training_data_${BASIN}.csv"
    fi
    
    if [ -f "$OUTPUT_FILE" ]; then
        FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        OBS_COUNT=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
        log "   ✅ Output file created: $OUTPUT_FILE"
        log "   File size: $FILE_SIZE"
        log "   Observations: $OBS_COUNT"
        log ""
        log "   Quick preview (first 3 lines):"
        head -3 "$OUTPUT_FILE" | while IFS= read -r line; do
            log "      $line"
        done
        
        # Auto-clean the data if not in test mode
        if [ "$TEST_MODE" != "true" ]; then
            log ""
            log "[7] Auto-cleaning dataset..."
            log "   Applying cleaning rules (drop missing translation_speed and SST)..."
            
            PYTHONUNBUFFERED=1 uv run python3 -u scripts/tc_intensity/clean_tc_data.py "$OUTPUT_FILE" \
                >> logs/extract_tc_variables_${SLURM_JOB_ID}.log 2>&1
            
            CLEANING_EXIT=${PIPESTATUS[0]}
            
            if [ $CLEANING_EXIT -eq 0 ]; then
                # Check final count after cleaning
                FINAL_OBS=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
                log "   ✅ Cleaning complete!"
                log "   Final observations after cleaning: $FINAL_OBS"
                
                # Quick verification
                PYTHONUNBUFFERED=1 uv run python3 -u -c "
import pandas as pd
df = pd.read_csv('$OUTPUT_FILE')
missing_trans = df['translation_speed'].isna().sum()
missing_sst = df['sst'].isna().sum()
if missing_trans == 0 and missing_sst == 0:
    print('✅ Verification: No missing translation_speed or SST')
else:
    print(f'⚠️  Warning: {missing_trans} missing translation_speed, {missing_sst} missing SST')
" >> logs/extract_tc_variables_${SLURM_JOB_ID}.log 2>&1 || true
            else
                log "   ⚠️  Cleaning had issues (exit code: $CLEANING_EXIT), but continuing..."
            fi
        fi
    else
        log "   ⚠️  Output file not found: $OUTPUT_FILE"
    fi
    
    log ""
    log "✅ Extraction completed successfully!"
else
    log "❌ Extraction failed or incomplete"
    log "   Check error log: logs/extract_tc_variables_${SLURM_JOB_ID}.err"
fi

log ""
log "======================================================================"
log "Job completed: $(date '+%Y-%m-%d %H:%M:%S')"
log "======================================================================"

exit $EXIT_CODE

