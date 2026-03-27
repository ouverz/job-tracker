import { X, CheckCircle, XCircle, Loader2, Clock } from "lucide-react";

const SOURCE_LABELS = {
  arbeitnow: "Arbeitnow",
  linkedin_indeed: "LinkedIn + Indeed",
  stepstone: "StepStone",
  jobware: "Jobware",
  yer: "yer.de",
  thryve: "thryve.de",
  deeprec: "DeepRec.ai",
  xcede: "xcede.com",
  hays: "Hays DACH",
  orange_quarter: "Orange Quarter",
  peritus: "Peritus Partners",
  redrecruitment: "Red Recruitment",
};

function StatusIcon({ status }) {
  if (status === "done") return <CheckCircle size={16} className="text-green-400" />;
  if (status === "failed") return <XCircle size={16} className="text-red-400" />;
  if (status === "running") return <Loader2 size={16} className="text-blue-400 animate-spin" />;
  return <Clock size={16} className="text-slate-500" />;
}

export default function ScrapeModal({ details, done, onClose }) {
  const totalNew = Object.values(details).reduce((s, d) => s + (d.jobs_new || 0), 0);
  const totalFound = Object.values(details).reduce((s, d) => s + (d.jobs_found || 0), 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-surface-1 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {done ? "Pipeline Complete" : "Running Pipeline…"}
            </h2>
            {done && totalNew > 0 && (
              <p className="text-sm text-green-400 mt-0.5">{totalNew} new jobs found!</p>
            )}
            {!done && (
              <p className="text-xs text-slate-500 mt-0.5">You can close this — scraping continues in background</p>
            )}
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-3">
          {Object.entries(SOURCE_LABELS).map(([key, label]) => {
            const detail = details[key];
            const status = detail?.status || "pending";

            return (
              <div key={key} className="flex items-center gap-3 bg-surface-2 rounded-xl px-4 py-3">
                <StatusIcon status={status} />
                <div className="flex-1">
                  <div className="text-sm font-medium text-slate-200">{label}</div>
                  {detail?.error_msg && (
                    <div className="text-xs text-red-400 mt-0.5 truncate">{detail.error_msg}</div>
                  )}
                </div>
                {detail && (status === "done" || status === "failed") && (
                  <div className="text-right text-xs text-slate-400">
                    <span className="text-green-400 font-medium">{detail.jobs_new}</span> new
                    <span className="text-slate-600 mx-1">/</span>
                    {detail.jobs_found} found
                  </div>
                )}
                {status === "running" && (
                  <span className="text-xs text-slate-500">scraping…</span>
                )}
                {status === "pending" && (
                  <span className="text-xs text-slate-600">waiting</span>
                )}
              </div>
            );
          })}
        </div>

        {done && (
          <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-sm text-slate-400">
              {totalFound} found · {totalNew} new
            </span>
            <button
              onClick={onClose}
              className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
            >
              View Jobs
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
