#!/bin/bash
#SBATCH --job-name=extract_tc_vars
#SBATCH --output=logs/extract_tc_variables_%j.out
#SBATCH --error=logs/extract_tc_variables_%j.err
#SBATCH --time=12:00:00
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
MIN_WIND_MS=${4:-17.0}
CHUNK_START=${5:-0}
CHUNK_SIZE=${6:-}
OUTPUT_FILE=${7:-}
MAX_WORKERS=${8:-1}

log "[1] Configuration:"
log "   Basin: $BASIN"
log "   Period: $START_YEAR-$END_YEAR"
log "   Minimum wind speed: $MIN_WIND_MS m/s"
if [ -n "$CHUNK_START" ] && [ -n "$CHUNK_SIZE" ]; then
    log "   Chunk start: $CHUNK_START"
    log "   Chunk size: $CHUNK_SIZE"
    log "   Processing chunk: $CHUNK_START to $((CHUNK_START + CHUNK_SIZE - 1))"
fi
if [ -n "$OUTPUT_FILE" ]; then
    log "   Output file: $OUTPUT_FILE"
fi
log "   Max workers (parallel): $MAX_WORKERS (sequential if 1)"
log ""

# Load ESMF environment (required for ORAS5 regridding with xesmf)
log "[2] Loading ESMF environment..."
if [ -f "scripts/load_esmf_env.sh" ]; then
    source scripts/load_esmf_env.sh
    log "✅ ESMF environment loaded"
else
    log "⚠️  WARNING: ESMF environment script not found at scripts/load_esmf_env.sh"
    log "   ORAS5 regridding may fail. Setting ESMFMKFILE manually..."
    export ESMFMKFILE="/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default/esmf.mk"
    export ESMF_DIR="/nethome/abdel042/esmf_build/esmf"
    export LD_LIBRARY_PATH="/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default:${LD_LIBRARY_PATH:-}"
fi

# Ensure ESMF environment variables persist after venv activation
export ESMFMKFILE="${ESMFMKFILE:-/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default/esmf.mk}"
export ESMF_DIR="${ESMF_DIR:-/nethome/abdel042/esmf_build/esmf}"
ESMF_LIB_DIR="${ESMF_DIR}/lib/libO/Linux.gfortran.64.mpiuni.default"
if [ -d "$ESMF_LIB_DIR" ]; then
    export LD_LIBRARY_PATH="${ESMF_LIB_DIR}:${LD_LIBRARY_PATH:-}"
fi

# WORKAROUND: ESMPy was installed with hardcoded path to /tmp/esmf_build
# Create symlink if it doesn't exist so ESMPy can find the libraries
if [ ! -d "/tmp/esmf_build" ] && [ -d "/nethome/abdel042/esmf_build" ]; then
    log "   Creating symlink /tmp/esmf_build -> /nethome/abdel042/esmf_build (ESMPy workaround)"
    mkdir -p /tmp
    ln -sf /nethome/abdel042/esmf_build /tmp/esmf_build 2>/dev/null || log "   Note: Symlink may already exist"
fi

log "   ESMFMKFILE=$ESMFMKFILE"
log "   ESMF_DIR=$ESMF_DIR"
log ""

# Check Python environment
log "[3] Checking Python environment..."
# Try venv first, then uv run
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Re-export ESMF variables after venv activation to ensure they persist
export ESMFMKFILE="${ESMFMKFILE:-/nethome/abdel042/esmf_build/esmf/lib/libO/Linux.gfortran.64.mpiuni.default/esmf.mk}"
export ESMF_DIR="${ESMF_DIR:-/nethome/abdel042/esmf_build/esmf}"
if [ -d "$ESMF_LIB_DIR" ]; then
    export LD_LIBRARY_PATH="${ESMF_LIB_DIR}:${LD_LIBRARY_PATH:-}"
fi

if ! python3 -c "import pandas, numpy, xarray; print('OK')" 2>/dev/null; then
    if ! uv run python3 -c "import pandas, numpy, xarray; print('OK')" 2>/dev/null; then
        error "Required Python packages not available"
    fi
    PYTHON_CMD="uv run python3"
else
    PYTHON_CMD="python3"
fi
log "✅ Python environment OK"

