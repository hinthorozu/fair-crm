export type BackupFormat = "postgresql_dump" | "postgresql_sql" | "universal_data_package";

export type DatabaseKey = "kyrox_core" | "fair_crm";

export interface SystemBackup {
  id: string;
  database_key: DatabaseKey;
  database_label: string;
  file_name: string;
  backup_format: BackupFormat;
  file_size: number | null;
  status: "running" | "completed" | "failed";
  progress_stage: "preparing" | "dumping" | "compressing" | "completed" | "failed";
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  created_by: string;
  created_by_email: string | null;
  notes: string | null;
  checksum: string | null;
  manifest_json: Record<string, unknown> | null;
  download_count: number;
  error_message: string | null;
}

export interface SystemBackupListResponse {
  items: SystemBackup[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateSystemBackupResponse {
  id: string;
  database_key: DatabaseKey;
  database_label: string;
  file_name: string;
  backup_format: BackupFormat;
  status: string;
  progress_stage: string;
}

export interface CreateSystemBackupBatchResponse {
  items: CreateSystemBackupResponse[];
}

export interface SystemBackupRestoreJobResponse {
  id: string;
  status: "manual_restore_required" | "running" | "completed" | "failed";
  source_type: "existing_backup" | "uploaded_file";
  source_database_key: DatabaseKey;
  target_database_key: DatabaseKey;
  backup_id: string | null;
  source_file_name: string;
  checksum_sha256: string | null;
  notes: string | null;
  requested_by_user_id: string;
  requested_by_email: string | null;
  requested_at: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  restore_log_path: string | null;
  message: string;
  uploaded: boolean;
  backup_file_name: string | null;
  backup_format: string | null;
}

export interface DeleteSystemBackupResponse {
  id: string;
  file_name: string;
}
