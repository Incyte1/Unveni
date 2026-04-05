import { useState } from "react";
import {
  createSession,
  getSession,
  logoutSession,
  toErrorMessage
} from "../lib/api";
import type { SessionCreateRequest, SessionResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useSession() {
  const resource = useResource<SessionResponse>(
    async (signal) => {
      try {
        return await getSession(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    []
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function startSession(payload: SessionCreateRequest) {
    setIsSaving(true);
    setActionError(null);

    try {
      await createSession(payload);
      resource.reload();
      return true;
    } catch (error) {
      setActionError(toErrorMessage(error));
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function endSession() {
    setIsSaving(true);
    setActionError(null);

    try {
      await logoutSession();
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
    endSession,
    isSaving,
    startSession
  };
}
