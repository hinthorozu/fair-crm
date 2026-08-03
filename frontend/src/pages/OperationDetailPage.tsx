import React from "react";
import { normalizeOperationRunProgressText } from "../utils/operationRunProgressText";
import { OperationDetailPage as LegacyOperationDetailPage } from "./OperationDetailPageLegacy";

type OperationDetailPageProps = React.ComponentProps<typeof LegacyOperationDetailPage>;

function normalizeProgressText(root: HTMLElement): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const current = node.nodeValue;
    if (current) {
      const normalized = normalizeOperationRunProgressText(current);
      if (normalized !== current) {
        node.nodeValue = normalized;
      }
    }
    node = walker.nextNode();
  }
}

/**
 * Compatibility wrapper for the operation detail page.
 *
 * The legacy page already contains the failed-recipient retry action. Live
 * backend counters make that action visible at the correct time; this wrapper
 * corrects the historical total/processed text order after table rendering and
 * after polling updates.
 */
export function OperationDetailPage(props: OperationDetailPageProps) {
  const rootRef = React.useRef<HTMLDivElement>(null);

  React.useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;

    const normalize = () => normalizeProgressText(root);
    normalize();

    const observer = new MutationObserver(normalize);
    observer.observe(root, {
      subtree: true,
      childList: true,
      characterData: true,
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} style={{ display: "contents" }}>
      <LegacyOperationDetailPage {...props} />
    </div>
  );
}
