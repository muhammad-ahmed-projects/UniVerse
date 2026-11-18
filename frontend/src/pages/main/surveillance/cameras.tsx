import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
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
import {
  ApiError,
  type Camera,
  type CameraStatus,
  camerasApi,
} from "@/services";
import { useEffect, useState } from "react";

function StatusBadge({ status }: { status: CameraStatus }) {
  if (status === "online") return <Badge color="success">online</Badge>;
  if (status === "offline") return <Badge color="error">offline</Badge>;
  return <Badge color="gray">unknown</Badge>;
}

export default function CamerasPage() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [streamSource, setStreamSource] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const load = () => {
    camerasApi
      .list()
      .then(setCameras)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load cameras",
        ),
      );
  };

  useEffect(load, []);

  useAlertsSocket((msg) => {
    // Reload rather than patch, so last_seen_at updates along with status.
    if (msg.type === "camera_status") load();
  });

  const handleCreate = async () => {
    setIsSaving(true);
    try {
      const created = await camerasApi.create({
        name,
        location: location || undefined,
        stream_source: streamSource,
      });
      setName("");
      setLocation("");
      setStreamSource("");
      setIsDialogOpen(false);
      toast.success("Camera added", created.name);
      load();
    } catch (err) {
      toast.error(
        "Couldn't add camera",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div>
      <PageMeta
        title="Cameras | UniVerse"
        description="Camera status and management"
      />
      <PageBreadcrumb pageTitle="Cameras" />

      <ComponentCard
        title="Cameras"
        description="Live status of every registered camera. Status updates arrive in real time over the dashboard's WebSocket connection."
      >
        <div className="mb-4 flex justify-end">
          {user?.role === "admin" && (
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <Button onClick={() => setIsDialogOpen(true)}>Add Camera</Button>
              <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Add Camera</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <Field>
                    <FieldLabel>Name</FieldLabel>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Front entrance"
                    />
                  </Field>
                  <Field>
                    <FieldLabel>Location</FieldLabel>
                    <Input
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="Mock office - entrance"
                    />
                  </Field>
                  <Field>
                    <FieldLabel>Stream source</FieldLabel>
                    <Input
                      value={streamSource}
                      onChange={(e) => setStreamSource(e.target.value)}
                      placeholder="Webcam index (0, 1, ...) or RTSP URL"
                    />
                  </Field>
                </div>
                <DialogFooter>
                  <DialogClose
                    render={<Button variant="outline">Cancel</Button>}
                  />
                  <Button
                    onClick={handleCreate}
                    disabled={isSaving || !name || !streamSource}
                  >
                    {isSaving ? <Spinner /> : "Save"}
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

        {cameras === null ? (
          <div className="flex justify-center py-12">
            <Spinner className="size-6" />
          </div>
        ) : cameras.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No cameras registered yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Name
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Location
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Source
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Status
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Last seen
                    </TableCell>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {cameras.map((camera) => (
                    <TableRow key={camera.id}>
                      <TableCell className="px-5 py-4 text-sm font-medium text-gray-800 dark:text-white/90">
                        {camera.name}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {camera.location ?? "â€”"}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {camera.stream_source}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <StatusBadge status={camera.status} />
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {camera.last_seen_at
                          ? new Date(camera.last_seen_at).toLocaleString()
                          : "â€”"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </ComponentCard>
    </div>
  );
}
