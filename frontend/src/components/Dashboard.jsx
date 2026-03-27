import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";

function StatCard({ label, value, color = "text-white" }) {
  return (
    <div className="bg-surface-1 border border-slate-800 rounded-xl p-5">
      <div className={`text-3xl font-bold ${color}`}>{value ?? "—"}</div>
      <div className="text-sm text-slate-500 mt-1">{label}</div>
    </div>
  );
}

function BarChart({ data, color, emptyMsg }) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-slate-500 text-center py-8">{emptyMsg}</p>;
  }
  const max = Math.max(...data.map((d) => d.count), 1);
  // Show last 30 days, filling gaps with 0
  const today = new Date();
  const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (29 - i));
    return d.toISOString().slice(0, 10);
  });
  const byDate = Object.fromEntries(data.map((d) => [d.date, d.count]));
  const filled = days.map((date) => ({ date, count: byDate[date] || 0 }));
  const filledMax = Math.max(...filled.map((d) => d.count), 1);

  return (
    <div className="flex items-end gap-px h-28 w-full">
      {filled.map((d) => (
        <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5 group relative">
          <div
            className={`w-full ${color} rounded-t min-h-[2px] transition-all`}
            style={{ height: `${Math.max((d.count / filledMax) * 100, d.count > 0 ? 4 : 0)}%` }}
          />
          {/* Tooltip */}
          <div className="absolute bottom-full mb-1 hidden group-hover:flex flex-col items-center pointer-events-none z-10">
            <div className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white whitespace-nowrap">
              {d.date}: {d.count}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function MonthAxis() {
  const today = new Date();
  const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (29 - i));
    return d;
  });
  // Show label every 7 days
  return (
    <div className="flex w-full mt-1">
      {days.map((d, i) => (
        <div key={i} className="flex-1 text-center">
          {i % 7 === 0 && (
            <span className="text-[10px] text-slate-600">
              {d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["kpi"],
    queryFn: api.getKpi,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="mt-16 flex items-center justify-center gap-3 text-slate-500">
        <Loader2 className="animate-spin" size={20} />
        Loading KPIs…
      </div>
    );
  }

  const s = data?.summary;

  return (
    <div className="mt-6 space-y-8">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Applied today" value={s?.applied_today} color="text-green-400" />
        <StatCard label="Applied this week" value={s?.applied_this_week} color="text-green-400" />
        <StatCard label="Total applied" value={s?.total_applied} color="text-white" />
        <StatCard label="Pending" value={s?.pending} color="text-yellow-400" />
        <StatCard label="Rejected" value={s?.total_rejected} color="text-red-400" />
        <StatCard
          label={`Roles with JD${s?.with_jd != null ? ` (${s.with_jd}/${s.total_jobs})` : ""}`}
          value={s?.jd_coverage_pct != null ? `${s.jd_coverage_pct}%` : "—"}
          color="text-blue-400"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-1 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Applications — last 30 days</h3>
          <BarChart
            data={data?.applied_daily}
            color="bg-green-500"
            emptyMsg="No applications recorded yet"
          />
          <MonthAxis />
        </div>

        <div className="bg-surface-1 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Rejections — last 30 days</h3>
          <BarChart
            data={data?.rejections_daily}
            color="bg-red-500"
            emptyMsg="No rejections recorded yet"
          />
          <MonthAxis />
        </div>
      </div>
    </div>
  );
}
