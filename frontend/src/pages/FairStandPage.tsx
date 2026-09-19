import React from "react";
import { buildApiHeaders } from "../config";

export function FairStandPage() {
  const hostRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    let cancelled = false;
    let unmount: (() => void) | undefined;

    void import("@fair-stand/mountFairStand.js").then(({ mountFairStand }) => {
      if (cancelled || !hostRef.current) return;
      unmount = mountFairStand(hostRef.current, { catalogHeaders: buildApiHeaders() });
    });

    return () => {
      cancelled = true;
      unmount?.();
    };
  }, []);

  return (
    <div className="fair-stand-standalone" data-testid="fair-stand-standalone">
      <div
        ref={hostRef}
        className="fair-stand-host"
        data-testid="fair-stand-host"
      />
    </div>
  );
}
