import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";

const STATUS_OPTIONS = ["new", "applied", "pending", "interview", "rejected"];

// Item appears in both lists — tooltip explains why
const OVERLAP_TOOLTIP =
  "Appears in both strengths and gaps. This means different JDs weight this skill " +
  "differently: some roles consider it covered by your CV, others require a deeper " +
  "level or more explicit evidence. Check which job types flag it as a gap.";

function FrequencyBar({ text, count, max, color, overlapCount, overlapLabel }) {
  const pct = max > 0 ? Math.max((count / max) * 100, 2) : 0;
  return (
    <div className="flex items-center gap-3 py-1.5">
      {/* Label */}
      <span className="flex-1 min-w-0 truncate text-sm text-slate-300" title={text}>
        {text}
      </span>

      {/* Overlap badge — shown when this entity also appears on the other side */}
      {overlapCount != null && (
        <span
          className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-900/40 text-amber-400 border border-amber-700/50 cursor-help"
          title={OVERLAP_TOOLTIP}
        >
          {overlapLabel} {overlapCount}
        </span>
      )}

      {/* Count */}
      <span className="w-6 text-right text-xs text-slate-500 shrink-0">{count}</span>

      {/* Bar */}
      <div className="w-36 h-2 rounded-full bg-surface-3 shrink-0 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Column({ title, items, color, emptyMsg, headerColor, overlapMap, overlapLabel }) {
  const max = items.length > 0 ? items[0].count : 0;
  return (
    <div className="bg-surface-1 border border-slate-800 rounded-xl p-5 flex flex-col gap-1">
      <h3 className={`text-xs font-semibold uppercase tracking-wide mb-3 ${headerColor}`}>
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 py-4 text-center">{emptyMsg}</p>
      ) : (
        items.map((item) => (
          <FrequencyBar
            key={item.text}
            text={item.text}
            count={item.count}
            max={max}
            color={color}
            overlapCount={overlapMap[item.text] ?? null}
            overlapLabel={overlapLabel}
          />
        ))
      )}
    </div>
  );
}

export default function GapAnalysis() {
  const [minScore, setMinScore] = useState(0);
  const [activeStatuses, setActiveStatuses] = useState([]);

  function toggleStatus(s) {
    setActiveStatuses((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ["gap-analysis", minScore, activeStatuses.join(",")],
    queryFn: () =>
      api.getGapAnalysis({
        min_score: minScore > 0 ? minScore : undefined,
        status: activeStatuses.length ? activeStatuses.join(",") : undefined,
      }),
    staleTime: 60_000,
  });

  // Build overlap lookup maps: entity text → count on the OTHER side
  const gapMap = {};
  const strengthMap = {};
  if (data) {
    const gapIndex = Object.fromEntries(data.gaps.map((g) => [g.text, g.count]));
    const strengthIndex = Object.fromEntries(data.strengths.map((s) => [s.text, s.count]));
    // For each strength, check if it also appears as a gap
    data.strengths.forEach((s) => {
      if (gapIndex[s.text]) strengthMap[s.text] = gapIndex[s.text];
    });
    // For each gap, check if it also appears as a strength
    data.gaps.forEach((g) => {
      if (strengthIndex[g.text]) gapMap[g.text] = strengthIndex[g.text];
    });
  }

  const overlapCount = Object.keys(gapMap).length;

  return (
    <div className="mt-6 space-y-5">
      {/* Filter bar */}
      <div className="bg-surface-1 border border-slate-800 rounded-xl px-5 py-4 flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 font-medium whitespace-nowrap">Score ≥</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-28 accent-blue-500"
          />
          <span className={`text-xs font-medium w-8 ${minScore > 0 ? "text-blue-400" : "text-slate-500"}`}>
            {minScore > 0 ? minScore : "Any"}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500 font-medium">Status:</span>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => toggleStatus(s)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                activeStatuses.includes(s)
                  ? "bg-blue-600 text-white"
                  : "bg-surface-2 text-slate-400 hover:text-slate-200 hover:bg-surface-3"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="mt-16 flex items-center justify-center gap-3 text-slate-500">
          <Loader2 className="animate-spin" size={20} />
          Loading analysis…
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-sm text-red-300">
          Failed to load analysis: {error.message}
        </div>
      )}

      {data && (
        <>
          <div className="flex items-center gap-4 flex-wrap">
            <p className="text-xs text-slate-500">
              Analysing{" "}
              <span className="text-slate-300 font-medium">{data.total_scored}</span> scored job
              {data.total_scored !== 1 ? "s" : ""}
              {minScore > 0 && ` · score ≥ ${minScore}`}
              {activeStatuses.length > 0 && ` · status: ${activeStatuses.join(", ")}`}
            </p>
            {/* Overlap summary */}
            {overlapCount > 0 && (
              <span
                className="text-xs px-2 py-0.5 rounded bg-amber-900/30 text-amber-400 border border-amber-700/40 cursor-help"
                title={OVERLAP_TOOLTIP}
              >
                ⚡ {overlapCount} skill{overlapCount !== 1 ? "s" : ""} appear in both lists
              </span>
            )}
          </div>

          {data.total_scored === 0 ? (
            <div className="mt-12 text-center text-slate-500">
              <p className="text-lg">No scored jobs match your filters</p>
              <p className="text-sm mt-1">Try lowering the min score or removing status filters</p>
            </div>
          ) : data.gaps.length === 0 && data.strengths.length === 0 ? (
            <div className="mt-12 text-center text-slate-500">
              <p className="text-lg">No breakdown data yet</p>
              <p className="text-sm mt-1">Score more jobs to populate this view</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Column
                title="✓ Strengths"
                items={data.strengths}
                color="bg-green-500"
                headerColor="text-green-400"
                emptyMsg="No strength data in the selected jobs"
                overlapMap={strengthMap}
                overlapLabel="△ gap in"
              />
              <Column
                title="△ Gaps"
                items={data.gaps}
                color="bg-red-500"
                headerColor="text-red-400"
                emptyMsg="No gap data in the selected jobs"
                overlapMap={gapMap}
                overlapLabel="✓ strength in"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
