"""Tests for transcript summarization."""

from unittest.mock import MagicMock, patch

import pytest

from yt_summary.summarizer import SummarizerError, summarize_transcript


class TestSummarizeTranscript:
    """Test transcript summarization using Claude API."""

    @patch("yt_summary.summarizer.anthropic.Anthropic")
    def test_summarize_transcript_success(self, mock_anthropic_class) -> None:
        """Successfully summarize a transcript."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""SUMMARY:
A great video about AI.

TOP TAKEAWAYS:
- Point one
- Point two
- Point three

PROTOCOLS & INSTRUCTIONS:
None mentioned."""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = summarize_transcript("Sample transcript", "test-api-key")

        assert "great video about AI" in result
        assert "Point one" in result
        assert "Point two" in result
        assert "Point three" in result

    @patch("yt_summary.summarizer.anthropic.Anthropic")
    def test_summarize_with_custom_model(self, mock_anthropic_class) -> None:
        """Use custom Claude model for summarization."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="SUMMARY:\nTest summary")]
        mock_client.messages.create.return_value = mock_response

        summarize_transcript("Sample transcript", "test-api-key", model="claude-opus-4-6")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"

    @patch("yt_summary.summarizer.anthropic.Anthropic")
    def test_summarize_api_error_raises_error(self, mock_anthropic_class) -> None:
        """Raise SummarizerError on API failure."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Rate limit exceeded")

        with pytest.raises(SummarizerError, match="Claude API error"):
            summarize_transcript("Sample transcript", "test-api-key")


class TestSummarizerError:
    """Test SummarizerError exception."""

    def test_summarizer_error_message(self) -> None:
        """SummarizerError stores error message."""
        error = SummarizerError("Test error message")
        assert str(error) == "Test error message"

    @patch("yt_summary.summarizer.anthropic.Anthropic")
    def test_summarize_empty_transcript(self, mock_anthropic_class) -> None:
        """Summarize empty transcript."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="SUMMARY:\nEmpty transcript provided.")]
        mock_client.messages.create.return_value = mock_response

        result = summarize_transcript("", "test-api-key")

        assert "Empty" in result
        # Should still work even with empty input

    @patch("yt_summary.summarizer.anthropic.Anthropic")
    def test_summarize_unicode_transcript(self, mock_anthropic_class) -> None:
        """Summarize transcript with unicode characters."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""SUMMARY:
Unicode test

TOP TAKEAWAYS:
- Contains 世界
- Has émojis 🌍

PROTOCOLS & INSTRUCTIONS:
None mentioned."""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        result = summarize_transcript("Hello 世界 🌍", "test-api-key")

        assert "世界" in result
        # Verify API was called with unicode
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "世界" in call_kwargs["messages"][0]["content"]
