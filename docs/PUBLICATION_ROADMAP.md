# Publication Roadmap: ENSO-Modulated TC Risk Assessment with Hybrid Physics-ML Approach

**Goal**: Achieve publication-quality results comparable to UQAM-TCW (Carozza et al., 2024) and Emanuel (2017), with novel ML bias correction and CMIP6 projections.

**Target Journals**:
- Primary: *Journal of Advances in Modeling Earth Systems (JAMES)*
- Alternative: *Climate Dynamics*, *Weather and Climate Extremes*

---

## Current Status Assessment

### ✅ **Completed Components**

1. **ENSO Classification System**
   - Event-based classification with Extreme El Niño detection
   - ONI-based (Niño3.4 with 3-month running mean)
   - Four categories: Extreme El Niño (ONI ≥ 2.0°C + Niño3 precip), Moderate El Niño, La Niña, Neutral
   - Implementation: `scripts/tc_intensity/postprocess_enso_tagging.py`
   - Status: **Production-ready**

2. **UQAM-TCW Full Pipeline**
   - All 5 components calibrated: frequency, cyclogenesis, trajectory, intensity, size/profile
   - Basin-specific calibrations (NA, EP, WP, NI, SI, SP)
   - Follows UQAM Appendix A & B methodology
   - Implementation: `src/tc_intensity/uqam/`
   - Status: **Production-ready**

3. **Hybrid FAST-ML Intensity Model**
   - FAST model (Emanuel 2017) as physics backbone
   - Gradient Boosting corrections for improved point-wise predictions
   - UQAM quantile matching post-processing for distribution matching
   - Basin and ENSO phase-specific calibrations
   - Implementation: `src/tc_intensity/ml/hybrid_fast_ml_model.py`
   - Status: **Production-ready, validated**

4. **Environmental Data Infrastructure**
   - ERA5 (0.25°): 29 pressure levels + surface variables
   - ORAS5 (ocean): regridded to ERA5 grid
   - IBTrACS: unified CSV format with ENSO tagging
   - Monthly data catalog for efficient access
   - Status: **Production-ready**

5. **Landfall Detection**
   - Bathymetry-based ocean-to-land transition detection
   - Implemented in multiple validation scripts
   - Implementation: `scripts/tc_intensity/analyze_landfalling_tcs_for_axa.py`
   - Status: **Production-ready**

6. **Hazard Mapping Framework**
   - Track density maps with ENSO stratification
   - Return period calculations (GEV and GPD fitting)
   - Direct and indirect hit definitions
   - Implementation: `scripts/tc_intensity/validate_hazard_maps.py`, `validate_track_density_maps.py`
   - Status: **Framework ready, needs large-scale generation**

7. **CMIP6 Integration**
   - Model selection based on ENSO representation quality
   - 186 model-variant combinations from 38 models
   - Cloud-based access (no downloads needed)
   - GWL calculation framework
   - Implementation: `notebooks/01_process_cmip6_enso.py`
   - Status: **Infrastructure ready, needs full processing**

### ⚠️ **Gaps to Address**

1. **Temporal Multi-Scale Validation**
   - Need systematic validation at hourly, daily, monthly, seasonal, annual, and interannual scales
   - Track consistency checks across timescales

2. **Large-Scale Synthetic Event Generation**
   - Need 1M years of synthetic tracks (UQAM standard) per ENSO phase
   - Currently have framework but not full-scale generation

3. **Comprehensive Hazard Maps**
   - Need Cat1+ and Cat4-5 hazard maps for all basins
   - Per ENSO phase stratification
   - Return periods: 10-yr, 50-yr, 100-yr, 250-yr

4. **CMIP6 Historical Validation**
   - Train hybrid model on CMIP6 historical era (1850-2014)
   - Validate ENSO-TC relationships in models vs observations

---

## Publication Roadmap: 6-Phase Plan

### **Phase 1: Validation & Consistency (Weeks 1-3)**

**Goal**: Ensure synthetic tracks are physically consistent across all temporal scales.

#### 1.1 Multi-Scale Temporal Validation

**Script to create**: `scripts/tc_intensity/validate_multiscale_temporal_consistency.py`

```python
"""
Validate synthetic tracks at multiple temporal scales:
1. Hourly (4-min timesteps): Intensity evolution smoothness
2. Daily: Track displacement consistency
3. Monthly: Seasonal cycle preservation
4. Seasonal: Basin-specific cyclone season timing
5. Annual: Frequency match to calibration
6. Interannual: ENSO signal preservation
"""
```

