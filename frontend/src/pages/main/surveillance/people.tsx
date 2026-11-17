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
import { useAuth } from "@/contexts";
import { ApiError, type Person, peopleApi } from "@/services";
import { useEffect, useState } from "react";

export default function PeoplePage() {
  const { user } = useAuth();
  const [people, setPeople] = useState<Person[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const isAdmin = user?.role === "admin";

  const load = () => {
    peopleApi
      .list()
      .then(setPeople)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load people",
        ),
      );
  };

  useEffect(load, []);

  const handleCreate = async () => {
    setIsSaving(true);
    try {
      await peopleApi.create({ name, notes: notes || undefined });
      setName("");
      setNotes("");
      setIsDialogOpen(false);
      load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to register person",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleRemove = async (person: Person) => {
    if (!window.confirm(`Remove ${person.name} from the registry?`)) return;
    setRemovingId(person.id);
    setError(null);
    try {
      await peopleApi.remove(person.id);
      setPeople((prev) => prev?.filter((p) => p.id !== person.id) ?? prev);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to remove person",
      );
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div>
      <PageMeta
        title="Registered People | UniVerse"
        description="Consent-based face recognition registry"
      />
      <PageBreadcrumb pageTitle="Registered People" />

      <ComponentCard
        title="Registered People"
        description="Individuals authorized for face-recognition matching. Face embeddings are captured separately via the AI registration script; this registry tracks the consent-based record."
      >
        <div className="mb-4 flex justify-end">
          {isAdmin && (
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <Button onClick={() => setIsDialogOpen(true)}>
                Register Person
              </Button>
              <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Register Person</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <Field>
                    <FieldLabel>Name</FieldLabel>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Full name"
                    />
                  </Field>
                  <Field>
                    <FieldLabel>Notes</FieldLabel>
                    <Input
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Optional"
                    />
                  </Field>
                </div>
                <DialogFooter>
                  <DialogClose
                    render={<Button variant="outline">Cancel</Button>}
                  />
                  <Button onClick={handleCreate} disabled={isSaving || !name}>
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

        {people === null ? (
          <div className="flex justify-center py-12">
            <Spinner className="size-6" />
          </div>
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
                      Notes
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Status
                    </TableCell>
                    {isAdmin && (
                      <TableCell
                        isHeader
                        className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                      >
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
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={removingId === person.id}
                            onClick={() => void handleRemove(person)}
                          >
                            {removingId === person.id ? <Spinner /> : "Remove"}
                          </Button>
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
    </div>
  );
}
