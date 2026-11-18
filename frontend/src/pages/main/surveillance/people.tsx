import { ComponentCard } from "@/components/shared/component-card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { FacePhotosDialog } from "@/components/surveillance/face-photos-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast-manager";
import { useAuth } from "@/contexts";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { useNow } from "@/hooks/use-now";
import {
  ApiError,
  type Camera,
  type Person,
  camerasApi,
  peopleApi,
} from "@/services";
import { timeAgo } from "@/utils";
import { useEffect, useState } from "react";

const HEADER_CELL =
  "px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

export default function PeoplePage() {
  const { user } = useAuth();
  const [people, setPeople] = useState<Person[] | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [hasConsent, setHasConsent] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [photosFor, setPhotosFor] = useState<Person | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<Person | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const now = useNow(30_000);
  const isAdmin = user?.role === "admin";

  const load = () => {
    peopleApi
      .list()
      .then((list) => {
        setPeople(list);
        setError(null);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load people",
        ),
      );
  };

  useEffect(() => {
    load();
    // Camera names for the "Last seen" column; IDs are shown if this fails.
    camerasApi
      .list()
      .then(setCameras)
      .catch(() => undefined);
  }, []);

  useAlertsSocket((msg) => {
    if (msg.type !== "person_seen") return;
    setPeople(
      (prev) =>
        prev?.map((p) =>
          p.id === msg.person_id
            ? {
                ...p,
                last_seen_at: msg.seen_at,
                last_seen_camera_id: msg.camera_id,
              }
            : p,
        ) ?? prev,
    );
  });

  const resetForm = () => {
    setName("");
    setNotes("");
    setHasConsent(false);
  };

  const handleCreate = async () => {
    setIsSaving(true);
    try {
      const created = await peopleApi.create({
        name: name.trim(),
        notes: notes.trim() || undefined,
      });
      resetForm();
      setIsDialogOpen(false);
      setPeople((prev) => [...(prev ?? []), created]);
      toast.success("Person registered", "Now add their face photos.");
      // Recognition needs face photos, so go straight to adding them.
      setPhotosFor(created);
    } catch (err) {
      toast.error(
        "Couldn't register person",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleRemove = async () => {
    if (!pendingRemoval) return;
    const person = pendingRemoval;
    setIsRemoving(true);
    try {
      await peopleApi.remove(person.id);
      setPeople((prev) => prev?.filter((p) => p.id !== person.id) ?? prev);
      setPendingRemoval(null);
      toast.success(
        "Person removed",
        `${person.name} and their face photos were deleted.`,
      );
    } catch (err) {
      toast.error(
        "Couldn't remove person",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsRemoving(false);
    }
  };

  const cameraName = (id: number) =>
    cameras.find((c) => c.id === id)?.name ?? `Camera #${id}`;

  return (
    <div>
      <PageMeta
        title="Registered People | UniVerse"
        description="Consent-based face recognition registry"
      />
      <PageBreadcrumb pageTitle="Registered People" />

      <ComponentCard
        title="Registered People"
        description="People the face recognizer should know. Register a person with their consent, then add face photos; the face_recognition script picks them up automatically and reports where each person was last seen."
      >
        <div className="mb-4 flex justify-end">
          {isAdmin && (
            <Dialog
              open={isDialogOpen}
              onOpenChange={(open) => {
                setIsDialogOpen(open);
                if (!open) resetForm();
              }}
            >
              <Button onClick={() => setIsDialogOpen(true)}>
                Register Person
              </Button>
              <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Register Person</DialogTitle>
                  <DialogDescription>
                    Step 1 of 2. Next you'll add their face photos.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Field>
                    <FieldLabel>Name</FieldLabel>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Full name"
                      maxLength={100}
                    />
                  </Field>
                  <Field>
                    <FieldLabel>Notes</FieldLabel>
                    <Input
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Optional, e.g. consent form number"
                      maxLength={500}
                    />
                  </Field>
                  <Field orientation="horizontal">
                    <Checkbox
                      checked={hasConsent}
                      onCheckedChange={(checked) => setHasConsent(checked)}
                    />
                    <FieldLabel className="font-normal">
                      This person has consented to their face data being stored
                      for recognition.
                    </FieldLabel>
                  </Field>
                </div>
                <DialogFooter>
                  <DialogClose
                    render={<Button variant="outline">Cancel</Button>}
                  />
                  <Button
                    onClick={handleCreate}
                    disabled={isSaving || !name.trim() || !hasConsent}
                  >
                    {isSaving ? <Spinner /> : "Next: add photos"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {people === null ? (
          !error && (
            <div className="flex justify-center py-12">
              <Spinner className="size-6" />
            </div>
          )
        ) : people.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No one registered yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    <TableCell isHeader className={HEADER_CELL}>
                      Name
                    </TableCell>
                    <TableCell isHeader className={HEADER_CELL}>
                      Face photos
                    </TableCell>
                    <TableCell isHeader className={HEADER_CELL}>
                      Last seen
                    </TableCell>
                    <TableCell isHeader className={HEADER_CELL}>
                      Notes
                    </TableCell>
                    <TableCell isHeader className={HEADER_CELL}>
                      Status
                    </TableCell>
                    {isAdmin && (
                      <TableCell isHeader className={HEADER_CELL}>
                        Action
                      </TableCell>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {people.map((person) => (
                    <TableRow key={person.id}>
                      <TableCell className="px-5 py-4 text-sm font-medium text-gray-800 dark:text-white/90">
                        {person.name}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        {person.face_count === 0 ? (
                          <Badge color="warning">No photos</Badge>
                        ) : (
                          <Badge color="success">
                            {person.face_count} photo
                            {person.face_count === 1 ? "" : "s"}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {person.last_seen_at ? (
                          <>
                            <span className="text-gray-800 dark:text-white/90">
                              {person.last_seen_camera_id !== null
                                ? cameraName(person.last_seen_camera_id)
                                : "Removed camera"}
                            </span>
                            <span className="block text-xs">
                              {timeAgo(person.last_seen_at, now)}
                            </span>
                          </>
                        ) : (
                          "Never"
                        )}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {person.notes ?? "—"}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <Badge color={person.is_active ? "success" : "gray"}>
                          {person.is_active ? "active" : "inactive"}
                        </Badge>
                      </TableCell>
                      {isAdmin && (
                        <TableCell className="px-5 py-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setPhotosFor(person)}
                            >
                              Face photos
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setPendingRemoval(person)}
                            >
                              Remove
                            </Button>
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </ComponentCard>

      <FacePhotosDialog
        person={photosFor}
        onOpenChange={(open) => {
          if (!open) setPhotosFor(null);
        }}
        onChanged={(personId, faceCount) =>
          setPeople(
            (prev) =>
              prev?.map((p) =>
                p.id === personId ? { ...p, face_count: faceCount } : p,
              ) ?? prev,
          )
        }
      />

      <ConfirmDialog
        open={pendingRemoval !== null}
        onOpenChange={(open) => {
          if (!open) setPendingRemoval(null);
        }}
        title="Remove person?"
        description={
          <>
            <span className="font-medium text-gray-800 dark:text-white/90">
              {pendingRemoval?.name}
            </span>{" "}
            and all their face photos will be deleted. The recognizer stops
            knowing them within 30 seconds. This can't be undone.
          </>
        }
        confirmLabel="Remove"
        destructive
        isConfirming={isRemoving}
        onConfirm={() => void handleRemove()}
      />
    </div>
  );
}
