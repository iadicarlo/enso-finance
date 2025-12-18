#!/bin/bash
#SBATCH --job-name=test_kd_all
#SBATCH --output=logs/test_kd_all_%j.log
#SBATCH --error=logs/test_kd_all_%j.err
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=normal

echo "Testing K&D Hybrid on All Basins"
echo "================================="
date

source .venv/bin/activate

# Test all basins with N=500 tracks each (more tracks = more landfalls)
for BASIN in NA EP WP NI SI SP; do
    echo ""
    echo "========================================================================"
    echo "BASIN: $BASIN (N=500 tracks)"
    echo "========================================================================"
    
    uv run python scripts/tc_intensity/generate_event_set.py \
        --basin $BASIN \
        --n-tracks 500 \
        --random-seed 42
    
    # Find generated file
    EVENT_FILE=$(ls -t outputs/tc_intensity/synthetic_tracks/synthetic_event_set_${BASIN}_*.csv 2>/dev/null | head -1)
    
    if [ -f "$EVENT_FILE" ]; then
        echo ""
        echo "✅ Generated: $EVENT_FILE"
        echo "Running validation..."
        
        uv run python scripts/tc_intensity/validate_physical_constraints.py \
            --synthetic-file "$EVENT_FILE" \
            --basin $BASIN
    else
        echo "❌ File not found for $BASIN"
    fi
done

echo ""
echo "================================="
echo "All basins complete!"
date
