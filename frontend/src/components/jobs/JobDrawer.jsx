import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, ExternalLink, Loader2, Star, CheckCircle, XCircle, Archive, Clock, Sparkles, MessageSquare, Bell, Users } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api } from "../../api/client";
import { relativeDate, toDateInput } from "../../utils/dates";
import { StatusBadge, SourceBadge, TypeBadge } from "./StatusBadge";
import { ScoreBar } from "./ScoreBar";
import NetworkSection from "./NetworkSection";

const STATUS_ACTIONS = [
  { status: "new",       icon: Star,          label: "New",       color: "text-blue-400" },
  { status: "pending",   icon: Clock,         label: "Pending",   color: "text-yellow-400" },
  { status: "applied",   icon: CheckCircle,   label: "Applied",   color: "text-green-400" },
  { status: "interview", icon: MessageSquare, label: "Interview", color: "text-purple-400" },
  { status: "rejected",  icon: XCircle,       label: "Rejected",  color: "text-red-400" },
  { status: "archived",  icon: Archive,       label: "Archive",   color: "text-slate-400" },
];

function cleanDescription(text) {
  if (!text) return "";
  return text
    .replace(/\\([*_\-\.()[\]#!])/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+\n/g, "\n")
    .trim();
}

function safeUrl(url) {
  if (!url) return null;
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch { return null; }
}


export default function JobDrawer({ jobId, onClose, onUpdate }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState("");
  const [notesTimeout, setNotesTimeout] = useState(null);

  const { data: job, isLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    enabled: !!jobId,
  });

  useEffect(() => {
    if (job) setNotes(job.notes || "");
  }, [job?.id]);

  const updateMutation = useMutation({
    mutationFn: (data) => api.updateJob(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      onUpdate?.();
    },
  });

  const scoreMutation = useMutation({
    mutationFn: () => api.scoreJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const handleNotesChange = (value) => {
    setNotes(value);
    if (notesTimeout) clearTimeout(notesTimeout);
    setNotesTimeout(setTimeout(() => updateMutation.mutate({ notes: value }), 800));
  };

  const handleStatus = (status) => {
    updateMutation.mutate({ status });
  };

  const handleStar = () => {
    updateMutation.mutate({ starred: job.starred ? 0 : 1 });
  };

  const handleFollowUp = (dateStr) => {
    updateMutation.mutate({ follow_up_at: dateStr || null });
  };

  let breakdown = null;
  if (job?.cv_score_breakdown) {
    try { breakdown = JSON.parse(job.cv_score_breakdown); } catch {}
  }

  const isOverdue = job?.follow_up_at && new Date(job.follow_up_at.endsWith("Z") ? job.follow_up_at : job.follow_up_at + "Z") < new Date();

  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />

      <div className="w-full max-w-2xl bg-surface-1 border-l border-slate-800 flex flex-col h-full overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
              <X size={20} />
            </button>
            {job && (
              <button
                onClick={handleStar}
                className={`transition-colors ${job.starred ? "text-yellow-400 hover:text-yellow-300" : "text-slate-600 hover:text-slate-400"}`}
                title={job.starred ? "Remove star" : "Star this job"}
              >
                <Star size={18} fill={job.starred ? "currentColor" : "none"} />
              </button>
            )}
          </div>
          {job && safeUrl(job.url) && (
            <a
              href={safeUrl(job.url)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Open original <ExternalLink size={13} />
            </a>
          )}
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <Loader2 className="animate-spin" size={24} />
          </div>
        ) : job ? (
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* Title block */}
            <div>
              <h2 className="text-xl font-semibold text-white leading-snug">{job.title}</h2>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {job.company && <span className="text-slate-300 font-medium">{job.company}</span>}
                {job.location && <span className="text-slate-500 text-sm">· {job.location}</span>}
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                <SourceBadge source={job.source} />
                <TypeBadge type={job.employment_type} />
                {job.remote_type && <TypeBadge type={job.remote_type} />}
                {job.salary_raw && (
                  <span className="text-xs text-slate-400 bg-surface-3 px-2 py-0.5 rounded">{job.salary_raw}</span>
                )}
              </div>
              <div className="flex gap-4 mt-2 text-xs text-slate-500">
                {job.posted_at && <span>Posted {relativeDate(job.posted_at)}</span>}
                <span>Found {relativeDate(job.scraped_at)}</span>
                {job.applied_at && <span>Applied {relativeDate(job.applied_at)}</span>}
              </div>
            </div>

            {/* Status actions */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Status</h3>
              <div className="flex flex-wrap gap-2">
                {STATUS_ACTIONS.map(({ status, icon: Icon, label, color }) => (
                  <button
                    key={status}
                    onClick={() => handleStatus(status)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                      job.status === status
                        ? "bg-surface-3 border-slate-600 text-white"
                        : "bg-surface-2 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
                    }`}
                  >
                    <Icon size={14} className={job.status === status ? color : ""} />
                    {label}
                  </button>
                ))}
              </div>
              {job.status_changed_at && (
                <p className="mt-1.5 text-xs text-slate-500">Status set {relativeDate(job.status_changed_at)}</p>
              )}
            </div>

            {/* Follow-up reminder */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                <Bell size={11} /> Follow-up Reminder
                {isOverdue && <span className="text-orange-400 font-normal normal-case tracking-normal">— overdue!</span>}
              </h3>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={toDateInput(job.follow_up_at)}
                  onChange={(e) => handleFollowUp(e.target.value)}
                  className="bg-surface-2 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500 [color-scheme:dark]"
                />
                {job.follow_up_at && (
                  <button
                    onClick={() => handleFollowUp("")}
                    className="text-slate-500 hover:text-slate-300 text-xs"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Network */}
            <NetworkSection jobId={jobId} company={job.company} title={job.title} />

            {/* ATS Score */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">CV Match Score</h3>
                <button
                  onClick={() => scoreMutation.mutate()}
                  disabled={scoreMutation.isPending}
                  className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors"
                >
                  {scoreMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  {job.cv_score != null ? "Re-score" : "Score with AI"}
                </button>
              </div>

              {scoreMutation.isError && (
                <p className="text-xs text-red-400 mb-2">{scoreMutation.error.message}</p>
              )}

              {job.cv_score != null ? (
                <div className="bg-surface-2 rounded-xl p-4 space-y-3">
                  <ScoreBar score={job.cv_score} size="lg" />

                  {breakdown && (
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-surface-3 rounded-lg p-2">
                        <div className="text-slate-500 mb-1">Skills Match</div>
                        <ScoreBar score={breakdown.skill_match_score} />
                      </div>
                      <div className="bg-surface-3 rounded-lg p-2">
                        <div className="text-slate-500 mb-1">Experience Match</div>
                        <ScoreBar score={breakdown.experience_match_score} />
                      </div>
                      {breakdown.language_match_score != null && (
                        <div className="bg-surface-3 rounded-lg p-2">
                          <div className="text-slate-500 mb-1">Language Match</div>
                          <ScoreBar score={breakdown.language_match_score} />
                        </div>
                      )}
                      {breakdown.location_score != null && (
                        <div className="bg-surface-3 rounded-lg p-2">
                          <div className="text-slate-500 mb-1">Location Fit</div>
                          <ScoreBar score={breakdown.location_score} />
                        </div>
                      )}
                    </div>
                  )}

                  {job.cv_score_rationale && (
                    <p className="text-sm text-slate-300 leading-relaxed">{job.cv_score_rationale}</p>
                  )}

                  {breakdown?.strengths?.length > 0 && (
                    <div>
                      <div className="text-xs text-green-400 font-medium mb-1">Strengths</div>
                      <ul className="space-y-0.5">
                        {breakdown.strengths.map((s, i) => (
                          <li key={i} className="text-xs text-slate-300 flex gap-1.5">
                            <span className="text-green-500 mt-0.5">✓</span> {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {breakdown?.gaps?.length > 0 && (
                    <div>
                      <div className="text-xs text-yellow-400 font-medium mb-1">Gaps</div>
                      <ul className="space-y-0.5">
                        {breakdown.gaps.map((g, i) => (
                          <li key={i} className="text-xs text-slate-300 flex gap-1.5">
                            <span className="text-yellow-500 mt-0.5">△</span> {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-surface-2 rounded-xl p-4 text-center text-slate-500 text-sm">
                  No score yet — click "Score with AI" to compare against your CV
                </div>
              )}
            </div>

            {/* Notes */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Notes</h3>
              <textarea
                value={notes}
                onChange={(e) => handleNotesChange(e.target.value)}
                placeholder="Add notes about this role…"
                rows={4}
                className="w-full bg-surface-2 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            {/* Job Description */}
            {job.description && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Job Description</h3>
                <div className="bg-surface-2 rounded-xl p-4 max-h-[500px] overflow-y-auto prose prose-sm prose-invert max-w-none
                  [&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-white [&_h1]:mt-4 [&_h1]:mb-1
                  [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:text-white [&_h2]:mt-4 [&_h2]:mb-1
                  [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-slate-200 [&_h3]:mt-3 [&_h3]:mb-1
                  [&_p]:text-slate-300 [&_p]:leading-relaxed [&_p]:my-1.5
                  [&_ul]:my-1.5 [&_ul]:pl-4 [&_li]:text-slate-300 [&_li]:my-0.5
                  [&_strong]:text-slate-100 [&_hr]:border-slate-700">
                  <ReactMarkdown>{cleanDescription(job.description)}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">Job not found</div>
        )}
      </div>
    </div>
  );
}
