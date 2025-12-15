# Publication Roadmap - Executive Summary

**Created**: 2025-12-15
**Target Journal**: Journal of Advances in Modeling Earth Systems (JAMES)
**Timeline**: 24 weeks (6 months)
**Current Status**: 15% complete (Week 1)

---

## What We're Building

**A publication-quality hybrid physics-ML tropical cyclone risk assessment system with:**

1. **Novel ML-enhanced FAST model** - First hybrid approach improving on Emanuel (2017)
2. **Extreme El Niño impacts** - First systematic assessment using 4-phase ENSO classification
3. **CMIP6 future projections** - TC risk under climate change with ENSO stratification
4. **UQAM-TCW methodology** - Full implementation of Carozza et al. (2024) approach
5. **Comprehensive hazard maps** - Return periods, landfall rates, spatial risk assessment

---

## The Roadmap System

You now have a **complete tracking and management system** to follow this roadmap like your "coding bible":

### 📋 Core Documents

1. **[PUBLICATION_ROADMAP.md](PUBLICATION_ROADMAP.md)** (Master Plan)
   - Complete 6-phase breakdown
   - Week-by-week milestones
   - Success criteria
   - Computational requirements
   - **Read when**: Planning, estimating, big picture questions

2. **[ROADMAP_STATUS.md](ROADMAP_STATUS.md)** (Live Tracker)
   - Real-time progress tracking
   - Task checklists with completion status
   - Current blockers
   - Weekly activity log
   - **Update**: Every Friday (mandatory!)

3. **[ROADMAP_QUICK_GUIDE.md](ROADMAP_QUICK_GUIDE.md)** (Daily Reference)
   - Commands and workflows
   - What to do when stuck
   - Quick reference for everything
   - **Use**: Daily, keep open in browser tab

4. **[Weekly Checkpoints](weekly_checkpoints/)** (Daily Log)
   - Detailed day-by-day tracking
   - Time investment logging
   - Technical decisions
   - Learning notes
   - **Update**: Daily (5-10 min)

5. **[README_ROADMAP_TRACKING.md](README_ROADMAP_TRACKING.md)** (System Guide)
   - How to use the tracking system
   - Workflows and best practices
   - Troubleshooting
   - **Read once**: Now, then refer as needed

### 🛠️ Tools

1. **Progress Report Generator** (`scripts/utils/generate_roadmap_report.py`)
   ```bash
   uv run python scripts/utils/generate_roadmap_report.py
   ```
   - Colorful terminal reports
   - Markdown/Slack formats
   - Auto-calculates progress

2. **Interactive Updater** (`scripts/utils/update_roadmap.sh`)
   ```bash
   bash scripts/utils/update_roadmap.sh
   ```
   - Quick daily updates
   - Add tasks/blockers
   - Friday summaries
   - Full checkpoint editing

---

## Your Daily Workflow

### ⏰ Morning (5 minutes)
```bash
cd /nethome/abdel042/enso_finance
uv run python scripts/utils/generate_roadmap_report.py
# Review today's tasks in weekly checkpoint
```

### 🌙 Evening (10 minutes)
```bash
bash scripts/utils/update_roadmap.sh
# Option 1: Quick daily update
# - Log completed tasks
# - Note any blockers
# - Log hours worked
```

### 📅 Friday (30 minutes)
```bash
bash scripts/utils/update_roadmap.sh
# Option 8: Friday end-of-week summary
# Option 7: Update ROADMAP_STATUS.md
# - Mark completed tasks [x]
# - Update phase percentages
# - Add activity log entry
```

---

## The 6 Phases

### Phase 1: Validation & Consistency (Weeks 1-3) 🟡 IN PROGRESS
**Goal**: Ensure synthetic tracks are physically consistent at all temporal scales

**Key Deliverables**:
- Multi-scale validation report
- UQAM comparison table
- Physical constraints report

**Status**: 30% complete

### Phase 2: Large-Scale Synthetic Generation (Weeks 4-6) ⚪ NOT STARTED
**Goal**: Generate 1M-year synthetic catalogs for all basins and ENSO phases