**Metrics**:
- Hourly: Max intensity change ≤ 10 m/s/hr (physical constraint)
- Daily: Translation speed 0-15 m/s (Landsea et al. 1993)
- Monthly: Match observed monthly distribution per basin
- Seasonal: Peak season timing ±1 month vs IBTrACS
- Annual: Frequency within calibrated Negative Binomial 95% CI
- Interannual: ENSO signal strength (rate ratios) match calibration

**Deliverable**: Validation report showing consistency at all scales

#### 1.2 UQAM Comparison Validation

**Script**: `scripts/tc_intensity/comprehensive_validation_uqam_style.py` (already exists)

**Add missing components**:
- Track density spatial correlation (Pearson r > 0.8 with IBTrACS)
- LMI distribution by ENSO phase (Chi-squared test, p > 0.05)
- Genesis location PDF comparison (2D KS test)
- Trajectory displacement correlation by latitude bin

**Deliverable**: Table comparing all metrics to UQAM Table 3, Section 4 results

#### 1.3 Physical Constraints Validation

**Script to create**: `scripts/tc_intensity/validate_physical_constraints.py`

```python
"""
Verify synthetic tracks obey physical constraints:
1. No storms form at latitude > 30° or < 5°
2. No storms intensify when Vp < 20 m/s
3. Intensity decay over land follows exponential (Kaplan & DeMaria 1995)
4. RMW scales with intensity (Willoughby et al. 2006)
5. Translation speed realistic for latitude
"""
```

**Deliverable**: Physical constraint violation report (should be < 1%)

---

### **Phase 2: Large-Scale Synthetic Generation (Weeks 4-6)**

**Goal**: Generate publication-quality 1M-year synthetic catalogs per basin and ENSO phase.

#### 2.1 Production-Scale Synthetic Track Generation

**Script to enhance**: `scripts/tc_intensity/generate_event_set.py`

**Parameters**:
- Duration: 1,000,000 years per ENSO phase per basin
- ENSO phases: 4 (Extreme El Niño, Moderate El Niño, La Niña, Neutral)
- Basins: 6 (NA, EP, WP, NI, SI, SP)
- Total storms: ~1-10 million tracks (varies by basin/phase)

**Computational requirements**:
- Estimated runtime: 2-5 hours per 10K years on HPC
- Total: ~600-1500 compute hours for all basins/phases
- Storage: ~100-500 GB for all tracks

**SLURM script to create**: `scripts/batch/generate_million_year_catalogs.sh`

```bash
#!/bin/bash
#SBATCH --job-name=synthetic_1M
#SBATCH --array=0-23  # 6 basins × 4 ENSO phases
#SBATCH --time=48:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4

# Generate 1M years for basin-ENSO combination
```

**Deliverable**: Complete synthetic catalogs for all basins and ENSO phases

#### 2.2 Hybrid Intensity Application

**Script**: `scripts/batch/apply_hybrid_intensity_all_synthetic.sh` (already exists)

**Apply to all 1M-year catalogs**:
- Use calibrated FAST parameters per basin
- Apply ML corrections
- Apply UQAM quantile matching per ENSO phase
- Add size/profile (RMW, wind radii)

**Deliverable**: Full synthetic catalogs with intensity, size, and wind profiles

---

### **Phase 3: Hazard Map Generation (Weeks 7-9)**

**Goal**: Create publication-quality hazard maps following UQAM Section 5 methodology.

#### 3.1 Landfall Identification

**Script to create**: `scripts/tc_intensity/identify_all_landfalls.py`

```python
"""
Process all synthetic tracks to identify:
1. Direct hits: Eye reaches land
2. Indirect hits: Wind radius reaches land (RMW + decay distance)
3. Landfall intensity (at coastline crossing)
4. Landfall location (lat, lon)
"""
```

**Grid resolution**: 2 km (UQAM standard) or 0.1° (~10 km)

**Deliverable**: Landfall database for all synthetic storms

#### 3.2 Hazard Map Calculation

**Script to enhance**: `scripts/tc_intensity/validate_hazard_maps.py`

**Create hazard maps for**:
- Categories: Cat1+ (≥33 m/s), Cat3+ (≥50 m/s), Cat4-5 (≥58 m/s)
- ENSO phases: All 4 phases + climatology (all phases combined)
- Basins: All 6 basins
- Metrics:
  - Annual hit rate (hits/year/grid cell)
  - Return periods: 10-yr, 50-yr, 100-yr, 250-yr
  - Intensity at landfall distributions

