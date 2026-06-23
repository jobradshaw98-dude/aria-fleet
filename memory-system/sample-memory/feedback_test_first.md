---
name: feedback_test_first
description: Write a failing test before implementation code on Helios features
metadata:
  type: feedback
---

For any new feature or bugfix on [[project_helios]], write the failing test first, watch it fail, then implement.

**Why:** Catches regressions early and forces a clear spec before code.
**How to apply:** No implementation PR without an accompanying test. Pairs with [[feedback_db_migrations_reversible]].
