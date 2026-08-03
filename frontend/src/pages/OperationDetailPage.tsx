import React from "react";
import { normalizeOperationRunProgressText } from "../utils/operationRunProgressText";
import { OperationDetailPage as LegacyOperationDetailPage } from "./OperationDetailPageLegacy";

type OperationDetailPageProps = React.ComponentProps<typeof LegacyOperationDetailPage>;

function normalizeProgressNodes(node: React.ReactNode): React.ReactNode {
  if (typeof node === "string") {
    return normalizeOperationRunProgressText(node);
  }
  if (Array.isArray(node)) {
    return node.map((child) => normalizeProgressNodes(child));
  }
  if (!React.isValidElement(node)) {
    return node;
  }

  const element = node as React.ReactElement<{ children?: React.ReactNode }>;
  if (element.props.children === undefined) {
    return element;
  }
  return React.cloneElement(
    element,
    undefined,
    normalizeProgressNodes(element.props.children),
  );
}

/**
 * Compatibility wrapper for the operation detail page.
 *
 * The legacy page already contains the failed-recipient retry action. Live
 * backend counters make that action visible at the correct time; this wrapper
 * only corrects the historical total/processed text order in the run table.
 */
export function OperationDetailPage(props: OperationDetailPageProps) {
  const page = LegacyOperationDetailPage(props);
  return <>{normalizeProgressNodes(page)}</>;
}
