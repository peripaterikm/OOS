# OOS Roadmap вЂ” 8 Weeks (Checklist Version)

## 0. Current Position

- [x] **0.1.1** v1 kernel assembled
- [x] **0.1.2** deterministic/file-based pipeline is working
- [x] **0.1.3** founder loop mostly closed
- [x] **0.1.4** Windows-native developer operations established
- [ ] **0.2.1** Current phase: **Phase 2 - Real Input Path**
- [ ] **0.2.2** Current item: **4.2 Evaluation and rollback rules**
- [ ] **0.2.3** Total mini-epics in this roadmap: **8**
- [ ] **0.2.4** Completed from this roadmap: **7 / 8**
- [ ] **0.2.5** Remaining: **1 / 8**

---

## 1. Phase 1 вЂ” Operational Reliability

### 1.1. Safe dry-run against dirty state
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 1

- [ ] **1.1.1** Define explicit behavior for `v1-dry-run --project-root .` when local `artifacts/` already exist
- [ ] **1.1.2** Implement one clear policy:
  - [ ] **1.1.2.1** auto-isolation
  - [ ] **1.1.2.2** auto-clean
  - [ ] **1.1.2.3** hard fail with actionable message
- [ ] **1.1.3** Add focused tests for the chosen behavior
- [ ] **1.1.4** Validate behavior in Windows-native mode
- [ ] **1.1.5** Confirm `python -m oos.cli v1-dry-run --project-root .` no longer fails with cryptic transition errors

### 1.2. Deterministic runtime contract
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done  
**Week:** 2

- [x] **1.2.1** Make dry-run and weekly-review behavior explicitly deterministic
- [x] **1.2.2** Remove hidden dependence on stale repo-root state
- [x] **1.2.3** Add repeatability checks for key runtime scenarios
- [x] **1.2.4** Document the runtime contract briefly where needed
- [x] **1.2.5** Confirm the same input yields the same class of outputs

---

## 2. Phase 2 вЂ” Real Input Path

### 2.1. Real signal batch ingestion
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Week:** 3

- [x] **2.1.1** Define one working format for real signal batch input
- [x] **2.1.2** Add a stable path for ingesting real signals without manual reshaping
- [x] **2.1.3** Run a real batch through the pipeline end-to-end
- [x] **2.1.4** Verify that outputs are real artifacts, not only demo-package outputs

### 2.2. Real founder package
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Week:** 4

- [x] **2.2.1** Verify that checklist and weekly review remain useful on real signals
- [x] **2.2.2** Remove the biggest UX friction points in the founder review package
- [x] **2.2.3** Verify founder decisions can be recorded back into the system without artifact archaeology
- [x] **2.2.4** Confirm traceability still works with real input

---

## 3. Phase 3 вЂ” Weekly Operating Cadence

### 3.1. First real weekly cycle
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Week:** 5

- [x] **3.1.1** Run one real weekly cycle on real signals
- [x] **3.1.2** Process the batch through the pipeline
- [x] **3.1.3** Complete founder review on the produced package
- [x] **3.1.4** Record founder decisions
- [x] **3.1.5** Verify portfolio and weekly review reflect the result

### 3.2. Weekly runbook v1
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Week:** 6

- [x] **3.2.1** Write one concise weekly runbook
- [ ] **3.2.2** Cover:
  - [x] **3.2.2.1** input
  - [x] **3.2.2.2** launch
  - [x] **3.2.2.3** review
  - [x] **3.2.2.4** decision recording
  - [x] **3.2.2.5** output check
- [x] **3.2.3** Remove unnecessary manual steps
- [x] **3.2.4** Confirm the weekly cycle is reproducible from the runbook alone

---

## 4. Phase 4 вЂ” Controlled Model Enablement

### 4.1. AI-assisted ideation behind flag
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Week:** 7

- [x] **4.1.1** Choose one safe layer for model-assisted mode
- [x] **4.1.2** Add the model-assisted mode behind a feature flag
- [x] **4.1.3** Preserve deterministic fallback behavior
- [x] **4.1.4** Confirm the assisted mode adds useful value without destabilizing the core

### 4.2. Evaluation and rollback rules
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Week:** 8

- [ ] **4.2.1** Define quality criteria for assisted mode
- [ ] **4.2.2** Define rollback rules
- [ ] **4.2.3** Compare deterministic vs assisted mode on several real cases
- [ ] **4.2.4** Document where model assistance helps and where it should be disabled

---

## 5. Milestones

- [ ] **5.1** Milestone A reached: Operational stability achieved after **1.2**
- [ ] **5.2** Milestone B reached: Real input path operational after **2.2**
- [ ] **5.3** Milestone C reached: OOS becomes a real internal operating tool after **3.2**
- [ ] **5.4** Milestone D reached: Controlled model-enabled mode established after **4.2**

---

## 6. Tracking Rules

- [ ] **6.1** Always record current status as: `Current item: X.Y`
- [ ] **6.2** Always record progress as: `Completed: N / 8`
- [ ] **6.3** Always record remaining work as: `Remaining: M / 8`
- [ ] **6.4** Mark mini-epics only when Definition of Done is actually met

---

## 7. Priority Order

- [ ] **7.1** Priority 1: **1.1 Safe dry-run against dirty state**
- [ ] **7.2** Priority 2: **1.2 Deterministic runtime contract**
- [ ] **7.3** Priority 3: **2.1 Real signal batch ingestion**
- [ ] **7.4** Priority 4: **2.2 Real founder package**
- [ ] **7.5** Priority 5: **3.1 First real weekly cycle**
- [ ] **7.6** Priority 6: **3.2 Weekly runbook v1**
- [ ] **7.7** Priority 7: **4.1 AI-assisted ideation behind flag**
- [ ] **7.8** Priority 8: **4.2 Evaluation and rollback rules**

---

## 8. Explicit Non-Goals for This Roadmap

- [ ] **8.1** No UI
- [ ] **8.2** No database migration / serious storage redesign
- [ ] **8.3** No multi-user support
- [ ] **8.4** No all-purpose smart agent redesign
- [ ] **8.5** No architecture refactor for aesthetics only

---

## 9. Notes

- Use `[x]` for done
- Use `[-]` manually in text if you want to mark something as in progress inside comments or headings
- Keep this file updated after each accepted mini-epic