# Verify xesmf can be imported (required for SST extraction)
log "[3.5] Verifying xesmf (required for ORAS5 regridding)..."
# Explicitly export ESMF variables for the Python subprocess
export ESMFMKFILE="${ESMFMKFILE}"
export ESMF_DIR="${ESMF_DIR}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}"
# Limit thread usage to avoid NetCDF/HDF5 threading issues
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
if ! env ESMFMKFILE="${ESMFMKFILE}" ESMF_DIR="${ESMF_DIR}" LD_LIBRARY_PATH="${LD_LIBRARY_PATH}" python3 -c "import xesmf; print('OK')" 2>&1; then
    log "   Attempting xesmf import failed. Error output:"
    env ESMFMKFILE="${ESMFMKFILE}" ESMF_DIR="${ESMF_DIR}" LD_LIBRARY_PATH="${LD_LIBRARY_PATH}" python3 -c "import xesmf" 2>&1 | head -20 | while read line; do
        log "      $line"
    done
    error "xesmf cannot be imported! Check ESMF environment variables. ESMFMKFILE=$ESMFMKFILE"
fi
log "✅ xesmf import successful"
log ""

# Check data availability
log "[4] Checking data availability..."
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
log "[5] Checking monthly data catalog..."
if [ ! -f "data/tc_intensity/monthly/monthly_data_catalog.json" ]; then
    error "Monthly data catalog not found. Run download scripts first!"
fi
log "✅ Monthly data catalog exists"
log ""

# Start extraction
log "[6] Starting parallel extraction..."
log "   This may take 30-60 minutes for test mode, 6-12 hours for full basin."
log ""

START_TIME=$(date +%s)

# Build Python command arguments
PYTHON_ARGS=(
    scripts/tc_intensity/extract_tc_variables_by_basin_parallel.py
    --basin "$BASIN"
    --start-year "$START_YEAR"
    --end-year "$END_YEAR"
    --min-wind-ms "$MIN_WIND_MS"
    --max-workers "$MAX_WORKERS"
)

# Add chunk parameters if provided
if [ -n "$CHUNK_START" ] && [ -n "$CHUNK_SIZE" ]; then
    PYTHON_ARGS+=(--chunk-start "$CHUNK_START")
    PYTHON_ARGS+=(--chunk-size "$CHUNK_SIZE")
fi

# Add output file if provided
if [ -n "$OUTPUT_FILE" ]; then
    PYTHON_ARGS+=(--output-file "$OUTPUT_FILE")
fi

# Run extraction script - write directly to log file with unbuffered output
log "Executing: PYTHONUNBUFFERED=1 $PYTHON_CMD -u ${PYTHON_ARGS[*]}"
log "Output will be written to: logs/extract_tc_variables_${SLURM_JOB_ID}.log"
log ""

# Use explicit bash array expansion to ensure it works
PYTHONUNBUFFERED=1 $PYTHON_CMD -u "${PYTHON_ARGS[@]}" \
    >> logs/extract_tc_variables_${SLURM_JOB_ID}.log 2>&1 &
PYTHON_PID=$!
log "Python process started with PID: $PYTHON_PID"
wait $PYTHON_PID

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
    if [ -z "$OUTPUT_FILE" ]; then
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
        
        # Auto-clean the data (skip for chunk files, will combine later)
        if [[ ! "$OUTPUT_FILE" =~ chunk ]]; then
            log ""
            log "[7] Auto-cleaning dataset..."
            log "   Applying cleaning rules (drop missing translation_speed and SST)..."
            
            PYTHONUNBUFFERED=1 $PYTHON_CMD -u scripts/tc_intensity/clean_tc_data.py "$OUTPUT_FILE" \
                >> logs/extract_tc_variables_${SLURM_JOB_ID}.log 2>&1
            
            CLEANING_EXIT=${PIPESTATUS[0]}
            
            if [ $CLEANING_EXIT -eq 0 ]; then
                # Check final count after cleaning
                FINAL_OBS=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
                log "   ✅ Cleaning complete!"
                log "   Final observations after cleaning: $FINAL_OBS"
                
                # Quick verification
                PYTHONUNBUFFERED=1 $PYTHON_CMD -u -c "
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

