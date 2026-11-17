# AI Release Notes Generator (`doksmith/release-notes`)

A modern, modular, production-ready GitHub Action that generates clean, professional release notes from your Git commit history using official AI SDKs (**Google Gemini**, **Groq**, or **OpenAI**).

---

## Key Features

- **Standard GitHub Action Call**: Use directly as `uses: doksmith/release-notes@v1` anywhere in your release jobs.
- **Up-to-Date Major Stack**: Runs on `actions/setup-python@v7` and `actions/checkout@v7`.
- **Live Models Discovery**: Dynamically queries `client.models.list()` via official SDKs (`google-genai`, `groq`, `openai`).
- **Resilient Fallback Policy**:
  - **Gemini**: Prioritizes `gemini-flash-latest`, followed by minor 3.x versions (`3.5` -> `3.6` -> `3.7` -> `3.8`) to avoid both 5xx capacity overloads and 4xx deprecation.
  - **Groq**: Prioritizes token-efficient direct models (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) before heavy reasoning models like `openai/gpt-oss-20b`.
  - **OpenAI**: Prioritizes `gpt-4o-mini` and `gpt-4o`.
- **Sanitized Markdown**: Strictly removes native emojis and formats clean technical categories.

---

## Quick Start

```yaml
name: Release

on:
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Generate AI Release Notes
        id: notes
        uses: doksmith/release-notes@v1
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          groq-api-key: ${{ secrets.GROQ_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}

      - name: Publish GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAG: ${{ github.ref_name }}
        run: |
          gh release create "${TAG}" \
            --title "${TAG}" \
            --notes-file "${{ steps.notes.outputs.notes_path }}" \
            --verify-tag
```

---

## Inputs

| Input | Description | Default |
| :--- | :--- | :--- |
| `version` | Target release version / tag | `${{ github.ref_name }}` |
| `provider` | Preferred provider order | `gemini,groq,openai` |
| `model` | Explicit model ID (leave empty for live dynamic resolution) | `""` |
| `output-file` | Destination markdown file path | `release-notes.md` |
| `prompt-template` | Optional custom prompt markdown file | *Default prompt* |
| `gemini-api-key` | Google Gemini API Key | `""` |
| `groq-api-key` | Groq API Key | `""` |
| `openai-api-key` | OpenAI API Key | `""` |

---

## Outputs

| Output | Description |
| :--- | :--- |
| `notes_path` | File path of the generated release notes |
| `notes_content` | Raw markdown content |
| `provider_used` | Provider that generated the release notes |
| `model_used` | Resolved active model name |

---

## License

MIT License. See [LICENSE](LICENSE) for details.
