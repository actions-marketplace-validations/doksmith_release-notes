"""
Doksmith Release Notes Engine: Orchestrator CLI.
Coordinates Git discovery, AI inference, and markdown assembly.
"""

import os
import sys
from pathlib import Path
from typing import List

from git_collector import GitContextCollector, GitCommit
from formatter import ChangelogBuilder
from providers import get_provider, get_available_providers


def render_prompt(template_path: str, version: str, commits: List[GitCommit]) -> str:
    path_obj = Path(template_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    raw_template = path_obj.read_text(encoding="utf-8")
    commit_lines = "\n".join(f"- {c.subject}" for c in commits) if commits else "- Initial project setup"

    return raw_template.replace("{{COMMIT_LOG}}", commit_lines).replace("{{VERSION}}", version)


def export_github_output(key: str, value: str):
    gh_output = os.getenv("GITHUB_OUTPUT")
    if not gh_output:
        return
    with open(gh_output, "a", encoding="utf-8") as f:
        if "\n" in value:
            delimiter = "EOF_" + os.urandom(8).hex()
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            f.write(f"{key}={value}\n")


def generate_fallback_summary(version: str, prev_tag: str, commits: List[GitCommit]) -> str:
    items = "\n".join(f"- {c.subject}" for c in commits) if commits else "- Initial release"
    scope = f" since {prev_tag}" if prev_tag else ""
    return f"## Release {version}\n\n### Changes{scope}\n{items}"


def main():
    action_root = Path(__file__).resolve().parent.parent

    # Resolve target version
    target_version = (
        os.getenv("INPUT_VERSION", "").strip()
        or os.getenv("VERSION", "").strip()
        or (sys.argv[1] if len(sys.argv) > 1 else "HEAD")
    )

    # Resolve destination path
    dest_path_str = (
        os.getenv("INPUT_OUTPUT_FILE", "").strip()
        or os.getenv("OUTPUT_PATH", "").strip()
        or (sys.argv[2] if len(sys.argv) > 2 else "release-notes.md")
    )

    # Resolve prompt template
    template_file = (
        os.getenv("INPUT_PROMPT_TEMPLATE", "").strip()
        or os.getenv("PROMPT_TEMPLATE", "").strip()
        or str(action_root / "default-prompt.md")
    )

    # Provider prioritization
    providers_order = [
        p.strip().lower()
        for p in os.getenv("INPUT_PROVIDER", "gemini,groq,openai").split(",")
        if p.strip()
    ]
    explicit_model = os.getenv("INPUT_MODEL", "").strip()

    # 1. Discover Repository & Commit History
    repo_url = GitContextCollector.resolve_repository_url()
    prev_tag, commits = GitContextCollector.collect_commits(target_version)

    print(f"[release-notes] Target Version: {target_version}")
    print(f"[release-notes] Repository URL: {repo_url}")
    print(f"[release-notes] Baseline Tag: {prev_tag or 'Root commit (Initial release)'}")
    print(f"[release-notes] Commits in scope: {len(commits)}")

    # 2. Render Prompt
    try:
        final_prompt = render_prompt(template_file, target_version, commits)
    except Exception as e:
        print(f"[release-notes] Warning loading template: {e}")
        final_prompt = None

    # 3. AI Execution with Registry Fallback
    summary_text = None
    successful_provider = None
    successful_model = None

    if final_prompt:
        for prov_name in providers_order:
            provider = get_provider(prov_name)
            if not provider or not provider.is_configured():
                continue

            try:
                print(f"[release-notes] Introspecting live models for '{prov_name}'...")
                active_model = provider.resolve_model(explicit_model)
                print(f"[release-notes] Selected verified model: {active_model}")

                system_spec = (
                    "You are an expert release manager generating concise, professional release notes without emojis."
                )
                print(f"[release-notes] Generating release notes using {prov_name} ({active_model})...")
                generated = provider.generate_release_notes(final_prompt, system_spec, active_model)

                if generated and generated.strip():
                    summary_text = generated.strip()
                    successful_provider = prov_name
                    successful_model = active_model
                    break
            except Exception as e:
                print(f"[release-notes] Provider '{prov_name}' failed: {e}. Trying fallback...", file=sys.stderr)

    # Fallback if all providers failed or unconfigured
    if not summary_text:
        print("[release-notes] Falling back to local commit listing.")
        summary_text = generate_fallback_summary(target_version, prev_tag, commits)
        successful_provider = "local"
        successful_model = "git-log"

    # 4. Assemble Final Document (ATM Design)
    final_document = ChangelogBuilder.assemble_release_document(
        summary_markdown=summary_text,
        commits=commits,
        repo_url=repo_url,
        provider_name=successful_provider,
        model_name=successful_model,
    )

    # 5. Write to File & GitHub Outputs
    dest_path = Path(dest_path_str).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(final_document, encoding="utf-8")
    print(f"[release-notes] Release notes successfully generated at: {dest_path}")

    export_github_output("notes_path", str(dest_path))
    export_github_output("notes_content", final_document)
    export_github_output("provider_used", successful_provider)
    export_github_output("model_used", successful_model)


if __name__ == "__main__":
    main()
