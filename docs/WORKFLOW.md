# ENSO-GWL Analysis Workflow

## Overview

This project analyzes how ENSO (El Niño-Southern Oscillation) changes with Global Warming Levels (GWL) using CMIP6 models, with applications for insurance and reinsurance risk assessment.

**High-Level Workflow:**
1. **Model Selection** → 2. **Data Processing** → 3. **GWL Calculation** → 4. **ENSO Classification** → 5. **Scientific Analysis** → 6. **Insurance Metrics**

---

## Workflow Stages

### Stage 1: Model Selection

**Goal:** Select CMIP6 models that adequately represent ENSO dynamics using Cai et al. (2014) criteria.

**Scripts:**
- `scripts/process_all_variants.py` - Processes all variants and applies Cai criteria

**Inputs:**
- Pangeo CMIP6 catalog (`data/catalogs/pangeo-cmip6.json`)
- Model inventory

**Outputs:**
- `outputs/processed_data/cai_all_variants.csv` - All variants with Cai test results
- `outputs/processed_data/cai_model_summary.csv` - Models that pass (>50% variants pass)

**Key Steps:**
1. Load CMIP6 catalog from Pangeo
2. For each model variant:
   - Extract Niño 3.4 SST and Niño 3 precipitation
   - Compute DJF means
   - Calculate Niño 3 rainfall skewness (must be > 1.0)
   - Detect extreme El Niño events (Niño3.4 SSTa > 0.5×STD AND Niño3 PR > 5 mm/day)
3. A model "passes" if >50% of its variants pass both criteria

---

### Stage 2: Data Preprocessing

**Goal:** Standardize CMIP6 data for GWL and ENSO analysis.

**Modules:**
- `src/cmip6/preprocessing.py` - Core preprocessing functions
- `src/cmip6/model_finder.py` - Find available models in catalog

**Key Functions:**
- `create_target_grid()` - Create 1°×1° regular lat/lon grid
- `linear_detrend()` - Remove linear trend from monthly data
- `compute_djf_means()` - Calculate December-January-February seasonal means
- `extract_region()` - Extract regional means (global, Niño3.4, Niño3)

**Standard Processing:**
1. Interpolate to 1°×1° grid (handles curvilinear ocean grids)
2. Linear detrend monthly time series
3. Compute DJF means (December assigned to following year)
4. Calculate anomalies relative to 1850-2014 baseline

---

### Stage 3: GWL Calculation

**Goal:** Calculate Global Warming Levels for each model-variant-SSP combination.

**Scripts:**
- `scripts/process_gwl_batch.py` - Process single variant (designed for SLURM array jobs)
- `scripts/combine_gwl_results.py` - Combine results from all variants

**Modules:**
- `src/cmip6/gwl_calculator.py` - `GWLProcessor` class

**Method:**
1. For each variant-SSP combination (e.g., CESM2 r1i1p1f1 + SSP370):
   - Load historical + SSP temperature data
   - Compute DJF Global Mean Surface Temperature (GMST)
   - Fit 4th-order polynomial using Ridge regression
   - Calculate warming index relative to 1850-1900 baseline
   - Assign GWL bins: 0.0°C, 1.0°C, 1.5°C, 2.0°C, 2.5°C, 3.0°C, 4.0°C

2. **Important:** Each variant-SSP gets its own independent polynomial fit

**Batch Processing:**
```bash
# Submit array job for all 93 variants
sbatch scripts/submit_gwl_batch.sh

# Monitor progress
bash scripts/monitor_gwl_jobs.sh

# Combine results when complete
uv run python scripts/combine_gwl_results.py
```

**Outputs:**
- `outputs/processed_data/gwl_batch/gwl_variant_*.csv` - Individual variant results
- `outputs/processed_data/enso_gwl_results.csv` - Combined all variants

---

### Stage 4: ENSO Classification

**Goal:** Classify ENSO events by type and link to GWL bins.

**Classification (Cai et al. 2014 criteria):**
- **La Niña**: Normalized Niño3.4 SST < -0.5
- **Neutral**: -0.5 ≤ Normalized Niño3.4 SST ≤ +0.5
- **Moderate El Niño**: Normalized Niño3.4 SST > +0.5 AND Niño3 PR ≤ 5 mm/day
- **Extreme El Niño**: Normalized Niño3.4 SST > +0.5 AND Niño3 PR > 5 mm/day

**Normalization:**
- Niño3.4 anomalies normalized by 1850-2014 standard deviation

**This happens during Stage 3** in `compute_gwl_and_classify_enso()` function.

---

### Stage 5: Scientific Analysis

**Goal:** Generate figures and tables showing ENSO changes by GWL.

**Scripts:**
- `scripts/scientific_analysis.py` - Main analysis script

**Key Functions:**
- `calculate_frequency_changes()` - ENSO frequency changes by GWL
- `model_robustness_check()` - Multi-model robustness analysis
- `insurance_risk_framing()` - Translate to insurance language

**Outputs:**
- `outputs/figures/enso_frequency_by_gwl.png` - Frequency changes
- `outputs/figures/model_robustness.png` - Multi-model agreement
- `outputs/tables/enso_frequency_changes.csv` - Frequency change table
- `outputs/tables/model_robustness_analysis.csv` - Model agreement metrics
- `outputs/tables/enso_gwl_insurance_summary.csv` - Insurance implications

