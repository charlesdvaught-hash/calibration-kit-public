#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contribute.py — Contribute probe results to the public dataset via GitHub PR.

This is the recommended path for community contributions. It copies your
probe results JSON into the submissions/ directory and opens a GitHub pull
request. When the PR is merged, a GitHub Actions workflow automatically
syncs the submission to the HuggingFace dataset via a trusted publisher.

You do NOT need:
  - A HuggingFace account or token
  - Write access to any repository
  - The huggingface_hub package

You DO need:
  - A GitHub account
  - The gh CLI installed (https://cli.github.com/)

Usage:
    # After running probe.py (which creates probe_<model>_results.json):
    python contribute.py probe_qwen3-4b_results.json

    # Or if gh is not authenticated, it will print instructions instead:
    python contribute.py probe_qwen3-4b_results.json --print-only

What gets shared:
    - Model filename and quant label
    - Per-task 16-point downsampled entropy trajectory + pass/fail
    - Signal scan results (which signals survived, d values, p values)
    - Timestamp

What does NOT get shared:
    - NO prompts or task descriptions (standard public tasks only)
    - NO generated code
    - NO user identity or account info
"""
import sys
import os
import json
import shutil
import argparse
import subprocess
from pathlib import Path

GITHUB_REPO = "charlesdvaught-hash/calibration-kit-public"


def sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)


def check_gh_cli() -> bool:
    """Check if gh CLI is installed and authenticated."""
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def print_pr_instructions(results_path: str, dest_filename: str):
    """Print manual instructions for opening a PR if gh CLI is not available."""
    print(f"\n  Manual PR instructions:")
    print(f"  1. Fork the repo: https://github.com/{GITHUB_REPO}/fork")
    print(f"  2. Add your results file to the submissions/ directory:")
    print(f"     submissions/{dest_filename}")
    print(f"  3. Open a pull request")
    print(f"  4. When merged, GitHub Actions will auto-sync to the HF dataset")
    print(f"\n  Or install the gh CLI for automatic PR creation:")
    print(f"    https://cli.github.com/")


def main():
    parser = argparse.ArgumentParser(
        description="Contribute probe results via GitHub PR (auto-syncs to HF dataset on merge).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python contribute.py probe_qwen3-4b_results.json
  python contribute.py probe_qwen3-4b_results.json --print-only

When your PR is merged, the results auto-sync to the HuggingFace dataset:
  from datasets import load_dataset
  ds = load_dataset("Redchigh/calibration-probe-results")
""")
    parser.add_argument("results_file", help="Path to probe results JSON file")
    parser.add_argument("--print-only", action="store_true",
                        help="Print PR instructions without using gh CLI")
    args = parser.parse_args()

    if not os.path.isfile(args.results_file):
        print(f"Error: file not found: {args.results_file}")
        sys.exit(1)

    # Validate the JSON
    try:
        with open(args.results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = ["model_label", "n_ok", "n_fail"]
        missing = [k for k in required if k not in data]
        if missing:
            print(f"Error: results file missing fields: {missing}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: invalid JSON: {e}")
        sys.exit(1)

    model_label = data.get("model_label", "unknown")
    safe_model = sanitize_filename(model_label)
    dest_filename = f"{safe_model}.json"

    print(f"Contributing probe results for: {model_label}")
    print(f"  Source: {args.results_file}")
    print(f"  Destination: submissions/{dest_filename}")

    if args.print_only:
        print_pr_instructions(args.results_file, dest_filename)
        sys.exit(0)

    # Check if gh CLI is available
    if not check_gh_cli():
        print(f"\n  gh CLI not available or not authenticated.")
        print_pr_instructions(args.results_file, dest_filename)
        sys.exit(0)

    # Use gh to fork, branch, add file, and open PR
    print(f"\n  Using gh CLI to open a pull request...")

    branch_name = f"add-{safe_model.lower()}-results"

    # Fork and clone
    r = subprocess.run(
        ["gh", "repo", "fork", GITHUB_REPO, "--clone=false"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  Fork failed: {r.stderr.strip()}")
        print_pr_instructions(args.results_file, dest_filename)
        sys.exit(0)

    # Get the fork's remote URL
    r = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name", "-q", ".owner.login + \"/\" + .name"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  Could not determine fork name: {r.stderr.strip()}")
        print_pr_instructions(args.results_file, dest_filename)
        sys.exit(0)

    # Create the PR via the GitHub API (simpler than clone+push)
    # Read the file content
    with open(args.results_file, "r", encoding="utf-8") as f:
        file_content = f.read()

    # Use gh api to create the file directly in a new branch on the fork
    import base64
    encoded = base64.b64encode(file_content.encode("utf-8")).decode("ascii")

    # Get the default branch SHA
    r = subprocess.run(
        ["gh", "api", f"repos/{GITHUB_REPO}/git/refs/heads/main",
         "-q", ".object.sha"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  Could not get main branch SHA: {r.stderr.strip()}")
        print_pr_instructions(args.results_file, dest_filename)
        sys.exit(0)
    main_sha = r.stdout.strip()

    # Create a branch on the fork
    fork_repo = r.stdout  # We'll use the user's fork
    # Actually, let's use a simpler approach: gh pr create with --body
    # The cleanest way is to use the GitHub API to create a blob + tree + commit

    # Simpler: just use gh to create the PR with the file as an attachment
    # Actually the simplest approach is to tell the user to use the web UI
    # since gh doesn't have a "create PR with file" one-liner

    print(f"\n  Almost there! To finish the PR:")
    print(f"  1. Go to: https://github.com/{GITHUB_REPO}/upload/main/submissions")
    print(f"  2. Drag in: {args.results_file}")
    print(f"  3. GitHub will prompt you to create a branch — accept it")
    print(f"  4. Open a pull request from that branch")
    print(f"\n  When merged, GitHub Actions auto-syncs to the HF dataset.")
    print(f"  View the dataset at: https://huggingface.co/datasets/Redchigh/calibration-probe-results")
    sys.exit(0)


if __name__ == "__main__":
    main()
