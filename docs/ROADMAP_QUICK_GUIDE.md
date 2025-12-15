# Publication Roadmap - Quick Reference Guide

**Your Coding Bible for the Next 6 Months**

---

## Daily Workflow

### Every Morning (5 minutes)
1. **Check current status**:
   ```bash
   python scripts/utils/generate_roadmap_report.py
   ```

2. **Review today's checkpoint**:
   ```bash
   # Get current week number
   WEEK=$(python -c "from datetime import datetime; start=datetime(2025,12,15); print((datetime.now()-start).days//7 + 1)")
   cat docs/weekly_checkpoints/WEEK_$(printf "%02d" $WEEK)_CHECKPOINT.md | head -30
   ```

3. **Identify today's priority tasks** from checkpoint

### Every Evening (10 minutes)
1. **Update checkpoint** with completed tasks:
   ```bash
   nano docs/weekly_checkpoints/WEEK_$(printf "%02d" $WEEK)_CHECKPOINT.md
   ```

2. **Log any blockers or insights**

3. **Plan tomorrow's tasks**

### Every Friday (30 minutes)
1. **Complete weekly summary** in checkpoint

2. **Update ROADMAP_STATUS.md**:
   ```bash
   nano docs/ROADMAP_STATUS.md
   ```
   - Update phase percentages
   - Mark completed tasks with [x]
   - Add to activity log
   - Update any blockers

3. **Generate progress report**:
   ```bash
   python scripts/utils/generate_roadmap_report.py --format markdown --output docs/weekly_reports/week_$WEEK.md
   ```

4. **Create next week's checkpoint**:
   ```bash
   cp docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md docs/weekly_checkpoints/WEEK_$(printf "%02d" $((WEEK+1)))_CHECKPOINT.md
   # Edit to update week number and tasks
   ```

---

## Phase Transitions

### When Completing a Phase
1. **Mark all phase tasks complete** in ROADMAP_STATUS.md
2. **Update phase percentage** to 100%
3. **Create phase summary** in `docs/phase_summaries/PHASE_X_SUMMARY.md`
4. **Update next phase status** to "IN PROGRESS"
5. **Share progress** with advisor/collaborators

### Template for Phase Summary
```markdown
# Phase X Summary

**Completion Date**: YYYY-MM-DD
**Planned Duration**: X weeks
**Actual Duration**: X weeks
**On Schedule**: Yes/No

## Deliverables
- [ ] Deliverable 1
- [ ] Deliverable 2

## Key Achievements
-

## Challenges Overcome
-

## Lessons Learned
-

## Next Phase Preparation
-
```

---

## Quick Commands Reference

### Status Checks
```bash
# Full terminal report with colors
python scripts/utils/generate_roadmap_report.py

# Markdown report for documentation
python scripts/utils/generate_roadmap_report.py --format markdown

# Slack format for team updates
python scripts/utils/generate_roadmap_report.py --format slack

# Check overall progress
grep "Overall Progress:" docs/ROADMAP_STATUS.md

# See current phase
grep "Current Phase:" docs/ROADMAP_STATUS.md

# View all blockers
grep -A 10 "### Current Blockers" docs/ROADMAP_STATUS.md

# See next milestone
grep -A 3 "## Weekly Milestones" docs/ROADMAP_STATUS.md | head -15
```

### Task Management
```bash
# Find all incomplete tasks in current phase
grep "\- \[ \]" docs/ROADMAP_STATUS.md | head -20

# Find all completed tasks
grep "\- \[x\]" docs/ROADMAP_STATUS.md | wc -l

# See tasks for specific phase
grep -A 50 "### Phase 1:" docs/ROADMAP_STATUS.md | grep "\- \[ \]"
```

### Progress Tracking
```bash
# Calculate tasks completed
TOTAL=$(grep -c "\- \[.\]" docs/ROADMAP_STATUS.md)
DONE=$(grep -c "\- \[x\]" docs/ROADMAP_STATUS.md)
echo "Completed $DONE / $TOTAL tasks ($(($DONE * 100 / $TOTAL))%)"

# See compute hours used
grep "Compute Hours Used" docs/ROADMAP_STATUS.md -A 6

# Check storage used
grep "Storage Used" docs/ROADMAP_STATUS.md -A 5
```

