import { Spinner } from "@/components/ui/spinner";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { type ReviewStats, alertTypeLabel, alertsApi } from "@/services";
import { useCallback, useEffect, useState } from "react";

const percent = (value: number | null) =>
  value === null ? "—" : `${Math.round(value * 100)}%`;

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 px-4 py-3 dark:border-white/5">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-semibold text-gray-800 dark:text-white/90">
        {value}
      </p>
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

/** Measured detection accuracy from operators' verdicts (for the evaluation report). */
export function ReviewStatsCard() {
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [failed, setFailed] = useState(false);
  const [showTypes, setShowTypes] = useState(false);

  const load = useCallback(() => {
    alertsApi
      .reviewStats()
      .then((s) => {
        setStats(s);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(load, [load]);
  useAlertsSocket((msg) => {
    if (
      msg.type === "alert" ||
      msg.type === "alert_review" ||
      msg.type === "incident_update"
    )
      load();
  });

  if (failed) {
    return (
      <p className="text-sm text-red-600 dark:text-red-400">
        Couldn't load review statistics.
      </p>
    );
  }
  if (!stats) {
    return (
      <div className="flex justify-center py-4">
        <Spinner className="size-5" />
      </div>
    );
  }

  const { overall } = stats;
  const reviewed = overall.confirmed + overall.false_alarm;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label="Precision"
          value={percent(overall.precision)}
          hint="Reviewed alerts that were real"
        />
        <Stat
          label="False-alarm rate"
          value={percent(overall.false_alarm_rate)}
          hint={`${overall.false_alarm} of ${reviewed} reviewed`}
        />
        <Stat label="Confirmed" value={String(overall.confirmed)} />
        <Stat
          label="Not reviewed yet"
          value={String(overall.unreviewed)}
          hint={`of ${overall.total} alerts`}
        />
      </div>
      {stats.by_type.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowTypes((v) => !v)}
            className="text-sm font-medium text-brand-500 hover:underline"
          >
            {showTypes ? "Hide" : "Show"} accuracy per alert type
          </button>
          {showTypes && (
            <div className="mt-2 overflow-x-auto rounded-xl border border-gray-200 dark:border-white/5">
              <table className="min-w-full text-sm">
                <thead className="text-xs text-gray-500 dark:text-gray-400">
                  <tr>
                    {[
                      "Type",
                      "Confirmed",
                      "False alarms",
                      "Not reviewed",
                      "Precision",
                    ].map((h) => (
                      <th key={h} className="px-4 py-2 text-start font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-gray-700 dark:divide-white/5 dark:text-gray-300">
                  {stats.by_type.map((row) => (
                    <tr key={row.alert_type}>
                      <td className="px-4 py-2">
                        {alertTypeLabel(row.alert_type)}
                      </td>
                      <td className="px-4 py-2">{row.confirmed}</td>
                      <td className="px-4 py-2">{row.false_alarm}</td>
                      <td className="px-4 py-2">{row.unreviewed}</td>
                      <td className="px-4 py-2 font-medium">
                        {percent(row.precision)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
