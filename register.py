#!/usr/bin/env python3
"""
register.py — Repo Access Registration

Grants you access to the private calibration-kit GitHub repo for ongoing
updates. Run this once after purchasing the kit on AgentMart.

You supply your AgentMart buyer license key (bak_...) and your GitHub
username. The server validates your purchase and sends you a GitHub
collaborator invite. Accept it (GitHub emails you automatically), then
'git pull' gets you future updates.

This is separate from federation.py — you don't need to contribute
anything to get repo access. Just run this once.

Usage:
    python register.py --license-key bak_YOUR_KEY --github-user YOUR_USERNAME
    python register.py --license-key bak_YOUR_KEY --github-user YOUR_USERNAME --dry-run
    python register.py  # prompts for both values interactively
"""

import argparse
import json
import os
import sys
import urllib.request

# ─── Constants ─────────────────────────────────────────────────────────────
# Webhook URL is env-var-driven. The default is the deployed Worker URL.
# If you're running a self-hosted Worker, set CALIBRATION_KIT_WEBHOOK_URL.

WEBHOOK_URL = os.environ.get(
    "CALIBRATION_KIT_WEBHOOK_URL",
    "https://calibration-kit-federation.charlesdvaught-hash.workers.dev"
)
REGISTER_URL = WEBHOOK_URL.rstrip("/") + "/register"

# Detect undeployed webhook
_PLACEHOLDER_MARKER = "example.workers.dev"


# ─── Registration ───────────────────────────────────────────────────────────

def register(license_key: str, github_username: str, dry_run: bool = False) -> bool:
    """Send registration to the Worker's /register endpoint."""
    if _PLACEHOLDER_MARKER in WEBHOOK_URL:
        print("  ERROR: The registration webhook is not deployed yet.")
        print("  The developer needs to deploy the Cloudflare Worker before")
        print("  registration can work. Contact them for manual access.")
        print(f"  (Webhook URL is still a placeholder: {WEBHOOK_URL})")
        return False

    payload = {
        "license_key": license_key,
        "github_username": github_username,
    }

    if dry_run:
        print(f"[DRY RUN] Would send to {REGISTER_URL}")
        print(f"  license_key: {license_key[:6]}...{license_key[-4:]}")
        print(f"  github_username: {github_username}")
        return True

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            REGISTER_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

            if result.get("registered"):
                print()
                print(f"  Success! GitHub invite sent to @{github_username}.")
                print(f"  Check your GitHub notifications or email to accept.")
                print(f"  Repo: {result.get('repo', 'unknown')}")
                print()
                print("  After accepting the invite:")
                print("    git clone https://github.com/" + result.get("repo", "owner/repo") + ".git")
                print("    # or add as a remote to your existing checkout:")
                print("    git remote add upstream https://github.com/" + result.get("repo", "owner/repo") + ".git")
                print("    git pull upstream main")
                return True
            else:
                print(f"  Registration failed: {result.get('error', 'unknown error')}")
                return False

    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body).get("error", body)
        except (json.JSONDecodeError, ValueError):
            err = body
        print(f"  Registration failed (HTTP {e.code}): {err}")
        return False
    except Exception as e:
        print(f"  Registration failed: {e}")
        return False


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Register for private repo access (run once after purchase)"
    )
    parser.add_argument("--license-key", default=os.environ.get("AGENTMART_API_KEY", ""),
                        help="AgentMart buyer API key (bak_...) or set AGENTMART_API_KEY env var")
    parser.add_argument("--github-user", default=os.environ.get("GITHUB_USERNAME", ""),
                        help="Your GitHub username (for repo collaborator invite)")
    parser.add_argument("--dry-run", action="store_true", help="No network calls — just print")
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  Calibration Kit — Repo Access Registration")
    print("=" * 64)
    print()

    # Prompt for missing values (interactive mode)
    license_key = args.license_key
    if not license_key and not args.dry_run:
        license_key = input("  AgentMart license key (bak_...): ").strip()

    github_username = args.github_user
    if not github_username and not args.dry_run:
        github_username = input("  GitHub username: ").strip()

    # Validate
    if not license_key:
        print("  Error: license key required. Use --license-key or set AGENTMART_API_KEY.")
        sys.exit(1)

    if not license_key.startswith("bak_"):
        print(f"  Error: license key must start with 'bak_', got: {license_key[:6]}...")
        sys.exit(1)

    if not github_username:
        print("  Error: GitHub username required. Use --github-user or set GITHUB_USERNAME.")
        sys.exit(1)

    # Confirm
    print(f"  License key: {license_key[:6]}...{license_key[-4:]}")
    print(f"  GitHub user: @{github_username}")
    print(f"  Endpoint:    {REGISTER_URL}")
    print()

    if not args.dry_run:
        confirm = input("  Send registration? [y/N]: ").strip().lower()
        if confirm != "y":
            print("  Cancelled.")
            sys.exit(0)
        print()

    success = register(license_key, github_username, dry_run=args.dry_run)

    print()
    if success:
        print("  Registration complete.")
    else:
        print("  Registration failed — see error above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
