import React from "react";
import { startViewerSession, viewerStatusCopy } from "@fair-stand/liveTabShare.js";

export type StandWatchPageProps = {
  token: string;
};

type WatchStatus = {
  status: string;
  message: string;
};

export function StandWatchPage({ token }: StandWatchPageProps) {
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const [watch, setWatch] = React.useState<WatchStatus>({
    status: "waiting",
    message: viewerStatusCopy("waiting"),
  });

  React.useEffect(() => {
    const video = videoRef.current;
    if (!video) return undefined;
    return startViewerSession({
      token,
      videoElement: video,
      location: window.location,
      WebSocket: window.WebSocket,
      RTCPeerConnection: window.RTCPeerConnection,
      onStatus: (next: WatchStatus) => setWatch(next),
    });
  }, [token]);

  return (
    <main className="stand-watch" data-testid="stand-watch">
      <video ref={videoRef} autoPlay playsInline muted />
      {watch.message ? (
        <p className="stand-watch-status" role="status">
          {watch.message}
        </p>
      ) : null}
    </main>
  );
}
