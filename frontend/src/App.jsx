import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle } from "lucide-react";
import { api } from "./api/client";
import Header from "./components/Header";
import FilterBar from "./components/FilterBar";
import JobTable from "./components/jobs/JobTable";
import JobDrawer from "./components/jobs/JobDrawer";
import ScrapeModal from "./components/scraping/ScrapeModal";
import Dashboard from "./components/Dashboard";
import PipelineView from "./components/PipelineView";
import GapAnalysis from "./components/GapAnalysis";
import ActivityLog from "./components/ActivityLog";

const PAGE_SIZE = 15;

const DEFAULT_FILTERS = {
  status: "new",
  source: "",
  employment_type: "",
  remote_type: "",
  location: "",
  scraped_days: "",
  q: "",
  sort: "scraped_at",
  order: "desc",
  starred: "",
  min_score: "",
  max_score: "",
  no_jd: "",
};

function readFiltersFromUrl() {
  const p = new URLSearchParams(window.location.search);
  const out = { ...DEFAULT_FILTERS };
  for (const key of Object.keys(DEFAULT_FILTERS)) {
    if (p.has(key)) out[key] = p.get(key);
  }
  return out;
}

function filtersToUrl(filters) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v && v !== DEFAULT_FILTERS[k]) p.set(k, v);
  }
  return p.toString();
}

export default function App() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState(readFiltersFromUrl);
  const [page, setPage] = useState(0);
  const [tab, setTab] = useState("jobs");
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [scrapeRunId, setScrapeRunId] = useState(null);
  const [scrapeModalOpen, setScrapeModalOpen] = useState(false);
  const [scrapeDetails, setScrapeDetails] = useState({});
  const [scrapeDone, setScrapeDone] = useState(false);
  const isFirstRender = useRef(true);

  // Persist filters to URL (skip first render to avoid redundant replace)
  useEffect(() => {
    if (isFirstRender.current) { isFirstRender.current = false; return; }
    const qs = filtersToUrl(filters);
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, "", newUrl);
  }, [filters]);

  // SSE lives here so it survives modal close
  useEffect(() => {
    if (!scrapeRunId) return;
    setScrapeDetails({});
    setScrapeDone(false);

    const es = new EventSource(`/api/scraping/runs/${scrapeRunId}/stream`);

    es.addEventListener("source_update", (e) => {
      const detail = JSON.parse(e.data);
      setScrapeDetails((prev) => ({ ...prev, [detail.source]: detail }));
    });

    es.addEventListener("done", () => {
      setScrapeDone(true);
      es.close();
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    });

    es.addEventListener("error", () => {
      setScrapeDone(true);
      es.close();
    });

    return () => es.close();
  }, [scrapeRunId, queryClient]);

  const apiFilters = { ...filters };
  if (apiFilters.starred === "true") apiFilters.starred = true;
  else delete apiFilters.starred;
  if (!apiFilters.min_score) delete apiFilters.min_score;
  if (!apiFilters.max_score) delete apiFilters.max_score;
  if (apiFilters.no_jd === "true") apiFilters.no_jd = true;
  else delete apiFilters.no_jd;
  // Exclude starred jobs from the "new" inbox — they live in the "To Apply" shortlist
  if (apiFilters.status === "new" && !apiFilters.starred) {
    apiFilters.exclude_starred = true;
  }

  const { data: jobsData, isLoading, error } = useQuery({
    queryKey: ["jobs", filters, page],
    queryFn: () => api.getJobs({ ...apiFilters, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    refetchInterval: scrapeRunId && !scrapeDone ? 5000 : false,
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: api.getStats,
    refetchInterval: 10_000,
  });

  const handleScrape = useCallback(async () => {
    const run = await api.triggerRun();
    setScrapeRunId(run.run_id);
    setScrapeModalOpen(true);
  }, []);

  const handleScrapeClose = useCallback(() => {
    setScrapeModalOpen(false);
    if (scrapeDone) setScrapeRunId(null);
  }, [scrapeDone]);

  const handleFilterChange = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(0);
  }, []);

  const handleBulkStatus = useCallback(async (jobIds, status) => {
    await api.batchUpdateStatus(jobIds, status);
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
  }, [queryClient]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header stats={stats} onScrape={handleScrape} />

      <main className="flex-1 flex flex-col px-4 pb-8 max-w-screen-2xl mx-auto w-full">
        {/* Tab navigation */}
        <div className="mt-4 flex gap-1 border-b border-slate-800">
          {["jobs", "pipeline", "dashboard", "analysis", "activity"].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
                tab === t ? "text-white border-blue-500" : "text-slate-500 border-transparent hover:text-slate-300"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "jobs" && (
          <>
            <FilterBar filters={filters} onChange={handleFilterChange} stats={stats} />

            {error && (
              <div className="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
                Error loading jobs: {error.message}
              </div>
            )}

            <JobTable
              jobs={jobsData?.items || []}
              total={jobsData?.total || 0}
              isLoading={isLoading}
              filters={filters}
              onFilterChange={handleFilterChange}
              onSelectJob={setSelectedJobId}
              selectedJobId={selectedJobId}
              onRefresh={() => queryClient.invalidateQueries({ queryKey: ["jobs"] })}
              onBulkStatus={handleBulkStatus}
              page={page}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
            />
          </>
        )}

        {tab === "pipeline" && <PipelineView />}
        {tab === "dashboard" && <Dashboard />}
        {tab === "analysis" && <GapAnalysis />}
        {tab === "activity" && <ActivityLog />}
      </main>

      {selectedJobId && (
        <JobDrawer
          jobId={selectedJobId}
          onClose={() => setSelectedJobId(null)}
          onUpdate={() => {
            queryClient.invalidateQueries({ queryKey: ["jobs"] });
            queryClient.invalidateQueries({ queryKey: ["job", selectedJobId] });
          }}
        />
      )}

      {scrapeModalOpen && scrapeRunId && (
        <ScrapeModal
          details={scrapeDetails}
          done={scrapeDone}
          onClose={handleScrapeClose}
        />
      )}

      {scrapeRunId && !scrapeModalOpen && (
        <button
          onClick={() => setScrapeModalOpen(true)}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 bg-surface-1 border border-slate-600 rounded-full px-4 py-2 shadow-xl hover:border-slate-400 transition-colors text-sm"
        >
          {scrapeDone ? (
            <CheckCircle size={15} className="text-green-400" />
          ) : (
            <Loader2 size={15} className="text-blue-400 animate-spin" />
          )}
          <span className="text-slate-200">
            {scrapeDone ? "Scraping done — view results" : "Scraping in progress…"}
          </span>
        </button>
      )}
    </div>
  );
}
