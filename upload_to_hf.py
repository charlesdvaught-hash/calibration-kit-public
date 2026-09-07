#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_to_hf.py — Upload probe results to the public HuggingFace dataset.

Turns your local probe results JSON into a permanent, citable public artifact
that other researchers can load with:

    from datasets import load_dataset
    ds = load_dataset("charlesdvaught-hash/calibration-probe-results")

Usage:
    # After running probe.py (which creates probe_<model>_results.json):
    python upload_to_hf.py probe_qwen3-4b_results.json

    # With a specific HF token (get one at huggingface.co/settings/tokens):
    python upload_to_hf.py probe_qwen3-4b_results.json --token hf_xxxxx

    # Or set the token via environment variable:
    set HF_TOKEN=hf_xxxxx
    python upload_to_hf.py probe_qwen3-4b_results.json

Requirements:
    pip install huggingface_hub

What gets uploaded:
    - Model filename and quant label
    - Per-task 16-point downsampled entropy trajectory + pass/fail
    - Signal scan results (which signals survived, d values, p values)
    - Timestamp

What does NOT get uploaded:
    - NO prompts or task descriptions (standard public tasks only)
    - NO generated code
    - NO user identity or account info

The submission is stored as a single JSON file in the dataset repo at:
    data/submissions/{model_label}_{timestamp}.json

This is append-only and concurrent-safe — multiple people can upload at once
without conflicts. Each submission is one file.
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path

# Default dataset repo. Change this if you fork to your own HF account.
DEFAULT_DATASET_REPO = "charlesdvaught-hash/calibration-probe-results"


def sanitize_filename(s: str) -> str:
    """Make a string safe for use as a filename."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)


def upload_to_hf(results_path: str, repo_id: str, token: str,
                 private: bool = False, create_pr: bool = True) -> bool:
    """Upload a probe results JSON to a HuggingFace dataset repo.

    By default uses create_pr=True, which opens a pull request instead of
    committing directly. This means submitters DON'T need write access to
    your dataset — they just need a HF account. You review and merge PRs,
    which gives you quality control over what enters the dataset.

    Set create_pr=False only if you own the repo and want to commit directly.
    """
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("Error: huggingface_hub not installed.")
        print("  pip install huggingface_hub")
        return False

    # Load the local results
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model_label = data.get("model_label", "unknown_model")
    timestamp = int(time.time())

    # Build the submission filename
    safe_model = sanitize_filename(model_label)
    filename = f"data/submissions/{safe_model}_{timestamp}.json"

    # Validate the payload has the expected fields
    required = ["model_label", "n_ok", "n_fail", "per_task"]
    missing = [k for k in required if k not in data]
    if missing:
        print(f"Error: results file missing fields: {missing}")
        return False

    print(f"Uploading to HuggingFace dataset: {repo_id}")
    print(f"  File: {filename}")
    print(f"  Model: {model_label}")
    print(f"  Tasks: {data.get('n_ok', 0)} passed, {data.get('n_fail', 0)} failed")

    api = HfApi(token=token)

    # Create the repo if it doesn't exist
    try:
        api.repo_info(repo_id, repo_type="dataset")
    except Exception:
        print(f"  Dataset repo doesn't exist yet. Creating {repo_id}...")
        try:
            create_repo(repo_id, repo_type="dataset", private=private, token=token)
            print(f"  Created. {'Private' if private else 'Public'} dataset.")
        except Exception as e:
            print(f"  Error creating dataset repo: {e}")
            print(f"  You may need to create it manually at:")
            print(f"    https://huggingface.co/new-dataset")
            print(f"  Set name to '{repo_id}' and type to 'dataset'.")
            return False

    # Upload the file
    try:
        # Write to a temp file in the expected format
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2)
            tmp_path = tmp.name

        api.upload_file(
            path_or_fileobj=tmp_path,
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            create_pr=create_pr,
            commit_message=f"Add probe results for {model_label}",
        )
        os.unlink(tmp_path)
    except Exception as e:
        print(f"  Upload failed: {e}")
        if "403" in str(e) or "Forbidden" in str(e):
            print(f"\n  This usually means you don't have write access to {repo_id}.")
            print(f"  If this is not your repo, make sure create_pr=True (default).")
            print(f"  If it IS your repo, check that your token has write permissions.")
        return False

    if create_pr:
        print(f"\n  Pull request opened! The dataset owner will review and merge it.")
        print(f"  View PRs at: https://huggingface.co/datasets/{repo_id}/pulls")
        print(f"\n  Once merged, other researchers can load the dataset with:")
        print(f"    from datasets import load_dataset")
        print(f'    ds = load_dataset("{repo_id}")')
    else:
        print(f"\n  Uploaded successfully!")
        print(f"  View at: https://huggingface.co/datasets/{repo_id}")
        print(f"\n  Other researchers can now load this dataset with:")
        print(f"    from datasets import load_dataset")
        print(f'    ds = load_dataset("{repo_id}")')
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Upload probe results to a public HuggingFace dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # As a contributor (opens a PR for the owner to review):
  python upload_to_hf.py probe_qwen3-4b_results.json --token hf_xxxxx

  # As the dataset owner (commits directly, no PR):
  python upload_to_hf.py probe_qwen3-4b_results.json --token hf_xxxxx --direct

  # To your own dataset repo:
  python upload_to_hf.py probe_qwen3-4b_results.json --repo your-name/your-dataset --direct

After the PR is merged, anyone can load the dataset:
  from datasets import load_dataset
  ds = load_dataset("charlesdvaught-hash/calibration-probe-results")
""")
    parser.add_argument("results_file", help="Path to probe results JSON file")
    parser.add_argument("--repo", default=DEFAULT_DATASET_REPO,
                        help=f"HuggingFace dataset repo ID (default: {DEFAULT_DATASET_REPO})")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN", ""),
                        help="HuggingFace API token (or set HF_TOKEN env var)")
    parser.add_argument("--private", action="store_true",
                        help="Create the dataset as private (default: public)")
    parser.add_argument("--direct", action="store_true",
                        help="Commit directly instead of opening a PR (use this only if you own the repo)")
    args = parser.parse_args()

    if not os.path.isfile(args.results_file):
        print(f"Error: file not found: {args.results_file}")
        sys.exit(1)

    if not args.token:
        print("Error: no HuggingFace token provided.")
        print("  Get one at: https://huggingface.co/settings/tokens")
        print("  Then either:")
        print("    python upload_to_hf.py results.json --token hf_xxxxx")
        print("  Or:")
        print("    set HF_TOKEN=hf_xxxxx")
        print("    python upload_to_hf.py results.json")
        sys.exit(1)

    ok = upload_to_hf(args.results_file, args.repo, args.token,
                      args.private, create_pr=not args.direct)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
