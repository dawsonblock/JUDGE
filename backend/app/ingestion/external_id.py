"""
Utilities for building and parsing namespaced external IDs.

Every adapter must use :func:`make_external_id` to construct its
``external_id`` field.  The consistent format prevents collisions between
sources that share the same raw identifier space and makes deduplication in
:mod:`app.ingestion.source_runner` unambiguous.
"""

from __future__ import annotations


def make_external_id(source_key: str, raw_id: "str | int | None") -> "str | None":
    """Return a namespaced external ID string, or ``None`` when *raw_id* is falsy.

    Format: ``"<source_key>:<raw_id>"``

    The colon separator does not appear in any canonical source key (see
    :mod:`app.ingestion.source_keys`), so the two components can always be
    recovered unambiguously by splitting on the first colon.

    Parameters
    ----------
    source_key:
        The canonical source key (e.g. ``"saskatoon_open_data_crime"``).
    raw_id:
        The identifier from the upstream source.  Integers are converted to
        their string representation.  Empty strings and ``None`` both return
        ``None``.

    Examples
    --------
    >>> make_external_id("saskatoon_open_data_crime", 12345)
    'saskatoon_open_data_crime:12345'
    >>> make_external_id("saskatoon_open_data_crime", None) is None
    True
    >>> make_external_id("saskatoon_open_data_crime", "") is None
    True
    """
    if raw_id is None:
        return None
    cleaned = str(raw_id).strip()
    if not cleaned:
        return None
    return f"{source_key}:{cleaned}"


def split_external_id(external_id: str) -> "tuple[str, str] | None":
    """Reverse of :func:`make_external_id`.

    Returns ``(source_key, raw_id)`` or ``None`` when the input is not in the
    expected ``"source_key:raw_id"`` format.

    Parameters
    ----------
    external_id:
        A string previously produced by :func:`make_external_id`.

    Examples
    --------
    >>> split_external_id("saskatoon_open_data_crime:12345")
    ('saskatoon_open_data_crime', '12345')
    >>> split_external_id("bad-format") is None
    True
    """
    if not external_id or ":" not in external_id:
        return None
    source_key, _, raw_id = external_id.partition(":")
    if not source_key or not raw_id:
        return None
    return source_key, raw_id