**SLURM script to create**: `scripts/batch/generate_hazard_maps_all_basins.sh`

**Deliverable**:
- Hazard maps (PNG and NetCDF format)
- Return period intensity maps
- CSV tables of hit rates by region

#### 3.3 Comparison to Literature

**Compare to**:
- **IBTrACS observations**: 1981-2020 landfall rates
- **STORM dataset** (Bloemendaal et al. 2020): Global synthetic tracks
- **GAR15** (UNDRR): Global risk assessment
- **UQAM**: North Atlantic and Western Pacific results (Section 5.1-5.2)

**Metrics**:
- Spatial correlation of landfall rates
- Return period intensity comparison
- ENSO modulation strength (El Niño / Neutral ratio)

**Deliverable**: Validation table and discussion

---

### **Phase 4: CMIP6 Historical Training (Weeks 10-13)**

**Goal**: Train hybrid model on CMIP6 historical era to establish bias correction methodology.

#### 4.1 CMIP6 Model Selection

**Use existing**: `data/cmip6/final_selection_r1r2_priority.csv`

**Priority models** (good ENSO representation):
1. **IPSL-CM6A-LR**: 10 variants, complete SSPs
2. **GISS-E2-1-G**: 10 variants, complete SSPs
3. **CNRM-CM6-1**: 6 variants, complete SSPs
4. **MIROC6**: 10 variants (3 complete SSPs)
5. **CanESM5**: 10 variants, complete SSPs
6. **MPI-ESM1-2-LR**: 10 variants, complete SSPs

**Start with**: 3-5 models, r1i1p1f1 variants only (~5 variants)

**Period**: 1850-2014 (CMIP6 historical)

#### 4.2 Environmental Variable Extraction from CMIP6

**Script to create**: `scripts/tc_intensity/extract_cmip6_environmental_vars.py`

```python
"""
Extract environmental variables from CMIP6 for synthetic TC tracks:
1. Use IBTrACS tracks (1981-2020) as template
2. Extract from CMIP6 instead of ERA5/ORAS5
3. Variables: SST, Vp, shear, MLD, thermal stratification
4. Monthly resolution (same as current workflow)
"""
```

**Key challenge**: CMIP6 has different vertical levels than ERA5
- Solution: Use model's native levels, interpolate to standard pressure levels

**Deliverable**: CMIP6-based training data for 5 models × 6 basins

#### 4.3 Hybrid Model Training on CMIP6

**Script to create**: `scripts/tc_intensity/train_hybrid_cmip6_bias_correction.py`

```python
"""
Train hybrid FAST-ML model on CMIP6 data:
1. Use CMIP6 environmental variables as input
2. Target: IBTrACS observed intensities (1981-2020)
3. Learn model-specific bias corrections
4. Separate calibrations per:
   - Model (IPSL, GISS, CNRM, MIROC, CanESM)
   - Basin (NA, EP, WP, NI, SI, SP)
   - ENSO phase (4 phases)
"""
```

**ML architecture**:
- Same Gradient Boosting as current implementation
- Features: CMIP6 environmental vars + FAST predictions + basin/temporal
- Target: Observed intensity bias (Observed - FAST_CMIP6)

**Deliverable**:
- Trained bias correction models for each CMIP6 model
- Validation metrics (R², RMSE, distribution matching)

#### 4.4 Historical Validation

**Compare**:
- CMIP6-driven synthetic tracks vs IBTrACS (1981-2020)
- Frequency by ENSO phase
- Spatial patterns (genesis, tracks, intensity)
- Intensity distributions per ENSO phase

**Deliverable**:
- Validation report showing CMIP6 historical matches observations
- Quantification of model biases before/after ML correction

---

### **Phase 5: CMIP6 Future Projections (Weeks 14-18)**

**Goal**: Generate future TC projections under different SSPs and GWLs.

#### 5.1 GWL-Based Projection Framework

**Use existing**: `src/cmip6/gwl_calculator.py`

**GWL bins**: 0.0°C (1850-1900), 1.0°C, 1.5°C, 2.0°C, 2.5°C, 3.0°C, 4.0°C

**SSPs**: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5

**For each GWL**:
- Calculate ENSO statistics (frequency, intensity of events)
- Extract environmental climatologies
- Generate synthetic TC tracks

#### 5.2 Future Synthetic Track Generation

**Script to create**: `scripts/tc_intensity/generate_cmip6_future_tracks.py`

