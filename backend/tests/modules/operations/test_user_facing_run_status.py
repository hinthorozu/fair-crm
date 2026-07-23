from datetime import datetime, timedelta, timezone

from app.modules.operations.application.user_facing_run_status import (
    USER_FACING_STATUS_LABELS_TR,
    expand_user_facing_status_filter,
    map_technical_run_status_to_user_facing,
    user_facing_status_label_tr,
)


def test_maps_core_technical_statuses():
    assert map_technical_run_status_to_user_facing("running") == "running"
    assert map_technical_run_status_to_user_facing("paused") == "paused"
    assert map_technical_run_status_to_user_facing("completed") == "completed"
    assert map_technical_run_status_to_user_facing("cancelled") == "cancelled"
    assert map_technical_run_status_to_user_facing("failed") == "failed"
    assert map_technical_run_status_to_user_facing("scheduled") == "scheduled"


def test_queued_without_schedule_is_running_not_scheduled():
    assert map_technical_run_status_to_user_facing("queued") == "running"
    assert map_technical_run_status_to_user_facing("queued", run_settings={}) == "running"
    assert user_facing_status_label_tr("running") == "Çalışıyor"


def test_queued_with_future_schedule_is_scheduled():
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert (
        map_technical_run_status_to_user_facing(
            "queued", run_settings={"scheduled_at": future}
        )
        == "scheduled"
    )
    assert user_facing_status_label_tr("scheduled") == "Zamanlandı"


def test_failed_completed_cancelled_labels():
    assert USER_FACING_STATUS_LABELS_TR["failed"] == "Hata"
    assert USER_FACING_STATUS_LABELS_TR["completed"] == "Bitti"
    assert USER_FACING_STATUS_LABELS_TR["cancelled"] == "İptal"
    assert USER_FACING_STATUS_LABELS_TR["paused"] == "Durduruldu"


def test_expand_user_facing_filter_includes_queued_under_running():
    assert expand_user_facing_status_filter("running") == ("running", "queued")
    assert expand_user_facing_status_filter("failed") == ("failed",)
    assert expand_user_facing_status_filter("scheduled") == ("scheduled",)
