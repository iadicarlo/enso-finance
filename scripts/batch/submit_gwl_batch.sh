#!/bin/bash
#SBATCH --job-name=enso_gwl
#SBATCH --output=logs/gwl_%A_%a.out
#SBATCH --error=logs/gwl_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --array=0-92  # Process 93 variants (0-92), no concurrency limit

# Load modules (adjust for Lorenz - uncomment/modify as needed)
# module load python/3.11
# module load gcc

# Activate environment (choose one method)
# Method 1: Virtual environment
# source /nethome/abdel042/enso_finance/venv_lorenz/bin/activate

# Method 2: uv (if available)
# export PATH="/path/to/uv:$PATH"
# uv run python scripts/process_gwl_batch.py ...

# Method 3: System Python with packages
# (ensure all dependencies are installed)

# Set working directory (UPDATE THIS PATH!)
cd /nethome/abdel042/enso_finance

# Create logs directory
mkdir -p logs
mkdir -p outputs/processed_data/gwl_batch

# Configure SSL for accessing Pangeo cloud data
# On HPC systems, SSL certificates may not be configured, so disable verification
export DISABLE_SSL_VERIFY=1
export REQUESTS_CA_BUNDLE=""
export CURL_CA_BUNDLE=""
export SSL_CERT_FILE=""
export PYTHONHTTPSVERIFY=0
# Note: This disables SSL verification which is needed for Pangeo access on HPC systems

# Run processing for this array task
# Use uv for package management as requested
if ! command -v uv &> /dev/null
then
    echo "uv not found in PATH, attempting to load from .local/bin"
    export PATH="/nethome/abdel042/.local/bin:$PATH"
    if ! command -v uv &> /dev/null
    then
        echo "Error: uv still not found after updating PATH."
        exit 1
    fi
fi

uv run python scripts/batch/process_gwl_batch.py \
    --variant-idx $SLURM_ARRAY_TASK_ID \
    --output-dir outputs/processed_data/gwl_batch \
    --catalog-url data/catalogs/pangeo-cmip6.json

echo "Job $SLURM_ARRAY_TASK_ID completed"

