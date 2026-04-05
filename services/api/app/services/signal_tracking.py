from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
import json
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.db import DatabaseSession
from app.errors import AppError
from app.models import (
    IntradayScorecardResponse,
    MarketClock,
    SignalAlert,
    SignalAlertsResponse,
    SignalAlertStatus,
    SignalChangeRecord,
    SignalChangeType,
    SignalHistoryResponse,
    SignalScorecardItem,
    SignalSetupScorecardStat,
    SignalSnapshotRecord,
    SignalTransitionSummary,
    TradingSignalRecord
)
from app.repositories.signal_tracking import SignalTrackingRepository
from app.services.session import AuthenticatedSessionContext


US_EASTERN = ZoneInfo("America/New_York")
CONFIDENCE_DELTA_THRESHOLD = 10
LEVEL_MOVE_THRESHOLD_PCT = 0.2
MAX_HISTORY_ITEMS = 30
MAX_ALERT_ITEMS = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value))


def _format_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "n/a"


def _as_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _material_price_change(previous: float | None, current: float | None) -> bool:
    if previous is None or current is None:
        return previous != current
    if previous == 0:
        return current != 0
    change_pct = abs(((current - previous) / previous) * 100)
    return change_pct >= LEVEL_MOVE_THRESHOLD_PCT


def _eastern_day_bounds(lookback_days: int = 1) -> tuple[datetime, datetime]:
    now_et = _now().astimezone(US_EASTERN)
    end_et = datetime.combine(now_et.date(), time.max, tzinfo=US_EASTERN)
    start_date = now_et.date() - timedelta(days=max(0, lookback_days - 1))
    start_et = datetime.combine(start_date, time.min, tzinfo=US_EASTERN)
    return (
        start_et.astimezone(timezone.utc),
        end_et.astimezone(timezone.utc)
    )


def _history_start_iso(minutes: int | None = None, lookback_days: int = 1) -> str:
    if minutes is not None:
        return (_now() - timedelta(minutes=max(1, minutes))).isoformat()
    return _eastern_day_bounds(lookback_days)[0].isoformat()


def _to_signal_snapshot(row: dict[str, object]) -> SignalSnapshotRecord:
    snapshot_payload = json.loads(str(row["snapshot_json"]))
    transition_payload = row.get("transition_json")
    transition = (
        SignalTransitionSummary.model_validate(json.loads(str(transition_payload)))
        if transition_payload
        else None
    )
    return SignalSnapshotRecord.model_validate(
        {
            **snapshot_payload,
            "snapshot_id": row["id"],
            "snapshot_at": row["created_at"],
            "market_phase": row["market_phase"],
            "regime_headline": row["regime_headline"],
            "transition": transition.model_dump(mode="json") if transition else None
        }
    )


def _to_alert(row: dict[str, object]) -> SignalAlert:
    payload = json.loads(str(row["payload_json"]))
    return SignalAlert.model_validate(
        {
            "id": row["id"],
            "type": row["alert_type"],
            "symbol": row["symbol"],
            "severity": row["severity"],
            "title": row["title"],
            "message": row["message"],
            "timestamp": row["created_at"],
            "status": row["status"],
            "snapshot_id": row["snapshot_id"],
            "change_types": json.loads(str(row["change_types_json"])),
            "data_quality": row["data_quality"],
            "read_at": row["read_at"],
            "acknowledged_at": row["acknowledged_at"],
            **payload
        }
    )


