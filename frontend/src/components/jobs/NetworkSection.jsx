import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, ExternalLink, Trash2, Plus, X } from "lucide-react";
import { api } from "../../api/client";

function safeUrl(url) {
  if (!url) return null;
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch { return null; }
}

const TYPE_ICON = {
  managers: "👔",
  peers: "👥",
  recruiters: "🎯",
};

export default function NetworkSection({ jobId, company, title }) {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", role: "", linkedin_url: "" });

  const { data: links = [] } = useQuery({
    queryKey: ["search-links", jobId],
    queryFn: () => api.getSearchLinks(jobId),
    enabled: !!jobId && !!(company || title),
  });

  const { data: contacts = [] } = useQuery({
    queryKey: ["contacts", jobId],
    queryFn: () => api.getContacts(jobId),
    enabled: !!jobId,
  });

  const addMutation = useMutation({
    mutationFn: (data) => api.addContact(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts", jobId] });
      setForm({ name: "", role: "", linkedin_url: "" });
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.updateContact(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts", jobId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => api.deleteContact(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts", jobId] }),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    addMutation.mutate({
      name: form.name.trim(),
      role: form.role.trim() || null,
      linkedin_url: form.linkedin_url.trim() || null,
    });
  };

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
        <Users size={11} /> Network
      </h3>

      {/* Search links */}
      {links.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {links.map((link) => (
            <a
              key={link.type}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-surface-2 border border-slate-700 text-slate-300 hover:border-blue-500 hover:text-blue-300 transition-colors"
            >
              <span>{TYPE_ICON[link.type] || "🔍"}</span>
              {link.label}
              <ExternalLink size={10} className="opacity-60" />
            </a>
          ))}
        </div>
      )}

      {/* Contact list */}
      {contacts.length > 0 && (
        <div className="space-y-2 mb-3">
          {contacts.map((c) => (
            <div
              key={c.id}
              className="flex items-center gap-2 bg-surface-2 rounded-lg px-3 py-2"
            >
              <input
                type="checkbox"
                checked={!!c.reached_out}
                onChange={(e) =>
                  updateMutation.mutate({ id: c.id, data: { reached_out: e.target.checked ? 1 : 0 } })
                }
                className="accent-blue-500 cursor-pointer"
                title="Mark as reached out"
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm text-slate-200 truncate">{c.name}</span>
                {c.role && (
                  <span className="ml-2 text-xs text-slate-500 bg-surface-3 px-1.5 py-0.5 rounded">
                    {c.role}
                  </span>
                )}
              </div>
              {safeUrl(c.linkedin_url) && (
                <a
                  href={safeUrl(c.linkedin_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 transition-colors flex-shrink-0"
                  title="Open LinkedIn profile"
                >
                  <ExternalLink size={13} />
                </a>
              )}
              <button
                onClick={() => deleteMutation.mutate(c.id)}
                className="text-slate-600 hover:text-red-400 transition-colors flex-shrink-0"
                title="Remove contact"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add contact form */}
      {showForm ? (
        <form onSubmit={handleSubmit} className="bg-surface-2 rounded-lg p-3 space-y-2">
          <input
            type="text"
            placeholder="Name *"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="w-full bg-surface-3 border border-slate-700 rounded px-2.5 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            required
          />
          <input
            type="text"
            placeholder="Role (e.g. Recruiter)"
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            className="w-full bg-surface-3 border border-slate-700 rounded px-2.5 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <input
            type="url"
            placeholder="LinkedIn URL"
            value={form.linkedin_url}
            onChange={(e) => setForm((f) => ({ ...f, linkedin_url: e.target.value }))}
            className="w-full bg-surface-3 border border-slate-700 rounded px-2.5 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded px-3 py-1.5 transition-colors"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setForm({ name: "", role: "", linkedin_url: "" }); }}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
          {addMutation.isError && (
            <p className="text-xs text-red-400">{addMutation.error.message}</p>
          )}
        </form>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <Plus size={13} /> Add contact
        </button>
      )}
    </div>
  );
}
