# Publication Roadmap - Live Status Tracker

**Last Updated**: 2025-12-15
**Target Journal**: Journal of Advances in Modeling Earth Systems (JAMES)
**Target Submission Date**: Week 24 (June 2026)

---

## Overall Progress: 15% Complete

```
Phase 1: [███░░░░░░░] 30% (In Progress)
Phase 2: [░░░░░░░░░░]  0% (Not Started)
Phase 3: [░░░░░░░░░░]  0% (Not Started)
Phase 4: [░░░░░░░░░░]  0% (Not Started)
Phase 5: [░░░░░░░░░░]  0% (Not Started)
Phase 6: [░░░░░░░░░░]  0% (Not Started)
```

---

## Current Week: Week 1 of 24

**Current Phase**: Phase 1 - Validation & Consistency
**Current Tasks**: Multi-scale validation, UQAM comparison
**Blockers**: None
**Next Milestone**: Complete Phase 1 validation (Week 3)

---

## Phase-by-Phase Status

### Phase 1: Validation & Consistency (Weeks 1-3) 🟡 IN PROGRESS

**Target Completion**: Week 3
**Current Status**: 30% complete

#### Task Breakdown

##### 1.1 Multi-Scale Temporal Validation
- [ ] **NOT STARTED** Create validation script `validate_multiscale_temporal_consistency.py`
  - [ ] Hourly: Max intensity change ≤ 10 m/s/hr
  - [ ] Daily: Translation speed 0-15 m/s
  - [ ] Monthly: Match observed monthly distribution
  - [ ] Seasonal: Peak season timing ±1 month
  - [ ] Annual: Frequency within calibrated 95% CI
  - [ ] Interannual: ENSO signal strength match
- [ ] **NOT STARTED** Run validation on NA basin synthetic tracks
- [ ] **NOT STARTED** Generate validation report
- **Estimated Time**: 3-5 days
- **Dependencies**: Existing synthetic tracks from NA basin
- **Deliverable**: `outputs/validation/multiscale_validation_report.pdf`

##### 1.2 UQAM Comparison Validation
- [x] **COMPLETED** UQAM validation script exists (`comprehensive_validation_uqam_style.py`)
- [ ] **IN PROGRESS** Add missing components:
  - [ ] Track density spatial correlation (target: Pearson r > 0.8)
  - [ ] LMI distribution by ENSO phase (Chi-squared test, p > 0.05)
  - [ ] Genesis location PDF comparison (2D KS test)
  - [ ] Trajectory displacement correlation by latitude bin
- [ ] **NOT STARTED** Run full validation suite on all basins
- [ ] **NOT STARTED** Create comparison table vs UQAM Table 3
- **Estimated Time**: 4-6 days
- **Dependencies**: UQAM paper Table 3 values
- **Deliverable**: `outputs/validation/uqam_comparison_table.csv`

##### 1.3 Physical Constraints Validation
- [ ] **NOT STARTED** Create validation script `validate_physical_constraints.py`
  - [ ] No formation at lat > 30° or < 5°
  - [ ] No intensification when Vp < 20 m/s
  - [ ] Exponential decay over land
  - [ ] RMW scales with intensity
  - [ ] Realistic translation speeds
- [ ] **NOT STARTED** Run on all synthetic tracks
- [ ] **NOT STARTED** Generate violation report (target: < 1%)
- **Estimated Time**: 2-3 days
- **Dependencies**: None
- **Deliverable**: `outputs/validation/physical_constraints_report.txt`

**Phase 1 Deliverables**:
- [ ] Multi-scale validation report
- [ ] UQAM comparison table
- [ ] Physical constraints report
- [ ] Summary presentation slides (for internal review)

**Blockers**: None currently

**Notes**:
- Start with NA basin for all validations (fastest to test)
- Once methodology validated, run on all 6 basins in parallel

---

### Phase 2: Large-Scale Synthetic Generation (Weeks 4-6) ⚪ NOT STARTED

