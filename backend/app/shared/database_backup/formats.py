from enum import StrEnum


class BackupFormat(StrEnum):
    POSTGRESQL_DUMP = "postgresql_dump"
    POSTGRESQL_SQL = "postgresql_sql"
    UNIVERSAL_DATA_PACKAGE = "universal_data_package"


ALLOWED_BACKUP_EXTENSIONS: frozenset[str] = frozenset({".dump", ".sql", ".zip"})

FORMAT_EXTENSIONS: dict[BackupFormat, str] = {
    BackupFormat.POSTGRESQL_DUMP: ".dump",
    BackupFormat.POSTGRESQL_SQL: ".sql",
    BackupFormat.UNIVERSAL_DATA_PACKAGE: ".zip",
}

FORMAT_FILENAME_PREFIX: dict[BackupFormat, str] = {
    BackupFormat.POSTGRESQL_DUMP: "faircrm_backup_",
    BackupFormat.POSTGRESQL_SQL: "faircrm_backup_",
    BackupFormat.UNIVERSAL_DATA_PACKAGE: "faircrm_data_package_",
}
