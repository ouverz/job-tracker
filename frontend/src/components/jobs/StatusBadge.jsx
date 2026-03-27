const STATUS_STYLES = {
  new: "bg-blue-900/50 text-blue-300 border-blue-700",
  pending: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  applied: "bg-green-900/50 text-green-300 border-green-700",
  interview: "bg-purple-900/50 text-purple-300 border-purple-700",
  rejected: "bg-red-900/50 text-red-300 border-red-700",
  archived: "bg-slate-800 text-slate-500 border-slate-700",
};

const SOURCE_STYLES = {
  linkedin: "bg-blue-900/30 text-blue-400",
  indeed: "bg-purple-900/30 text-purple-400",
  stepstone: "bg-orange-900/30 text-orange-400",
  arbeitnow: "bg-emerald-900/30 text-emerald-400",
  jobware: "bg-cyan-900/30 text-cyan-400",
  yer: "bg-rose-900/30 text-rose-400",
  thryve: "bg-lime-900/30 text-lime-400",
  deeprec: "bg-indigo-900/30 text-indigo-400",
  xcede: "bg-amber-900/30 text-amber-400",
  hays: "bg-sky-900/30 text-sky-400",
  orange_quarter: "bg-orange-900/40 text-orange-300",
  peritus: "bg-teal-900/30 text-teal-400",
  redrecruitment: "bg-red-900/30 text-red-400",
};

export function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || "bg-slate-800 text-slate-400 border-slate-700";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {status}
    </span>
  );
}

export function SourceBadge({ source }) {
  const style = SOURCE_STYLES[source] || "bg-slate-800 text-slate-400";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${style}`}>
      {source}
    </span>
  );
}

export function TypeBadge({ type }) {
  if (!type || type === "unknown") return null;
  const style = type === "freelance"
    ? "bg-violet-900/30 text-violet-400"
    : "bg-teal-900/30 text-teal-400";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${style}`}>
      {type === "permanent" ? "perm" : type}
    </span>
  );
}
