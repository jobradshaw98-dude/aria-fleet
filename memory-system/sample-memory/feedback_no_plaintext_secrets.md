---
name: feedback_no_plaintext_secrets
description: Never commit secrets; load from env vars, keep an .env.example template
metadata:
  type: feedback
---

Never hardcode or commit API keys, tokens, or passwords. Load from environment variables; commit only an `.env.example` with placeholders.

**Why:** A single leaked key in git history is permanently compromised.
**How to apply:** Add a pre-commit secret scan. Applies across [[project_helios_auth]] and [[project_helios_deploy]].
