import subprocess
from typing import Optional, Tuple


class GitCollector:
    """Collects git commit history and tags from repository."""

    @staticmethod
    def _run_git(*args: str) -> str:
        cmd = ["git"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    @classmethod
    def get_latest_commit_sha(cls) -> str:
        try:
            return cls._run_git("rev-parse", "--short", "HEAD")
        except subprocess.SubprocessError:
            return "unknown"

    @classmethod
    def get_previous_tag(cls, current_ref: Optional[str] = None) -> Optional[str]:
        """Find the most recent tag before current_ref."""
        target = current_ref or "HEAD"
        try:
            # Describe closest tag reachable before target
            return cls._run_git("describe", "--tags", "--abbrev=0", f"{target}^")
        except subprocess.SubprocessError:
            try:
                # If target itself is a tag or only 1 tag exists
                tags = cls._run_git("tag", "--sort=-creatordate").splitlines()
                if len(tags) > 1:
                    return tags[1]
            except subprocess.SubprocessError:
                pass
            return None

    @classmethod
    def get_commit_logs(cls, target_version: str) -> Tuple[str, Optional[str]]:
        """
        Extract commit logs between previous tag and target version.
        Returns (commit_log_str, previous_tag).
        """
        prev_tag = cls.get_previous_tag(target_version)

        try:
            if prev_tag:
                rev_range = f"{prev_tag}..HEAD"
                logs = cls._run_git("log", rev_range, "--pretty=format:%h - %s (%an)")
            else:
                # First release: fetch all commits up to HEAD (up to 150 commits)
                logs = cls._run_git("log", "-n", "150", "--pretty=format:%h - %s (%an)")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to retrieve git commit logs: {e}") from e

        if not logs.strip():
            # Fallback if no commits in range
            logs = cls._run_git("log", "-n", "10", "--pretty=format:%h - %s (%an)")

        return logs.strip(), prev_tag
