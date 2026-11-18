import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CameraIcon } from "@/icons";
import { useEffect, useRef, useState } from "react";

type CameraState =
  | { status: "off" }
  | { status: "starting" }
  | { status: "on" }
  | { status: "error"; message: string };

function describeCameraError(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError")
    return "Camera permission was denied. Allow camera access for this site in the browser's address bar, then try again.";
  if (name === "NotFoundError") return "No camera was found on this computer.";
  if (name === "NotReadableError")
    return "The camera is busy. Close other apps using it (including any UniVerse detection script running on this webcam) and try again.";
  return "Could not start the camera.";
}

/** Live preview from the computer's camera with a "Take photo" button. */
export function WebcamCapture({
  onCapture,
  busy = false,
}: {
  onCapture: (photo: Blob) => void;
  busy?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [camera, setCamera] = useState<CameraState>({ status: "off" });

  const stop = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  // Release the camera when the dialog closes.
  useEffect(() => stop, []);

  const start = async () => {
    setCamera({ status: "starting" });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamera({ status: "on" });
    } catch (err) {
      stop();
      setCamera({ status: "error", message: describeCameraError(err) });
    }
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob);
      },
      "image/jpeg",
      0.92,
    );
  };

  return (
    <div className="space-y-3">
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-gray-900">
        {/* Mirrored like a selfie camera; the captured photo is not mirrored. */}
        <video
          ref={videoRef}
          muted
          playsInline
          className={
            camera.status === "on"
              ? "size-full -scale-x-100 object-cover"
              : "hidden"
          }
        />
        {camera.status !== "on" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
            {camera.status === "starting" ? (
              <Spinner className="size-6 text-white" />
            ) : (
              <>
                <CameraIcon className="size-8 text-gray-500" />
                {camera.status === "error" && (
                  <p className="text-sm text-red-300">{camera.message}</p>
                )}
                <Button size="sm" onClick={() => void start()}>
                  {camera.status === "error" ? "Try again" : "Turn on camera"}
                </Button>
              </>
            )}
          </div>
        )}
      </div>
      {camera.status === "on" && (
        <Button className="w-full" disabled={busy} onClick={capture}>
          {busy ? <Spinner /> : "Take photo"}
        </Button>
      )}
    </div>
  );
}
