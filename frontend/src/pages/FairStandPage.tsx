import React from "react";
import { PageShell } from "../components/ui/PageShell";

export function FairStandPage() {
  const hostRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    let cancelled = false;
    let unmount: (() => void) | undefined;

    void import("@fair-stand/mountFairStand.js").then(({ mountFairStand }) => {
      if (cancelled || !hostRef.current) return;
      unmount = mountFairStand(hostRef.current);
    });

    return () => {
      cancelled = true;
      unmount?.();
    };
  }, []);

  return (
    <PageShell fullWidth className="fair-stand-page">
      <div
        ref={hostRef}
        className="fair-stand-host"
        data-testid="fair-stand-host"
      />
    </PageShell>
  );
}