```python
"""
Generate synthetic tracks for CMIP6 future scenarios:
1. For each GWL (1.5°C, 2.0°C, 3.0°C, 4.0°C)
2. For each ENSO phase
3. For each CMIP6 model (5 models)
4. Duration: 100,000 years per combination
5. Apply bias-corrected hybrid intensity model
"""
```

**Total combinations**: 4 GWLs × 4 ENSO phases × 5 models × 6 basins = 480 scenarios

**Computational**: ~2000-5000 compute hours

**SLURM script**: `scripts/batch/generate_cmip6_future_projections.sh`

**Deliverable**: Future synthetic track catalogs

#### 5.3 Future Hazard Map Generation

**Same methodology as Phase 3**, applied to future projections

**Output**:
- Hazard maps at each GWL
- Change maps (GWL X - GWL 0.0)
- ENSO modulation changes over GWLs

**Deliverable**: Future hazard maps and change projections

---

### **Phase 6: Manuscript Preparation (Weeks 19-24)**

**Goal**: Write and submit manuscript to JAMES.

#### 6.1 Manuscript Outline

**Title**: *ENSO-Modulated Tropical Cyclone Risk Under Global Warming: A Hybrid Physics-Machine Learning Approach with CMIP6 Projections*

**Sections**:

1. **Introduction**
   - TC risk and insurance/reinsurance applications
   - ENSO influence on TC activity
   - Need for future projections under climate change
   - Novelty: Hybrid physics-ML, Extreme El Niño, CMIP6 projections

2. **Data and Methods**
   - 2.1 Observational Data (IBTrACS, ERA5, ORAS5)
   - 2.2 ENSO Classification (including Extreme El Niño)
   - 2.3 CMIP6 Models and Selection Criteria
   - 2.4 UQAM-TCW Methodology (Frequency, Cyclogenesis, Trajectory, Size)
   - 2.5 Hybrid FAST-ML Intensity Model
   - 2.6 CMIP6 Bias Correction
   - 2.7 Synthetic Track Generation
   - 2.8 Hazard Map Calculation

3. **Validation**
   - 3.1 Multi-Scale Temporal Consistency
   - 3.2 Comparison to UQAM-TCW Benchmarks
   - 3.3 Landfall Rate Validation
   - 3.4 CMIP6 Historical Validation

4. **Results**
   - 4.1 Observed ENSO-TC Relationships (1981-2020)
   - 4.2 Hybrid Model Performance vs FAST alone
   - 4.3 Hazard Maps by ENSO Phase
   - 4.4 CMIP6 Historical Evaluation
   - 4.5 Future Projections at Different GWLs
     - Frequency changes
     - Intensity changes
     - Spatial pattern shifts
     - ENSO modulation changes

5. **Discussion**
   - 5.1 Value of Hybrid Physics-ML Approach
   - 5.2 Extreme El Niño Impacts
   - 5.3 Uncertainty Sources and Model Spread
   - 5.4 Implications for Risk Assessment
   - 5.5 Limitations

6. **Conclusions**

**Target length**: 8,000-10,000 words (JAMES typical)

#### 6.2 Key Figures (15-20 total)

**Figure proposals**:

1. **ENSO Classification Schematic**: 4 phases, criteria, time series example
2. **Methodology Flowchart**: Full pipeline from IBTrACS to hazard maps
3. **Multi-Scale Validation**: 6 panels showing hourly to interannual consistency
4. **Hybrid Model Performance**: Observed vs predicted, before/after ML correction
5. **Distribution Matching**: LMI distributions by ENSO phase, before/after quantile matching
6. **Track Density Maps - Observed**: IBTrACS 1981-2020, by ENSO phase (4 phases × 2 basins = 8 panels)
7. **Track Density Maps - Synthetic**: Same layout, show match to observations
8. **Cyclogenesis PDF Comparison**: Observed vs synthetic, all basins
9. **Landfall Rate Validation**: Observed vs synthetic, by region
10. **Hazard Maps - North Atlantic**: Cat1+ and Cat4-5, by ENSO phase (4 phases × 2 cats = 8 panels)
11. **Hazard Maps - Western Pacific**: Same layout
12. **Return Period Intensities**: 10-yr, 50-yr, 100-yr by ENSO phase
13. **CMIP6 Historical Validation**: Model spread, bias correction impact
14. **Future Frequency Changes**: By GWL and ENSO phase (multi-model mean ± spread)
15. **Future Intensity Changes**: Same layout
16. **Future Hazard Map Changes**: GWL 3.0°C - GWL 0.0°C, El Niño vs La Niña
17. **ENSO Modulation Changes**: How El Niño/Neutral ratio evolves with GWL
18. **Model Uncertainty**: Spread across CMIP6 models at each GWL