**Key Deliverables**:
- 24 catalogs (6 basins × 4 ENSO phases)
- Quality control reports
- Intensity distributions

**Compute**: 600-1500 hours

### Phase 3: Hazard Map Generation (Weeks 7-9) ⚪ NOT STARTED
**Goal**: Create publication-quality hazard maps following UQAM Section 5

**Key Deliverables**:
- Hazard maps (Cat1+, Cat3+, Cat4-5)
- Return period maps (10, 50, 100, 250-yr)
- Literature comparison

**Compute**: 200-400 hours

### Phase 4: CMIP6 Historical Training (Weeks 10-13) ⚪ NOT STARTED
**Goal**: Train hybrid model on CMIP6 historical era with bias correction

**Key Deliverables**:
- CMIP6 training data (5 models)
- Bias correction models
- Historical validation report

**Compute**: 100-200 hours

### Phase 5: CMIP6 Future Projections (Weeks 14-18) ⚪ NOT STARTED
**Goal**: Generate future TC projections at different GWLs and SSPs

**Key Deliverables**:
- Future synthetic catalogs (480 scenarios)
- Future hazard maps
- Change projections

**Compute**: 2000-5000 hours

### Phase 6: Manuscript Preparation (Weeks 19-24) ⚪ NOT STARTED
**Goal**: Write and submit manuscript to JAMES

**Key Deliverables**:
- Complete manuscript (8,000-10,000 words)
- 15-20 main figures
- 8-10 main tables
- Supplementary material
- Code/data repository
- **SUBMISSION TO JAMES**

---

## Success Metrics

### Scientific Quality
- ✅ Multi-scale validation consistent
- ✅ Spatial correlation with IBTrACS > 0.8
- ✅ LMI distribution matching (p > 0.05)
- ✅ Landfall rates within ±20% of observations
- ✅ CMIP6 bias correction demonstrably effective

### Novelty Claims
- ✅ First hybrid physics-ML TC model with FAST
- ✅ First Extreme El Niño TC hazard assessment
- ✅ First CMIP6-based TC projections with ENSO stratification
- ✅ Improvement over UQAM-TCW with ML while maintaining physics

### Reproducibility
- ✅ Code openly available (GitHub)
- ✅ Data archived (Zenodo with DOI)
- ✅ Complete documentation
- ✅ SLURM scripts provided

---

## Resources Required

### Computational
- **Total**: ~3,000-7,000 compute hours
- **Peak**: Phase 5 (2,000-5,000 hours)
- **Strategy**: SLURM array jobs, 100 parallel cores
- **Timeline**: ~1-3 weeks wall-clock time on HPC

### Storage
- **Current**: ~1,000 GB (environmental data - existing)
- **Phase 2**: +500 GB (synthetic tracks)
- **Phase 4-5**: +300 GB (CMIP6)
- **Phase 3**: +50 GB (hazard maps)
- **Total**: ~1,850 GB

### Time Investment
- **Total**: ~480 person-hours (20 hrs/week × 24 weeks)
- **Daily**: 2-3 hours
- **Weekly peak**: 25-30 hours (during critical phases)

---

## Risk Mitigation

### Built-in Flexibility

1. **Scope Reduction Options**:
   - Phase 5: 5 models → 3 models
   - Phase 5: 100K years → 50K years
   - Phase 5: All SSPs → SSP2-4.5 and SSP5-8.5 only
   - Phase 3: All categories → Cat1+ focus

2. **Timeline Buffers**:
   - Each phase has some slack
   - Phase 6 can start early (methods writing)
   - 24-week timeline is ambitious but achievable

3. **Validation Fallbacks**:
   - Focus on North Atlantic if multi-basin too challenging
   - Use pseudo-global-warming if CMIP6 bias too large
   - Position as methodological paper if some validations fail

---

## Key Contacts and Collaborations

### Planned Outreach
- **Week 3**: Share Phase 1 validation with advisor
- **Week 9**: Informal feedback from UQAM team (David Carozza)
- **Week 13**: Share CMIP6 methodology with climate modeler
- **Week 18**: Pre-submission review by 2-3 experts

