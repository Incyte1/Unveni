import type { SessionResponse } from "./contracts";

export type ExecutionMode = SessionResponse["execution_mode"];
export type DataEntitlement = SessionResponse["entitlement"];

export function formatExecutionMode(mode: ExecutionMode) {
  return mode === "live" ? "Live mode" : "Paper mode";
}

export function formatEntitlement(entitlement: DataEntitlement) {
  if (entitlement === "delayed-demo") {
    return "Delayed OPRA-safe analytics";
  }

  return entitlement;
}

export function formatSessionLabel(session: SessionResponse | null) {
  if (!session) {
    return "Loading session";
  }

  if (!session.is_authenticated || !session.user) {
    return "Signed out";
  }

  if (session.mode === "development") {
    return `${session.user.name} (dev)`;
  }

  return session.user.name;
}
