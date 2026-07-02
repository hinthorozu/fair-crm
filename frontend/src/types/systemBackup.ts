export interface SystemBackup {
  id: string;
  file_name: string;
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
  file_name: string;
  status: string;
  progress_stage: string;
}
