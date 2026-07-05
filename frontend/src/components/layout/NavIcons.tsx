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

const DI_NAV_ICONS: Record<string, React.ComponentType<IconProps>> = {
  imports: NavIconImports,
  new: NavIconNewImport,
  jobs: NavIconJobs,
  reports: NavIconReports,
  adapters: NavIconAdapters,
  "run-history": NavIconRunHistory,
  "scraper-test": NavIconScraperTest,
};

export function DataIntegrationNavIcon({ id }: { id: string }) {
  const Icon = DI_NAV_ICONS[id] ?? NavIconImports;
  return <Icon />;
}
