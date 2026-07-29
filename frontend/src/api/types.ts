export type ScanStatus =
  | "queued"
  | "cloning"
  | "indexing"
  | "analyzing"
  | "completed"
  | "failed";

export type Severity = "blocker" | "warning" | "info";
export type StaticStatus = "passed" | "warnings" | "blocked" | "failed";
export type VerificationStatus = "not-run" | "verified" | "failed" | "stale";

export type ScanJob = {
  id: string;
  repo_url: string;
  requested_ref: string | null;
  resolved_commit: string | null;
  status: ScanStatus;
  stage_message: string;
  created_at: string;
  updated_at: string;
  failure_code: string | null;
  failure_message: string | null;
};

export type SourceReference = {
  title: string;
  url: string;
};

export type RepositorySnapshot = {
  provider: "github" | "gitee";
  owner: string;
  name: string;
  url: string;
  commit: string;
};

export type Finding = {
  rule_id: string;
  rule_version: number;
  severity: Severity;
  category: string;
  title: string;
  relative_path: string;
  line_start: number;
  line_end: number;
  evidence: string;
  message: string;
  recommendation: string;
  references: SourceReference[];
};

export type ScanSummary = {
  total_count: number;
  blocker_count: number;
  warning_count: number;
  info_count: number;
};

export type MigrationChecklistItem = {
  rule_id: string;
  title: string;
  action: string;
  affected_files: string[];
  completed: boolean;
};

export type AnalysisWarning = {
  code: string;
  relative_path: string | null;
  message: string;
};

export type ScanReport = {
  schema_version: "1.0";
  scan_id: string;
  repository: RepositorySnapshot;
  tool_version: string;
  ruleset_version: string;
  scanned_at: string;
  summary: ScanSummary;
  findings: Finding[];
  migration_checklist: MigrationChecklistItem[];
  analysis_warnings: AnalysisWarning[];
  static_status: StaticStatus;
  verification_status: VerificationStatus;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, string>;
  };
};
