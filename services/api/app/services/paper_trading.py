from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from app.db import DatabaseSession
from app.errors import AppError
from app.models import (
    PaperExecutionAssumptions,
    PaperFillRecord,
    PaperOrderPlacementResponse,
    PaperOrderRecord,
    PaperOrderRequest,
    PaperOrdersResponse,
    PaperPortfolioSummary,
    PaperPositionRecord,
    PaperPositionsResponse
)
from app.repositories.audit import AuditRepository
from app.repositories.paper_trading import PaperTradingRepository
from app.services.market import get_market_clock, get_quote_snapshot
from app.services.session import AuthenticatedSessionContext


VALID_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,15}$")
FIXED_SLIPPAGE_BPS = 10

PAPER_EXECUTION_ASSUMPTIONS = PaperExecutionAssumptions(
    fill_model="Market orders fill immediately at the current quote with 10 bps adverse slippage.",
    price_source="Latest price comes from the configured market data provider, preferring intraday bars for the current session when available, with explicit development fallback when live credentials are absent or the provider fails.",
    commissions="No commissions or fees are modeled in Phase 2.",
    sells_require_existing_position=True
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or not VALID_SYMBOL.fullmatch(normalized):
        raise AppError(
            code="invalid_symbol",
            message="Enter a valid symbol.",
            status_code=400
        )
    return normalized


def _fill_price(market_price: float, side: str) -> float:
    slippage_ratio = FIXED_SLIPPAGE_BPS / 10_000
    multiplier = 1 + slippage_ratio if side == "buy" else 1 - slippage_ratio
    return round(market_price * multiplier, 4)


def _to_order_record(order_row: dict[str, object]) -> PaperOrderRecord:
    return PaperOrderRecord.model_validate(order_row)


def _to_position_record(position_row: dict[str, object]) -> PaperPositionRecord:
    quote = get_quote_snapshot(str(position_row["symbol"]))
    quantity = int(position_row["quantity"])
    average_cost = float(position_row["average_cost"])
    realized_pnl = float(position_row["realized_pnl"])
    market_value = round(quantity * quote.last, 2)
    cost_basis = round(quantity * average_cost, 2)
    unrealized_pnl = round((quote.last - average_cost) * quantity, 2)

    return PaperPositionRecord(
        symbol=str(position_row["symbol"]),
        quantity=quantity,
        average_cost=round(average_cost, 4),
        market_price=quote.last,
        market_value=market_value,
        cost_basis=cost_basis,
        realized_pnl=round(realized_pnl, 2),
        unrealized_pnl=unrealized_pnl,
        total_pnl=round(realized_pnl + unrealized_pnl, 2),
        market_source=quote.source,
        market_quality=quote.quality,
        updated_at=position_row["updated_at"]
    )


def list_open_positions(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext
) -> PaperPositionsResponse:
    repository = PaperTradingRepository(session)
    positions = repository.list_positions(current_session.user_id)
    return PaperPositionsResponse(
        as_of=datetime.now(timezone.utc),
        items=[_to_position_record(position) for position in positions]
    )


def list_order_history(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext
) -> PaperOrdersResponse:
    repository = PaperTradingRepository(session)
    orders = repository.list_orders(current_session.user_id)
    return PaperOrdersResponse(
        as_of=datetime.now(timezone.utc),
        items=[_to_order_record(order) for order in orders]
    )


def get_portfolio_summary(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext
) -> PaperPortfolioSummary:
    repository = PaperTradingRepository(session)
    positions = list_open_positions(session, current_session).items
    realized_pnl = round(repository.get_realized_pnl_total(current_session.user_id), 2)
    unrealized_pnl = round(sum(position.unrealized_pnl for position in positions), 2)
    market_value = round(sum(position.market_value for position in positions), 2)
    cost_basis = round(sum(position.cost_basis for position in positions), 2)
    qualities = {position.market_quality for position in positions}
    sources = {position.market_source for position in positions}
    if not positions:
        clock = get_market_clock()
        quality = clock.quality
        source = clock.source
    elif len(qualities) == 1:
        quality = next(iter(qualities))
        source = next(iter(sources))
    else:
        quality = "mixed"
        source = "mixed-market-data"

    return PaperPortfolioSummary(
        as_of=datetime.now(timezone.utc),
        positions=len(positions),
        gross_exposure=market_value,
        market_value=market_value,
        cost_basis=cost_basis,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        total_pnl=round(realized_pnl + unrealized_pnl, 2),
        market_data_source=source,
        market_data_quality=quality,
        assumptions=PAPER_EXECUTION_ASSUMPTIONS
    )


def place_paper_order(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    payload: PaperOrderRequest
) -> PaperOrderPlacementResponse:
    repository = PaperTradingRepository(session)
    audit_repository = AuditRepository(session)
    symbol = _normalize_symbol(payload.symbol)
    quote = get_quote_snapshot(symbol)
    market_price = quote.last
    fill_price = _fill_price(market_price, payload.side)
    submitted_at = utc_now_iso()

    current_position = repository.get_position(current_session.user_id, symbol)
    order_id = str(uuid4())

    if payload.side == "sell":
        current_quantity = int(current_position["quantity"]) if current_position else 0
        if current_quantity < payload.quantity:
            repository.record_rejected_order(
                {
                    "id": order_id,
                    "user_id": current_session.user_id,
                    "symbol": symbol,
                    "side": payload.side,
                    "quantity": payload.quantity,
                    "order_type": payload.order_type,
                    "status": "rejected",
                    "requested_price": market_price,
                    "fill_price": None,
                    "submitted_at": submitted_at,
                    "filled_at": None,
                    "rejection_reason": "insufficient_position"
                }
            )
            audit_repository.record_event(
                event_type="paper.order.rejected",
                user_id=current_session.user_id,
                session_id=current_session.session_id,
                entity_type="paper_order",
                entity_id=order_id,
                payload={
                    "reason": "insufficient_position",
                    "symbol": symbol,
                    "quantity": payload.quantity,
                    "side": payload.side
                }
            )
            session.commit()
            raise AppError(
                code="insufficient_position",
                message="You cannot sell more shares than the current paper position.",
                status_code=400
            )

    existing_quantity = int(current_position["quantity"]) if current_position else 0
    existing_average_cost = (
        float(current_position["average_cost"]) if current_position else 0.0
    )
    existing_realized_pnl = (
        float(current_position["realized_pnl"]) if current_position else 0.0
    )

    realized_delta = 0.0
    if payload.side == "buy":
        next_quantity = existing_quantity + payload.quantity
        next_average_cost = (
            ((existing_quantity * existing_average_cost) + (payload.quantity * fill_price))
            / next_quantity
        )
        next_realized_pnl = existing_realized_pnl
    else:
        next_quantity = existing_quantity - payload.quantity
        realized_delta = round(
            (fill_price - existing_average_cost) * payload.quantity,
            2
        )
        next_average_cost = existing_average_cost if next_quantity > 0 else 0.0
        next_realized_pnl = round(existing_realized_pnl + realized_delta, 2)

    order_row = {
        "id": order_id,
        "user_id": current_session.user_id,
        "symbol": symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "order_type": payload.order_type,
        "status": "filled",
        "requested_price": market_price,
        "fill_price": fill_price,
        "submitted_at": submitted_at,
        "filled_at": submitted_at,
        "rejection_reason": None
    }
    fill_row = {
        "id": str(uuid4()),
        "order_id": order_id,
        "user_id": current_session.user_id,
        "symbol": symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "market_price": market_price,
        "fill_price": fill_price,
        "realized_pnl": realized_delta,
        "filled_at": submitted_at
    }

    position_row = None
    if next_quantity > 0:
        position_row = {
            "user_id": current_session.user_id,
            "symbol": symbol,
            "quantity": next_quantity,
            "average_cost": round(next_average_cost, 4),
            "realized_pnl": next_realized_pnl,
            "created_at": current_position["created_at"] if current_position else submitted_at,
            "updated_at": submitted_at
        }

    repository.record_filled_order(order_row, fill_row, position_row)
    audit_repository.record_event(
        event_type="paper.order.filled",
        user_id=current_session.user_id,
        session_id=current_session.session_id,
        entity_type="paper_order",
        entity_id=order_id,
        payload={
            "symbol": symbol,
            "side": payload.side,
            "quantity": payload.quantity,
            "fill_price": fill_price,
            "market_price": market_price
        }
    )

    current_position_record = _to_position_record(position_row) if position_row else None
    portfolio = get_portfolio_summary(session, current_session)

    return PaperOrderPlacementResponse(
        order=_to_order_record(order_row),
        fill=PaperFillRecord.model_validate(fill_row),
        position=current_position_record,
        portfolio=portfolio,
        assumptions=PAPER_EXECUTION_ASSUMPTIONS
    )
