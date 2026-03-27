import { useRef, useState, useEffect } from "react";
import { Briefcase, Zap, Upload, CheckCircle, AlertCircle, Loader2, FileText } from "lucide-react";
import { api } from "../api/client";

function CvUploadButton() {
  const inputRef = useRef(null);
  const [state, setState] = useState("idle"); // idle | uploading | done | error
  const [msg, setMsg] = useState("");
  const [cvStatus, setCvStatus] = useState(null); // { loaded, words }

  useEffect(() => {
    api.getCvStatus().then(setCvStatus).catch(() => {});
  }, []);

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setState("uploading");
    setMsg("");
    try {
      const result = await api.uploadCv(file);
      setState("done");
      setMsg(`${result.words.toLocaleString()} words loaded`);
      setCvStatus({ loaded: true, words: result.words });
    } catch (err) {
      setState("error");
      setMsg(err.message || "Upload failed");
    } finally {
      e.target.value = "";
      setTimeout(() => setState("idle"), 4000);
    }
  }

  const isIdle = state === "idle";

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={handleFile}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={state === "uploading"}
        className="flex items-center gap-2 border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        title={cvStatus?.loaded ? `CV loaded (${cvStatus.words.toLocaleString()} words) — click to replace` : "Upload your CV (PDF or DOCX) for AI scoring"}
      >
        {state === "uploading" ? (
          <Loader2 size={14} className="animate-spin" />
        ) : state === "done" ? (
          <CheckCircle size={14} className="text-green-400" />
        ) : state === "error" ? (
          <AlertCircle size={14} className="text-red-400" />
        ) : cvStatus?.loaded ? (
          <FileText size={14} className="text-green-400" />
        ) : (
          <Upload size={14} />
        )}
        <span className="hidden sm:inline">
          {state === "uploading"
            ? "Uploading…"
            : state === "done"
            ? msg
            : state === "error"
            ? "Failed"
            : isIdle && cvStatus?.loaded
            ? `CV · ${cvStatus.words.toLocaleString()}w`
            : "Upload CV"}
        </span>
      </button>
      {state === "error" && (
        <span className="text-xs text-red-400 max-w-[160px] truncate" title={msg}>{msg}</span>
      )}
    </div>
  );
}

export default function Header({ stats, onScrape }) {
  return (
    <header className="border-b border-slate-800 bg-surface-1 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Briefcase className="text-blue-400" size={24} />
        <div>
          <h1 className="text-lg font-semibold text-white">Job Tracker</h1>
          <p className="text-xs text-slate-500">AI · Data · Analytics · Germany / DACH</p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {stats && (
          <div className="hidden sm:flex items-center gap-4 text-sm">
            <span className="text-slate-400">
              <span className="text-white font-medium">{stats.total}</span> total
            </span>
            <span className="text-slate-400">
              <span className="text-blue-400 font-medium">{stats.by_status?.new || 0}</span> new
            </span>
            <span className="text-slate-400">
              <span className="text-yellow-400 font-medium">{stats.by_status?.pending || 0}</span> pending
            </span>
            <span className="text-slate-400">
              <span className="text-green-400 font-medium">{stats.by_status?.applied || 0}</span> applied
            </span>
            <span className="text-slate-400">
              <span className="text-purple-400 font-medium">{stats.by_status?.interview || 0}</span> interview
            </span>
            <span className="text-slate-400">
              <span className="text-slate-400 font-medium">{stats.by_status?.archived || 0}</span> archived
            </span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <CvUploadButton />
          <button
            onClick={onScrape}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Zap size={15} />
            Run Pipeline
          </button>
        </div>
      </div>
    </header>
  );
}
