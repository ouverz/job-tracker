import { useState } from "react";
import { ExternalLink, ChevronUp, ChevronDown, Loader2, Star, Clock, CheckCircle, XCircle, Archive, X, ChevronLeft, ChevronRight, Bell } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { relativeDate } from "../../utils/dates";
import { StatusBadge, SourceBadge, TypeBadge } from "./StatusBadge";
import { ScoreBar } from "./ScoreBar";

function safeUrl(url) {
  if (!url) return null;
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch { return null; }
}

const VALID_STATUSES = ["new", "pending", "applied", "rejected", "archived"];

const BULK_ACTIONS = [
  { status: "new", icon: Star, label: "New", color: "text-blue-400" },
  { status: "pending", icon: Clock, label: "Pending", color: "text-yellow-400" },
  { status: "applied", icon: CheckCircle, label: "Applied", color: "text-green-400" },
  { status: "rejected", icon: XCircle, label: "Rejected", color: "text-red-400" },
  { status: "archived", icon: Archive, label: "Archive", color: "text-slate-400" },
];


function isOverdue(follow_up_at) {
  if (!follow_up_at) return false;
  return new Date(follow_up_at.endsWith("Z") ? follow_up_at : follow_up_at + "Z") < new Date();
}

function StarButton({ job }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (starred) => api.updateJob(job.id, { starred }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  return (
    <button
      onClick={(e) => { e.stopPropagation(); mutation.mutate(job.starred ? 0 : 1); }}
      className={`transition-colors ${job.starred ? "text-yellow-400 hover:text-yellow-300" : "text-slate-700 hover:text-slate-400"}`}
      title={job.starred ? "Unstar" : "Star this job"}
    >
      <Star size={14} fill={job.starred ? "currentColor" : "none"} />
    </button>
  );
}

export default function JobTable({
  jobs, total, isLoading, filters, onFilterChange,
  onSelectJob, selectedJobId, onRefresh, onBulkStatus,
  page, pageSize, onPageChange,
}) {
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkPending, setBulkPending] = useState(false);

  function SortHeader({ label, field }) {
    const active = filters.sort === field;
    return (
      <button
        className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-slate-400 hover:text-slate-200 transition-colors"
        onClick={() => {
          if (active) onFilterChange("order", filters.order === "desc" ? "asc" : "desc");
          else { onFilterChange("sort", field); onFilterChange("order", "desc"); }
        }}
      >
        {label}
        {active && (filters.order === "desc" ? <ChevronDown size={12} /> : <ChevronUp size={12} />)}
      </button>
    );
  }

  const allVisibleIds = jobs.map((j) => j.id);
  const allSelected = allVisibleIds.length > 0 && allVisibleIds.every((id) => selectedIds.has(id));
  const someSelected = allVisibleIds.some((id) => selectedIds.has(id));

  function toggleAll() {
    setSelectedIds(allSelected ? new Set() : new Set(allVisibleIds));
  }

  function toggleOne(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleBulkAction(status) {
    if (!selectedIds.size || bulkPending) return;
    setBulkPending(true);
    try {
      await onBulkStatus([...selectedIds], status);
      setSelectedIds(new Set());
    } finally {
      setBulkPending(false);
    }
  }

  if (isLoading) {
    return (
      <div className="mt-8 flex items-center justify-center gap-3 text-slate-500">
        <Loader2 className="animate-spin" size={20} /> Loading jobs…
      </div>
    );
  }

  if (!jobs.length) {
    return (
      <div className="mt-12 text-center text-slate-500">
        <p className="text-lg">No jobs found</p>
        <p className="text-sm mt-1">Run the pipeline or adjust your filters</p>
      </div>
    );
  }

  return (
    <div className="mt-4">
      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="mb-2 flex items-center gap-3 bg-surface-1 border border-slate-700 rounded-xl px-4 py-2.5">
          <span className="text-sm text-slate-300 font-medium">{selectedIds.size} selected</span>
          <span className="text-slate-700">·</span>
          <span className="text-xs text-slate-500">Set status:</span>
          <div className="flex gap-1.5 flex-wrap">
            {BULK_ACTIONS.map(({ status, icon: Icon, label, color }) => (
              <button
                key={status}
                onClick={() => handleBulkAction(status)}
                disabled={bulkPending}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border border-slate-700 bg-surface-2 text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-50"
              >
                <Icon size={12} className={color} /> {label}
              </button>
            ))}
          </div>
          <button onClick={() => setSelectedIds(new Set())} className="ml-auto text-slate-500 hover:text-slate-300">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-slate-500">
          {total === 0 ? "0 jobs" : `${page * pageSize + 1}–${Math.min((page + 1) * pageSize, total)} of ${total} jobs`}
        </span>
        {total > pageSize && (
          <div className="flex items-center gap-1">
            <button onClick={() => onPageChange(page - 1)} disabled={page === 0}
              className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs text-slate-500 px-2">{page + 1} / {Math.ceil(total / pageSize)}</span>
            <button onClick={() => onPageChange(page + 1)} disabled={(page + 1) * pageSize >= total}
              className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-surface-1">
                <th className="px-3 py-3 w-8">
                  <input type="checkbox" checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                    onChange={toggleAll} className="accent-blue-500 cursor-pointer" />
                </th>
                <th className="px-2 py-3 w-6"></th>
                <th className="px-4 py-3 text-left"><SortHeader label="Role" field="title" /></th>
                <th className="px-4 py-3 text-left hidden md:table-cell">
                  <SortHeader label="Company" field="company" />
                </th>
                <th className="px-4 py-3 text-left hidden lg:table-cell">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Source</span>
                </th>
                <th className="px-4 py-3 text-left hidden lg:table-cell">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Type</span>
                </th>
                <th className="px-4 py-3 text-left"><SortHeader label="Score" field="cv_score" /></th>
                <th className="px-4 py-3 text-left">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Status</span>
                </th>
                <th className="px-4 py-3 text-left hidden sm:table-cell"><SortHeader label="Found" field="scraped_at" /></th>
                <th className="px-4 py-3 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => onSelectJob(job.id)}
                  className={`border-b border-slate-800/50 cursor-pointer transition-colors hover:bg-surface-1 ${
                    selectedJobId === job.id ? "bg-surface-1 border-l-2 border-l-blue-500" : ""
                  } ${selectedIds.has(job.id) ? "bg-blue-950/20" : ""}`}
                >
                  <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" checked={selectedIds.has(job.id)} onChange={() => toggleOne(job.id)} className="accent-blue-500 cursor-pointer" />
                  </td>
                  <td className="px-2 py-3" onClick={(e) => e.stopPropagation()}>
                    <StarButton job={job} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-200 leading-tight max-w-xs truncate">
                      {job.title}
                      {!job.has_description && (
                        <span className="ml-1.5 inline-flex items-center text-[10px] text-amber-500 bg-amber-500/10 border border-amber-500/30 rounded px-1 py-0.5 font-medium" title="No job description available">
                          No JD
                        </span>
                      )}
                      {isOverdue(job.follow_up_at) && (
                        <span className="ml-1.5 inline-flex items-center gap-0.5 text-xs text-orange-400" title={`Follow up: ${job.follow_up_at}`}>
                          <Bell size={10} /> follow up
                        </span>
                      )}
                    </div>
                    {job.location && <div className="text-xs text-slate-500 mt-0.5 truncate">{job.location}</div>}
                    {(() => {
                      try {
                        const b = job.cv_score_breakdown ? JSON.parse(job.cv_score_breakdown) : null;
                        const gaps = b?.gaps?.slice(0, 2) ?? [];
                        if (!gaps.length) return null;
                        return (
                          <div className="relative inline-block group/gaps mt-1">
                            <span className="text-xs text-amber-400/60 cursor-default">△ {gaps.length} gap{gaps.length > 1 ? "s" : ""}</span>
                            <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover/gaps:block w-64 bg-slate-800 border border-slate-700 rounded-lg p-2 shadow-xl">
                              <ul className="space-y-1">
                                {gaps.map((g, i) => (
                                  <li key={i} className="text-xs text-amber-400/80 leading-snug">△ {g}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        );
                      } catch { return null; }
                    })()}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="text-slate-300 truncate max-w-[140px] block">{job.company || "—"}</span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell"><SourceBadge source={job.source} /></td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <div className="flex flex-col gap-1">
                      <TypeBadge type={job.employment_type} />
                      {job.remote_type && job.remote_type !== "onsite" && <TypeBadge type={job.remote_type} />}
                    </div>
                  </td>
                  <td className="px-4 py-3"><ScoreBar score={job.cv_score} /></td>
                  <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                  <td className="px-4 py-3 hidden sm:table-cell text-xs text-slate-500">{relativeDate(job.scraped_at, "relative")}</td>
                  <td className="px-4 py-3">
                    {safeUrl(job.url) && (
                      <a href={safeUrl(job.url)} target="_blank" rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()} className="text-slate-600 hover:text-blue-400 transition-colors">
                        <ExternalLink size={14} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
