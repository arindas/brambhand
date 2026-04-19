from __future__ import annotations

import pytest

from brambhand.bridge.runtime_stream import (
    BODY_ID_CATALOG_SCHEMA_VERSION,
    RUNTIME_STREAM_SCHEMA_VERSION,
    RuntimeStreamPublisher,
)


def test_runtime_stream_publisher_derives_body_catalog_diffs() -> None:
    publisher = RuntimeStreamPublisher()

    frames = [
        {
            "run_id": "run-a",
            "tick_id": 1,
            "sim_time_s": 0.0,
            "sequence": 10,
            "bodies": [{"body_id": "sun"}, {"body_id": "probe"}],
            "events": [],
        },
        {
            "run_id": "run-a",
            "tick_id": 2,
            "sim_time_s": 1.0,
            "sequence": 11,
            "bodies": [{"body_id": "sun"}, {"body_id": "probe2"}],
            "events": [],
        },
    ]

    emitted = publisher.publish_frames(frames)
    assert len(emitted) == 2

    first_catalog = emitted[0]["body_id_catalog"]
    assert first_catalog["schema_version"] == BODY_ID_CATALOG_SCHEMA_VERSION
    assert first_catalog["initial_body_ids"] == ["probe", "sun"]
    assert first_catalog["created_body_ids"] == []
    assert first_catalog["destroyed_body_ids"] == []

    second_catalog = emitted[1]["body_id_catalog"]
    assert "initial_body_ids" not in second_catalog
    assert second_catalog["created_body_ids"] == ["probe2"]
    assert second_catalog["destroyed_body_ids"] == ["probe"]

    assert emitted[0]["schema_version"] == RUNTIME_STREAM_SCHEMA_VERSION
    assert emitted[1]["schema_version"] == RUNTIME_STREAM_SCHEMA_VERSION


def test_runtime_stream_publisher_preserves_valid_explicit_catalog() -> None:
    publisher = RuntimeStreamPublisher()

    frames = [
        {
            "run_id": "run-a",
            "tick_id": 1,
            "sim_time_s": 0.0,
            "sequence": 10,
            "bodies": [{"body_id": "sun"}],
            "body_id_catalog": {
                "schema_version": 1,
                "initial_body_ids": ["sun"],
                "created_body_ids": [],
                "destroyed_body_ids": [],
            },
        },
        {
            "run_id": "run-a",
            "tick_id": 2,
            "sim_time_s": 1.0,
            "sequence": 11,
            "bodies": [{"body_id": "sun"}, {"body_id": "probe"}],
            "body_id_catalog": {
                "schema_version": 1,
                "created_body_ids": ["probe"],
                "destroyed_body_ids": [],
            },
        },
    ]

    emitted = publisher.publish_frames(frames)
    assert emitted[0]["body_id_catalog"]["initial_body_ids"] == ["sun"]
    assert emitted[1]["body_id_catalog"]["created_body_ids"] == ["probe"]


def test_runtime_stream_publisher_rejects_invalid_initial_body_catalog_usage() -> None:
    publisher = RuntimeStreamPublisher()

    with pytest.raises(ValueError, match="initial_body_ids"):
        publisher.publish_frames(
            [
                {
                    "run_id": "run-a",
                    "tick_id": 1,
                    "sim_time_s": 0.0,
                    "sequence": 10,
                    "bodies": [{"body_id": "sun"}],
                    "body_id_catalog": {
                        "schema_version": 1,
                        "created_body_ids": [],
                        "destroyed_body_ids": [],
                    },
                }
            ]
        )
