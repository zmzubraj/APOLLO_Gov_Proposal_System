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


def test_discord_poll_messages():
    with patch("src.execution.discord_bot.requests.get") as get:
        get.return_value.ok = True
        get.return_value.json.return_value = [{"content": "msg"}]
        msgs = discord_bot.poll_messages("123", token="tok")
        assert msgs == ["msg"]
        get.assert_called_once_with(
            "https://discord.com/api/v10/channels/123/messages",
            headers={"Authorization": "Bot tok"},
            params={"limit": 50},
            timeout=10,
        )


def test_telegram_poll_messages():
    with patch("src.execution.telegram_bot.requests.get") as get:
        get.return_value.ok = True
        get.return_value.json.return_value = {
            "result": [
                {"message": {"chat": {"id": "c"}, "text": "hi"}},
                {"message": {"chat": {"id": "other"}, "text": "skip"}},
            ]
        }
        msgs = telegram_bot.poll_messages(token="TOKEN", chat_id="c")
        assert msgs == ["hi"]
        get.assert_called_once_with(
            "https://api.telegram.org/botTOKEN/getUpdates",
            params={"limit": 50},
            timeout=10,
        )


def test_twitter_poll_messages():
    with patch("src.execution.twitter_bot.requests.get") as get:
        get.return_value.ok = True
        get.return_value.json.return_value = {"data": [{"text": "tw"}]}
        msgs = twitter_bot.poll_messages("dot", bearer_token="tok")
        assert msgs == ["tw"]
        get.assert_called_once_with(
            "https://api.twitter.com/2/tweets/search/recent",
            headers={"Authorization": "Bearer tok"},
            params={"query": "dot", "max_results": 10},
            timeout=10,
        )
