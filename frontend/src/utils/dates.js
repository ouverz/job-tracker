/**
 * Shared date formatting utilities used across job components.
 */

/**
 * Format an ISO date string as a human-readable date.
 * JobTable uses relative format ("2d ago"); JobDrawer uses absolute ("27 Mar 2026").
 * Both call this with the same input shape — always append Z if missing so
 * the Date constructor treats the string as UTC rather than local time.
 *
 * @param {string|null} str - ISO date string
 * @param {"relative"|"absolute"} [mode="absolute"] - output format
 * @returns {string}
 */
export function relativeDate(str, mode = "absolute") {
  if (!str) return mode === "relative" ? "—" : null;
  const d = new Date(str.endsWith("Z") ? str : str + "Z");
  if (mode === "relative") {
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
    if (diff < 86400 * 30) return `${Math.round(diff / 86400)}d ago`;
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
  }
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/**
 * Convert an ISO date string to a YYYY-MM-DD string suitable for <input type="date">.
 *
 * @param {string|null} str
 * @returns {string}
 */
export function toDateInput(str) {
  if (!str) return "";
  return str.slice(0, 10);
}
