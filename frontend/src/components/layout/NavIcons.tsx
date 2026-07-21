import React from "react";

interface IconProps {
  className?: string;
}

function IconBase({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className ?? "nav-icon"}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function NavIconDashboard(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </IconBase>
  );
}

export function NavIconCustomers(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </IconBase>
  );
}

export function NavIconFairs(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </IconBase>
  );
}

export function NavIconTodos(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </IconBase>
  );
}

export function NavIconFollowUps(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
      <path d="M8 14h.01M12 14h.01M16 14h.01" />
    </IconBase>
  );
}

export function NavIconDataIntegration(props: IconProps) {
  return (
    <IconBase {...props}>
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v6c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      <path d="M3 11v6c0 1.66 4 3 9 3s9-1.34 9-3v-6" />
    </IconBase>
  );
}

export function NavIconAdmin(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </IconBase>
  );
}

export function NavIconImports(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </IconBase>
  );
}

export function NavIconNewImport(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 5v14M5 12h14" />
    </IconBase>
  );
}

export function NavIconJobs(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </IconBase>
  );
}

export function NavIconReports(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M18 20V10M12 20V4M6 20v-6" />
    </IconBase>
  );
}

export function NavIconAdapters(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </IconBase>
  );
}

export function NavIconRunHistory(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 3v5h5" />
      <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
      <path d="M12 7v5l3 3" />
    </IconBase>
  );
}

export function NavIconScraperTest(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M10 2v7.31M14 9.3V2" />
      <path d="M8.5 2h7" />
      <path d="M14 9.3a6.5 6.5 0 1 1-4 0" />
      <path d="M5.52 16h12.96" />
    </IconBase>
  );
}

export function NavIconEnrichment(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="M15 5l4 4" />
    </IconBase>
  );
}

export function NavIconChevronLeft(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M15 18l-6-6 6-6" />
    </IconBase>
  );
}

export function NavIconChevronRight(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9 18l6-6-6-6" />
    </IconBase>
  );
}

export function NavIconDatabase(props: IconProps) {
  return (
    <IconBase {...props}>
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
    </IconBase>
  );
}

export function NavIconMail(props: IconProps) {
  return (
    <IconBase {...props}>
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 7l-10 7L2 7" />
    </IconBase>
  );
}

export function NavIconTemplate(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </IconBase>
  );
}

export function NavIconDataOperations(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" />
    </IconBase>
  );
}

export function NavIconSettings(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </IconBase>
  );
}

export function NavIconEye(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </IconBase>
  );
}

export function NavIconEyeOff(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </IconBase>
  );
}

const DI_NAV_ICONS: Record<string, React.ComponentType<IconProps>> = {
  imports: NavIconImports,
  new: NavIconNewImport,
  jobs: NavIconJobs,
  reports: NavIconReports,
  adapters: NavIconAdapters,
  "run-history": NavIconRunHistory,
  "scraper-test": NavIconScraperTest,
  enrichment: NavIconEnrichment,
};

export function DataIntegrationNavIcon({ id }: { id: string }) {
  const Icon = DI_NAV_ICONS[id] ?? NavIconImports;
  return <Icon />;
}

const ADMIN_NAV_ICONS: Record<string, React.ComponentType<IconProps>> = {
  backups: NavIconDatabase,
  smtp: NavIconMail,
  "mail-templates": NavIconTemplate,
  "mail-operations": NavIconRunHistory,
  "data-operations": NavIconDataOperations,
  "background-jobs": NavIconJobs,
  "audit-logs": NavIconReports,
  health: NavIconSettings,
  storage: NavIconDatabase,
  maintenance: NavIconSettings,
  scheduler: NavIconJobs,
  "disaster-recovery": NavIconDatabase,
};

export function AdminNavIcon({ id }: { id: string }) {
  const Icon = ADMIN_NAV_ICONS[id] ?? NavIconAdmin;
  return <Icon />;
}
