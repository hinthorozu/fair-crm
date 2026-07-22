from uuid import uuid4

import pytest

from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.source_normalization import (
    build_normalized_source_config,
    extract_source_ids,
    normalize_source_kind,
)
from app.modules.operations.domain.value_objects import SourceKind


def test_normalize_maps_multiple_fairs_to_fair():
    assert normalize_source_kind("multiple_fairs") == SourceKind.FAIR


def test_build_fair_source_requires_ids():
    with pytest.raises(InvalidOperationConfigError, match="source_ids"):
        build_normalized_source_config(
            source_kind="fair",
            source_ids=[],
            source_config={},
        )


def test_build_fair_source_accepts_one_and_many():
    one = uuid4()
    kind, config, ids = build_normalized_source_config(
        source_kind="fair",
        source_ids=[one],
        source_config={},
    )
    assert kind == SourceKind.FAIR
    assert ids == [one]
    assert config["source_ids"] == [str(one)]

    two = uuid4()
    kind, config, ids = build_normalized_source_config(
        source_kind="multiple_fairs",
        source_ids=[one, two, one],
        source_config={},
    )
    assert kind == SourceKind.FAIR
    assert ids == [one, two]
    assert config["source_ids"] == [str(one), str(two)]
    assert "fair_id" not in config

    legacy = uuid4()
    kind, config, ids = build_normalized_source_config(
        source_kind="fair",
        source_ids=None,
        source_config={"fair_id": str(legacy)},
    )
    assert ids == [legacy]
    assert config["source_ids"] == [str(legacy)]
    assert "fair_id" not in config


def test_extract_source_ids_reads_legacy_keys():
    fair_id = uuid4()
    assert extract_source_ids({"fair_id": str(fair_id)}) == [fair_id]
    a, b = uuid4(), uuid4()
    assert extract_source_ids({"fair_ids": [str(a), str(b)]}) == [a, b]


def test_non_fair_rejects_source_ids():
    with pytest.raises(InvalidOperationConfigError, match="only allowed"):
        build_normalized_source_config(
            source_kind="none",
            source_ids=[uuid4()],
            source_config={},
        )
