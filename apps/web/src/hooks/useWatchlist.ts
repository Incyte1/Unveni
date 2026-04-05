import { useEffect, useState } from "react";
import {
  addWatchlistItem,
  getWatchlist,
  removeWatchlistItem,
  toErrorMessage
} from "../lib/api";
import type { WatchlistResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useWatchlist(enabled: boolean, scopeKey: string) {
  const resource = useResource<WatchlistResponse>(
    async (signal) => {
      try {
        return await getWatchlist(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey],
    { enabled }
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setActionError(null);
      setIsSaving(false);
    }
  }, [enabled, scopeKey]);

  async function addSymbol(symbol: string, notes: string) {
    setIsSaving(true);
    setActionError(null);

    try {
      await addWatchlistItem({
        symbol,
        notes: notes.trim() ? notes : null
      });
      resource.reload();
      return true;
    } catch (error) {
      setActionError(toErrorMessage(error));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function removeSymbol(symbol: string) {
    setIsSaving(true);
    setActionError(null);

    try {
      await removeWatchlistItem(symbol);
      resource.reload();
      return true;
    } catch (error) {
      setActionError(toErrorMessage(error));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  return {
    ...resource,
    actionError,
    addSymbol,
    removeSymbol,
    isSaving
  };
}
