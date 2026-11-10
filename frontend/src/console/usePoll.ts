import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

/** Fetch a resource and keep it fresh while the page is visible (Wekil works in the background). */
export function usePoll<T>(path: string | null, every = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!path) return;
    try { setData(await api<T>(path)); setError(""); } catch (e) { setError((e as Error).message); }
  }, [path]);
  useEffect(() => {
    load();
    const id = setInterval(() => document.visibilityState === "visible" && load(), every);
    return () => clearInterval(id);
  }, [load, every]);
  return { data, error, reload: load };
}
