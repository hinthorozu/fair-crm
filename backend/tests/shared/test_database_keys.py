from app.shared.database_backup.database_keys import (
    DatabaseKey,
    infer_database_key_from_backup_filename,
    validate_backup_format_for_database,
)
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.paths import generate_backup_filename


def test_infer_fair_stand_backup_filename():
    assert infer_database_key_from_backup_filename("fair_stand_backup_20260920_120000.dump") == DatabaseKey.FAIR_STAND
    assert infer_database_key_from_backup_filename("kyrox_core_backup_20260920_120000.dump") == DatabaseKey.KYROX_CORE
    assert infer_database_key_from_backup_filename("fair_crm_backup_20260920_120000.dump") == DatabaseKey.FAIR_CRM


def test_generate_fair_stand_dump_filename():
    name = generate_backup_filename(
        database_key=DatabaseKey.FAIR_STAND,
        backup_format=BackupFormat.POSTGRESQL_DUMP,
    )
    assert name.startswith("fair_stand_backup_")
    assert name.endswith(".dump")


def test_universal_package_rejected_for_fair_stand():
    try:
        validate_backup_format_for_database(DatabaseKey.FAIR_STAND, BackupFormat.UNIVERSAL_DATA_PACKAGE)
    except ValueError as exc:
        assert "fair_crm" in str(exc)
    else:
        raise AssertionError("expected ValueError")
