# ENSO Finance

Tropical cyclone environmental variable extraction for intensity prediction.

## Scripts

- `scripts/tc_intensity/extract_tc_variables_by_basin_parallel.py` - Extract environmental variables at TC locations
- `scripts/tc_intensity/clean_tc_data.py` - Clean datasets (drop missing translation_speed and SST)
- `scripts/batch/extract_tc_variables_batch.sh` - Batch job script with auto-cleaning
- `scripts/batch/submit_tc_extraction_full.sh` - Submit extraction job for a basin
- `scripts/batch/submit_sequential_basins.sh` - Submit multiple basins sequentially

## Usage

```bash
# Extract variables for a basin
./scripts/batch/submit_tc_extraction_full.sh EP 1

# Clean a dataset
python3 scripts/tc_intensity/clean_tc_data.py outputs/tc_intensity/training_data/tc_training_data_EP.csv
```
