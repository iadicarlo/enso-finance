# AI Assistant Handoff Guide

**How to Seamlessly Switch Between GitHub Copilot and Claude Code**

---

## 🎯 Why You Need This

When you hit token limits or need to switch AI assistants, you want the next AI to pick up exactly where you left off without losing context. This system ensures smooth handoffs.

---

## 🔄 The Three Handoff Methods

### Method 1: Quick Handoff (Session Checkpoints) ⭐ Recommended

**Use when**: Switching due to token limits in the middle of work

**How it works**:
1. Your weekly checkpoint (`docs/weekly_checkpoints/WEEK_0X_CHECKPOINT.md`) is auto-updated
2. Attach it when starting with the new AI
3. Say: "I'm continuing from this checkpoint, please read and continue"

**Commands**:
```bash
# Update checkpoint before switching
checkpoint-edit

# In new session, view it
checkpoint-view
```

**What to include in checkpoint before switching**:
- ✅ Last completed task
- ✅ Current task in progress (what you're in the middle of)
- ✅ Any errors/blockers encountered
- ✅ Next immediate step
- ✅ Files being worked on

---

### Method 2: Dedicated Handoff Document

**Use when**: Major context shift or complex multi-step task

**How it works**:
1. Create a dedicated handoff document with full context
2. Attach to next AI conversation
3. More detailed than weekly checkpoint

**Commands**:
```bash
# Interactive creation (asks questions)
handoff-create

# Quick create (from Copilot to Claude)
handoff-to-claude

# Quick create (from Claude to Copilot)
handoff-to-copilot

# View recent handoffs
handoff-view

# Read latest handoff
handoff-latest
```

**Template includes**:
- Current phase and progress
- What was just completed
- What's in progress
- Next steps with priorities
- Technical details (environment, configs)
- Blockers and open questions
- Files to review

---

### Method 3: Git Commit as Context

**Use when**: Wrapping up a complete feature/task

**How it works**:
1. Commit your changes with detailed message
2. Next AI can see git history
3. Good for clean handoff between complete tasks

**Example**:
```bash
git add scripts/tc_intensity/validate_multiscale.py
git commit -m "WIP: Multi-scale validation - hourly/daily checks complete

Completed:
- Hourly intensity change validation (max 10 m/s/hr check)
- Daily translation speed validation (0-15 m/s range)
- Test suite passing for NA basin

Next steps:
- Add monthly distribution validation
- Add seasonal cycle validation
- Generate validation report

Files:
- scripts/tc_intensity/validate_multiscale_temporal_consistency.py (main)
- tests/test_multiscale_validation.py (tests)

Note: Need to check UQAM paper Table 3 for exact thresholds"
```

Then in next session:
```bash
git log -1 --stat  # See what was done
git show HEAD      # See the changes
```

---

## 📋 Handoff Best Practices

### Before Switching (5 min)

1. **Update checkpoint or create handoff**:
   ```bash
   checkpoint-edit  # or handoff-create
   ```

2. **Add key info**:
   - What you just did
   - What you're in the middle of
   - Exact next step
   - Any errors/issues

3. **Save uncommitted work**:
   ```bash
   git stash push -m "WIP: [description]"
   # or
   git add -A && git commit -m "WIP: [description]"
   ```

4. **Note important context**:
   - Files being edited
   - Variables/parameters set
   - Commands run
   - Specific line numbers if relevant

### When Resuming (2 min)

1. **Attach handoff document** to new AI conversation

2. **Say something like**:
   ```
   "I'm continuing my tropical cyclone ML project. I hit token limits 
   with [previous AI]. Please read the attached handoff document and 
   continue from where I left off. The immediate next step is [X]."
   ```

3. **Let AI read and confirm**:
   - AI will summarize understanding
   - Confirm before proceeding
   - Clarify any confusion

---

## 🎯 What Makes a Good Handoff

### ✅ Good Handoff Example

```markdown
## Current Task
Creating multi-scale temporal validation script 
(`scripts/tc_intensity/validate_multiscale_temporal_consistency.py`)

## Last Action
- Implemented hourly validation (lines 45-89)
- Tested on NA basin synthetic tracks
- Validation passing for max intensity change ≤ 10 m/s/hr

## Current Issue
Getting KeyError: 'translation_speed' when trying to access 
synthetic track DataFrame. Column might be named 'trans_speed' 
or 'vt' instead.

## Next Step
1. Check column names in synthetic track file:
   `data/processed/synthetic_tracks/NA_neutral_2024.csv`
2. Update line 67 to use correct column name
3. Then implement daily validation (translation speed 0-15 m/s)

## Files
- Editing: `scripts/tc_intensity/validate_multiscale_temporal_consistency.py`
- Reference: `docs/PUBLICATION_ROADMAP.md` (Phase 1.1 section)
- Input data: `data/processed/synthetic_tracks/NA_neutral_2024.csv`
```

### ❌ Poor Handoff Example

```markdown
## Current Task
Working on validation

## Last Action
Wrote some code

## Next Step
Continue validation
```

**Why it's poor**: Too vague! New AI won't know:
- Which validation script?
- What specific part?
- What works/doesn't work?
- Where to find files?

---

## 🛠️ Handoff Workflow Examples

### Example 1: Token Limit Mid-Task

**Situation**: Building a validation script, hit token limit halfway through

**Steps**:
1. Quick update to checkpoint:
   ```bash
   checkpoint-edit
   ```
   Add to today's entry:
   ```markdown
   ### 2025-12-15 (Continued - Switching to Claude)
   - ✅ Implemented hourly validation (lines 1-89)
   - 🚧 IN PROGRESS: Daily validation (lines 90-150)
   - ❌ ISSUE: KeyError on 'translation_speed' column
   - ➡️ NEXT: Fix column name, then add monthly validation
   - Files: scripts/tc_intensity/validate_multiscale_temporal_consistency.py
   ```

2. Start new AI session with:
   ```
   "Continuing my TC validation script. Hit Copilot token limit. 
   Please read docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md 
   (today's entry at bottom). Need to fix the KeyError and 
   continue with daily validation."
   ```

### Example 2: End of Day Handoff

**Situation**: Finishing for the day, want to pick up tomorrow with different AI

**Steps**:
1. Complete checkpoint day entry:
   ```bash
   checkpoint-edit
   ```

2. Create detailed handoff:
   ```bash
   handoff-to-claude  # if switching to Claude tomorrow
   ```

3. Commit any completed work:
   ```bash
   git add -A
   git commit -m "Day 1 progress: Hourly and daily validation complete"
   ```

4. Tomorrow, attach both:
   - Checkpoint file
   - Handoff document

### Example 3: Complex Multi-Step Task

**Situation**: Debugging complex issue across multiple files

**Steps**:
1. Create detailed handoff:
   ```bash
   handoff-create
   ```

2. In handoff, document:
   - Error message (full stack trace)
   - Files involved (with line numbers)
   - What you've tried
   - Hypothesis about cause
   - Next debugging step

3. Attach handoff + relevant error logs

---

## 📁 File Organization

```
docs/
├── weekly_checkpoints/
│   ├── WEEK_01_CHECKPOINT.md  ← Daily updates (lightweight)
│   └── WEEK_02_CHECKPOINT.md
├── handoffs/
│   ├── handoff_20251215_143022.md  ← Dedicated handoffs (detailed)
│   ├── handoff_20251216_091534.md
│   └── ...
├── HANDOFF_TEMPLATE.md  ← Template for new handoffs
└── AI_HANDOFF_GUIDE.md  ← This file
```

---

## 🚀 Quick Reference

### Daily Handoff (Token Limit)
```bash
checkpoint-edit  # Update current task status
# Then attach checkpoint to new AI
```

### Detailed Handoff (Complex Task)
```bash
handoff-create  # Creates timestamped handoff
# Edit file, then attach to new AI
```

### View Recent Handoffs
```bash
handoff-view     # List recent handoffs
handoff-latest   # Read latest handoff
```

### Resume From Handoff
**Attach file to AI conversation and say**:
```
"Please read the attached handoff document and continue from there.
The immediate priority is [specific next step]."
```

---

## 💡 Pro Tips

1. **Update checkpoint daily even without handoff**
   - Makes any handoff easier
   - Good record keeping

2. **Use descriptive commit messages**
   - Git history helps context
   - WIP commits are fine!

3. **Reference specific line numbers**
   - "Line 67 has the bug" > "There's a bug"

4. **Include error messages verbatim**
   - Copy-paste full error
   - Don't paraphrase

5. **Mention what didn't work**
   - "Tried approach X, got error Y"
   - Saves new AI from repeating

6. **Link to relevant docs**
   - "See PUBLICATION_ROADMAP.md Phase 1.1"
   - "Reference UQAM paper Section 3.2"

7. **Test before handoff if possible**
   - Note what works/doesn't
   - Include test commands

---

## 🔍 Troubleshooting

### "New AI doesn't understand my handoff"

**Solution**: Add more specifics:
- Exact file paths
- Line numbers
- Variable names
- Error messages
- Expected vs actual behavior

### "Lost context between sessions"

**Solution**: Improve checkpoint habit:
- Update checkpoint at end of each coding session
- Include file paths and line numbers
- Note important decisions made

### "Too much context to convey"

**Solution**: Break it down:
1. High-level: What phase/task?
2. Immediate: What's the next 1-2 steps?
3. Detail: Only for current file being edited
4. Reference: Point to docs for background

---

## ✅ Handoff Checklist

Before switching AI assistants:

- [ ] Updated checkpoint or created handoff document
- [ ] Noted current task in progress
- [ ] Listed immediate next step (specific!)
- [ ] Documented any errors/blockers
- [ ] Saved uncommitted work (git stash or commit)
- [ ] Listed files being edited (with paths)
- [ ] Noted important variables/parameters
- [ ] Referenced relevant documentation sections

When resuming with new AI:

- [ ] Attached handoff document/checkpoint
- [ ] Provided clear context in first message
- [ ] Let AI summarize understanding before continuing
- [ ] Confirmed immediate next step

---

## 🎓 Example Handoff Message to AI

```
Hi! I'm continuing my tropical cyclone ML project (enso_finance repo).

I was working with [GitHub Copilot/Claude Code] but hit token limits.

Please read the attached handoff document: docs/handoffs/handoff_20251215_143022.md

**Quick Context**:
- Phase 1, Week 1: Multi-scale validation
- Currently implementing hourly validation in 
  scripts/tc_intensity/validate_multiscale_temporal_consistency.py
- Got a KeyError on 'translation_speed' column (line 67)

**Immediate Next Step**:
Check the actual column names in the synthetic track DataFrame 
and update line 67 to use the correct column name.

Can you review the handoff and continue from there?
```

---

**Remember**: Good handoffs = seamless continuity between AI assistants!
