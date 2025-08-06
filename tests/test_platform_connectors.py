"""Tests for social platform connector payloads."""
from __future__ import annotations

from unittest.mock import patch

import src.execution.discord_bot as discord_bot
import src.execution.telegram_bot as telegram_bot
import src.execution.twitter_bot as twitter_bot


def test_discord_payload():
    with patch("src.execution.discord_bot.requests.post") as post:
        post.return_value.ok = True
        assert discord_bot.post_summary("hello", webhook_url="url") is True
        post.assert_called_once_with("url", json={"content": "hello"})


def test_telegram_payload():
    with patch("src.execution.telegram_bot.requests.post") as post:
        post.return_value.ok = True
        assert telegram_bot.post_summary("hi", token="TOKEN", chat_id="c") is True
        post.assert_called_once_with(
            "https://api.telegram.org/botTOKEN/sendMessage",
            json={"chat_id": "c", "text": "hi"},
        )


def test_twitter_payload():
    with patch("src.execution.twitter_bot.requests.post") as post:
        post.return_value.ok = True
        assert twitter_bot.post_summary("tweet", bearer_token="tok") is True
        post.assert_called_once_with(
            "https://api.twitter.com/2/tweets",
            json={"text": "tweet"},
            headers={"Authorization": "Bearer tok"},
        )
