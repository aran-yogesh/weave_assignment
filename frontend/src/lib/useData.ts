import { useEffect, useState } from "react";
import type { DashboardData } from "../types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DashboardData };

// Load the precomputed static data.json (no live API calls at view time).
export function useData(): State {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    // no-store: data.json lives at a fixed URL, so a cached copy could go stale
    // and make one page disagree with another. Always read the current file.
    fetch(`${import.meta.env.BASE_URL}data.json`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`data.json ${r.status}`);
        return r.json();
      })
      .then((data: DashboardData) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((e) => {
        if (!cancelled) setState({ status: "error", message: String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
