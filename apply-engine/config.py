"""Shared paths and constants for apply_engine."""
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ARIA_DATA = Path(os.environ.get("ARIA_CORE_DATA",
                                str(Path.home() / "projects" / "aria-core" / "data")))
JOBS_JSON = ARIA_DATA / "jobs.json"
APPLICATIONS_JSON = ARIA_DATA / "applications.json"
STAGED_MANIFEST = ARIA_DATA / "staged_applications.json"  # the apply-queue staged-record manifest

RUNS_DIR = PKG_DIR / "runs"              # per-job run artifacts (git-ignored)
PROFILE_DIR = PKG_DIR / "profile"        # dedicated bot Chrome user-data-dir (git-ignored)
PROFILE_EXAMPLE = PKG_DIR / "applicant_profile.example.json"
PROFILE_JSON = PKG_DIR / "applicant_profile.json"  # real PII (git-ignored)
