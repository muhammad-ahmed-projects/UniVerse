import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { ApiError, type Incident, incidentsApi } from "@/services";
import { useEffect, useState } from "react";

function StatusBadge({ status }: { status: Incident["status"] }) {
  if (status === "open") return <Badge color="error">open</Badge>;
  if (status === "acknowledged") return <Badge color="warning">acknowledged</Badge>;
  return <Badge color="success">resolved</Badge>;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => {
    incidentsApi
      .list()
      .then(setIncidents)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load incidents"));
  };

  useEffect(load, []);

  useAlertsSocket((msg) => {
    if (msg.type === "incident_update") {
      load();
    }
  });

  const act = async (incident: Incident, action: "acknowledge" | "resolve") => {
    setBusyId(incident.id);
    try {
      const updated =
        action === "acknowledge"
          ? await incidentsApi.acknowledge(incident.id)
          : await incidentsApi.resolve(incident.id);
      setIncidents((prev) => prev?.map((i) => (i.id === updated.id ? updated : i)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <PageMeta title="Incidents | UniVerse" description="Human-reviewed security incidents" />
      <PageBreadcrumb pageTitle="Incidents" />

      <ComponentCard
        title="Incidents"
        description="Alerts a human has reviewed and confirmed. Acknowledge, then resolve once handled."
      >
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {incidents === null ? (
          <div className="flex justify-center py-12">
            <Spinner className="size-6" />
          </div>
        ) : incidents.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No incidents yet. Promote an alert from the Alerts page to create one.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Title</TableCell>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Camera</TableCell>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Priority</TableCell>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Status</TableCell>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Created</TableCell>
                    <TableCell isHeader className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400">Action</TableCell>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {incidents.map((incident) => (
                    <TableRow key={incident.id}>
                      <TableCell className="px-5 py-4 text-sm font-medium text-gray-800 dark:text-white/90">{incident.title}</TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">#{incident.camera_id}</TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">{incident.priority}</TableCell>
                      <TableCell className="px-5 py-4"><StatusBadge status={incident.status} /></TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {new Date(incident.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        {incident.status === "open" && (
                          <Button size="sm" variant="outline" disabled={busyId === incident.id} onClick={() => act(incident, "acknowledge")}>
                            {busyId === incident.id ? <Spinner /> : "Acknowledge"}
                          </Button>
                        )}
                        {incident.status === "acknowledged" && (
                          <Button size="sm" disabled={busyId === incident.id} onClick={() => act(incident, "resolve")}>
                            {busyId === incident.id ? <Spinner /> : "Resolve"}
                          </Button>
                        )}
                        {incident.status === "resolved" && (
                          <span className="text-sm text-gray-400">Done</span>
                        )}
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