**Run:**
```bash
# On login node or interactive session
uv run python scripts/scientific_analysis.py
```

---

### Stage 6: Insurance Metrics (Future: CLIMADA Integration)

**Goal:** Translate physical changes to insurance/reinsurance metrics.

**Modules:**
- `src/analysis/insurance_metrics.py` - Insurance-specific calculations
- `src/analysis/enso_risk.py` - ENSO-conditional risk ratios

**Current Metrics:**
- Annual Average Loss (AAL)
- Value at Risk (VaR) at 99.5% (Solvency II standard)
- Risk ratios by ENSO phase
- Optimal contract timing

**Future (with CLIMADA):**
- Physical hazard modeling (TC tracks, floods)
- Exposure-vulnerability-impact calculation
- Projected losses under future warming

---

## File Organization

### Scripts Structure

```
scripts/
├── batch/                    # SLURM batch job scripts
│   ├── submit_gwl_batch.sh   # Main array job submission
│   └── submit_single_variant.sh  # Test single variant
├── analysis/                 # Analysis scripts
│   └── scientific_analysis.py
├── utils/                    # Utility scripts
│   ├── combine_gwl_results.py
│   ├── download_pangeo_catalog.sh
│   └── monitor_gwl_jobs.sh
└── README_LORENZ.md         # HPC-specific instructions
```

### Notebooks Structure

```
notebooks/
├── 01_process_cmip6_enso.py      # Model selection & preprocessing
├── 02_enso_gwl_analysis.ipynb    # GWL + ENSO classification
└── 03_cmip6_enso_gwl_analysis.py # Scientific analysis & insurance framing
```

### Source Code Structure

```
src/
├── cmip6/              # CMIP6-specific modules
│   ├── preprocessing.py
│   ├── gwl_calculator.py
│   ├── enso_cmip6.py
│   └── model_finder.py
├── analysis/           # Statistical analysis
│   ├── enso_risk.py
│   ├── insurance_metrics.py
│   └── rigorous_methods.py
├── data_loaders/       # Data I/O
│   ├── enso_data.py
│   └── hazard_data.py
└── visualization/      # Plotting functions
    └── plots.py
```

---

## Running the Complete Workflow

### On HPC (Lorenz)

```bash
# 1. Download catalog (one-time setup)
bash scripts/utils/download_pangeo_catalog.sh

# 2. Process all variants (batch job)
sbatch scripts/batch/submit_gwl_batch.sh

# 3. Monitor jobs
bash scripts/utils/monitor_gwl_jobs.sh

# 4. Combine results
uv run python scripts/utils/combine_gwl_results.py

# 5. Scientific analysis (interactive or batch)
uv run python scripts/analysis/scientific_analysis.py
```

### Local Development

```bash
# 1. Model selection (small subset)
uv run python scripts/process_all_variants.py --max-models 5

# 2. Process single variant (testing)
uv run python scripts/batch/process_gwl_batch.py --variant-idx 0

# 3. Analysis
uv run python scripts/analysis/scientific_analysis.py
```

---

## Key Configuration

### GWL Parameters

```python
# In scripts/process_gwl_batch.py
gwl_processor = GWLProcessor(
    reference_period=(1850, 1900),  # Pre-industrial baseline
    polynomial_order=4,              # 4th-order polynomial fit
    method='ridge',                  # Ridge regression (L2 regularization)
    compute_uncertainty=False,       # Disable for batch (faster)
    n_bootstrap=0
)
```

### ENSO Classification Thresholds

```python
# Normalized Niño3.4 threshold
THRESHOLD_NORMALIZED = 0.5  # Standard deviations

# Niño3 precipitation threshold (Cai et al. 2014)
THRESHOLD_PR_MMDAY = 5.0   # mm/day
```

---

## Data Flow

```
Pangeo CMIP6 Cloud
    ↓ (intake-esm)
Raw CMIP6 Data (tas, pr)
    ↓ (preprocessing)
Interpolated & Detrended
    ↓ (GWL calculation)
Warming Index + GWL Bins
    ↓ (ENSO classification)
ENSO Events by GWL
    ↓ (scientific analysis)
Figures & Tables
    ↓ (insurance metrics)
Risk Metrics
```

---

## Dependencies

See `pyproject.toml` for complete list. Key dependencies:
- `xarray`, `pandas`, `numpy` - Data handling
- `intake-esm`, `gcsfs`, `zarr` - CMIP6 data access
- `scikit-learn` - Polynomial fitting (GWL)
- `matplotlib`, `seaborn` - Visualization
- `statsmodels`, `scipy` - Statistical analysis

---

## Troubleshooting

See `docs/BATCH_PROCESSING.md` for HPC-specific issues (SSL, memory, etc.)

---

## Future Enhancements

1. **CLIMADA Integration** (in progress)
   - Physical hazard modeling
   - Exposure-vulnerability-impact
   - Future projections with CLIMADA

2. **Additional Hazards**
   - Floods, droughts, wildfires

3. **Regional Analysis**
   - Region-specific teleconnections
   - Sub-national risk assessment