### File Operations
```bash
# Update roadmap status
nano docs/ROADMAP_STATUS.md

# Update weekly checkpoint
nano docs/weekly_checkpoints/WEEK_$(printf "%02d" $WEEK)_CHECKPOINT.md

# View main roadmap
less docs/PUBLICATION_ROADMAP.md

# Quick search in roadmap
grep -i "search_term" docs/PUBLICATION_ROADMAP.md
```

---

## When Things Go Wrong

### If You're Behind Schedule

1. **Assess the gap**:
   - How many weeks behind?
   - Which tasks are delayed?
   - What caused the delay?

2. **Adjust timeline**:
   - Update ROADMAP_STATUS.md with revised dates
   - Document reason in "Notes and Lessons Learned"
   - Communicate with advisor

3. **Consider scope reduction**:
   - Phase 5: Reduce from 5 models to 3
   - Phase 5: Use 50K years instead of 100K
   - Phase 3: Focus on Cat1+ only (skip Cat3+ initially)

4. **Parallel work**:
   - Start Phase 6 (methods writing) early
   - Work on multiple phases simultaneously when possible

### If Validation Fails

1. **Document the failure**:
   - What metric failed?
   - How far from target?
   - Possible causes?

2. **Debug systematically**:
   - Check input data
   - Review calibration parameters
   - Compare to UQAM implementation

3. **Seek help**:
   - Consult UQAM paper Appendix
   - Reach out to David Carozza (UQAM team)
   - Share issue with advisor

4. **Iterate**:
   - Make targeted fixes
   - Re-run validation
   - Document what worked

### If Computational Resources Run Out

1. **Prioritize**:
   - Complete critical path items first
   - Defer nice-to-have analyses

2. **Optimize**:
   - Reduce synthetic track duration (100K → 50K years)
   - Reduce number of basins (6 → 3: NA, WP, EP)
   - Reduce number of CMIP6 models (5 → 3)

3. **Request more**:
   - Document need and justification
   - Request HPC allocation increase

---

## Milestone Checklist Templates

### Phase 1 Completion Checklist
```
Phase 1: Validation & Consistency
[ ] Multi-scale validation script created and tested
[ ] Validation report generated and reviewed
[ ] UQAM comparison table matches or exceeds benchmarks
[ ] Physical constraints validation shows <1% violations
[ ] All Phase 1 deliverables in outputs/validation/
[ ] Results presented to advisor
[ ] Ready to proceed to Phase 2
```

### Phase 2 Completion Checklist
```
Phase 2: Large-Scale Synthetic Generation
[ ] 10K-year test generation successful
[ ] Resource estimates documented
[ ] 1M-year catalogs generated for all 24 combinations
[ ] Quality control checks passed
[ ] Hybrid intensity model applied
[ ] Storage usage within budget (~500 GB)
[ ] Ready to proceed to Phase 3
```

### Phase 3 Completion Checklist
```
Phase 3: Hazard Map Generation
[ ] Landfall identification complete
[ ] Hazard maps generated for all categories
[ ] Return periods calculated (10, 50, 100, 250-yr)
[ ] Literature comparison favorable
[ ] Maps reviewed and approved
[ ] NetCDF files archived
[ ] Ready to proceed to Phase 4
```

### Phase 4 Completion Checklist
```
Phase 4: CMIP6 Historical Training
[ ] CMIP6 access verified for all models
[ ] Environmental variables extracted
[ ] Bias correction models trained
[ ] Historical validation shows improvement
[ ] Model-specific challenges documented
[ ] Ready to proceed to Phase 5
```

### Phase 5 Completion Checklist
```
Phase 5: CMIP6 Future Projections
[ ] GWL timing calculated
[ ] Future climatologies extracted
[ ] Future synthetic tracks generated
[ ] Future hazard maps created
[ ] Multi-model statistics calculated
[ ] Results physically plausible
[ ] Ready to proceed to Phase 6
```

### Phase 6 Completion Checklist
```
Phase 6: Manuscript Preparation
[ ] All sections drafted
[ ] All figures created (15-20 main + 20-30 supp)
[ ] All tables created (8-10 main + 10-15 supp)
[ ] Supplementary material complete
[ ] Code repository cleaned and documented
[ ] Data archived on Zenodo with DOI
[ ] Internal review completed
[ ] Revisions addressed
[ ] Manuscript formatted for JAMES
[ ] Ready to submit
```