#### 6.3 Key Tables (8-10 total)

1. **CMIP6 Model Selection**: Models, variants, ENSO skill metrics
2. **ENSO Event Statistics**: Observed 1981-2020, frequency, intensity by phase
3. **Hybrid Model Calibration**: Parameters per basin and ENSO phase
4. **Validation Metrics Summary**: All basins, all metrics vs UQAM benchmarks
5. **Landfall Rate Comparison**: Observed vs synthetic, major coastal regions
6. **Return Period Intensities**: Current climate, by basin and ENSO phase
7. **CMIP6 Bias Correction Impact**: Metrics before/after ML correction
8. **Future Changes Summary**: Frequency and intensity % change at GWL 2.0°C and 3.0°C
9. **ENSO Modulation Changes**: Rate ratios (El Niño/Neutral) by GWL
10. **Uncertainty Quantification**: Model spread (5th-95th percentile) for key metrics

#### 6.4 Supplementary Material

**Supplementary Figures** (~20-30):
- All basins not shown in main text
- Additional ENSO phases
- Sensitivity analyses
- Detailed validation plots
- All CMIP6 models individually

**Supplementary Tables** (~10-15):
- Complete calibration parameters
- Full validation statistics
- Regional landfall rates
- Detailed future projections

**Supplementary Data**:
- Synthetic track catalogs (Zenodo repository)
- Hazard maps (NetCDF files)
- Code repository (GitHub)

#### 6.5 Code and Data Availability

**GitHub Repository** (already exists): `enso_finance/`
- Clean up repository structure
- Add comprehensive README
- Document all scripts
- Create reproducibility guide

**Zenodo Archive**:
- Synthetic track catalogs (compressed)
- Hazard maps (NetCDF)
- Calibration results (JSON)
- Figures (high-res PNG/PDF)

**DOI**: Obtain Zenodo DOI before submission

---

## Computational Resources Required

### Storage Requirements

- **Synthetic Tracks**: ~500 GB (1M years × 6 basins × 4 phases)
- **CMIP6 Projections**: ~200 GB (100K years × 480 scenarios)
- **Hazard Maps**: ~50 GB (NetCDF grids)
- **Environmental Data**: ~1 TB (already exists)
- **Total**: ~1.75 TB

### Compute Requirements

- **Phase 2 (Synthetic Generation)**: 600-1500 hours
- **Phase 3 (Hazard Maps)**: 200-400 hours
- **Phase 4 (CMIP6 Training)**: 100-200 hours
- **Phase 5 (CMIP6 Projections)**: 2000-5000 hours
- **Total**: ~3000-7000 compute hours (~125-290 days on single core, ~1-3 weeks on HPC with 100 cores)

### HPC Batch Job Strategy

Use SLURM array jobs for parallelization:
```bash
# Example: 24 simultaneous jobs (6 basins × 4 ENSO phases)
#SBATCH --array=0-23
#SBATCH --time=48:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
```

---

## Success Criteria for Publication

### Scientific Quality
- [ ] Multi-scale validation shows consistency across all temporal scales
- [ ] Spatial correlation with IBTrACS > 0.8 for track density
- [ ] LMI distribution matching: Chi-squared p-value > 0.05
- [ ] Landfall rate validation within ±20% of observations
- [ ] CMIP6 historical validation demonstrates bias correction effectiveness

### Novelty Claims
- [ ] First hybrid physics-ML tropical cyclone model with FAST backbone
- [ ] First systematic assessment of Extreme El Niño impacts on TC hazard
- [ ] First CMIP6-based TC projections with ENSO phase stratification
- [ ] Improved upon UQAM-TCW with ML corrections while maintaining physical consistency

### Reproducibility
- [ ] All code openly available on GitHub
- [ ] All synthetic tracks archived on Zenodo with DOI
- [ ] Complete documentation enables reproduction
- [ ] SLURM scripts provided for HPC workflow

