import { getSignalAlerts, getSignalAlertHistory, toErrorMessage, updateSignalAlertStatus } from "../lib/api";
import type { SignalAlert, SignalAlertsResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useSignalAlerts(
  scopeKey: string,
  options: {
    enabled?: boolean;
    limit?: number;
    minutes?: number;
    includeHistory?: boolean;
    status?: "new" | "read" | "acknowledged";
  } = {}
) {
  const resource = useResource<SignalAlertsResponse>(
    async (signal) => {
      try {
        if (options.includeHistory) {
          return await getSignalAlertHistory({
            limit: options.limit,
            status: options.status,
            signal
          });
        }

        return await getSignalAlerts({
          limit: options.limit,
          minutes: options.minutes,
          status: options.status,
          signal
        });
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey, options.limit ?? 25, options.minutes ?? 0, options.includeHistory ?? false, options.status ?? "all"],
    {
      enabled: options.enabled,
      refreshIntervalMs: 60_000
    }
  );

  async function setStatus(alertId: string, status: "read" | "acknowledged") {
    const updatedAlert = await updateSignalAlertStatus(alertId, { status });
    resource.reload();
    return updatedAlert;
  }

  return {
    ...resource,
    setStatus,
    items: resource.data?.items ?? []
  };
}

export type SignalAlertRecord = SignalAlert;
