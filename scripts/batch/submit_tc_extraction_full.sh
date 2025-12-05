#!/bin/bash
# Submit Full Basin Extraction Job for TC Variables
# Usage: ./scripts/batch/submit_tc_extraction_full.sh [BASIN] [MAX_WORKERS]
#        ./scripts/batch/submit_tc_extraction_full.sh all [MAX_WORKERS]  # Process all basins

set -e

BASIN=${1:-EP}  # Default to EP (East Pacific)
MAX_WORKERS=${2:-1}  # Default to 1 (sequential, thread-safe)

# Available basins (excluding NA which requires HURDAT2)
ALL_BASINS=("EP" "WP" "NI" "SI" "SP" "SA")

if [ "$BASIN" = "all" ]; then
    echo "======================================================================"
    echo "Submitting TC Variable Extraction Jobs for ALL Basins"
    echo "======================================================================"
    echo ""
    echo "Basins to process: ${ALL_BASINS[@]}"
    echo "Processing mode: Sequential (thread-safe)"
    echo "Period: 1980-2020"
    echo ""
    
    JOB_IDS=()
    
    for BASIN_CODE in "${ALL_BASINS[@]}"; do
        echo "----------------------------------------------------------------------"
        echo "Submitting job for basin: $BASIN_CODE"
        echo "----------------------------------------------------------------------"
        
        JOB=$(sbatch \
            --job-name=extract_tc_${BASIN_CODE} \
            --output=logs/extract_tc_variables_${BASIN_CODE}_%j.out \
            --error=logs/extract_tc_variables_${BASIN_CODE}_%j.err \
            --time=12:00:00 \
            --mem=16G \
            --cpus-per-task=$MAX_WORKERS \
            scripts/batch/extract_tc_variables_batch.sh \
            $BASIN_CODE 1980 2020 false 50 $MAX_WORKERS 17.0)
        
        JOB_ID=$(echo $JOB | grep -oP '\d+')
        JOB_IDS+=($JOB_ID)
        
        echo "  ✅ Job submitted: $JOB_ID"
        echo ""
    done
    
    echo "======================================================================"
    echo "All Jobs Submitted Successfully"
    echo "======================================================================"
    echo ""
    echo "Job IDs: ${JOB_IDS[@]}"
    echo ""
    echo "Monitor all jobs with:"
    echo "   squeue -u abdel042"
    echo ""
    echo "Monitor individual jobs:"
    for i in "${!ALL_BASINS[@]}"; do
        BASIN_CODE="${ALL_BASINS[$i]}"
        JOB_ID="${JOB_IDS[$i]}"
        echo "   tail -f logs/extract_tc_variables_${BASIN_CODE}_${JOB_ID}.out  # $BASIN_CODE"
    done
    echo ""
    echo "Expected outputs:"
    for BASIN_CODE in "${ALL_BASINS[@]}"; do
        echo "   outputs/tc_intensity/training_data/tc_training_data_${BASIN_CODE}.csv"
    done
    echo ""
    
else
    echo "======================================================================"
    echo "Submitting TC Variable Extraction Job (Full Basin)"
    echo "======================================================================"
    echo ""
    echo "Configuration:"
    echo "  Basin: $BASIN"
    echo "  Period: 1980-2020"
    echo "  Test mode: NO (full basin processing)"
    echo "  Max workers: $MAX_WORKERS (sequential, thread-safe)"
    echo ""
    
    # Estimate time based on basin (EP has ~12,697 obs, estimate 2-3 hours at 1.3 obs/s)
    echo "Estimated time: 2-4 hours (depending on basin size)"
    echo ""
    
    # Submit batch job
    echo "Submitting batch job..."
    JOB=$(sbatch \
        --job-name=extract_tc_${BASIN} \
        --output=logs/extract_tc_variables_${BASIN}_%j.out \
        --error=logs/extract_tc_variables_${BASIN}_%j.err \
        --time=12:00:00 \
        --mem=16G \
        --cpus-per-task=$MAX_WORKERS \
        scripts/batch/extract_tc_variables_batch.sh \
        $BASIN 1980 2020 false 50 $MAX_WORKERS 17.0)
    
    JOB_ID=$(echo $JOB | grep -oP '\d+')
    echo ""
    echo "✅ Job submitted successfully!"
    echo "   Job ID: $JOB_ID"
    echo "   Job name: extract_tc_${BASIN}"
    echo ""
    echo "Monitor with:"
    echo "   squeue -j $JOB_ID"
    echo "   tail -f logs/extract_tc_variables_${BASIN}_${JOB_ID}.out"
    echo "   tail -f logs/extract_tc_variables_${JOB_ID}.log"
    echo ""
    echo "Expected output:"
    echo "   outputs/tc_intensity/training_data/tc_training_data_${BASIN}.csv"
    echo ""
fi

