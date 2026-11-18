import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast-manager";
import { ApiError, type Camera, camerasApi } from "@/services";
import { useState } from "react";

/** Add a camera (camera = "new") or edit one (camera = the camera). */
export function CameraFormDialog({
  camera,
  onOpenChange,
  onSaved,
}: {
  camera: Camera | "new" | null;
  onOpenChange: (open: boolean) => void;
  onSaved: (camera: Camera) => void;
}) {
  const editing = camera !== null && camera !== "new" ? camera : null;
  const [name, setName] = useState(editing?.name ?? "");
  const [location, setLocation] = useState(editing?.location ?? "");
  // The API returns the source with any password masked ("user:***@"), so it
  // is only sent back if the admin actually changed it.
  const [streamSource, setStreamSource] = useState(
    editing?.stream_source ?? "",
  );
  const [isSaving, setIsSaving] = useState(false);
  const hasMaskedPassword = editing?.stream_source.includes(":***@") ?? false;

  const save = async () => {
    setIsSaving(true);
    try {
      const saved = editing
        ? await camerasApi.update(editing.id, {
            name: name.trim(),
            location: location.trim() || null,
            ...(streamSource.trim() !== editing.stream_source
              ? { stream_source: streamSource.trim() }
              : {}),
          })
        : await camerasApi.create({
            name: name.trim(),
            location: location.trim() || undefined,
            stream_source: streamSource.trim(),
          });
      toast.success(editing ? "Camera updated" : "Camera added", saved.name);
      onSaved(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(
        editing ? "Couldn't update camera" : "Couldn't add camera",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={camera !== null}
      onOpenChange={(open) => {
        if (!isSaving) onOpenChange(open);
      }}
    >
      <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Camera" : "Add Camera"}</DialogTitle>
          {editing && (
            <DialogDescription>
              If monitoring is running, restart it after changing the stream
              source.
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="space-y-4">
          <Field>
            <FieldLabel>Name</FieldLabel>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Front entrance"
              maxLength={100}
            />
          </Field>
          <Field>
            <FieldLabel>Location</FieldLabel>
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Mock office - entrance"
              maxLength={255}
            />
          </Field>
          <Field>
            <FieldLabel>Stream source</FieldLabel>
            <Input
              value={streamSource}
              onChange={(e) => setStreamSource(e.target.value)}
              placeholder="Webcam index (0, 1, ...) or RTSP URL"
              maxLength={500}
            />
            <p className="text-xs text-gray-400">
              {hasMaskedPassword
                ? "The saved password is hidden (***). Leave this as it is to keep it, or type the full URL with the password to change it."
                : "0 = this computer's first webcam. IP camera: rtsp://user:password@ip:554/..."}
            </p>
          </Field>
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline">Cancel</Button>} />
          <Button
            onClick={() => void save()}
            disabled={isSaving || !name.trim() || !streamSource.trim()}
          >
            {isSaving ? <Spinner /> : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
