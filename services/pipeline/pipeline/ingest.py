from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class IngestionJob:
    provider: str
    dataset: str
    cadence: str
    destination: str


def build_ingestion_plan() -> dict[str, object]:
    jobs = [
        IngestionJob(
            provider="options_provider",
            dataset="chains_plus_greeks",
            cadence="1m snapshots during RTH",
            destination="raw/options/date=YYYY-MM-DD/"
        ),
        IngestionJob(
            provider="official_macro",
            dataset="cpi_jobs_fomc_calendar",
            cadence="daily",
            destination="raw/macro/date=YYYY-MM-DD/"
        ),
        IngestionJob(
            provider="news_provider",
            dataset="headline_tone_events",
            cadence="5m batches",
            destination="raw/news/date=YYYY-MM-DD/"
        )
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jobs": [asdict(job) for job in jobs]
    }

