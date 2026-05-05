"""Factory for instantiating Canadian source adapters.

Centralises the adapter-construction logic so that:
* API keys (CanLII, Lexum) are injected from ``Settings`` rather than
  scattered across caller sites.
* The ``public_record_authority`` field is always wired from the DB row.
* Callers obtain a ``CanadianSourceAdapter`` without knowing each adapter's
  exact constructor signature.

Usage::

    from app.ingestion.source_adapter_factory import build_adapter
    from app.core.config import get_settings

    adapter = build_adapter(source, get_settings())
    if adapter is None:
        # parser key unknown — no adapter registered
        ...
    result = adapter.run()
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.ingestion.adapters import CanadianSourceAdapter
from app.ingestion.source_adapters import ADAPTER_REGISTRY

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.models.entities import SourceRegistry

logger = logging.getLogger(__name__)

# Parser keys that accept an ``api_key`` positional-or-keyword argument.
_API_KEY_ADAPTERS: frozenset[str] = frozenset({"canlii_api", "scc_lexum_api"})


def build_adapter(
    source: "SourceRegistry",
    settings: "Settings",
) -> CanadianSourceAdapter | None:
    """Return a configured :class:`CanadianSourceAdapter` for *source*.

    Returns ``None`` if no adapter is registered for ``source.parser``.

    The factory will:

    1. Look up the adapter class in ``ADAPTER_REGISTRY``.
    2. Inject ``api_key`` from ``settings.canlii_api_key`` for CanLII and
       Lexum adapters.
    3. Pass ``public_record_authority`` from the DB row.
    """
    parser_key = source.parser
    if not parser_key:
        logger.warning(
            "Source %r has no parser key; skipping factory.", source.source_key
        )
        return None

    adapter_cls = ADAPTER_REGISTRY.get(parser_key)
    if adapter_cls is None:
        logger.warning(
            "No adapter registered for parser %r (source %r).",
            parser_key,
            source.source_key,
        )
        return None

    common_kwargs: dict = {
        "source_key": source.source_key,
        "base_url": source.base_url or "",
        "allowed_domains_json": source.allowed_domains or "[]",
        "public_record_authority": source.public_record_authority,
    }

    if parser_key in _API_KEY_ADAPTERS:
        common_kwargs["api_key"] = settings.canlii_api_key

    # Parse config_json once and forward adapter-specific fields.
    config: dict = {}
    if source.config_json:
        try:
            config = json.loads(source.config_json)
        except json.JSONDecodeError:
            logger.warning(
                "Source %r has malformed config_json; ignoring extra config.",
                source.source_key,
            )

    if parser_key == "ckan_api":
        resource_id = config.get("resource_id")
        if resource_id:
            common_kwargs["resource_id"] = resource_id

    source_class = getattr(source, "source_class", None)
    if source_class != "machine_ingest":
        raise ValueError(
            f"Source '{source.source_key}' has source_class={source_class!r} which "
            f"cannot be auto-ingested. Only 'machine_ingest' sources may be run. "
            f"Classify this source correctly before enabling adapter runs."
        )

    try:
        adapter: CanadianSourceAdapter = adapter_cls(**common_kwargs)
    except TypeError as exc:
        logger.error(
            "Failed to instantiate adapter %r for source %r: %s",
            adapter_cls.__name__,
            source.source_key,
            exc,
        )
        return None

    return adapter
