import React from "react";

interface DataIntegrationLayoutProps {
  children: React.ReactNode;
}

export function DataIntegrationLayout({ children }: DataIntegrationLayoutProps) {
  return <div className="data-integration-layout">{children}</div>;
}