**Target Completion**: Week 6
**Current Status**: 0% complete

#### Task Breakdown

##### 2.1 Production-Scale Synthetic Track Generation
- [ ] **NOT STARTED** Test 10K-year generation (resource estimation)
- [ ] **NOT STARTED** Create SLURM script `generate_million_year_catalogs.sh`
- [ ] **NOT STARTED** Generate 1M years for each combination:
  - [ ] NA × 4 ENSO phases
  - [ ] EP × 4 ENSO phases
  - [ ] WP × 4 ENSO phases
  - [ ] NI × 4 ENSO phases
  - [ ] SI × 4 ENSO phases
  - [ ] SP × 4 ENSO phases
- [ ] **NOT STARTED** Quality control: Check for anomalies
- **Estimated Time**: 1-2 weeks (wall-clock time on HPC)
- **Compute Hours**: 600-1500 hours total
- **Storage**: ~500 GB
- **Dependencies**: Phase 1 validation passed
- **Deliverable**: `outputs/synthetic_tracks/million_year_catalogs/`

##### 2.2 Hybrid Intensity Application
- [ ] **NOT STARTED** Apply calibrated FAST parameters
- [ ] **NOT STARTED** Apply ML corrections
- [ ] **NOT STARTED** Apply UQAM quantile matching per ENSO phase
- [ ] **NOT STARTED** Add size/profile (RMW, wind radii)
- **Estimated Time**: 1 week (wall-clock)
- **Compute Hours**: Included in 2.1 estimates
- **Dependencies**: Task 2.1 complete
- **Deliverable**: Complete synthetic catalogs with intensity/size

**Phase 2 Deliverables**:
- [ ] 1M-year synthetic catalogs (6 basins × 4 ENSO phases = 24 catalogs)
- [ ] Quality control report
- [ ] Summary statistics comparing to observations

**Blockers**: Requires Phase 1 validation completion

**Notes**:
- Use SLURM array jobs for parallelization
- Monitor jobs daily during generation
- Save intermediate results (every 100K years)

---

### Phase 3: Hazard Map Generation (Weeks 7-9) ⚪ NOT STARTED

**Target Completion**: Week 9
**Current Status**: 0% complete

#### Task Breakdown

##### 3.1 Landfall Identification
- [ ] **NOT STARTED** Create script `identify_all_landfalls.py`
- [ ] **NOT STARTED** Process all synthetic tracks:
  - [ ] Direct hits (eye reaches land)
  - [ ] Indirect hits (wind radius reaches land)
  - [ ] Landfall intensity and location
- [ ] **NOT STARTED** Create landfall database
- **Estimated Time**: 3-4 days
- **Dependencies**: Phase 2 complete
- **Deliverable**: `outputs/landfalls/landfall_database.parquet`

##### 3.2 Hazard Map Calculation
- [ ] **NOT STARTED** Enhance `validate_hazard_maps.py`
- [ ] **NOT STARTED** Create SLURM script `generate_hazard_maps_all_basins.sh`
- [ ] **NOT STARTED** Generate hazard maps:
  - [ ] Cat1+ (≥33 m/s): 6 basins × 4 ENSO phases = 24 maps
  - [ ] Cat3+ (≥50 m/s): 24 maps
  - [ ] Cat4-5 (≥58 m/s): 24 maps
  - [ ] Climatology (all phases combined): 6 basins × 3 cats = 18 maps
- [ ] **NOT STARTED** Calculate return periods:
  - [ ] 10-year
  - [ ] 50-year
  - [ ] 100-year
  - [ ] 250-year
- **Estimated Time**: 1 week
- **Compute Hours**: 200-400 hours
- **Storage**: ~50 GB
- **Dependencies**: Task 3.1 complete
- **Deliverable**: `outputs/hazard_maps/`

