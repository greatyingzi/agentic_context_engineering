"""
Git history scanner for extracting high-value technical decisions.
Focuses on architectural decisions and significant implementations.
"""

import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


async def scan_git_history(since_months: int = 3, max_commits: int = 20) -> List[Dict]:
    """
    Scan Git history for high-value commits.

    Args:
        since_months: Only look at commits from last N months
        max_commits: Maximum number of commits to analyze
    """
    project_root = Path.cwd()

    # Get commit history with detailed info
    try:
        # Get formatted commit info
        cmd = [
            "git",
            "log",
            f"--since={since_months} months ago",
            "--max-count={max_commits}",
            "--pretty=format:%H|%s|%b|%an|%ad|%P",
            "--date=iso",
            "--no-merges",  # Skip merge commits
        ]

        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            commit = {
                "hash": parts[0],
                "subject": parts[1],
                "body": parts[2],
                "author": parts[3],
                "date": parts[4],
                "parents": parts[4] if len(parts) > 4 else "",
            }

            # Quality filter
            if is_high_value_commit(commit):
                commits.append(commit)

        return commits

    except Exception:
        return []


def is_high_value_commit(commit: Dict) -> bool:
    """Determine if a commit contains valuable knowledge."""

    # Skip if no detailed body
    if not commit["body"] or len(commit["body"].strip()) < 100:
        return False

    # Skip revert commits (handled separately)
    if commit["subject"].startswith("Revert"):
        return False

    # High-value indicators
    subject = commit["subject"].lower()
    body = commit["body"].lower()

    # Look for architectural decisions
    arch_patterns = [
        r"architecture",
        r"redesign",
        r"refactor.*major",
        r"implement.*system",
        r"add.*support for",
        r"migrate.*to",
    ]

    # Look for performance optimizations
    perf_patterns = [
        r"performance",
        r"optimization",
        r"speed.*up",
        r"reduce.*time",
        r"improve.*efficiency",
        r"\+\d+%",  # Performance metrics
    ]

    # Look for important fixes
    fix_patterns = [
        r"fix.*critical",
        r"security",
        r"data.*loss",
        r"memory.*leak",
        r"race.*condition",
    ]

    # Check if any pattern matches
    all_patterns = arch_patterns + perf_patterns + fix_patterns

    for pattern in all_patterns:
        if re.search(pattern, subject + " " + body):
            return True

    # Look for detailed technical explanations
    if has_technical_details(body):
        return True

    return False


def has_technical_details(body: str) -> bool:
    """Check if commit body contains technical details."""

    # Count technical indicators
    indicators = 0

    # Code examples
    if re.search(r"```", body):
        indicators += 2

    # File paths or code references
    if re.search(r"\w+\.\w+:\d+", body):
        indicators += 1

    # Technical terms
    tech_terms = [
        "algorithm",
        "implementation",
        "interface",
        "api",
        "database",
        "cache",
        "queue",
        "thread",
        "async",
        "timeout",
        "retry",
        "fallback",
        "deprecated",
    ]

    for term in tech_terms:
        if term in body:
            indicators += 1

    # Numbers with units (performance metrics)
    if re.search(r"\d+\s*(ms|s|%|mb|kb)", body):
        indicators += 2

    return indicators >= 3


def extract_revert_commits(since_months: int = 3) -> List[Dict]:
    """Extract revert commits as learning opportunities."""

    project_root = Path.cwd()

    try:
        cmd = [
            "git",
            "log",
            f"--since={since_months} months ago",
            "--grep=^Revert",
            "--pretty=format:%H|%s|%b|%an|%ad",
            "--date=iso",
        ]

        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        reverts = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) >= 5:
                reverts.append(
                    {
                        "hash": parts[0],
                        "subject": parts[1],
                        "body": parts[2],
                        "author": parts[3],
                        "date": parts[4],
                        "type": "revert",
                    }
                )

        return reverts

    except Exception:
        return []


async def extract_git_knowledge(playbook: Dict) -> Dict:
    """Extract knowledge from Git history."""

    # Get high-value commits
    valuable_commits = await scan_git_history(since_months=3, max_commits=50)

    # Get revert commits (learning from failures)
    revert_commits = extract_revert_commits(since_months=3)

    # Prepare content for analysis
    git_content = []

    # Process valuable commits
    for commit in valuable_commits[:10]:  # Limit to top 10
        content = f"""
--- Commit: {commit["hash"][:8]} ({commit["date"]}) ---
Subject: {commit["subject"]}

Details:
{commit["body"]}
"""
        git_content.append(content)

    # Process revert commits
    for revert in revert_commits[:5]:  # Limit to top 5
        content = f"""
--- REVERTED: {revert["hash"][:8]} ({revert["date"]}) ---
Subject: {revert["subject"]}

This commit was reverted, indicating the approach did not work.
Details:
{revert["body"]}
"""
        git_content.append(content)

    if not git_content:
        return {"new_key_points": [], "merged_key_points": []}

    # Extract knowledge using Git-specific prompt
    from common import extract_keypoints

    messages = [{"role": "user", "content": "\n\n".join(git_content)}]

    extraction_result = await extract_keypoints(messages, playbook, "git_extraction")

    # Add source information
    for point in extraction_result.get("new_key_points", []):
        point["source_type"] = "git_history"
        point["confidence"] = "medium"  # Git knowledge needs validation

    return extraction_result
