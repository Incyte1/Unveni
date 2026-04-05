import { useEffect, useState, type DependencyList } from "react";

interface ResourceState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  reload: () => void;
}

export function useResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
  options: {
    enabled?: boolean;
    refreshIntervalMs?: number;
  } = {}
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);
  const enabled = options.enabled ?? true;
  const refreshIntervalMs = options.refreshIntervalMs ?? 0;

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    loader(controller.signal)
      .then((value) => {
        setData(value);
        setIsLoading(false);
      })
      .catch((requestError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(requestError instanceof Error ? requestError.message : "Request failed.");
        setIsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [enabled, ...deps, reloadToken]);

  useEffect(() => {
    if (!enabled || refreshIntervalMs <= 0) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setReloadToken((value) => value + 1);
    }, refreshIntervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [enabled, refreshIntervalMs, ...deps]);

  return {
    data,
    error,
    isLoading,
    reload: () => setReloadToken((value) => value + 1)
  };
}
