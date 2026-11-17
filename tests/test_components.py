import unittest
from unittest.mock import patch, MagicMock
from src.providers import get_provider, get_available_providers
from src.formatter import MarkdownFormatter


class TestReleaseNotesAction(unittest.TestCase):
    def test_registry(self):
        providers = get_available_providers()
        self.assertIn("gemini", providers)
        self.assertIn("groq", providers)
        self.assertIn("openai", providers)

    def test_markdown_formatter_sanitization(self):
        sample = "# Release Notes 🚀\n\n- Fix issue 🐛 and improve speed ⚡."
        cleaned = MarkdownFormatter.sanitize(sample)
        self.assertNotIn("🚀", cleaned)
        self.assertNotIn("🐛", cleaned)
        self.assertNotIn("⚡", cleaned)
        self.assertIn("Fix issue", cleaned)

    @patch("src.providers.groq.GroqProvider._get_client")
    def test_groq_model_resolution(self, mock_client_getter):
        mock_client = MagicMock()
        mock_model_1 = MagicMock()
        mock_model_1.id = "llama-3.3-70b-versatile"
        mock_model_1.active = True

        mock_model_2 = MagicMock()
        mock_model_2.id = "llama-3.1-8b-instant"
        mock_model_2.active = True

        mock_resp = MagicMock()
        mock_resp.data = [mock_model_1, mock_model_2]
        mock_client.models.list.return_value = mock_resp
        mock_client_getter.return_value = mock_client

        provider = get_provider("groq")
        provider.api_key = "dummy_key"
        selected = provider.resolve_model()
        self.assertEqual(selected, "llama-3.3-70b-versatile")

    @patch("src.providers.gemini.GeminiProvider._get_client")
    def test_gemini_model_resolution(self, mock_client_getter):
        mock_client = MagicMock()
        mock_item_1 = MagicMock()
        mock_item_1.name = "models/gemini-3.5-flash"
        mock_item_1.supported_generation_methods = ["generateContent"]

        mock_item_2 = MagicMock()
        mock_item_2.name = "models/gemini-3.8-flash"
        mock_item_2.supported_generation_methods = ["generateContent"]

        mock_client.models.list.return_value = [mock_item_1, mock_item_2]
        mock_client_getter.return_value = mock_client

        provider = get_provider("gemini")
        provider.api_key = "dummy_key"
        selected = provider.resolve_model()
        # Should pick 3.5 over 3.8 as per policy (latest -> minor 3.x terkecil)
        self.assertEqual(selected, "gemini-3.5-flash")

    @patch("src.providers.openai_compat.OpenAIProvider._get_client")
    def test_openai_model_resolution(self, mock_client_getter):
        mock_client = MagicMock()
        mock_item = MagicMock()
        mock_item.id = "gpt-4o-mini"
        mock_resp = MagicMock()
        mock_resp.data = [mock_item]
        mock_client.models.list.return_value = mock_resp
        mock_client_getter.return_value = mock_client

        provider = get_provider("openai")
        provider.api_key = "dummy_key"
        selected = provider.resolve_model()
        self.assertEqual(selected, "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()
