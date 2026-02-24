"""Tests for utils/helpers.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from utils.helpers import (
    EmbedData,
    message_extractor,
    make_hash,
    is_from_isekaid,
    is_in_channel,
    contains_keywords,
    get_embed_field_value,
)


class TestEmbedData:
    """Tests for EmbedData class."""

    def test_default_values(self):
        """Test default values."""
        data = EmbedData()
        assert data.id == ""
        assert data.author == ""
        assert data.title == ""
        assert data.desc == ""
        assert data.content == ""
        assert data.fields == []

    def test_with_values(self):
        """Test creating with values."""
        data = EmbedData(
            id="123",
            title="Test Title",
            desc="Test Description",
        )
        assert data.id == "123"
        assert data.title == "Test Title"
        assert data.desc == "Test Description"


class TestMessageExtractor:
    """Tests for message_extractor function."""

    def test_extract_basic_message(self, mock_message):
        """Test extracting basic message data."""
        mock_message.content = "test content"

        data = message_extractor(mock_message)

        assert data.id == str(mock_message.id)
        assert data.author == str(mock_message.author.id)
        assert data.content == "test content"

    def test_extract_with_embed(self, mock_message, mock_embed):
        """Test extracting embed data."""
        mock_embed.title = "Embed Title"
        mock_embed.description = "Embed Description"
        mock_message.embeds = [mock_embed]

        data = message_extractor(mock_message)

        assert data.title == "Embed Title"
        assert data.desc == "Embed Description"

    def test_extract_with_fields(self, mock_message, mock_embed):
        """Test extracting embed fields."""
        field = MagicMock()
        field.name = "Field Name"
        field.value = "Field Value"
        field.inline = True
        mock_embed.fields = [field]
        mock_message.embeds = [mock_embed]

        data = message_extractor(mock_message)

        assert len(data.fields) == 1
        assert data.fields[0]["name"] == "Field Name"
        assert data.fields[0]["value"] == "Field Value"

    def test_extract_no_embed(self, mock_message):
        """Test extracting message without embeds."""
        mock_message.embeds = []

        data = message_extractor(mock_message)

        assert data.title == ""
        assert data.desc == ""


class TestMakeHash:
    """Tests for make_hash function."""

    def test_default_length(self):
        """Test default hash length."""
        h = make_hash()
        assert len(h) == 5

    def test_custom_length(self):
        """Test custom hash length."""
        h = make_hash(10)
        assert len(h) == 10

    def test_alphanumeric(self):
        """Test hash contains only alphanumeric characters."""
        h = make_hash(100)
        assert h.isalnum()

    def test_randomness(self):
        """Test that hashes are different."""
        h1 = make_hash()
        h2 = make_hash()
        # Could theoretically be same but very unlikely
        assert h1 != h2 or len(set([make_hash() for _ in range(100)])) > 1


class TestIsFromIsekaid:
    """Tests for is_from_isekaid function."""

    def test_true_for_isekaid(self, mock_message):
        """Test returns True for Isekaid author."""
        mock_message.author.name = "Isekaid"

        assert is_from_isekaid(mock_message) is True

    def test_false_for_other(self, mock_message):
        """Test returns False for other authors."""
        mock_message.author.name = "SomeUser"

        assert is_from_isekaid(mock_message) is False

    def test_false_for_no_author(self, mock_message):
        """Test returns False for missing author."""
        mock_message.author = None

        assert is_from_isekaid(mock_message) is False


class TestIsInChannel:
    """Tests for is_in_channel function."""

    def test_true_for_matching_channel(self, mock_message):
        """Test returns True for matching channel."""
        mock_message.channel.id = 1234567890

        assert is_in_channel(mock_message, "1234567890") is True

    def test_false_for_different_channel(self, mock_message):
        """Test returns False for different channel."""
        mock_message.channel.id = 9999999999

        assert is_in_channel(mock_message, "1234567890") is False


class TestContainsKeywords:
    """Tests for contains_keywords function."""

    def test_single_keyword_found(self):
        """Test finding single keyword."""
        text = "This is a battle message"

        assert contains_keywords(text, ["battle"]) is True

    def test_multiple_keywords_one_found(self):
        """Test with multiple keywords where one matches."""
        text = "Mining Complete!"

        assert contains_keywords(text, ["fishing", "mining", "foraging"]) is True

    def test_no_keywords_found(self):
        """Test when no keywords match."""
        text = "Hello world"

        assert contains_keywords(text, ["battle", "mining"]) is False

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        text = "BATTLE STARTED"

        assert contains_keywords(text, ["battle"]) is True


class TestGetEmbedFieldValue:
    """Tests for get_embed_field_value function."""

    def test_field_found(self, mock_message, mock_embed):
        """Test finding field value."""
        field = MagicMock()
        field.name = "EXP"
        field.value = "+100"
        mock_embed.fields = [field]
        mock_message.embeds = [mock_embed]

        value = get_embed_field_value(mock_message, "EXP")

        assert value == "+100"

    def test_field_not_found(self, mock_message, mock_embed):
        """Test when field doesn't exist."""
        mock_embed.fields = []
        mock_message.embeds = [mock_embed]

        value = get_embed_field_value(mock_message, "NonExistent")

        assert value is None

    def test_no_embeds(self, mock_message):
        """Test when message has no embeds."""
        mock_message.embeds = []

        value = get_embed_field_value(mock_message, "EXP")

        assert value is None
