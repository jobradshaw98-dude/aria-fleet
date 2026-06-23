---
name: feedback_db_migrations_reversible
description: Every Helios DB migration must have a tested down-migration
metadata:
  type: feedback
---

Every schema migration on [[project_helios]] ships with a reversible `down` step, tested locally before merge.

**Why:** A bad forward migration with no rollback means downtime.
**How to apply:** CI rejects migrations missing a `down`. Relates to [[feedback_test_first]].
