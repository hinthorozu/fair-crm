import React from "react";

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
    <div className="fair-stand-page" data-testid="fair-stand-page">
      <div
        ref={hostRef}
        className="fair-stand-host"
        data-testid="fair-stand-host"
      />
    </div>
  );
}