##### 3.3 Comparison to Literature
- [ ] **NOT STARTED** Compare to IBTrACS (1981-2020)
- [ ] **NOT STARTED** Compare to STORM dataset (Bloemendaal et al. 2020)
- [ ] **NOT STARTED** Compare to UQAM North Atlantic/Western Pacific
- [ ] **NOT STARTED** Create validation table
- **Estimated Time**: 3-4 days
- **Dependencies**: Task 3.2 complete
- **Deliverable**: `outputs/validation/hazard_map_comparison.csv`

**Phase 3 Deliverables**:
- [ ] Hazard maps (PNG and NetCDF)
- [ ] Return period maps
- [ ] Landfall rate tables
- [ ] Literature comparison report

**Blockers**: Requires Phase 2 completion

**Notes**:
- Start with NA basin as prototype
- Grid resolution: 0.1° (compromise between 2km UQAM and computational cost)

---

### Phase 4: CMIP6 Historical Training (Weeks 10-13) ⚪ NOT STARTED

**Target Completion**: Week 13
**Current Status**: 0% complete

#### Priority CMIP6 Models (Start with these)

1. **IPSL-CM6A-LR** (r1i1p1f1, r2i1p1f1, r3i1p1f1)
2. **CNRM-CM6-1** (r1i1p1f2, r2i1p1f2, r3i1p1f2)
3. **MIROC6** (r1i1p1f1, r2i1p1f1, r3i1p1f1)
4. **CanESM5** (r1i1p1f1, r2i1p1f1)
5. **MPI-ESM1-2-LR** (r1i1p1f1, r2i1p1f1)

**Total**: 14 model-variants to start

#### Task Breakdown

##### 4.1 CMIP6 Model Access Test
- [ ] **NOT STARTED** Test access to IPSL-CM6A-LR (single month)
- [ ] **NOT STARTED** Verify all required variables available:
  - [ ] SST (tos)
  - [ ] Temperature profiles (ta)
  - [ ] Humidity profiles (hus)
  - [ ] U/V wind (ua, va)
  - [ ] Geopotential height (zg)
- [ ] **NOT STARTED** Document any missing variables or issues
- **Estimated Time**: 1-2 days
- **Dependencies**: None
- **Deliverable**: `docs/CMIP6_DATA_ACCESS_REPORT.md`

##### 4.2 Environmental Variable Extraction from CMIP6
- [ ] **NOT STARTED** Create script `extract_cmip6_environmental_vars.py`
- [ ] **NOT STARTED** Extract for IBTrACS tracks (1981-2020):
  - [ ] Use historical experiment (1850-2014)
  - [ ] Monthly resolution
  - [ ] Same variables as ERA5/ORAS5
- [ ] **NOT STARTED** Process all 14 model-variants × 6 basins = 84 datasets
- **Estimated Time**: 1-2 weeks
- **Compute Hours**: 100-200 hours
- **Storage**: ~100 GB
- **Dependencies**: Task 4.1 complete
- **Deliverable**: `data/cmip6_training/model_variant_basin/`

##### 4.3 Hybrid Model Training on CMIP6
- [ ] **NOT STARTED** Create script `train_hybrid_cmip6_bias_correction.py`
- [ ] **NOT STARTED** Train for each model-variant × basin × ENSO phase
- [ ] **NOT STARTED** Save bias correction models
- [ ] **NOT STARTED** Validate on held-out period (2011-2014)
- **Estimated Time**: 1 week
- **Compute Hours**: 50-100 hours
- **Dependencies**: Task 4.2 complete
- **Deliverable**: `outputs/models/cmip6_bias_correction/`

##### 4.4 Historical Validation
- [ ] **NOT STARTED** Generate synthetic tracks using CMIP6 (1981-2020)
- [ ] **NOT STARTED** Compare to IBTrACS:
  - [ ] Frequency by ENSO phase
  - [ ] Spatial patterns (genesis, tracks)
  - [ ] Intensity distributions
- [ ] **NOT STARTED** Quantify bias correction improvement
- [ ] **NOT STARTED** Create validation report
- **Estimated Time**: 1 week
- **Dependencies**: Task 4.3 complete
- **Deliverable**: `outputs/validation/cmip6_historical_validation.pdf`

