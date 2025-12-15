# AI Handoff Quick Guide - Copilot ↔ Claude Code

## 🎯 3 Ways to Switch AI Assistants

### Method 1: Quick Handoff (Fastest - 2 min) ⭐

**When**: Hit token limit mid-task

**Steps**:
```bash
# 1. Update checkpoint with current status
checkpoint-edit   # or: vim docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md

# 2. Add to today's section:
#    - ✅ What you just completed
#    - 🚧 What you're in middle of (specific!)
#    - ➡️ Exact next step
#    - 📁 Files being edited (with paths)

# 3. Save and exit (:wq in vim)
```

**Tell new AI**:
```
I'm continuing my tropical cyclone ML project. Hit token limits with [Copilot/Claude].

Please read: docs/weekly_checkpoints/WEEK_01_CHECKPOINT.md (today's entry at bottom)

Immediate next step: [specific action]
```

---

### Method 2: Dedicated Handoff (Complex tasks - 5 min)

**When**: Complex debugging or end-of-day handoff

**Steps**:
```bash
# Interactive creation
handoff-create

# OR quick one-liners
handoff-to-claude      # When switching from Copilot to Claude
handoff-to-copilot     # When switching from Claude to Copilot
```

**Tell new AI**:
```
Continuing my project. Please read the attached handoff document:
docs/handoffs/handoff_[timestamp].md

Next step: [specific action]
```

---

### Method 3: Git Commit (Clean handoff)

**When**: Just finished a complete task/feature

**Steps**:
```bash
git add -A
git commit -m "WIP: [Task description]

Completed:
- [What works]

Next:
- [What to do next]

Note: [Important context]"
```

**Tell new AI**:
```
Continuing from my last commit. Please check:
git log -1
git show HEAD

Next step: [specific action]
```

---

## 💡 Pro Tips

### What Makes a Good Handoff

✅ **Specific file paths**: `scripts/tc_intensity/validate.py` not "the validation script"
✅ **Line numbers**: "Line 67 has the KeyError" not "there's an error"
✅ **Exact next step**: "Fix column name on line 67" not "continue validation"
✅ **Include error messages**: Copy-paste full error, don't paraphrase
✅ **Note what didn't work**: "Tried X, got error Y" saves time

❌ **Too vague**: "Working on validation, continue please"
❌ **Missing context**: No file paths or line numbers
❌ **No next step**: AI doesn't know what to do

### Example Good Handoff Entry

```markdown
### 2025-12-15 16:30 - Switching to Claude

**Current Task**: Multi-scale validation script
- File: scripts/tc_intensity/validate_multiscale_temporal_consistency.py
- Status: Hourly validation complete (lines 1-89)

**Issue**: KeyError: 'translation_speed' on line 67
- Trying to access df['translation_speed'] 
- Column might be named 'trans_speed' or 'vt' instead

**Next Step**:
1. Check column names: df.columns.tolist()
2. Update line 67 with correct column name
3. Then add daily validation (translation speed 0-15 m/s check)

**Files**:
- Editing: scripts/tc_intensity/validate_multiscale_temporal_consistency.py
- Input: data/processed/synthetic_tracks/NA_neutral_2024.csv
- Reference: docs/PUBLICATION_ROADMAP.md (Phase 1.1)
```

---

## 📋 Quick Commands

```bash
# Update checkpoint
checkpoint-edit

# Create handoff
handoff-create
handoff-to-claude
handoff-to-copilot

# View latest
handoff-latest
checkpoint-view

# Check editor
echo $EDITOR   # Should be: vim
```

---

## 🔄 Typical Handoff Flow

1. **Before switching** (2 min):
   - Update checkpoint OR create handoff
   - Note current state, next step, files
   - Save uncommitted work (git stash or commit)

2. **Start new AI session**:
   - Attach checkpoint/handoff file
   - Provide context in first message
   - State immediate next step

3. **New AI response**:
   - AI reads and summarizes understanding
   - You confirm before proceeding
   - AI continues from where you left off

---

## ✅ Handoff Checklist

Before switching:
- [ ] Updated checkpoint or created handoff
- [ ] Listed current task + exact next step
- [ ] Noted any errors/blockers
- [ ] Listed files being edited (full paths)
- [ ] Saved uncommitted work

When resuming:
- [ ] Attached handoff/checkpoint file
- [ ] Stated immediate next step
- [ ] Let AI confirm understanding

---

**Quick Reference**: Full guide at `docs/AI_HANDOFF_GUIDE.md`
