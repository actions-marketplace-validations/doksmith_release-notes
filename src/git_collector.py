"""
Doksmith Release Notes Engine: Git Context & Log Collector.
Extracts commit ranges, author mentions, and commit URL references.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class GitCommit:
    sha: str
    subject: str
    author: str

    def to_markdown(self, base_repo_url: str) -> str:
        commit_link = f"[`{self.sha}`]({base_repo_url}/commit/{self.sha})"
        return f"- {commit_link} - {self.subject} (@{self.author})"


class GitContextCollector:
    """Discovers git repository metadata, tags, and commits."""

    @staticmethod
    def execute(*args: str) -> str:
        try:
            res = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout.strip()
        except OSError as err:
            print(f"[release-notes] Warning: git {args[0]} failed: {err}")
            return ""

    @classmethod
    def resolve_repository_url(cls) -> str:
        remote = cls.execute("remote", "get-url", "origin")
        if not remote:
            return "https://github.com/doksmith/release-notes"
        clean = re.sub(r"^git@github\.com:", "https://github.com/", remote)
        return re.sub(r"\.git$", "", clean)

    @classmethod
    def find_previous_tag(cls, current_version: str) -> Optional[str]:
        raw_tags = cls.execute("tag", "--sort=-creatordate")
        if not raw_tags:
            return None

        for tag_entry in raw_tags.splitlines():
            tag = tag_entry.strip()
            if tag == current_version:
                continue
            # Ignore pre-releases or dev tags
            if re.search(r"-(alpha|beta|rc|dev|staged)", tag, re.IGNORECASE):
                continue
            if re.match(r"^v?\d+\.\d+\.\d+", tag):
                return tag
        return None

    @classmethod
    def collect_commits(cls, target_version: str) -> Tuple[Optional[str], List[GitCommit]]:
        prev_tag = cls.find_previous_tag(target_version)
        target_ref = target_version
        if not cls.execute("rev-parse", "--verify", f"{target_version}^{{commit}}"):
            target_ref = "HEAD"

        rev_range = f"{prev_tag}..{target_ref}" if prev_tag else target_ref
        raw_log = cls.execute("log", rev_range, "--pretty=format:%h|%s|%an")

        commits: List[GitCommit] = []
        for line in raw_log.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 2)
            sha = parts[0].strip() if len(parts) > 0 else "unknown"
            subject = parts[1].strip() if len(parts) > 1 else ""
            author = parts[2].strip() if len(parts) > 2 else "contributor"
            commits.append(GitCommit(sha=sha, subject=subject, author=author))

        return prev_tag, commits