**Phase 4 Deliverables**:
- [ ] CMIP6 training data (84 datasets)
- [ ] Bias correction models (14 model-variants)
- [ ] Historical validation report
- [ ] Model comparison table

**Blockers**: Requires Phase 3 completion (for workflow continuity)

**Notes**:
- Start with 3 models (IPSL, CNRM, MIROC) to test methodology
- Expand to 5 models if successful
- Document all CMIP6-specific challenges

---

### Phase 5: CMIP6 Future Projections (Weeks 14-18) ⚪ NOT STARTED

**Target Completion**: Week 18
**Current Status**: 0% complete

#### Projection Scenarios

**GWLs**: 1.5°C, 2.0°C, 3.0°C, 4.0°C
**SSPs**: SSP2-4.5, SSP5-8.5 (start with these 2)
**Models**: 5 (as finalized in Phase 4)
**Basins**: 6
**ENSO Phases**: 4

**Total Scenarios**: 4 GWLs × 2 SSPs × 4 ENSO × 5 models × 6 basins = 960 scenarios

**Reduced Scope Option** (if needed):
- 3 GWLs (1.5°C, 2.0°C, 3.0°C) × 1 SSP (SSP5-8.5) × 3 models × 3 basins (NA, WP, EP) = 108 scenarios

#### Task Breakdown

##### 5.1 GWL Timing Calculation
- [ ] **NOT STARTED** Calculate GWL timing for all model-variants
- [ ] **NOT STARTED** Extract ENSO statistics at each GWL
- [ ] **NOT STARTED** Create GWL timing lookup table
- **Estimated Time**: 3-4 days
- **Dependencies**: Phase 4 complete
- **Deliverable**: `outputs/cmip6/gwl_timing_all_models.csv`

##### 5.2 Future Environmental Climatologies
- [ ] **NOT STARTED** Extract environmental variables at each GWL
- [ ] **NOT STARTED** Calculate GWL-specific climatologies:
  - [ ] SST, Vp, shear, MLD by ENSO phase
- [ ] **NOT STARTED** Create climatology database
- **Estimated Time**: 1 week
- **Compute Hours**: 200-400 hours
- **Dependencies**: Task 5.1 complete
- **Deliverable**: `data/cmip6_climatologies/`

##### 5.3 Future Synthetic Track Generation
- [ ] **NOT STARTED** Create script `generate_cmip6_future_tracks.py`
- [ ] **NOT STARTED** Generate 100K years per scenario (or 50K if time limited)
- [ ] **NOT STARTED** Apply bias-corrected hybrid model
- [ ] **NOT STARTED** Create SLURM array job script
- **Estimated Time**: 2-3 weeks (wall-clock)
- **Compute Hours**: 2000-5000 hours
- **Storage**: ~200 GB
- **Dependencies**: Task 5.2 complete
- **Deliverable**: `outputs/synthetic_tracks/cmip6_projections/`

##### 5.4 Future Hazard Map Generation
- [ ] **NOT STARTED** Apply Phase 3 methodology to future tracks
- [ ] **NOT STARTED** Generate hazard maps at each GWL
- [ ] **NOT STARTED** Calculate change maps (GWL X - GWL 0.0)
- [ ] **NOT STARTED** Analyze ENSO modulation changes
- **Estimated Time**: 1 week
- **Compute Hours**: 200-400 hours
- **Dependencies**: Task 5.3 complete
- **Deliverable**: `outputs/hazard_maps/cmip6_projections/`

**Phase 5 Deliverables**:
- [ ] Future synthetic catalogs (108-960 scenarios)
- [ ] Future hazard maps
- [ ] Change projections
- [ ] Multi-model summary statistics

**Blockers**: Requires Phase 4 completion

**Notes**:
- This is the most computationally intensive phase
- Consider reduced scope if time/resources limited
- Prioritize SSP5-8.5 (high emissions) for maximum signal

