"""Tests for the connector manifest schema + BaseConnector helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.connectors.base import (
    BaseConnector,
    Manifest,
    Retrieval,
    Runtime,
    Source,
    Tool,
)


def _valid_manifest(**overrides) -> Manifest:
    data = dict(
        id="fixture",
        category="utility",
        source=Source(
            name="Fixture API",
            type="official",
            url="https://example.com",
            refresh="realtime",
        ),
        tools=[
            Tool(
                name="do_thing",
                handler="do_thing",
                description="Does the thing for testing.",
                retrieval=Retrieval(
                    summary="A fixture tool used only in unit tests for the registry.",
                    example_queries=["q1", "q2", "q3"],
                ),
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ],
    )
    data.update(overrides)
    return Manifest(**data)


class TestManifestValidation:
    def test_happy_path(self):
        m = _valid_manifest()
        assert m.id == "fixture"
        assert m.pod == "app"  # default
        assert m.tools[0].name == "do_thing"

    def test_rejects_unknown_category(self):
        with pytest.raises(ValidationError):
            _valid_manifest(category="made-up")

    def test_rejects_unknown_pod(self):
        with pytest.raises(ValidationError):
            _valid_manifest(pod="gpu")

    def test_rejects_unknown_source_type(self):
        with pytest.raises(ValidationError):
            Source(
                name="x", type="unofficial", url="https://x", refresh="realtime"
            )

    def test_rejects_extra_fields(self):
        # Forbidding extras catches typos in manifest keys at load time.
        with pytest.raises(ValidationError):
            _valid_manifest(pood="app")

    def test_requires_at_least_one_tool(self):
        with pytest.raises(ValidationError):
            _valid_manifest(tools=[])

    def test_retrieval_summary_too_short(self):
        with pytest.raises(ValidationError):
            Retrieval(summary="too short")


class TestBaseConnector:
    def test_subclass_without_manifest_raises(self):
        with pytest.raises(TypeError):
            class Broken(BaseConnector):
                pass

    def test_ok_and_err_envelope(self):
        class Fixture(BaseConnector):
            manifest = _valid_manifest()

        f = Fixture()
        ok = f.ok({"x": 1})
        assert ok == {
            "success": True,
            "data": {"x": 1},
            "source": {"name": "Fixture API", "type": "official"},
            "error": None,
        }

        err = f.err("boom")
        assert err["success"] is False
        assert err["data"] is None
        assert err["error"] == "boom"
        assert err["source"] == {"name": "Fixture API", "type": "official"}


class TestRuntimeDefaults:
    def test_runtime_defaults(self):
        r = Runtime()
        assert r.timeout_s == 10
        assert r.cache_ttl_s == 0
        assert r.failure_mode == "return_error"
        assert r.env == []
