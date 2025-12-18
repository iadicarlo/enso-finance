#!/bin/bash
#SBATCH --job-name=test_kd
#SBATCH --output=logs/test_kd_%j.log
#SBATCH --error=logs/test_kd_%j.err
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=normal

echo "Testing K&D Hybrid Implementation"
echo "=================================="
date

# Activate environment
source .venv/bin/activate

# Test on NA basin (high landfall rate)
BASIN="NA"
N_TRACKS=200

echo ""
echo "Generating $N_TRACKS tracks for $BASIN with K&D decay..."
uv run python scripts/tc_intensity/generate_event_set.py \
    --basin $BASIN \
    --n-tracks $N_TRACKS \
    --random-seed 42

# Find the generated file
EVENT_FILE=$(ls -t outputs/tc_intensity/calibration/synthetic_event_set_${BASIN}_*.csv | head -1)

if [ -f "$EVENT_FILE" ]; then
    echo ""
    echo "✅ Event set generated: $EVENT_FILE"
    
    echo ""
    echo "Running physical constraints validation..."
    uv run python scripts/tc_intensity/validate_physical_constraints.py \
        --file "$EVENT_FILE" \
        --basin $BASIN
else
    echo "❌ Event set not found"
    exit 1
fi

echo ""
echo "Test complete!"
date