### Expert Network
- **David Carozza** (UQAM): UQAM-TCW methodology
- **Kerry Emanuel** (MIT): FAST model questions
- **Nadia Bloemendaal** (VU Amsterdam): STORM comparison
- **Wenchang Yang** (Princeton): CMIP6 ENSO expertise

---

## How to Stay on Track

### 1. Use the Tracking System Daily
- Morning: Check progress report
- Evening: Log tasks with update script
- Friday: Weekly summary and status update

### 2. Follow the Milestones
- Check ROADMAP_STATUS.md weekly milestones table
- If week matches milestone → on track ✅
- If behind → assess and adjust

### 3. Manage Blockers Proactively
- Log blockers immediately
- Don't let blockers persist > 2 days
- Escalate to advisor if stuck > 1 week

### 4. Celebrate Progress
- Mark tasks complete as you go
- Review weekly achievements
- Share milestones with advisor/colleagues

### 5. Adjust When Needed
- Update ROADMAP_STATUS.md if timeline changes
- Document reasons in "Notes and Lessons Learned"
- Communicate changes to advisor

---

## Next Steps (This Week)

### Immediate Actions

1. **✅ DONE** - Set up tracking system
2. **TODO** - Create multi-scale validation script
3. **TODO** - Test on NA basin synthetic tracks
4. **TODO** - Review UQAM paper Table 3 for comparison targets

### This Week's Goals

- Complete Phase 1.1 (multi-scale validation)
- Start Phase 1.2 (UQAM comparison)
- Establish daily tracking habit

---

## Motivation

### Why This Matters

**Scientific Impact**:
- Advancing TC intensity prediction methods
- Understanding ENSO-TC relationships under warming
- First systematic Extreme El Niño assessment

**Practical Impact**:
- Insurance/reinsurance risk assessment
- Climate adaptation planning
- Disaster preparedness

**Personal Impact**:
- Publication in top journal (JAMES)
- Methodological innovation
- 6 months of focused, organized work

### You're Ready!

You have:
- ✅ Clear roadmap with 6 phases
- ✅ Complete tracking system
- ✅ Validated methodology (UQAM + FAST)
- ✅ Infrastructure (ERA5, ORAS5, CMIP6 access)
- ✅ Computational resources (HPC)
- ✅ Support network (advisor, collaborators)

**All you need to do is follow the roadmap and track your progress.**

---

## Quick Reference Card

**Print this and keep at your desk!**

```
═══════════════════════════════════════════════════════════
                DAILY QUICK REFERENCE
═══════════════════════════════════════════════════════════

Morning Check (5 min):
  $ uv run python scripts/utils/generate_roadmap_report.py

Evening Log (10 min):
  $ bash scripts/utils/update_roadmap.sh  # Option 1

Friday Summary (30 min):
  $ bash scripts/utils/update_roadmap.sh  # Options 7 & 8

Key Files:
  - Master Plan:    docs/PUBLICATION_ROADMAP.md
  - Live Tracker:   docs/ROADMAP_STATUS.md (UPDATE FRIDAYS!)
  - Quick Guide:    docs/ROADMAP_QUICK_GUIDE.md
  - This Week:      docs/weekly_checkpoints/WEEK_XX_CHECKPOINT.md

Current Status:
  - Week:    1 of 24
  - Phase:   1 (Validation & Consistency)
  - Progress: 15%
  - Target:  JAMES submission Week 24

When Stuck:
  1. Check ROADMAP_QUICK_GUIDE.md
  2. Check PUBLICATION_ROADMAP.md
  3. Ask advisor
  4. Reach out to collaborators

Remember:
  ✓ Update weekly checkpoint EVERY DAY
  ✓ Update ROADMAP_STATUS.md EVERY FRIDAY
  ✓ Quality over speed
  ✓ Ask for help when stuck
  ✓ You've got this! 🚀

═══════════════════════════════════════════════════════════
```

---

**Start using the tracking system today. Your future self will thank you!**

**Next**: Run `bash scripts/utils/update_roadmap.sh` and choose option 1 to log today's work.
