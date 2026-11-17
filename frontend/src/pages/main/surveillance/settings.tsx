import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import {
  ApiError,
  type Camera,
  type CameraSettingsInput,
  camerasApi,
  cameraSettingsApi,
} from "@/services";
import { useEffect, useState } from "react";

const DEFAULTS: CameraSettingsInput = {
  roi_x1: 0.5,
  roi_y1: 0.0,
  roi_x2: 1.0,
  roi_y2: 1.0,
  loiter_seconds: 5.0,
  tamper_motion_threshold: 25.0,
  tamper_covered_brightness_ratio: 0.4,
  tamper_covered_sharpness_ratio: 0.3,
  tamper_defocus_sharpness_ratio: 0.35,
};

function NumberField({
  label,
  value,
  onChange,
  step = 0.05,
  min = 0,
  max = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
}) {
  return (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <Input
        type="number"
        step={step}
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Field>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>("");
  const [form, setForm] = useState<CameraSettingsInput>(DEFAULTS);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  useEffect(() => {
    camerasApi.list().then((list) => {
      setCameras(list);
      if (list.length > 0) setSelectedCameraId(String(list[0].id));
    });
  }, []);

  useEffect(() => {
    if (!selectedCameraId) return;
    setIsLoading(true);
    setMessage(null);
    cameraSettingsApi
      .get(Number(selectedCameraId))
      .then((settings) => setForm(settings))
      .catch((err) => setMessage({ type: "error", text: err instanceof ApiError ? err.message : "Failed to load settings" }))
      .finally(() => setIsLoading(false));
  }, [selectedCameraId]);

  const update = <K extends keyof CameraSettingsInput>(key: K, value: CameraSettingsInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      await cameraSettingsApi.update(Number(selectedCameraId), form);
      setMessage({ type: "success", text: "Settings saved." });
    } catch (err) {
      setMessage({ type: "error", text: err instanceof ApiError ? err.message : "Failed to save settings" });
    } finally {
      setIsSaving(false);
    }
  };

  const isReadOnly = user?.role !== "admin";

  return (
    <div>
      <PageMeta title="Settings | UniVerse" description="Per-camera ROI, loitering, and tamper thresholds" />
      <PageBreadcrumb pageTitle="Settings" />

      <ComponentCard
        title="Detection Settings"
        description="ROI zone, loitering threshold, and tamper sensitivity per camera. These values are read by the Phase 1 AI scripts instead of hardcoded defaults."
      >
        <div className="mb-6 max-w-xs">
          <Field>
            <FieldLabel>Camera</FieldLabel>
            <Select value={selectedCameraId} onValueChange={(v) => setSelectedCameraId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="Select a camera">
                  {(value: string) => cameras.find((c) => String(c.id) === value)?.name ?? "Select a camera"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {cameras.map((camera) => (
                  <SelectItem key={camera.id} value={String(camera.id)}>
                    {camera.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>

        {message && (
          <div
            className={`mb-4 rounded-lg px-4 py-3 text-sm ${
              message.type === "error"
                ? "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400"
                : "bg-green-50 text-green-600 dark:bg-green-500/10 dark:text-green-400"
            }`}
          >
            {message.text}
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner className="size-6" />
          </div>
        ) : !selectedCameraId ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No cameras registered yet — add one from the Cameras page first.
          </p>
        ) : (
          <fieldset disabled={isReadOnly} className="space-y-8 disabled:opacity-60">
            <div>
              <h4 className="mb-3 text-sm font-semibold text-gray-800 dark:text-white/90">
                Restricted Area (ROI)
              </h4>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <NumberField label="X1" value={form.roi_x1} onChange={(v) => update("roi_x1", v)} />
                <NumberField label="Y1" value={form.roi_y1} onChange={(v) => update("roi_y1", v)} />
                <NumberField label="X2" value={form.roi_x2} onChange={(v) => update("roi_x2", v)} />
                <NumberField label="Y2" value={form.roi_y2} onChange={(v) => update("roi_y2", v)} />
              </div>
              <p className="mt-1.5 text-xs text-gray-400">Fractions of frame size (0.0-1.0). X1/Y1 must be less than X2/Y2.</p>
            </div>

            <div>
              <h4 className="mb-3 text-sm font-semibold text-gray-800 dark:text-white/90">Loitering</h4>
              <div className="max-w-xs">
                <NumberField
                  label="Loiter threshold (seconds)"
                  value={form.loiter_seconds}
                  onChange={(v) => update("loiter_seconds", v)}
                  step={1}
                  min={1}
                  max={3600}
                />
              </div>
            </div>

            <div>
              <h4 className="mb-3 text-sm font-semibold text-gray-800 dark:text-white/90">
                Tamper Sensitivity
              </h4>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <NumberField
                  label="Motion threshold"
                  value={form.tamper_motion_threshold}
                  onChange={(v) => update("tamper_motion_threshold", v)}
                  step={1}
                  min={1}
                  max={255}
                />
                <NumberField
                  label="Covered: brightness ratio"
                  value={form.tamper_covered_brightness_ratio}
                  onChange={(v) => update("tamper_covered_brightness_ratio", v)}
                />
                <NumberField
                  label="Covered: sharpness ratio"
                  value={form.tamper_covered_sharpness_ratio}
                  onChange={(v) => update("tamper_covered_sharpness_ratio", v)}
                />
                <NumberField
                  label="Defocus: sharpness ratio"
                  value={form.tamper_defocus_sharpness_ratio}
                  onChange={(v) => update("tamper_defocus_sharpness_ratio", v)}
                />
              </div>
            </div>

            {!isReadOnly && (
              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? <Spinner /> : "Save Settings"}
              </Button>
            )}
            {isReadOnly && (
              <p className="text-sm text-gray-400">Only admins can change detection settings.</p>
            )}
          </fieldset>
        )}
      </ComponentCard>
    </div>
  );
}
