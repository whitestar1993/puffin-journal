// Minimal hash router: #/ (today), #/day/YYYY-MM-DD, #/history, #/settings.

export type Route =
  | { name: "checkin"; date: string | null }
  | { name: "history" }
  | { name: "settings" };

function parse(hash: string): Route {
  const path = hash.replace(/^#/, "") || "/";
  const day = path.match(/^\/day\/(\d{4}-\d{2}-\d{2})$/);
  if (day) return { name: "checkin", date: day[1] };
  if (path === "/history") return { name: "history" };
  if (path === "/settings") return { name: "settings" };
  return { name: "checkin", date: null };
}

export const router = $state({ route: parse(location.hash) });

window.addEventListener("hashchange", () => {
  router.route = parse(location.hash);
  window.scrollTo(0, 0);
});

export function go(path: string) {
  location.hash = path;
}
