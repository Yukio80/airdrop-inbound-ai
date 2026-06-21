"""Tests for the hardening module: retry, circuit breaker, state machine."""
import time
import json
import os
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.hardening.retry import retry, retry_async
from src.hardening.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from src.hardening.state_machine import StateMachine


# =============================================================================
# Retry (sync)
# =============================================================================

class TestRetry:
    def test_success_first_attempt(self):
        calls = 0

        @retry(max_attempts=3, delay=0.01)
        def ok():
            nonlocal calls
            calls += 1
            return "done"

        assert ok() == "done"
        assert calls == 1

    def test_retry_then_succeed(self):
        calls = 0

        @retry(max_attempts=3, delay=0.01)
        def flaky():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert calls == 3

    def test_exhaust_retries(self):
        @retry(max_attempts=2, delay=0.01)
        def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always_fails()

    def test_custom_exception_filter(self):
        @retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        def raises_typeerror():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raises_typeerror()

    def test_preserves_return_value(self):
        @retry(max_attempts=3, delay=0.01)
        def returns_list():
            return [1, 2, 3]

        assert returns_list() == [1, 2, 3]

    def test_preserves_args_and_kwargs(self):
        @retry(max_attempts=2, delay=0.01)
        def capture(*args, **kwargs):
            return (args, kwargs)

        result = capture(1, 2, key="val")
        assert result == ((1, 2), {"key": "val"})


# =============================================================================
# Circuit Breaker
# =============================================================================

class TestCircuitBreaker:
    def test_closed_passes_through(self):
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1)
        result = cb.call(lambda x: x + 1, 2)
        assert result == 3
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60)

        def fail():
            raise ValueError("nope")

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(fail)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_open_blocks_calls(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=60)

        def fail():
            raise ValueError("nope")

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail)

        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not reach")

    def test_fallback_on_open(self):
        cb = CircuitBreaker(
            name="test", failure_threshold=2, recovery_timeout=60,
            fallback=lambda *a, **kw: "fallback_value",
        )

        def fail():
            raise ValueError("nope")

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail)

        result = cb.call(lambda x: x, "ignored")
        assert result == "fallback_value"

    def test_half_open_recovers(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)

        def fail():
            raise ValueError("nope")

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail)

        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_fails_again(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)

        def fail():
            raise ValueError("nope")

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail)

        time.sleep(0.15)

        with pytest.raises(ValueError):
            cb.call(fail)

        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60)

        def fail():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            cb.call(fail)

        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

        result = cb.call(lambda: "working")
        assert result == "working"

    def test_stats(self):
        cb = CircuitBreaker(name="test_stats", failure_threshold=2, recovery_timeout=60)

        def fail():
            raise ValueError("nope")

        def ok():
            return "ok"

        cb.call(ok)
        with pytest.raises(ValueError):
            cb.call(fail)

        stats = cb.stats
        assert stats["name"] == "test_stats"
        assert stats["state"] == "closed"
        assert stats["total_calls"] == 2
        assert stats["total_failures"] == 1
        assert stats["failure_count"] == 1

    def test_thread_safety(self):
        cb = CircuitBreaker(name="thread_test", failure_threshold=5, recovery_timeout=60)
        errors = []

        def fail():
            raise ValueError("nope")

        threads = []
        for _ in range(10):
            t = threading.Thread(target=lambda: (
                errors.append("ok") if cb.call(lambda: "ok") is None else None
            ))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have any threading-related state corruption
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# =============================================================================
# State Machine
# =============================================================================