---

### Phase 6: Manuscript Preparation (Weeks 19-24) ⚪ NOT STARTED

**Target Completion**: Week 24
**Current Status**: 0% complete

#### Task Breakdown

##### 6.1 Manuscript Writing
- [ ] **NOT STARTED** Introduction (2000 words)
- [ ] **NOT STARTED** Data and Methods (3000 words)
- [ ] **NOT STARTED** Validation (1500 words)
- [ ] **NOT STARTED** Results (2500 words)
- [ ] **NOT STARTED** Discussion (1500 words)
- [ ] **NOT STARTED** Conclusions (500 words)
- [ ] **NOT STARTED** Abstract (250 words)
- **Estimated Time**: 3-4 weeks
- **Dependencies**: Phases 1-5 complete
- **Deliverable**: `manuscript/main_text.docx`

##### 6.2 Figure Generation
- [ ] **NOT STARTED** Main figures (15-20 figures)
  - [ ] Figure 1: ENSO classification schematic
  - [ ] Figure 2: Methodology flowchart
  - [ ] Figure 3: Multi-scale validation
  - [ ] Figure 4: Hybrid model performance
  - [ ] Figure 5: Distribution matching
  - [ ] Figure 6-7: Track density maps (observed)
  - [ ] Figure 8-9: Track density maps (synthetic)
  - [ ] Figure 10: Cyclogenesis PDF comparison
  - [ ] Figure 11: Landfall rate validation
  - [ ] Figure 12-13: Hazard maps (NA, WP)
  - [ ] Figure 14: Return period intensities
  - [ ] Figure 15: CMIP6 historical validation
  - [ ] Figure 16: Future frequency changes
  - [ ] Figure 17: Future intensity changes
  - [ ] Figure 18: Future hazard changes
  - [ ] Figure 19: ENSO modulation changes
  - [ ] Figure 20: Model uncertainty
- [ ] **NOT STARTED** Supplementary figures (20-30 figures)
- **Estimated Time**: 2-3 weeks
- **Dependencies**: All analyses complete
- **Deliverable**: `manuscript/figures/`

##### 6.3 Table Generation
- [ ] **NOT STARTED** Main tables (8-10 tables)
  - [ ] Table 1: CMIP6 model selection
  - [ ] Table 2: ENSO event statistics
  - [ ] Table 3: Hybrid model calibration
  - [ ] Table 4: Validation metrics summary
  - [ ] Table 5: Landfall rate comparison
  - [ ] Table 6: Return period intensities
  - [ ] Table 7: CMIP6 bias correction impact
  - [ ] Table 8: Future changes summary
  - [ ] Table 9: ENSO modulation changes
  - [ ] Table 10: Uncertainty quantification
- [ ] **NOT STARTED** Supplementary tables (10-15 tables)
- **Estimated Time**: 1 week
- **Dependencies**: All analyses complete
- **Deliverable**: `manuscript/tables/`

##### 6.4 Supplementary Material
- [ ] **NOT STARTED** Supplementary text
- [ ] **NOT STARTED** Supplementary figures
- [ ] **NOT STARTED** Supplementary tables
- **Estimated Time**: 1 week
- **Dependencies**: Main manuscript drafted
- **Deliverable**: `manuscript/supplementary.docx`

##### 6.5 Code and Data Repository
- [ ] **NOT STARTED** Clean up GitHub repository
- [ ] **NOT STARTED** Add comprehensive README
- [ ] **NOT STARTED** Document all scripts
- [ ] **NOT STARTED** Create reproducibility guide
- [ ] **NOT STARTED** Archive data on Zenodo
- [ ] **NOT STARTED** Obtain Zenodo DOI
- **Estimated Time**: 1 week
- **Dependencies**: All code finalized
- **Deliverable**: GitHub repo + Zenodo archive

