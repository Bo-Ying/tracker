import json
from types import SimpleNamespace

import anthropic
import httpx

from tracker.translate import TranslationCache, translate_all


class FakeMessages:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        result = self.behaviour(kwargs)
        if isinstance(result, Exception):
            raise result
        return result


def fake_client(behaviour):
    return SimpleNamespace(messages=FakeMessages(behaviour))


def ok_response(kwargs):
    lines = kwargs["messages"][0]["content"].split("\n")[1:]
    items = [json.loads(line) for line in lines]
    body = {"translations": [{"index": it["index"], "zh": "中:" + it["text"]} for it in items]}
    return SimpleNamespace(stop_reason="end_turn",
                           content=[SimpleNamespace(type="text", text=json.dumps(body))])


def status_error(cls, code):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx.Response(code, request=req), body=None)


def test_translates_and_caches(tmp_path):
    cache = TranslationCache(tmp_path / "t.json")
    client = fake_client(ok_response)
    report = translate_all(["a", "b", "a", ""], cache, "m", client)
    assert report.translated == 2 and report.config_error is None
    assert cache.data == {"a": "中:a", "b": "中:b"}

    report = translate_all(["a", "b"], cache, "m", client)
    assert report.cached == 2 and client.messages.calls == 1


def test_retired_model_is_config_error(tmp_path):
    cache = TranslationCache(tmp_path / "t.json")
    client = fake_client(lambda kw: status_error(anthropic.NotFoundError, 404))
    report = translate_all(["a"], cache, "m", client)
    assert report.config_error and "404" in report.config_error
    assert cache.data == {}


def test_bad_key_is_config_error(tmp_path):
    client = fake_client(lambda kw: status_error(anthropic.AuthenticationError, 401))
    report = translate_all(["a"], TranslationCache(tmp_path / "t.json"), "m", client)
    assert report.config_error


def test_overload_is_transient(tmp_path):
    client = fake_client(lambda kw: status_error(anthropic.InternalServerError, 529))
    report = translate_all(["a"], TranslationCache(tmp_path / "t.json"), "m", client)
    assert report.config_error is None and report.transient_errors


def test_refusal_is_transient(tmp_path):
    client = fake_client(lambda kw: SimpleNamespace(stop_reason="refusal", content=[]))
    report = translate_all(["a"], TranslationCache(tmp_path / "t.json"), "m", client)
    assert report.config_error is None and report.transient_errors


def test_missing_key_is_config_error(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    report = translate_all(["a"], TranslationCache(tmp_path / "t.json"), "m")
    assert report.config_error == "ANTHROPIC_API_KEY is not set"