class TestStateMachine:
    def test_default_state(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert sm.last_run is None
        assert sm.completed_steps == []

    def test_mark_step_complete(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.mark_step_complete("galxe_scan")
        assert "galxe_scan" in sm.completed_steps

    def test_is_step_complete(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert not sm.is_step_complete("lz_bridge")
        sm.mark_step_complete("lz_bridge")
        assert sm.is_step_complete("lz_bridge")

    def test_duplicate_step(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.mark_step_complete("step_a")
        sm.mark_step_complete("step_a")
        assert sm.completed_steps == ["step_a"]

    def test_reset_steps(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.mark_step_complete("scan")
        sm.mark_step_complete("bridge")
        sm.reset_steps()
        assert sm.completed_steps == []

    def test_last_run(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert sm.last_run is None
        sm.last_run = "2026-06-21T12:00:00"
        assert sm.last_run == "2026-06-21T12:00:00"

    def test_protocol_state(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.set_protocol_state("aave", {"last_run": "2026-06-21", "status": "ok"})
        state = sm.get_protocol_state("aave")
        assert state["status"] == "ok"

    def test_protocol_failure_tracking(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert not sm.should_skip_protocol("bad_proto", max_failures=3)
        sm.mark_protocol_failure("bad_proto", "connection error")
        sm.mark_protocol_failure("bad_proto", "timeout")
        assert not sm.should_skip_protocol("bad_proto", max_failures=3)
        sm.mark_protocol_failure("bad_proto", "rpc error")
        assert sm.should_skip_protocol("bad_proto", max_failures=3)

    def test_protocol_success_resets_failures(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.mark_protocol_failure("compound", "error1")
        sm.mark_protocol_failure("compound", "error2")
        sm.mark_protocol_success("compound")
        assert not sm.should_skip_protocol("compound", max_failures=3)

    def test_bridge_routes(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.add_bridge_route_used("arbitrum", "base")
        sm.add_bridge_route_used("optimism", "arbitrum")
        routes = sm._data["bridge_routes_used"]
        assert len(routes) == 2
        assert routes[0]["from"] == "arbitrum"

    def test_lz_route_index(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert sm.lz_last_route_index == 0
        sm.lz_last_route_index = 2
        assert sm.lz_last_route_index == 2

    def test_generic_kv(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        assert sm.get("nonexistent", "default") == "default"
        sm.set("custom_key", 42)
        assert sm.get("custom_key") == 42

    def test_persistence_across_instances(self, tmp_path):
        p = tmp_path / "persist.json"
        sm1 = StateMachine(state_path=p)
        sm1.mark_step_complete("step_one")
        sm1.last_run = "2026-06-21T10:00:00"
        sm1.set("score", 95)

        sm2 = StateMachine(state_path=p)
        assert sm2.is_step_complete("step_one")
        assert sm2.last_run == "2026-06-21T10:00:00"
        assert sm2.get("score") == 95

    def test_reset_all(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "state.json")
        sm.mark_step_complete("test")
        sm.last_run = "now"
        sm.reset()
        assert sm.completed_steps == []
        assert sm.last_run is None

    def test_corrupted_file(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("not json")
        sm = StateMachine(state_path=p)
        assert sm.completed_steps == []

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("")
        sm = StateMachine(state_path=p)
        assert sm.completed_steps == []


# =============================================================================
# Integration: retry + circuit breaker together
# =============================================================================

class TestHardeningIntegration:
    def test_retry_wraps_circuit_breaker_call(self):
        """Retry handles intermediate failures, circuit opens on persistent failure."""
        cb = CircuitBreaker(name="integ", failure_threshold=3, recovery_timeout=0.1)
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("nope")
            return "ok"

        @retry(max_attempts=3, delay=0.01)
        def retried_flaky():
            return cb.call(flaky_func)

        result = retried_flaky()
        assert result == "ok"
        assert call_count == 3
        assert cb.state == CircuitState.CLOSED

    def test_state_machine_tracks_bridge_with_circuit_breaker(self, tmp_path):
        sm = StateMachine(state_path=tmp_path / "integ.json")
        cb = CircuitBreaker(name="lz_bridge", failure_threshold=2, recovery_timeout=60)

        def failing_bridge():
            raise ConnectionError("rpc timeout")

        # Two failures -> circuit opens
        for _ in range(2):
            with pytest.raises(ConnectionError):
                cb.call(failing_bridge)

        sm.mark_protocol_failure("layerzero", "rpc timeout")
        sm.mark_protocol_failure("layerzero", "rpc timeout")

        assert cb.state == CircuitState.OPEN
        assert sm.should_skip_protocol("layerzero", max_failures=2)