def _fingerprint(
    signal: TradingSignalRecord,
    *,
    market_phase: str,
    regime_headline: str
) -> str:
    payload = {
        "symbol": signal.symbol,
        "action": signal.action,
        "setup_type": signal.setup_type,
        "entry_state": signal.entry_state,
        "confidence": signal.confidence,
        "score": signal.score,
        "entry_price": _as_float(signal.entry_price),
        "stop_loss": _as_float(signal.stop_loss),
        "take_profit1": _as_float(signal.take_profit1),
        "take_profit2": _as_float(signal.take_profit2),
        "is_actionable": signal.is_actionable,
        "has_position": signal.has_position,
        "market_phase": market_phase,
        "regime_headline": regime_headline,
        "market_data_quality": signal.market_data_quality
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _stop_breached(signal: TradingSignalRecord) -> bool:
    return (
        signal.has_position
        and signal.current_position is not None
        and signal.stop_loss is not None
        and signal.current_position.market_price <= signal.stop_loss * 1.01
    )


def _target_hit(signal: TradingSignalRecord) -> bool:
    return (
        signal.has_position
        and signal.current_position is not None
        and signal.take_profit1 is not None
        and signal.current_position.market_price >= signal.take_profit1
    )


def _add_change(
    changes: list[SignalChangeRecord],
    *,
    change_type: SignalChangeType,
    summary: str,
    detail: str,
    previous_value: str | None = None,
    current_value: str | None = None,
    is_material: bool = True
) -> None:
    changes.append(
        SignalChangeRecord(
            type=change_type,
            summary=summary,
            detail=detail,
            previous_value=previous_value,
            current_value=current_value,
            is_material=is_material
        )
    )


def detect_signal_transition(
    previous: SignalSnapshotRecord | None,
    current: TradingSignalRecord,
    *,
    market_clock: MarketClock,
    regime_headline: str
) -> SignalTransitionSummary | None:
    changes: list[SignalChangeRecord] = []

    if previous is None:
        _add_change(
            changes,
            change_type="initial_snapshot",
            summary="First tracked intraday snapshot",
            detail=f"{current.symbol} is being tracked from this snapshot onward."
        )
        if current.is_actionable and current.action in {"BUY", "SELL"}:
            _add_change(
                changes,
                change_type="new_actionable_setup",
                summary="Fresh actionable setup appeared",
                detail=(
                    f"{current.symbol} moved from no tracked prior state into a live {current.action} setup "
                    f"using {current.strategy_type.lower()}."
                )
            )
        if current.market_data_quality == "fallback":
            _add_change(
                changes,
                change_type="fallback_data_warning",
                summary="Signal quality is on fallback data",
                detail=f"{current.symbol} is currently running on fallback market data rather than provider-backed intraday data."
            )
        if current.has_position and market_clock.phase == "near_close":
            _add_change(
                changes,
                change_type="near_close_flatten_warning",
                summary="Near-close flatten window is active",
                detail=f"{current.symbol} is already held and the day-trading flatten rule is active into the close."
            )
    else:
        if previous.action != current.action:
            _add_change(
                changes,
                change_type="action_changed",
                summary=f"Action changed from {previous.action} to {current.action}",
                detail=f"{current.symbol} changed from {previous.action} to {current.action}.",
                previous_value=previous.action,
                current_value=current.action,
                is_material=True
            )

        if previous.setup_type != current.setup_type:
            _add_change(
                changes,
                change_type="setup_changed",
                summary="Active setup template changed",
                detail=(
                    f"{current.symbol} moved from {previous.strategy_type.lower()} "
                    f"to {current.strategy_type.lower()}."
                ),
                previous_value=previous.setup_type,
                current_value=current.setup_type
            )

        if not previous.is_actionable and current.is_actionable and current.action in {"BUY", "SELL"}:
            change_type: SignalChangeType = (
                "setup_confirmed"
                if previous.entry_state == "wait_for_confirmation"
                else "new_actionable_setup"
            )
            _add_change(
                changes,
                change_type=change_type,
                summary="Setup is actionable now" if change_type == "setup_confirmed" else "New actionable setup",
                detail=(
                    f"{current.symbol} is actionable now with {current.strategy_type.lower()}."
                    if change_type == "setup_confirmed"
                    else f"{current.symbol} now has a fresh {current.action} setup."
                )
            )

        if previous.is_actionable and not current.is_actionable:
            _add_change(
                changes,
                change_type="signal_invalidated",
                summary="Setup is no longer actionable",
                detail=f"{current.symbol} no longer clears the intraday entry bar and should stand aside.",
                previous_value=previous.action,
                current_value=current.action
            )

        if current.has_position and current.action == "EXIT" and previous.action != "EXIT":
            _add_change(
                changes,
                change_type="exit_signal",
                summary="Exit signal fired",
                detail=f"{current.symbol} flipped into a full exit signal for the current paper position."
            )
        elif current.has_position and current.action == "REDUCE" and previous.action not in {"REDUCE", "EXIT"}:
            _add_change(
                changes,
                change_type="signal_downgrade",
                summary="Signal downgraded into active defense",
                detail=f"{current.symbol} should move from normal management into partial profit-taking or tighter defense."
            )
        elif (
            previous.action in {"BUY", "HOLD"}
            and current.action in {"HOLD", "NO_TRADE"}
            and current.confidence <= previous.confidence - CONFIDENCE_DELTA_THRESHOLD
        ):
            _add_change(
                changes,
                change_type="signal_downgrade",
                summary="Confidence dropped materially",
                detail=f"{current.symbol} still exists in the book, but conviction has deteriorated enough to tighten expectations.",
                previous_value=str(previous.confidence),
                current_value=str(current.confidence)
            )

        if abs(previous.confidence - current.confidence) >= CONFIDENCE_DELTA_THRESHOLD:
            _add_change(
                changes,
                change_type="confidence_changed",
                summary="Confidence moved materially",
                detail=f"{current.symbol} confidence moved from {previous.confidence} to {current.confidence}.",
                previous_value=str(previous.confidence),
                current_value=str(current.confidence),
                is_material=abs(previous.confidence - current.confidence) >= 15
            )

        level_changes: list[str] = []
        if _material_price_change(previous.entry_price, current.entry_price):
            level_changes.append(f"entry {_format_price(previous.entry_price)} -> {_format_price(current.entry_price)}")
        if _material_price_change(previous.stop_loss, current.stop_loss):
            level_changes.append(f"stop {_format_price(previous.stop_loss)} -> {_format_price(current.stop_loss)}")
        if _material_price_change(previous.take_profit1, current.take_profit1):
            level_changes.append(f"target 1 {_format_price(previous.take_profit1)} -> {_format_price(current.take_profit1)}")
        if _material_price_change(previous.take_profit2, current.take_profit2):
            level_changes.append(f"target 2 {_format_price(previous.take_profit2)} -> {_format_price(current.take_profit2)}")
        if level_changes:
            _add_change(
                changes,
                change_type="level_changed",
                summary="Trade levels moved",
                detail=f"{current.symbol} adjusted its trade map: " + "; ".join(level_changes) + ".",
                is_material=True
            )

        if previous.market_phase != market_clock.phase:
            material = market_clock.phase in {"opening_range", "near_close"} or previous.market_phase in {"opening_range", "near_close"}
            _add_change(
                changes,
                change_type="session_changed",
                summary="Session phase changed",
                detail=(
                    f"The session changed from {previous.market_phase.replace('_', ' ')} "
                    f"to {market_clock.phase.replace('_', ' ')} for {current.symbol}."
                ),
                previous_value=previous.market_phase,
                current_value=market_clock.phase,
                is_material=material
            )

        if previous.regime_headline != regime_headline:
            _add_change(
                changes,
                change_type="regime_changed",
                summary="Market regime headline changed",
                detail=f"Broad market context changed from '{previous.regime_headline}' to '{regime_headline}'.",
                previous_value=previous.regime_headline,
                current_value=regime_headline,
                is_material=current.is_actionable or current.has_position
            )

        if previous.market_data_quality != current.market_data_quality and current.market_data_quality == "fallback":
            _add_change(
                changes,
                change_type="fallback_data_warning",
                summary="Signal quality degraded to fallback data",
                detail=f"{current.symbol} fell back from provider-backed intraday data to development-quality fallback data."
            )

        if _stop_breached(current) and not _stop_breached(previous):
            _add_change(
                changes,
                change_type="stop_breach",
                summary="Stop breach detected",
                detail=f"{current.symbol} is pressing the protective stop zone near {_format_price(current.stop_loss)}."
            )

        if _target_hit(current) and not _target_hit(previous):
            _add_change(
                changes,
                change_type="target_hit",
                summary="First target reached",
                detail=f"{current.symbol} reached the first target near {_format_price(current.take_profit1)}."
            )

        if current.has_position and market_clock.phase == "near_close" and previous.market_phase != "near_close":
            _add_change(
                changes,
                change_type="near_close_flatten_warning",
                summary="Near-close flatten window is active",
                detail=f"{current.symbol} is still open and the session is now in the near-close flatten window."
            )

    if not changes:
        return None

    material_changes = [change for change in changes if change.is_material]
    headline = material_changes[0].summary if material_changes else changes[0].summary
    return SignalTransitionSummary(
        has_meaningful_change=bool(material_changes),
        headline=headline,
        changes=changes
    )


def _snapshot_row(
    user_id: str,
    signal: TradingSignalRecord,
    *,
    market_clock: MarketClock,
    regime_headline: str,
    transition: SignalTransitionSummary | None,
    fingerprint: str,
    snapshot_id: str,
    snapshot_at: datetime
) -> dict[str, object]:
    return {
        "id": snapshot_id,
        "user_id": user_id,
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
        "setup_type": signal.setup_type,
        "action": signal.action,
        "entry_state": signal.entry_state,
        "confidence": signal.confidence,
        "score": signal.score,
        "thesis": signal.thesis,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit1": signal.take_profit1,
        "take_profit2": signal.take_profit2,
        "market_data_source": signal.market_data_source,
        "market_data_quality": signal.market_data_quality,
        "is_actionable": int(signal.is_actionable),
        "has_position": int(signal.has_position),
        "market_phase": market_clock.phase,
        "regime_headline": regime_headline,
        "reasons_json": json.dumps(signal.reasons),
        "warnings_json": json.dumps(signal.warnings),
        "signal_fingerprint": fingerprint,
        "transition_json": json.dumps(transition.model_dump(mode="json")) if transition else None,
        "snapshot_json": json.dumps(signal.model_dump(mode="json")),
        "created_at": snapshot_at.isoformat()
    }


def _dedupe_key(
    *,
    signal: TradingSignalRecord,
    change_type: SignalChangeType,
    signal_fingerprint: str,
    session_date: str
) -> str:
    if change_type == "near_close_flatten_warning":
        return f"{signal.symbol}:{change_type}:{session_date}"
    if change_type == "fallback_data_warning":
        return f"{signal.symbol}:{change_type}:{signal.market_data_source}:{session_date}"
    if change_type == "stop_breach":
        return f"{signal.symbol}:{change_type}:{_format_price(signal.stop_loss)}"
    if change_type == "target_hit":
        return f"{signal.symbol}:{change_type}:{_format_price(signal.take_profit1)}"
    return f"{signal.symbol}:{change_type}:{signal_fingerprint}"


def _build_alert_for_change(
    signal: TradingSignalRecord,
    *,
    change: SignalChangeRecord,
    snapshot_id: str,
    timestamp: datetime
) -> SignalAlert | None:
    if change.type == "new_actionable_setup":
        return SignalAlert(
            id=str(uuid4()),
            type="new_actionable_setup",
            symbol=signal.symbol,
            severity="info",
            title=f"New {signal.action} setup in {signal.symbol}",
            message=f"{signal.strategy_type} is actionable now around {signal.entry_zone or _format_price(signal.entry_price)}.",
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "setup_confirmed":
        return SignalAlert(
            id=str(uuid4()),
            type="setup_confirmed",
            symbol=signal.symbol,
            severity="info",
            title=f"{signal.symbol} setup confirmed",
            message=f"Confirmation cleared and the entry is live near {signal.entry_zone or _format_price(signal.entry_price)}.",
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "signal_downgrade":
        return SignalAlert(
            id=str(uuid4()),
            type="signal_downgrade",
            symbol=signal.symbol,
            severity="caution",
            title=f"Signal downgraded for {signal.symbol}",
            message=change.detail,
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "exit_signal":
        return SignalAlert(
            id=str(uuid4()),
            type="exit_signal",
            symbol=signal.symbol,
            severity="risk",
            title=f"Exit {signal.symbol}",
            message=f"Exit is active now. Protect around {_format_price(signal.stop_loss)} and flatten the position.",
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "stop_breach":
        return SignalAlert(
            id=str(uuid4()),
            type="stop_breach",
            symbol=signal.symbol,
            severity="risk",
            title=f"Stop breached in {signal.symbol}",
            message=change.detail,
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "target_hit":
        return SignalAlert(
            id=str(uuid4()),
            type="target_hit",
            symbol=signal.symbol,
            severity="info",
            title=f"Target reached in {signal.symbol}",
            message=change.detail,
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "near_close_flatten_warning":
        return SignalAlert(
            id=str(uuid4()),
            type="near_close_flatten_warning",
            symbol=signal.symbol,
            severity="caution",
            title=f"Flatten window active for {signal.symbol}",
            message=change.detail,
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    if change.type == "fallback_data_warning":
        return SignalAlert(
            id=str(uuid4()),
            type="fallback_data_warning",
            symbol=signal.symbol,
            severity="caution",
            title=f"Fallback data in use for {signal.symbol}",
            message=change.detail,
            timestamp=timestamp,
            snapshot_id=snapshot_id,
            change_types=[change.type],
            data_quality=signal.market_data_quality
        )
    return None


def _alert_row(
    user_id: str,
    alert: SignalAlert,
    *,
    dedupe_key: str,
    payload: dict[str, object]
) -> dict[str, object]:
    return {
        "id": alert.id,
        "user_id": user_id,
        "symbol": alert.symbol,
        "snapshot_id": alert.snapshot_id,
        "alert_type": alert.type,
        "severity": alert.severity,
        "status": alert.status,
        "title": alert.title,
        "message": alert.message,
        "dedupe_key": dedupe_key,
        "change_types_json": json.dumps(alert.change_types),
        "data_quality": alert.data_quality,
        "payload_json": json.dumps(payload),
        "created_at": alert.timestamp.isoformat(),
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
    }


def persist_signal_run(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    *,
    market_clock: MarketClock,
    regime_headline: str,
    items: list[TradingSignalRecord]
) -> list[SignalAlert]:
    repository = SignalTrackingRepository(session)
    session_date = _now().astimezone(US_EASTERN).date().isoformat()
    dedupe_after = _history_start_iso(lookback_days=1)
    created_alerts: list[SignalAlert] = []

    for signal in items:
        previous_row = repository.get_latest_snapshot(current_session.user_id, signal.symbol)
        previous_snapshot = (
            _to_signal_snapshot(dict(previous_row))
            if previous_row is not None
            else None
        )
        transition = detect_signal_transition(
            previous_snapshot,
            signal,
            market_clock=market_clock,
            regime_headline=regime_headline
        )
        snapshot_id = str(uuid4())
        snapshot_at = _now()
        signal_fingerprint = _fingerprint(
            signal,
            market_phase=market_clock.phase,
            regime_headline=regime_headline
        )
        repository.create_snapshot(
            _snapshot_row(
                current_session.user_id,
                signal,
                market_clock=market_clock,
                regime_headline=regime_headline,
                transition=transition,
                fingerprint=signal_fingerprint,
                snapshot_id=snapshot_id,
                snapshot_at=snapshot_at
            )
        )

        if transition is None:
            continue

        for change in transition.changes:
            alert = _build_alert_for_change(
                signal,
                change=change,
                snapshot_id=snapshot_id,
                timestamp=snapshot_at
            )
            if alert is None:
                continue

            dedupe_key = _dedupe_key(
                signal=signal,
                change_type=change.type,
                signal_fingerprint=signal_fingerprint,
                session_date=session_date
            )
            existing = repository.get_latest_alert_for_dedupe(
                current_session.user_id,
                dedupe_key,
                dedupe_after
            )
            if existing is not None:
                continue

            repository.create_alert(
                _alert_row(
                    current_session.user_id,
                    alert,
                    dedupe_key=dedupe_key,
                    payload={
                        "symbol": signal.symbol,
                        "action": signal.action,
                        "setup_type": signal.setup_type,
                        "timeframe": signal.timeframe
                    }
                )
            )
            created_alerts.append(alert)

    return created_alerts


def list_signal_alerts(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    *,
    limit: int = 25,
    minutes: int | None = None,
    status: SignalAlertStatus | None = None
) -> SignalAlertsResponse:
    repository = SignalTrackingRepository(session)
    rows = repository.list_alerts(
        current_session.user_id,
        limit=min(max(limit, 1), MAX_ALERT_ITEMS),
        created_after=_history_start_iso(minutes=minutes) if minutes is not None else None,
        status=status
    )
    return SignalAlertsResponse(
        as_of=_now(),
        items=[_to_alert(row) for row in rows]
    )


def get_signal_history(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    symbol: str,
    *,
    limit: int = 20
) -> SignalHistoryResponse:
    repository = SignalTrackingRepository(session)
    rows = repository.list_snapshots(
        current_session.user_id,
        symbol.upper(),
        limit=min(max(limit, 1), MAX_HISTORY_ITEMS)
    )
    return SignalHistoryResponse(
        as_of=_now(),
        symbol=symbol.upper(),
        items=[_to_signal_snapshot(row) for row in rows]
    )


def update_signal_alert_status(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    alert_id: str,
    *,
    status: SignalAlertStatus
) -> SignalAlert:
    repository = SignalTrackingRepository(session)
    existing = repository.get_alert(current_session.user_id, alert_id)
    if existing is None:
        raise AppError(
            code="signal_alert_not_found",
            message="The requested signal alert was not found.",
            status_code=404
        )

    current_timestamp = _now().isoformat()
    read_at = existing["read_at"]
    acknowledged_at = existing["acknowledged_at"]
    if status == "read" and read_at is None:
        read_at = current_timestamp
    if status == "acknowledged":
        read_at = read_at or current_timestamp
        acknowledged_at = current_timestamp

    repository.update_alert_status(
        current_session.user_id,
        alert_id,
        status=status,
        read_at=str(read_at) if read_at is not None else None,
        acknowledged_at=str(acknowledged_at) if acknowledged_at is not None else None
    )
    updated = repository.get_alert(current_session.user_id, alert_id)
    if updated is None:
        raise AppError(
            code="signal_alert_not_found",
            message="The requested signal alert was not found.",
            status_code=404
        )
    return _to_alert(dict(updated))


def get_intraday_scorecard(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    *,
    lookback_days: int = 1
) -> IntradayScorecardResponse:
    repository = SignalTrackingRepository(session)
    start_at, end_at = _eastern_day_bounds(lookback_days)
    snapshot_rows = repository.list_snapshots_in_window(
        current_session.user_id,
        start_at.isoformat(),
        created_before=end_at.isoformat(),
        limit=1000
    )
    alert_rows = repository.list_alerts(
        current_session.user_id,
        limit=1000,
        created_after=start_at.isoformat()
    )

    snapshots = [_to_signal_snapshot(row) for row in snapshot_rows]
    alerts = [_to_alert(row) for row in alert_rows]
    alerts_by_symbol: dict[str, list[SignalAlert]] = defaultdict(list)
    for alert in sorted(alerts, key=lambda item: item.timestamp):
        if alert.symbol is not None:
            alerts_by_symbol[alert.symbol].append(alert)

    actionable_triggers = [
        snapshot
        for snapshot in sorted(snapshots, key=lambda item: item.snapshot_at)
        if snapshot.transition is not None
        and any(
            change.type in {"new_actionable_setup", "setup_confirmed"}
            for change in snapshot.transition.changes
        )
    ]

    triggers_by_symbol: dict[str, list[SignalSnapshotRecord]] = defaultdict(list)
    for snapshot in actionable_triggers:
        triggers_by_symbol[snapshot.symbol].append(snapshot)

    scorecard_items: list[SignalScorecardItem] = []
    for symbol, symbol_triggers in triggers_by_symbol.items():
        for index, trigger in enumerate(symbol_triggers):
            next_trigger_at = (
                symbol_triggers[index + 1].snapshot_at
                if index + 1 < len(symbol_triggers)
                else None
            )
            relevant_alerts = [
                alert
                for alert in alerts_by_symbol.get(symbol, [])
                if alert.timestamp >= trigger.snapshot_at
                and (next_trigger_at is None or alert.timestamp < next_trigger_at)
            ]
            alert_types = [alert.type for alert in relevant_alerts]
            if "target_hit" in alert_types:
                outcome = "target_hit"
            elif "stop_breach" in alert_types:
                outcome = "stop_hit"
            elif "exit_signal" in alert_types:
                outcome = "exit_signal"
            elif lookback_days == 1 and trigger.snapshot_at.astimezone(US_EASTERN).date() == _now().astimezone(US_EASTERN).date():
                outcome = "open"
            else:
                outcome = "no_resolution"

            notes = [trigger.thesis]
            if trigger.transition and trigger.transition.headline:
                notes.append(trigger.transition.headline)
            if trigger.market_data_quality == "fallback":
                notes.append("This setup was tracked on fallback intraday data.")

            scorecard_items.append(
                SignalScorecardItem(
                    symbol=symbol,
                    setup_type=trigger.setup_type,
                    action=trigger.action,
                    triggered_at=trigger.snapshot_at,
                    outcome=outcome,
                    alert_count=len(relevant_alerts),
                    alert_types=sorted(set(alert_types)),
                    market_phase=trigger.market_phase,
                    market_data_quality=trigger.market_data_quality,
                    entry_price=trigger.entry_price,
                    stop_loss=trigger.stop_loss,
                    take_profit1=trigger.take_profit1,
                    notes=notes[:3]
                )
            )

    stats_by_setup: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "target_hits": 0,
            "stop_hits": 0,
            "exit_signals": 0,
            "open": 0,
            "no_resolution": 0
        }
    )
    for item in scorecard_items:
        setup_stats = stats_by_setup[item.setup_type]
        setup_stats["total"] += 1
        if item.outcome == "target_hit":
            setup_stats["target_hits"] += 1
        elif item.outcome == "stop_hit":
            setup_stats["stop_hits"] += 1
        elif item.outcome == "exit_signal":
            setup_stats["exit_signals"] += 1
        elif item.outcome == "open":
            setup_stats["open"] += 1
        else:
            setup_stats["no_resolution"] += 1

    setup_stats_items: list[SignalSetupScorecardStat] = []
    for setup_type, values in sorted(stats_by_setup.items()):
        resolved = values["target_hits"] + values["stop_hits"] + values["exit_signals"]
        win_rate = (values["target_hits"] / resolved) * 100 if resolved else 0.0
        setup_stats_items.append(
            SignalSetupScorecardStat(
                setup_type=setup_type,  # type: ignore[arg-type]
                total=values["total"],
                target_hits=values["target_hits"],
                stop_hits=values["stop_hits"],
                exit_signals=values["exit_signals"],
                open=values["open"],
                no_resolution=values["no_resolution"],
                win_rate_pct=round(win_rate, 2)
            )
        )

    return IntradayScorecardResponse(
        as_of=_now(),
        session_date=_now().astimezone(US_EASTERN).date().isoformat(),
        lookback_days=lookback_days,
        symbols_with_snapshots=len({snapshot.symbol for snapshot in snapshots}),
        actionable_signals=len(scorecard_items),
        alerts_fired=len(alerts),
        fallback_alerts=sum(1 for alert in alerts if alert.data_quality == "fallback"),
        items=sorted(scorecard_items, key=lambda item: item.triggered_at, reverse=True),
        setup_stats=setup_stats_items
    )
