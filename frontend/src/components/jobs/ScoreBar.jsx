function scoreColor(score) {
  if (score >= 75) return "bg-green-500";
  if (score >= 50) return "bg-yellow-500";
  if (score >= 25) return "bg-orange-500";
  return "bg-red-500";
}

export function ScoreBar({ score, size = "sm" }) {
  if (score == null) {
    return (
      <span className="text-slate-600 text-xs italic">unscored</span>
    );
  }

  const color = scoreColor(score);
  const pct = Math.min(100, Math.max(0, score));

  if (size === "lg") {
    return (
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-surface-3 rounded-full h-3">
          <div
            className={`${color} h-3 rounded-full transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-2xl font-bold text-white min-w-[48px] text-right">{Math.round(score)}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-surface-3 rounded-full h-1.5">
        <div
          className={`${color} h-1.5 rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-300 font-medium">{Math.round(score)}</span>
    </div>
  );
}
