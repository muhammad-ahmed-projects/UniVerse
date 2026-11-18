import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast-manager";
import { CameraIcon, TrashBinIcon, UploadIcon } from "@/icons";
import {
  ApiError,
  type FaceSample,
  type Person,
  faceImagePath,
  peopleApi,
} from "@/services";
import { cn } from "@/utils";
import { useEffect, useRef, useState } from "react";
import { AuthedImage } from "./authed-image";
import { WebcamCapture } from "./webcam-capture";

// Phone photos are often 5-12 MP; the server needs far less to find a face
// and rejects uploads over 5 MB.
const MAX_UPLOAD_SIDE_PX = 1600;

async function downscale(file: Blob): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(
      1,
      MAX_UPLOAD_SIDE_PX / Math.max(bitmap.width, bitmap.height),
    );
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas
      .getContext("2d")
      ?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9),
    );
    return blob ?? file;
  } catch {
    return file; // let the server report formats the browser can't decode
  }
}

type Mode = "upload" | "camera";

/** Admin dialog to add/remove a registered person's face photos. */
export function FacePhotosDialog({
  person,
  onOpenChange,
  onChanged,
}: {
  person: Person | null;
  onOpenChange: (open: boolean) => void;
  /** Called with the new photo count after an add/remove. */
  onChanged: (personId: number, faceCount: number) => void;
}) {
  const [faces, setFaces] = useState<FaceSample[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("upload");
  const [uploading, setUploading] = useState<{
    done: number;
    total: number;
  } | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const personId = person?.id ?? null;

  useEffect(() => {
    if (personId === null) return;
    let cancelled = false;
    peopleApi
      .listFaces(personId)
      .then((list) => {
        if (!cancelled) setFaces(list);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setLoadError(
            err instanceof ApiError ? err.message : "Failed to load photos",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [personId]);

  const close = () => {
    setFaces(null);
    setLoadError(null);
    setMode("upload");
    onOpenChange(false);
  };

  const upload = async (photos: { blob: Blob; name: string }[]) => {
    if (!person || photos.length === 0) return;
    let added: FaceSample[] = [];
    setUploading({ done: 0, total: photos.length });
    for (const [i, photo] of photos.entries()) {
      try {
        const face = await peopleApi.addFace(
          person.id,
          await downscale(photo.blob),
          photo.name,
        );
        added = [...added, face];
        setFaces((prev) => [...(prev ?? []), face]);
      } catch (err) {
        toast.error(
          photos.length > 1 ? `${photo.name}: not added` : "Photo not added",
          err instanceof ApiError ? err.message : undefined,
        );
      }
      setUploading({ done: i + 1, total: photos.length });
    }
    setUploading(null);
    if (added.length > 0) {
      const count = (faces?.length ?? 0) + added.length;
      onChanged(person.id, count);
      toast.success(
        added.length === 1
          ? "Face photo added"
          : `${added.length} face photos added`,
        `${person.name} now has ${count} photo${count === 1 ? "" : "s"}.`,
      );
    }
  };

  const remove = async (face: FaceSample) => {
    if (!person) return;
    setRemovingId(face.id);
    try {
      await peopleApi.removeFace(face);
      const remaining = (faces ?? []).filter((f) => f.id !== face.id);
      setFaces(remaining);
      onChanged(person.id, remaining.length);
      toast.success("Face photo removed");
    } catch (err) {
      toast.error(
        "Couldn't remove photo",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setRemovingId(null);
    }
  };

  const count = faces?.length ?? 0;

  return (
    <Dialog
      open={person !== null}
      onOpenChange={(open) => {
        if (!open && !uploading) close();
      }}
    >
      <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Face photos · {person?.name}</DialogTitle>
          <DialogDescription>
            Add 3-5 clear photos: looking straight at the camera, then turned
            slightly left and right. One face per photo, good light. The
            recognizer picks up new photos within 30 seconds.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-800 dark:text-white/90">
                Registered photos
              </h4>
              {faces !== null && (
                <Badge color={count === 0 ? "warning" : "success"}>
                  {count === 0
                    ? "Not recognizable yet"
                    : `${count} photo${count === 1 ? "" : "s"}`}
                </Badge>
              )}
            </div>
            {loadError ? (
              <p className="text-sm text-red-600 dark:text-red-400">
                {loadError}
              </p>
            ) : faces === null ? (
              <div className="flex justify-center py-6">
                <Spinner className="size-5" />
              </div>
            ) : faces.length === 0 ? (
              <p className="rounded-lg border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No photos yet. Upload some or take them with the camera below.
              </p>
            ) : (
              <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
                {faces.map((face, i) => (
                  <div key={face.id} className="group relative">
                    <AuthedImage
                      path={faceImagePath(face)}
                      alt={`${person?.name} face photo ${i + 1}`}
                      className="aspect-square w-full rounded-lg object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => void remove(face)}
                      disabled={removingId === face.id}
                      aria-label={`Remove face photo ${i + 1}`}
                      className="absolute end-1 top-1 rounded-md bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-600 focus-visible:opacity-100 disabled:opacity-100"
                    >
                      {removingId === face.id ? (
                        <Spinner className="size-3.5" />
                      ) : (
                        <TrashBinIcon className="size-3.5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="mb-3 inline-flex rounded-lg bg-gray-100 p-0.5 dark:bg-gray-900">
              {(
                [
                  ["upload", "Upload photos", UploadIcon],
                  ["camera", "Use camera", CameraIcon],
                ] as const
              ).map(([value, label, Icon]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMode(value)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    mode === value
                      ? "bg-white text-gray-900 shadow-theme-xs dark:bg-gray-800 dark:text-white"
                      : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white",
                  )}
                >
                  <Icon className="size-4" />
                  {label}
                </button>
              ))}
            </div>

            {mode === "upload" ? (
              <div className="rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center dark:border-gray-700">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    e.target.value = ""; // allow picking the same file again
                    void upload(files.map((f) => ({ blob: f, name: f.name })));
                  }}
                />
                <Button
                  variant="outline"
                  disabled={uploading !== null}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {uploading ? (
                    <>
                      <Spinner /> Checking photo{" "}
                      {Math.min(uploading.done + 1, uploading.total)} of{" "}
                      {uploading.total}...
                    </>
                  ) : (
                    <>
                      <UploadIcon className="size-4" /> Choose photos
                    </>
                  )}
                </Button>
                <p className="mt-2 text-xs text-gray-400">
                  JPEG, PNG or WebP. Several at once is fine.
                </p>
              </div>
            ) : (
              <WebcamCapture
                busy={uploading !== null}
                onCapture={(blob) =>
                  void upload([{ blob, name: `camera-${Date.now()}.jpg` }])
                }
              />
            )}
          </div>
        </div>

        <DialogFooter>
          <Button disabled={uploading !== null} onClick={close}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
