import React from "react";
import { OperationDetailPage as LegacyOperationDetailPage } from "./OperationDetailPageLegacy";

type OperationDetailPageProps = React.ComponentProps<typeof LegacyOperationDetailPage>;

export function OperationDetailPage(props: OperationDetailPageProps) {
  return <LegacyOperationDetailPage {...props} />;
}
