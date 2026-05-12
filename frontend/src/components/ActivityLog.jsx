import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { api } from "../api/client";

function currentMondayISO() {
  const today = new Date();
  const day = today.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diff);
  return monday.toISOString().slice(0, 10);
}

function addWeeks(isoDate, n) {
  const d = new Date(isoDate + "T00:00:00");
  d.setDate(d.getDate() + n * 7);
  return d.toISOString().slice(0, 10);
}

function weekLabel(weekStart, weekEnd) {
  const fmt = (s) =>
    new Date(s + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  return `${fmt(weekStart)} – ${fmt(weekEnd)}`;
}

function StatusChip({ status }) {
  if (status === "n/a")
    return <span className="text-xs text-slate-500">n/a</span>;
  if (status === "on_track")
    return (
      <span className="px-2 py-0.5 rounded-full text-xs bg-green-900/40 text-green-400 border border-green-700/40">
        on track
      </span>
    );
  return (
    <span className="px-2 py-0.5 rounded-full text-xs bg-red-900/40 text-red-400 border border-red-700/40">
      behind
    </span>
  );
}

function TargetCell({ activityKey, target, weekStart }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(String(target));

  const mutation = useMutation({
    mutationFn: (t) => api.updateActivityLog(weekStart, activityKey, { target: t }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["activity-log", weekStart] }),
  });

  const commit = () => {
    const n = parseInt(val, 10);
    if (!isNaN(n) && n >= 0) mutation.mutate(n);
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        autoFocus
        className="w-12 bg-slate-700 border border-blue-500 rounded px-1 py-0.5 text-sm text-white text-center outline-none"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setEditing(false);
        }}
      />
    );
  }

  return (
    <button
      className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
      onClick={() => { setVal(String(target)); setEditing(true); }}
      title="Click to edit target"
    >
      /{target}
    </button>
  );
}

function ActualCell({ activityKey, actual, autoTracked, weekStart }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (v) => api.updateActivityLog(weekStart, activityKey, { actual: v }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["activity-log", weekStart] }),
  });

  if (autoTracked) {
    return (
      <div className="text-center text-white font-semibold text-sm" title="Auto-tracked from your data">
        {actual}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-2">
      <button
        className="w-6 h-6 flex items-center justify-center rounded bg-slate-700 hover:bg-slate-600 text-slate-300 text-base leading-none transition-colors"
        onClick={() => mutation.mutate(Math.max(0, actual - 1))}
      >
        −
      </button>
      <span className="w-5 text-center text-white font-semibold text-sm">{actual}</span>
      <button
        className="w-6 h-6 flex items-center justify-center rounded bg-slate-700 hover:bg-slate-600 text-slate-300 text-base leading-none transition-colors"
        onClick={() => mutation.mutate(actual + 1)}
      >
        +
      </button>
    </div>
  );
}

export default function ActivityLog() {
  const [weekStart, setWeekStart] = useState(currentMondayISO);
  const isCurrentWeek = weekStart === currentMondayISO();

  const { data, isLoading } = useQuery({
    queryKey: ["activity-log", weekStart],
    queryFn: () => api.getActivityLog(weekStart),
  });

  if (isLoading) {
    return (
      <div className="mt-16 flex items-center justify-center gap-3 text-slate-500">
        <Loader2 className="animate-spin" size={20} />
        Loading activity log…
      </div>
    );
  }

  return (
    <div className="mt-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-base font-semibold text-white flex-1">Weekly activity log</h2>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setWeekStart(addWeeks(weekStart, -1))}
            className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          >
            <ChevronLeft size={15} />
          </button>
          <span className="text-sm text-slate-300 w-36 text-center select-none">
            {data ? weekLabel(data.week_start, data.week_end) : "…"}
          </span>
          <button
            onClick={() => setWeekStart(addWeeks(weekStart, 1))}
            disabled={isCurrentWeek}
            className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors disabled:opacity-30 disabled:pointer-events-none"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>

      <div className="bg-surface-1 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left text-xs font-medium text-slate-500 px-5 py-3">Activity</th>
              <th className="text-center text-xs font-medium text-slate-500 px-4 py-3 w-20">Target</th>
              <th className="text-center text-xs font-medium text-slate-500 px-4 py-3 w-32">Actual</th>
              <th className="text-center text-xs font-medium text-slate-500 px-4 py-3 w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.activities.map((a) => (
              <tr key={a.key} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors">
                <td className="px-5 py-3.5 text-sm text-slate-200">
                  {a.label}
                  {a.auto_tracked && (
                    <span className="ml-2 text-[10px] text-slate-600 uppercase tracking-wide font-medium">
                      auto
                    </span>
                  )}
                </td>
                <td className="px-4 py-3.5 text-center">
                  <TargetCell activityKey={a.key} target={a.target} weekStart={data.week_start} />
                </td>
                <td className="px-4 py-3.5">
                  <ActualCell
                    activityKey={a.key}
                    actual={a.actual}
                    autoTracked={a.auto_tracked}
                    weekStart={data.week_start}
                  />
                </td>
                <td className="px-4 py-3.5 text-center">
                  <StatusChip status={a.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-2.5 text-xs text-slate-600">
        <span className="text-slate-500 font-medium">auto</span> rows are pulled from your job &amp; contacts data · click any target to edit
      </p>
    </div>
  );
}
