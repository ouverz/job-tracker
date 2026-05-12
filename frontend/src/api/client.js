const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Jobs
  getJobs: (params = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
    ).toString();
    return request(`/jobs${q ? `?${q}` : ""}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  updateJob: (id, data) => request(`/jobs/${id}`, { method: "PATCH", body: data }),
  deleteJob: (id) => request(`/jobs/${id}`, { method: "DELETE" }),
  getStats: () => request("/jobs/stats"),
  getKpi: () => request("/jobs/kpi"),
  getGapAnalysis: (params = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== 0)
    ).toString();
    return request(`/analysis/gaps${q ? `?${q}` : ""}`);
  },

  // Scraping
  triggerRun: (sources) =>
    request("/scraping/run", { method: "POST", body: sources ? { sources } : undefined }),
  getRuns: () => request("/scraping/runs"),
  getRun: (id) => request(`/scraping/runs/${id}`),
  getLatestRun: () => request("/scraping/runs/latest"),

  batchUpdateStatus: (job_ids, status) =>
    request("/jobs/batch-status", { method: "PATCH", body: { job_ids, status } }),

  // Scoring
  scoreJob: (id) => request(`/scoring/jobs/${id}`, { method: "POST" }),
  scoreBatch: (job_ids) =>
    request("/scoring/batch", { method: "POST", body: job_ids }),
  rescoreRange: (min, max) => {
    const p = new URLSearchParams();
    if (min != null && min !== "") p.set("min_score", min);
    if (max != null && max !== "") p.set("max_score", max);
    return request(`/scoring/batch?${p.toString()}`, { method: "POST" });
  },
  getBatchScoreStatus: () => request("/scoring/batch/status"),

  // Contacts / Networking
  getContacts: (jobId) => request(`/jobs/${jobId}/contacts`),
  addContact: (jobId, data) => request(`/jobs/${jobId}/contacts`, { method: "POST", body: data }),
  updateContact: (id, data) => request(`/contacts/${id}`, { method: "PATCH", body: data }),
  deleteContact: (id) => request(`/contacts/${id}`, { method: "DELETE" }),
  getSearchLinks: (jobId) => request(`/jobs/${jobId}/search-links`),

  // Activity log
  getActivityLog: (week) => {
    const q = week ? `?week=${week}` : "";
    return request(`/activity-log${q}`);
  },
  updateActivityLog: (week, activity, data) =>
    request(`/activity-log/${week}/${activity}`, { method: "PATCH", body: data }),

  // CV
  getCvStatus: () => request("/cv/status"),
  uploadCv: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/cv/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },
};
