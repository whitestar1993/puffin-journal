// Dates are plain "YYYY-MM-DD" strings. The server decides what "today" is
// (TZ env), so the client never derives it from the browser clock.

export function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return t.toISOString().slice(0, 10);
}

export function formatDay(iso: string, today?: string): string {
  if (today) {
    if (iso === today) return "Today";
    if (iso === addDays(today, -1)) return "Yesterday";
  }
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d));
  const sameYear = today ? today.slice(0, 4) === iso.slice(0, 4) : true;
  return t.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: sameYear ? undefined : "numeric",
    timeZone: "UTC",
  });
}

export const isIsoDate = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s);
