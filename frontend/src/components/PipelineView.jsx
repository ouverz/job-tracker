import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import JobTable from "./jobs/JobTable";
import JobDrawer from "./jobs/JobDrawer";

const PIPELINE_STATUSES = "applied,pending,interview,rejected";
const PAGE_SIZE = 15;

const SORTS = [
  { value: "status_changed_at", label: "Status Changed" },
  { value: "scraped_at", label: "Date Found" },
  { value: "cv_score", label: "CV Score" },
];

export default function PipelineView() {
  const queryClient = useQueryClient();
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({
    status: PIPELINE_STATUSES,
    source: "",
    employment_type: "",
    remote_type: "",
    location: "",
    scraped_days: "",
    q: "",
    sort: "status_changed_at",
    order: "desc",
  });

  const handleFilterChange = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(0);
  }, []);

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ["pipeline-jobs", filters, page],
    queryFn: () => api.getJobs({ ...filters, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
  });

  return (
    <div className="mt-4 space-y-3">
      {/* Status filter — only pipeline statuses */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-slate-500 font-medium">Show:</span>
        {["applied", "pending", "interview", "rejected"].map((s) => {
          const active = filters.status.split(",").includes(s);
          return (
            <button
              key={s}
              onClick={() => {
                const parts = filters.status.split(",").filter(Boolean);
                const next = active
                  ? parts.filter((p) => p !== s)
                  : [...parts, s];
                handleFilterChange("status", next.join(",") || PIPELINE_STATUSES);
              }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                active
                  ? "bg-blue-600 text-white"
                  : "bg-surface-2 text-slate-400 hover:text-slate-200 hover:bg-surface-3"
              }`}
            >
              {s}
            </button>
          );
        })}

        <div className="ml-auto flex items-center gap-2">
          <select
            value={filters.sort}
            onChange={(e) => handleFilterChange("sort", e.target.value)}
            className="bg-surface-1 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none"
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>Sort: {s.label}</option>
            ))}
          </select>
        </div>
      </div>

      <JobTable
        jobs={jobsData?.items || []}
        total={jobsData?.total || 0}
        isLoading={isLoading}
        filters={filters}
        onFilterChange={handleFilterChange}
        onSelectJob={setSelectedJobId}
        selectedJobId={selectedJobId}
        onRefresh={() => queryClient.invalidateQueries({ queryKey: ["pipeline-jobs"] })}
        onBulkStatus={async (ids, status) => {
          await api.batchUpdateStatus(ids, status);
          queryClient.invalidateQueries({ queryKey: ["pipeline-jobs"] });
          queryClient.invalidateQueries({ queryKey: ["stats"] });
        }}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
      />

      {selectedJobId && (
        <JobDrawer
          jobId={selectedJobId}
          onClose={() => setSelectedJobId(null)}
          onUpdate={() => {
            queryClient.invalidateQueries({ queryKey: ["pipeline-jobs"] });
            queryClient.invalidateQueries({ queryKey: ["job", selectedJobId] });
          }}
        />
      )}
    </div>
  );
}