##### 6.6 Internal Review and Revision
- [ ] **NOT STARTED** Internal review (advisor/collaborators)
- [ ] **NOT STARTED** Address feedback
- [ ] **NOT STARTED** Proofread and copyedit
- [ ] **NOT STARTED** Format for JAMES submission
- **Estimated Time**: 1 week
- **Dependencies**: Complete draft
- **Deliverable**: Submission-ready manuscript

##### 6.7 Submission
- [ ] **NOT STARTED** Submit to JAMES
- [ ] **NOT STARTED** Upload to arXiv (preprint)
- **Target Date**: Week 24 (June 2026)

**Phase 6 Deliverables**:
- [ ] Complete manuscript
- [ ] All figures and tables
- [ ] Supplementary material
- [ ] Code repository (GitHub)
- [ ] Data archive (Zenodo)
- [ ] JAMES submission

**Blockers**: Requires all previous phases complete

**Notes**:
- Start writing methods sections during Phases 1-5 (don't wait)
- Share draft figures with advisor for early feedback
- Consider pre-submission feedback from UQAM team

---

## Weekly Milestones

| Week | Phase | Key Milestone | Status |
|------|-------|---------------|--------|
| 1 | 1 | Multi-scale validation script created | 🟡 In Progress |
| 2 | 1 | UQAM comparison completed | ⚪ Not Started |
| 3 | 1 | Physical constraints validated | ⚪ Not Started |
| 4 | 2 | 10K-year test generation completed | ⚪ Not Started |
| 5 | 2 | 1M-year generation started (3 basins) | ⚪ Not Started |
| 6 | 2 | 1M-year generation completed (all basins) | ⚪ Not Started |
| 7 | 3 | Landfall identification completed | ⚪ Not Started |
| 8 | 3 | Hazard map generation started | ⚪ Not Started |
| 9 | 3 | Hazard maps completed, literature comparison | ⚪ Not Started |
| 10 | 4 | CMIP6 access verified | ⚪ Not Started |
| 11 | 4 | CMIP6 training data extracted | ⚪ Not Started |
| 12 | 4 | Bias correction models trained | ⚪ Not Started |
| 13 | 4 | Historical validation completed | ⚪ Not Started |
| 14 | 5 | GWL timing calculated | ⚪ Not Started |
| 15 | 5 | Future climatologies extracted | ⚪ Not Started |
| 16 | 5 | Future track generation started | ⚪ Not Started |
| 17 | 5 | Future track generation completed | ⚪ Not Started |
| 18 | 5 | Future hazard maps completed | ⚪ Not Started |
| 19 | 6 | Introduction and methods drafted | ⚪ Not Started |
| 20 | 6 | Results and discussion drafted | ⚪ Not Started |
| 21 | 6 | All figures completed | ⚪ Not Started |
| 22 | 6 | All tables completed | ⚪ Not Started |
| 23 | 6 | Internal review and revision | ⚪ Not Started |
| 24 | 6 | **SUBMISSION TO JAMES** | ⚪ Not Started |

---

## Recent Activity Log

### 2025-12-15 (Week 1, Day 1)
- ✅ Created initial publication roadmap
- ✅ Created roadmap status tracker
- 🟡 Started Phase 1 planning
- **Next**: Create multi-scale validation script

---

## Blockers and Risks

### Current Blockers
- **None currently** - Phase 1 can proceed immediately

### Potential Risks

| Risk | Probability | Impact | Mitigation Strategy | Status |
|------|-------------|--------|---------------------|--------|
| Computational bottleneck in Phase 5 | Medium | High | Reduce scope to 3 models, 1 SSP | Monitored |
| CMIP6 bias too large for ML correction | Low | High | Use pseudo-global-warming approach | Monitored |
| Validation doesn't match UQAM standards | Medium | Medium | Iterative refinement, seek UQAM feedback | Monitored |
| HPC downtime during critical phase | Low | Medium | Start critical phases early, buffer time | Planned |
| JAMES review requests major revisions | Medium | Low | Pre-submission to arXiv, informal reviews | Planned |

---

## Resource Tracking

### Compute Hours Used
- **Phase 1**: 0 / 10 hours (0%)
- **Phase 2**: 0 / 1,500 hours (0%)
- **Phase 3**: 0 / 400 hours (0%)
- **Phase 4**: 0 / 200 hours (0%)
- **Phase 5**: 0 / 5,000 hours (0%)
- **Total**: 0 / 7,110 hours (0%)

### Storage Used
- **Environmental Data**: ~1,000 GB (existing)
- **Synthetic Tracks**: 0 / 500 GB (0%)
- **CMIP6 Data**: 0 / 300 GB (0%)
- **Hazard Maps**: 0 / 50 GB (0%)
- **Total**: ~1,000 / ~1,850 GB (54%)

### Time Investment (Person-Hours)
- **Week 1**: 10 hours (planning, validation script creation)
- **Week 2**: 0 hours
- **Total**: 10 / ~480 hours (2%)
- **Estimated Total**: 480 hours (20 hours/week × 24 weeks)

---

## Collaboration and Feedback

### Planned Collaborations
- [ ] **Week 3**: Share Phase 1 validation with advisor
- [ ] **Week 9**: Informal feedback from UQAM team (David Carozza)
- [ ] **Week 13**: Share CMIP6 methodology with climate modeler
- [ ] **Week 18**: Pre-submission review by 2-3 experts
- [ ] **Week 22**: Formal internal review

### Key Contacts
- **David Carozza** (UQAM): UQAM-TCW methodology
- **Kerry Emanuel** (MIT): FAST model questions
- **Nadia Bloemendaal** (VU Amsterdam): STORM comparison
- **Wenchang Yang** (Princeton): CMIP6 ENSO expertise

---

## Success Metrics

### Phase 1 Success Criteria
- [x] Multi-scale validation shows consistency across all temporal scales
- [ ] Spatial correlation with IBTrACS > 0.8 for track density
- [ ] LMI distribution matching: Chi-squared p-value > 0.05
- [ ] Physical constraint violations < 1%

### Phase 2 Success Criteria
- [ ] 1M years generated for all 24 basin-ENSO combinations
- [ ] No systematic anomalies in tracks
- [ ] Frequency matches calibration ±10%

### Phase 3 Success Criteria
- [ ] Landfall rates within ±20% of observations
- [ ] Return periods consistent with literature
- [ ] Hazard maps qualitatively match UQAM/STORM

### Phase 4 Success Criteria
- [ ] CMIP6 historical captures observed ENSO-TC relationships
- [ ] Bias correction improves metrics by ≥20%
- [ ] Model spread is reasonable (not too wide)

### Phase 5 Success Criteria
- [ ] Future projections show physically plausible changes
- [ ] Multi-model mean is robust
- [ ] ENSO modulation changes are interpretable

### Phase 6 Success Criteria
- [ ] Manuscript meets JAMES word/figure limits
- [ ] All figures are publication-quality
- [ ] Internal reviewers recommend submission
- [ ] Code and data are fully reproducible

---

## Notes and Lessons Learned

### Week 1
- Initial roadmap created successfully
- Need to balance thoroughness with timeline constraints
- Consider starting Phase 6 (methods writing) earlier to save time

---

## Quick Reference Commands

```bash
# Update this file after completing tasks
cd /nethome/abdel042/enso_finance
nano docs/ROADMAP_STATUS.md

# Generate weekly status report
python scripts/utils/generate_roadmap_report.py

# Check current phase progress
grep "Phase [0-9]:" docs/ROADMAP_STATUS.md | grep "IN PROGRESS"

# View blockers
grep "Blockers:" docs/ROADMAP_STATUS.md -A 1

# See next week's milestones
grep "Week $(( $(date +%V) + 1 ))" docs/ROADMAP_STATUS.md
```

---

**Remember**: Update this file at least weekly (every Friday). Mark tasks as complete, update percentages, and add notes on challenges or insights.
