---
name: project_helios_auth
description: Helios auth subsystem — OAuth2 login via Google, JWT sessions
metadata:
  type: project
---

Auth for [[project_helios]] uses OAuth2 (Google) with short-lived JWT sessions and refresh tokens.

Setup steps in [[reference_oauth_setup]]. Hard rule on secrets: [[feedback_no_plaintext_secrets]].
