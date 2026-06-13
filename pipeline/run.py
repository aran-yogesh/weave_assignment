"""Run the full offline pipeline: extract 90 days of PRs, then compute metrics.

Usage (from the pipeline/ dir):
    python run.py            # extract (resumable) + compute -> frontend/public/data.json

Requires a GitHub token via `gh auth token` or the GITHUB_TOKEN env var.
"""

import extract
import metrics


def main() -> None:
    """Extract PRs then compute the dashboard data in one shot."""
    print("[1/2] Extracting PRs from GitHub …")
    extract.main()
    print("\n[2/2] Computing impact metrics …")
    metrics.main()


if __name__ == "__main__":
    main()
