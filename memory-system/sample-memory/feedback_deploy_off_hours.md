---
name: feedback_deploy_off_hours
description: Ship production deploys outside peak traffic (before 9am or after 7pm PT)
metadata:
  type: feedback
---

Deploy [[project_helios_deploy]] to production only outside peak hours — before 9am or after 7pm PT.

**Why:** Limits blast radius if a rollout regresses.
**How to apply:** Schedule the release workflow; check [[user_timezone]] for the window.
