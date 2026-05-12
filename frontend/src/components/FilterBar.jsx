import { Search, X, MapPin, Star, FileX, RefreshCw } from "lucide-react";
import { useRef, useState, useEffect } from "react";
import { api } from "../api/client";

const STATUSES = ["new", "pending", "applied", "interview", "rejected", "archived"];

const SOURCES = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "indeed", label: "Indeed" },
  { value: "stepstone", label: "StepStone" },
  { value: "arbeitnow", label: "Arbeitnow" },
  { value: "jobware", label: "Jobware" },
  { value: "yer", label: "yer.de" },
  { value: "thryve", label: "thryve.de" },
  { value: "deeprec", label: "DeepRec" },
  { value: "xcede", label: "xcede" },
  { value: "hays", label: "Hays" },
  { value: "orange_quarter", label: "Orange Quarter" },
  { value: "peritus", label: "Peritus" },
  { value: "redrecruitment", label: "Red Recruitment" },
];

const DATE_RANGES = [
  { value: "1", label: "Today" },
  { value: "3", label: "3 days" },
  { value: "7", label: "7 days" },
  { value: "14", label: "14 days" },
];

const REMOTE = ["remote", "hybrid", "onsite"];

const SORTS = [
  { value: "scraped_at", label: "Date Found" },
  { value: "cv_score", label: "CV Score" },
  { value: "posted_at", label: "Date Posted" },
  { value: "company", label: "Company" },
];

