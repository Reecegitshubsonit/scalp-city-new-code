from types import SimpleNamespace

import pytest

from scalpcity.webull_client import WebullClient


def make(fail_times, message="HTTP Status: 429, Code: TOO_MANY_REQUESTS, Msg: Too many requests"):
    calls = {"n": 0}
    sleeps = []

    def get_history_bar(*a, **k):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError(message)
        return SimpleNamespace(json=lambda: {"result": [{"symbol": "QQQ", "result": []}]})

    data = SimpleNamespace(market_data=SimpleNamespace(get_history_bar=get_history_bar))
    client = WebullClient(data, SimpleNamespace(), sleep=sleeps.append, clock=lambda: 1000.0)
    return client, calls, sleeps


def test_retries_on_429_then_succeeds():
    client, calls, sleeps = make(2)
    assert client.recent_bars("QQQ", 3) == []
    assert calls["n"] == 3 and len(sleeps) >= 2 and sleeps[-1] > 0


def test_gives_up_after_repeated_429():
    client, calls, _ = make(99)
    with pytest.raises(RuntimeError):
        client.recent_bars("QQQ", 3)
    assert calls["n"] == 5


def test_other_errors_are_not_retried():
    client, calls, _ = make(99, message="HTTP Status: 401, Code: UNAUTHORIZED")
    with pytest.raises(RuntimeError):
        client.recent_bars("QQQ", 3)
    assert calls["n"] == 1


def test_calls_are_spaced_by_min_interval():
    client, _, sleeps = make(0)
    client.recent_bars("QQQ", 3)
    client.recent_bars("QQQ", 3)
    assert any(abs(s - 0.5) < 1e-9 for s in sleeps)       # clock is frozen, so the second call must wait the full interval
