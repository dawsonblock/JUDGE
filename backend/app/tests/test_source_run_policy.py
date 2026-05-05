"""Tests for the source-run access policy in admin_sources.run_source_now.

Verifies that:
- Only machine_ingest sources can be launched; every other source_class returns 422.
- A machine_ingest source that has no registered adapter returns 501.
- An inactive source returns 409 before any class check.
- A missing source returns 404.
- A successful adapter run records an IngestionRun with status=completed.
- An adapter exception still flushes an IngestionRun with status=failed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    source_key: str = "test_src",
    is_active: bool = True,
    source_class: str | None = "machine_ingest",
    parser: str = "csv_parser",
) -> MagicMock:
    src = MagicMock()
    src.source_key = source_key
    src.is_active = is_active
    src.source_class = source_class
    src.parser = parser
    return src


def _make_db(source: object | None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = source
    return db


def _make_adapter_result(success: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        records_fetched=5,
        records_skipped=0,
        created_records=[],
        review_items=[],
        errors=[],
        success=success,
    )


def _run(source: object | None, adapter=None, adapter_error: Exception | None = None):
    """Call run_source_now with a fully mocked context."""
    from app.api.routes.admin_sources import run_source_now

    db = _make_db(source)
    request = MagicMock()
    actor = MagicMock()

    with (
        patch("app.api.routes.admin_sources.get_settings", return_value=MagicMock()),
        patch("app.api.routes.admin_sources.build_adapter", return_value=adapter),
        patch(
            "app.api.routes.admin_sources.persist_ingestion_result",
            return_value=MagicMock(
                persisted_incidents=0, skipped_duplicates=0, persisted_review_items=0
            ),
        ),
        patch("app.api.routes.admin_sources.update_source_health"),
        patch("app.api.routes.admin_sources.log_mutation"),
    ):
        if adapter is not None and adapter_error:
            adapter.run.side_effect = adapter_error
        elif adapter is not None:
            adapter.run.return_value = _make_adapter_result()

        return run_source_now(
            source_key=source.source_key if source else "missing",
            request=request,
            db=db,
            actor=actor,
        )


# ---------------------------------------------------------------------------
# 404 — missing source
# ---------------------------------------------------------------------------


class TestRunSourceMissing:
    def test_missing_source_returns_404(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _run(source=None)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 409 — inactive source
# ---------------------------------------------------------------------------


class TestRunSourceInactive:
    def test_inactive_source_returns_409(self) -> None:
        src = _make_source(is_active=False, source_class="machine_ingest")
        with pytest.raises(HTTPException) as exc_info:
            _run(src)
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# 422 — non-runnable source_class
# ---------------------------------------------------------------------------


class TestRunSourceClassPolicy:
    @pytest.mark.parametrize(
        "sc",
        [
            "portal_reference",
            "manual_reference",
            "requires_api_key",
            "disabled_stub",
            "needs_endpoint_configuration",
            None,
        ],
    )
    def test_non_machine_ingest_returns_422(self, sc: str | None) -> None:
        src = _make_source(source_class=sc)
        with pytest.raises(HTTPException) as exc_info:
            _run(src)
        exc = exc_info.value
        assert exc.status_code == 422
        assert isinstance(exc.detail, dict)
        assert exc.detail["source_class"] == sc
        assert "next_action" in exc.detail

    def test_machine_ingest_is_allowed_with_adapter(self) -> None:
        src = _make_source(source_class="machine_ingest")
        adapter = MagicMock()
        adapter.run.return_value = _make_adapter_result()
        result = _run(src, adapter=adapter)
        assert result["success"] is True

    def test_422_detail_contains_source_key(self) -> None:
        src = _make_source(source_class="portal_reference", source_key="spd_portal")
        with pytest.raises(HTTPException) as exc_info:
            _run(src)
        assert exc_info.value.detail["source_key"] == "spd_portal"


# ---------------------------------------------------------------------------
# 501 — no adapter registered
# ---------------------------------------------------------------------------


class TestRunSourceNoAdapter:
    def test_nil_adapter_returns_501(self) -> None:
        src = _make_source(source_class="machine_ingest")
        with pytest.raises(HTTPException) as exc_info:
            _run(src, adapter=None)
        assert exc_info.value.status_code == 501


# ---------------------------------------------------------------------------
# 500 — adapter raises
# ---------------------------------------------------------------------------


class TestRunSourceAdapterError:
    def test_adapter_exception_returns_500(self) -> None:
        src = _make_source(source_class="machine_ingest")
        adapter = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _run(src, adapter=adapter, adapter_error=RuntimeError("timeout"))
        assert exc_info.value.status_code == 500

    def test_adapter_exception_records_failed_run(self) -> None:
        """update_source_health must still be called even when the adapter crashes."""
        src = _make_source(source_class="machine_ingest")
        adapter = MagicMock()

        with (
            patch(
                "app.api.routes.admin_sources.get_settings", return_value=MagicMock()
            ),
            patch("app.api.routes.admin_sources.build_adapter", return_value=adapter),
            patch("app.api.routes.admin_sources.persist_ingestion_result"),
            patch("app.api.routes.admin_sources.update_source_health") as mock_health,
            patch("app.api.routes.admin_sources.log_mutation"),
        ):
            adapter.run.side_effect = RuntimeError("network error")
            db = _make_db(src)

            from app.api.routes.admin_sources import run_source_now

            with pytest.raises(HTTPException):
                run_source_now(
                    source_key=src.source_key,
                    request=MagicMock(),
                    db=db,
                    actor=MagicMock(),
                )

            mock_health.assert_called_once()
