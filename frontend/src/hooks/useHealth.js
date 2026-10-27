import { useCallback, useEffect, useState } from "react";
import { getHealth } from "../services/api.js";

export function useHealth() {
  const [status, setStatus] = useState("checking");
  const refresh = useCallback(async (signal) => {
    setStatus("checking");
    try {
      const timeout = AbortSignal.timeout(8_000);
      const result = await getHealth(signal ? AbortSignal.any([signal, timeout]) : timeout);
      if (!signal?.aborted)
        setStatus(result.status === "ok" ? "online" : "offline");
    } catch (error) {
      if (error.name !== "AbortError") setStatus("offline");
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    const timer = setInterval(() => refresh(controller.signal), 60_000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [refresh]);
  return { status, refresh };
}
