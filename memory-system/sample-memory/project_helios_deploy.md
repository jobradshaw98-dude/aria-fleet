---
name: project_helios_deploy
description: Helios deploy pipeline — GitHub Actions to a containerized service
metadata:
  type: project
---

[[project_helios]] deploys via GitHub Actions: build image, run tests, push to registry, roll out. Secrets injected at runtime per [[feedback_no_plaintext_secrets]].

Deploy timing rule: [[feedback_deploy_off_hours]]. CI status: [[reference_ci_dashboard]].