### Comparison to Benchmarks
- [ ] Match or exceed UQAM-TCW validation metrics (Table 3)
- [ ] Show improvement over FAST alone (R² increase)
- [ ] Comparable to STORM dataset for global coverage
- [ ] Consistent with Emanuel's risk assessment findings

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1**: Validation & Consistency | Weeks 1-3 | Multi-scale validation report, UQAM comparison table |
| **Phase 2**: Large-Scale Synthetic Generation | Weeks 4-6 | 1M-year catalogs for all basins/phases |
| **Phase 3**: Hazard Map Generation | Weeks 7-9 | Hazard maps, return periods, landfall rates |
| **Phase 4**: CMIP6 Historical Training | Weeks 10-13 | Bias correction models, historical validation |
| **Phase 5**: CMIP6 Future Projections | Weeks 14-18 | Future catalogs, projection hazard maps |
| **Phase 6**: Manuscript Preparation | Weeks 19-24 | Complete manuscript, submission to JAMES |

**Total Duration**: 6 months (24 weeks)

---

## Risk Mitigation

### Potential Issues and Solutions

1. **Computational bottleneck**
   - **Risk**: Phase 5 takes longer than expected
   - **Mitigation**: Start with 3 models instead of 5, reduce to 50K years instead of 100K
   - **Fallback**: Focus on SSP2-4.5 and SSP5-8.5 only

2. **CMIP6 bias too large**
   - **Risk**: ML cannot adequately correct CMIP6 biases
   - **Mitigation**: Use pseudo-global-warming approach (observed tracks + CMIP6 deltas)
   - **Fallback**: Focus on GWL-based climatologies rather than full synthetic tracks

3. **Validation doesn't match UQAM**
   - **Risk**: Results don't meet publication standards
   - **Mitigation**: Iterative refinement of calibrations, leverage UQAM team expertise
   - **Fallback**: Position as "North Atlantic-focused" study, expand later

4. **Review requests major revisions**
   - **Risk**: 6-month delay for revisions
   - **Mitigation**: Pre-submission to arXiv, solicit informal feedback from UQAM team
   - **Fallback**: Target lower-tier journal if major methodological concerns

---

## Next Immediate Steps (This Week)

1. **Create multi-scale validation script** (Phase 1.1)
   - Script: `scripts/tc_intensity/validate_multiscale_temporal_consistency.py`
   - Run on existing synthetic tracks from NA basin

2. **Test 10K-year generation** (Phase 2 preparation)
   - Use existing `generate_event_set.py`
   - Verify runtime and resource usage
   - Extrapolate to 1M years

3. **Create hazard map prototype** (Phase 3 preparation)
   - Use existing NA synthetic tracks
   - Generate Cat1+ hazard map for El Niño vs La Niña
   - Verify methodology

4. **Review CMIP6 model list** (Phase 4 preparation)
   - Confirm access to all 5 priority models
   - Test extraction of single month from IPSL-CM6A-LR

5. **Draft manuscript outline** (Phase 6 preparation)
   - Expand outline above into full section structure
   - Identify placeholder text for methods (can write now)

---

## Key References for Manuscript

**Methodology**:
- Carozza et al. (2024) - UQAM-TCW model
- Emanuel (2017) - FAST model
- Bister & Emanuel (2002) - Potential Intensity
- Willoughby et al. (2006) - Wind profiles

**ENSO**:
- Cai et al. (2014) - Extreme El Niño definition
- Camargo & Sobel (2005) - ENSO-TC relationships
- Bove et al. (1998) - JMA index

**Validation**:
- Bloemendaal et al. (2020) - STORM dataset
- Knapp et al. (2010) - IBTrACS
- Hersbach et al. (2020) - ERA5

**CMIP6**:
- Eyring et al. (2016) - CMIP6 overview
- O'Neill et al. (2016) - SSP scenarios
- Planton et al. (2021) - ENSO metrics for CMIP6

**Machine Learning**:
- Friedman (2001) - Gradient Boosting
- Giffard-Roisin et al. (2020) - TC ML review

---

## Contact and Collaboration

**Potential collaborators to reach out to**:
- David Carozza (UQAM) - UQAM-TCW methodology questions
- Kerry Emanuel (MIT) - FAST model interpretation
- Nadia Bloemendaal (VU Amsterdam) - STORM dataset comparison
- Wenchang Yang (Princeton) - CMIP6 ENSO expertise

**When to reach out**: After Phase 1 validation is complete, before Phase 4 CMIP6 work

---

**End of Roadmap**

This roadmap provides a clear, actionable path to a high-quality publication. The 6-month timeline is ambitious but achievable with dedicated HPC resources. The modular approach allows for flexibility if certain phases take longer than expected.
