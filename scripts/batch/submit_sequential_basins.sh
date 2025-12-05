#!/bin/bash
# Submit all TC basin extractions sequentially with automatic cleaning
# Uses Slurm job dependencies to chain: WP → NI → SI → SP → SA

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "Submitting Sequential TC Basin Processing with Auto-Cleaning"
echo "======================================================================"
echo ""
echo "Processing order:"
echo "  ✅ EP (East Pacific) - Already complete"
echo "  ⏳ WP (West Pacific)"
echo "  ⏸️  NI (North Indian) - Will start after WP"
echo "  ⏸️  SI (South Indian) - Will start after NI"
echo "  ⏸️  SP (South Pacific) - Will start after SI"
echo "  ⏸️  SA (South Atlantic) - Will start after SP"
echo ""

# Basins to process (excluding EP which is already done)
BASINS=("WP" "NI" "SI" "SP" "SA")

# Check if WP job is already running
EXISTING_WP=$(squeue -u abdel042 -n extract_tc_WP -h -o "%i" 2>/dev/null | head -1)

if [ -n "$EXISTING_WP" ]; then
    echo "⚠️  WP basin job already running: $EXISTING_WP"
    echo "   Using this as dependency for remaining basins..."
    PREVIOUS_JOB=$EXISTING_WP
    START_FROM=1  # Start from NI (index 1)
else
    echo "Submitting WP basin first..."
    # Submit WP basin
    WP_JOB=$(sbatch \
        --job-name=extract_tc_WP \
        --output=logs/extract_tc_variables_WP_%j.out \
        --error=logs/extract_tc_variables_WP_%j.err \
        --time=12:00:00 \
        --mem=16G \
        --cpus-per-task=1 \
        scripts/batch/extract_tc_variables_batch.sh \
        WP 1980 2020 false 50 1 17.0 2>&1)
    
    WP_JOB_ID=$(echo "$WP_JOB" | grep -oP '\d+' | head -1)
    
    if [ -z "$WP_JOB_ID" ]; then
        echo "❌ Failed to submit WP job"
        echo "$WP_JOB"
        exit 1
    fi
    
    echo "  ✅ WP job submitted: $WP_JOB_ID"
    PREVIOUS_JOB=$WP_JOB_ID
    START_FROM=0  # Start from WP (index 0)
fi

# Submit remaining basins with dependencies
for i in $(seq $START_FROM $((${#BASINS[@]} - 1))); do
    BASIN=${BASINS[$i]}
    
    # Skip WP if it's already running
    if [ "$BASIN" = "WP" ] && [ -n "$EXISTING_WP" ]; then
        continue
    fi
    
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Submitting $BASIN basin (depends on previous job: $PREVIOUS_JOB)"
    echo "----------------------------------------------------------------------"
    
    # Submit with dependency on previous job
    JOB=$(sbatch \
        --job-name=extract_tc_${BASIN} \
        --output=logs/extract_tc_variables_${BASIN}_%j.out \
        --error=logs/extract_tc_variables_${BASIN}_%j.err \
        --time=12:00:00 \
        --mem=16G \
        --cpus-per-task=1 \
        --dependency=afterok:${PREVIOUS_JOB} \
        scripts/batch/extract_tc_variables_batch.sh \
        $BASIN 1980 2020 false 50 1 17.0 2>&1)
    
    JOB_ID=$(echo "$JOB" | grep -oP '\d+' | head -1)
    
    if [ -z "$JOB_ID" ]; then
        echo "❌ Failed to submit $BASIN job"
        echo "$JOB"
        exit 1
    fi
    
    echo "  ✅ $BASIN job submitted: $JOB_ID"
    echo "     (Will start after job $PREVIOUS_JOB completes + cleans data)"
    
    PREVIOUS_JOB=$JOB_ID
done

echo ""
echo "======================================================================"
echo "All Jobs Submitted Successfully!"
echo "======================================================================"
echo ""
echo "Job Chain:"
if [ -n "$EXISTING_WP" ]; then
    echo "  WP: $EXISTING_WP (already running, will auto-clean when done)"
    PREVIOUS_JOB=$EXISTING_WP
    for i in $(seq 1 $((${#BASINS[@]} - 1))); do
        BASIN=${BASINS[$i]}
        echo "  $BASIN: (submitted, will run after previous completes)"
    done
else
    for i in $(seq 0 $((${#BASINS[@]} - 1))); do
        BASIN=${BASINS[$i]}
        if [ "$i" -eq 0 ]; then
            echo "  $BASIN: $WP_JOB_ID"
        else
            echo "  $BASIN: (submitted, will run after previous completes)"
        fi
    done
fi

echo ""
echo "Monitor with:"
echo "  squeue -u abdel042"
echo ""
echo "Monitor specific jobs:"
if [ -n "$EXISTING_WP" ]; then
    echo "  tail -f logs/extract_tc_variables_WP_${EXISTING_WP}.out"
else
    echo "  tail -f logs/extract_tc_variables_WP_${WP_JOB_ID}.out"
fi
echo ""
echo "Each job will automatically:"
echo "  1. Extract environmental variables"
echo "  2. Clean the dataset (drop missing translation_speed and SST)"
echo "  3. Trigger the next basin job"