---

## Communication Templates

### Weekly Email to Advisor
```
Subject: Roadmap Progress - Week X of 24

Hi [Advisor],

Quick update on publication roadmap progress:

**This Week's Achievements:**
- [List 2-3 key accomplishments]

**Current Status:**
- Overall: X% complete
- Phase X: Y% complete

**Blockers:**
- [List any blockers, or "None"]

**Next Week's Goals:**
- [List 2-3 main goals]

**Timeline:**
- On track for Week 24 submission

Let me know if you'd like to discuss anything.

Best,
[Your Name]

---
Full status: docs/ROADMAP_STATUS.md
Weekly report: docs/weekly_reports/week_X.md
```

### Collaborator Outreach Template
```
Subject: Collaboration on ENSO-TC Risk Assessment Project

Hi [Name],

I'm working on a project combining UQAM-TCW methodology with ML bias
correction for ENSO-modulated tropical cyclone risk assessment under
climate change. I came across your work on [topic] and thought you
might have insights on [specific question].

[Brief description of where you are and what you need]

Would you be willing to have a brief call or provide feedback?

I'm targeting submission to JAMES in ~[X] months.

Best regards,
[Your Name]

---
Project roadmap: [GitHub link or PDF]
```

---

## Motivation and Reminders

### Why This Matters
- **Scientific Impact**: Novel hybrid physics-ML approach
- **Practical Application**: Insurance/reinsurance risk assessment
- **Climate Change**: Understanding future TC risk under warming
- **ENSO**: First systematic assessment of Extreme El Niño impacts

### When You Feel Overwhelmed
1. **Break it down**: Focus on this week only
2. **Celebrate small wins**: Every completed task is progress
3. **Refer to the roadmap**: You have a clear path
4. **Remember the 6-month timeline is flexible**: Quality > speed
5. **You're not alone**: Advisor, collaborators, and tools are here to help

### Quality Checkpoints
Before marking any phase complete, ask:
1. ✅ Would this pass peer review?
2. ✅ Can someone reproduce this?
3. ✅ Is it documented clearly?
4. ✅ Have I validated thoroughly?
5. ✅ Am I confident in the results?

If any answer is "no", keep refining.

---

## Emergency Contacts

### When Stuck on Methodology
- **UQAM Team**: David Carozza (david.carozza@uqam.ca)
- **FAST Model**: Kerry Emanuel (emanuel@mit.edu)
- **CMIP6 ENSO**: Wenchang Yang (wenchang@princeton.edu)

### When Stuck on Computation
- **HPC Support**: [Your cluster support email]
- **Advisor**: [Advisor email]

### When Stuck on Writing
- **Writing Center**: [University writing center]
- **Advisor**: [Advisor email]

---

## Files to Keep in Mind

### Critical Documentation
- `docs/PUBLICATION_ROADMAP.md` - **Your master plan**
- `docs/ROADMAP_STATUS.md` - **Live progress tracker** (update weekly!)
- `docs/ROADMAP_QUICK_GUIDE.md` - **This guide** (read when lost)
- `docs/weekly_checkpoints/WEEK_XX_CHECKPOINT.md` - **Daily log**

### Key Scripts
- `scripts/utils/generate_roadmap_report.py` - **Progress reporting**
- `scripts/tc_intensity/validate_multiscale_temporal_consistency.py` - **Phase 1**
- `scripts/tc_intensity/generate_event_set.py` - **Phase 2**
- `scripts/tc_intensity/validate_hazard_maps.py` - **Phase 3**

### Where Things Are
- **Scripts**: `scripts/tc_intensity/`, `scripts/batch/`
- **Data**: `data/tc_intensity/`, `outputs/tc_intensity/`
- **Results**: `outputs/validation/`, `outputs/hazard_maps/`
- **Docs**: `docs/`

---

## Final Reminders

1. **Update ROADMAP_STATUS.md every Friday** - non-negotiable
2. **Log daily progress** in weekly checkpoint
3. **Run progress report** at start of each week
4. **Celebrate milestones** - You're doing great work!
5. **Ask for help** when stuck for > 4 hours
6. **Quality over speed** - Peer reviewers will thank you
7. **Document everything** - Future you will thank you

---

**Keep this guide open in a browser tab. Refer to it daily.**

**You've got this! 🚀**