function Chip({ label, active, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "bg-surface-2 text-slate-400 hover:text-slate-200 hover:bg-surface-3"
      }`}
    >
      {Icon && <Icon size={11} />}
      {label}
    </button>
  );
}

function toggleFilter(current, value) {
  const parts = current ? current.split(",").filter(Boolean) : [];
  if (parts.includes(value)) return parts.filter((p) => p !== value).join(",");
  return [...parts, value].join(",");
}

export default function FilterBar({ filters, onChange, stats }) {
  const searchRef = useRef();
  const locationRef = useRef();
  const [rescoring, setRescoring] = useState(false);
  const [batchStatus, setBatchStatus] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const activeStatuses = filters.status ? filters.status.split(",") : [];
  const activeSources = filters.source ? filters.source.split(",") : [];

  const availableSources = stats?.by_source
    ? SOURCES.filter(({ value }) => (stats.by_source[value] || 0) > 0)
    : SOURCES;

  const hasActiveFilters =
    filters.status || filters.source || filters.employment_type ||
    filters.remote_type || filters.q || filters.location ||
    filters.scraped_days || filters.starred || filters.min_score || filters.max_score || filters.no_jd;

  const minScore = parseInt(filters.min_score) || 0;

  function clearAll() {
    ["status", "source", "employment_type", "remote_type", "q",
     "location", "scraped_days", "starred", "min_score", "max_score", "no_jd"].forEach((k) => onChange(k, ""));
  }

  return (
    <div className="mt-4 space-y-3">
      {/* Search + location + sort row */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
          <input
            ref={searchRef}
            type="text"
            placeholder="Search title or type…"
            value={filters.q}
            onChange={(e) => onChange("q", e.target.value)}
            className="w-full bg-surface-1 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          {filters.q && (
            <button onClick={() => onChange("q", "")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
              <X size={14} />
            </button>
          )}
        </div>

        <div className="relative min-w-[160px]">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
          <input
            ref={locationRef}
            type="text"
            placeholder="Location…"
            value={filters.location}
            onChange={(e) => onChange("location", e.target.value)}
            className="w-full bg-surface-1 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          {filters.location && (
            <button onClick={() => onChange("location", "")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
              <X size={14} />
            </button>
          )}
        </div>

        <select
          value={filters.sort}
          onChange={(e) => onChange("sort", e.target.value)}
          className="bg-surface-1 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-blue-500"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>Sort: {s.label}</option>
          ))}
        </select>

        <button
          onClick={() => onChange("order", filters.order === "desc" ? "asc" : "desc")}
          className="bg-surface-1 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-surface-2 transition-colors"
        >
          {filters.order === "desc" ? "↓ Desc" : "↑ Asc"}
        </button>
      </div>

      {/* Status + date + starred row */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-slate-500 font-medium">Status:</span>
        {STATUSES.map((s) => (
          <Chip key={s} label={s} active={activeStatuses.includes(s)} onClick={() => onChange("status", toggleFilter(filters.status, s))} />
        ))}

        <span className="text-xs text-slate-500 font-medium ml-2">Found:</span>
        {DATE_RANGES.map(({ value, label }) => (
          <Chip key={value} label={label} active={filters.scraped_days === value} onClick={() => onChange("scraped_days", filters.scraped_days === value ? "" : value)} />
        ))}

        <span className="text-xs text-slate-500 font-medium ml-2">|</span>
        <Chip
          label="To Apply"
          icon={Star}
          active={filters.starred === "true"}
          onClick={() => {
            if (filters.starred === "true") {
              onChange("starred", "");
            } else {
              onChange("starred", "true");
              onChange("status", "");
            }
          }}
        />
        <Chip
          label="No JD"
          icon={FileX}
          active={filters.no_jd === "true"}
          onClick={() => onChange("no_jd", filters.no_jd === "true" ? "" : "true")}
        />
      </div>

      {/* Source row */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-slate-500 font-medium">Source:</span>
        {availableSources.map(({ value, label }) => (
          <Chip key={value} label={label} active={activeSources.includes(value)} onClick={() => onChange("source", toggleFilter(filters.source, value))} />
        ))}
      </div>

      {/* Type + remote + min score row */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-slate-500 font-medium">Type:</span>
        <Chip label="Perm" active={filters.employment_type === "permanent"} onClick={() => onChange("employment_type", filters.employment_type === "permanent" ? "" : "permanent")} />
        <Chip label="Freelance" active={filters.employment_type === "freelance"} onClick={() => onChange("employment_type", filters.employment_type === "freelance" ? "" : "freelance")} />

        <span className="text-xs text-slate-500 font-medium ml-2">Work:</span>
        {REMOTE.map((r) => (
          <Chip key={r} label={r} active={filters.remote_type === r} onClick={() => onChange("remote_type", filters.remote_type === r ? "" : r)} />
        ))}

        <span className="text-xs text-slate-500 font-medium ml-2">Score:</span>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Min slider */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-500">≥</span>
            <input
              type="range" min={0} max={100} step={5}
              value={minScore}
              onChange={(e) => onChange("min_score", e.target.value === "0" ? "" : e.target.value)}
              className="w-20 accent-blue-500 cursor-pointer"
            />
            <span className={`text-xs font-medium w-7 ${minScore > 0 ? "text-blue-400" : "text-slate-500"}`}>
              {minScore > 0 ? minScore : "Any"}
            </span>
          </div>
          {/* Max slider */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-500">≤</span>
            <input
              type="range" min={0} max={100} step={5}
              value={parseInt(filters.max_score) || 100}
              onChange={(e) => onChange("max_score", e.target.value === "100" ? "" : e.target.value)}
              className="w-20 accent-blue-500 cursor-pointer"
            />
            <span className={`text-xs font-medium w-7 ${filters.max_score ? "text-blue-400" : "text-slate-500"}`}>
              {filters.max_score ? filters.max_score : "Any"}
            </span>
          </div>
          {(minScore > 0 || filters.max_score) && (
            <button onClick={() => { onChange("min_score", ""); onChange("max_score", ""); }} className="text-slate-500 hover:text-slate-300">
              <X size={12} />
            </button>
          )}
          {/* Re-score button — always visible when a range is set */}
          {(minScore > 0 || filters.max_score) && (
            <button
              onClick={async () => {
                setRescoring(true);
                try {
                  const res = await api.rescoreRange(minScore || null, filters.max_score || null);
                  if (res.queued > 0) {
                    // Start polling
                    pollRef.current = setInterval(async () => {
                      const s = await api.getBatchScoreStatus();
                      setBatchStatus(s);
                      if (!s.running) {
                        clearInterval(pollRef.current);
                        setRescoring(false);
                        setTimeout(() => setBatchStatus(null), 5000);
                      }
                    }, 1500);
                  } else {
                    setRescoring(false);
                    setBatchStatus({ running: false, queued: 0, message: res.message });
                    setTimeout(() => setBatchStatus(null), 4000);
                  }
                } catch (e) {
                  setRescoring(false);
                  setBatchStatus({ error: e.message });
                  setTimeout(() => setBatchStatus(null), 4000);
                }
              }}
              disabled={rescoring}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-slate-700 bg-surface-2 text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-50"
            >
              <RefreshCw size={11} className={rescoring ? "animate-spin" : ""} />
              Re-score range
            </button>
          )}
          {/* Progress indicator */}
          {batchStatus && (
            <span className={`text-xs ${batchStatus.error ? "text-red-400" : batchStatus.running ? "text-blue-400" : "text-green-400"}`}>
              {batchStatus.error
                ? `Error: ${batchStatus.error}`
                : batchStatus.running
                  ? `Scoring ${batchStatus.done}/${batchStatus.total}…`
                  : batchStatus.message || `Done — ${batchStatus.done} scored${batchStatus.errors > 0 ? `, ${batchStatus.errors} errors` : ""}`}
            </span>
          )}
        </div>

        {hasActiveFilters && (
          <button onClick={clearAll} className="ml-2 text-xs text-slate-500 hover:text-slate-300 underline">
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}
