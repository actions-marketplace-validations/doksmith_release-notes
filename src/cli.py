import os
import sys
from pathlib import Path
from typing import List

from git_collector import GitCollector
from formatter import MarkdownFormatter
from providers import get_provider, get_available_providers


def load_prompt_template(custom_path: str, action_dir: Path) -> str:
    """Load prompt template from custom path or default template."""
    if custom_path and Path(custom_path).is_file():
        return Path(custom_path).read_text(encoding="utf-8")

    default_file = action_dir / "default-prompt.md"
    if default_file.is_file():
        return default_file.read_text(encoding="utf-8")

    return (
        "Generate a professional, structured changelog in English for version {{VERSION}}.\n\n"
        "Commit History:\n{{COMMIT_LOG}}\n"
    )


def write_github_output(key: str, value: str):
    """Write output variable to GITHUB_OUTPUT environment file."""
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as f:
        if "\n" in value:
            delimiter = "EOF_" + os.urandom(8).hex()
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            f.write(f"{key}={value}\n")


def main():
    action_dir = Path(__file__).resolve().parent.parent

    # Retrieve environment inputs
    version = os.getenv("INPUT_VERSION", "").strip() or os.getenv("GITHUB_REF_NAME", "v1.0.0")
    requested_providers = [
        p.strip().lower()
        for p in os.getenv("INPUT_PROVIDER", "gemini,groq,openai").split(",")
        if p.strip()
    ]
    requested_model = os.getenv("INPUT_MODEL", "").strip()
    output_file_path = os.getenv("INPUT_OUTPUT_FILE", "release-notes.md").strip()
    custom_prompt_path = os.getenv("INPUT_PROMPT_TEMPLATE", "").strip()

    print(f"[Release Notes] Target Version: {version}")
    print(f"[Release Notes] Preferred Providers: {requested_providers}")

    # 1. Collect Git History
    try:
        commit_logs, prev_tag = GitCollector.get_commit_logs(version)
        print(f"[Release Notes] Reference previous tag: {prev_tag or 'Initial release'}")
    except Exception as e:
        print(f"[Release Notes] Error reading git history: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Prepare Prompt
    template = load_prompt_template(custom_prompt_path, action_dir)
    rendered_prompt = template.replace("{{VERSION}}", version).replace("{{COMMIT_LOG}}", commit_logs)
    system_instruction = "You are a professional release manager and software architect writing concise English release notes without emojis."

    # 3. Find and Execute First Available Provider
    notes = None
    used_provider = None
    used_model = None

    for prov_name in requested_providers:
        provider = get_provider(prov_name)
        if not provider:
            print(f"[Release Notes] Unknown provider: '{prov_name}'. Available: {get_available_providers()}")
            continue

        if not provider.is_configured():
            print(f"[Release Notes] Provider '{prov_name}' skipped (missing API credentials).")
            continue

        try:
            print(f"[Release Notes] Querying models list endpoint for '{prov_name}'...")
            resolved_model = provider.resolve_model(requested_model)
            print(f"[Release Notes] Resolved active model: {resolved_model}")

            print(f"[Release Notes] Generating release notes using {prov_name} ({resolved_model})...")
            raw_notes = provider.generate_release_notes(rendered_prompt, system_instruction, resolved_model)
            if raw_notes and raw_notes.strip():
                notes = MarkdownFormatter.sanitize(raw_notes)
                notes = MarkdownFormatter.append_footer(notes, prov_name, resolved_model)
                used_provider = prov_name
                used_model = resolved_model
                break
        except Exception as e:
            print(f"[Release Notes] Provider '{prov_name}' failed: {e}. Trying next provider...", file=sys.stderr)

    if not notes:
        print("[Release Notes] Fatal: All configured AI providers failed or no provider was configured.", file=sys.stderr)
        sys.exit(1)

    # 4. Save to Output File
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(notes, encoding="utf-8")
    print(f"[Release Notes] Successfully written to {output_path.resolve()}")

    # 5. Set GitHub Action Outputs
    write_github_output("notes_path", str(output_path))
    write_github_output("notes_content", notes)
    write_github_output("provider_used", used_provider)
    write_github_output("model_used", used_model)


if __name__ == "__main__":
    main()
