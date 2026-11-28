"""Freshness validation for ARK daily holdings CSVs.

ARK has served HTTP 200 responses with stale holdings files after a
file rename, so a successful download is not enough. Every ARK job
checks the newest holdings date before writing any output; a stale
file raises, main.py records that fund as failed, and the previous
good dataset stays in place.
"""

from datetime import datetime, timezone

import pandas as pd

MAX_ARK_HOLDINGS_AGE_DAYS = 7


def validate_ark_holdings_date(df, fund_label, max_age_days=MAX_ARK_HOLDINGS_AGE_DAYS, today=None):
    """Raise ValueError when an ARK holdings frame is stale or undated."""
    if 'date' not in df.columns:
        raise ValueError(f'{fund_label} source missing date column')

    parsed_dates = pd.to_datetime(df['date'], errors='coerce')
    latest = parsed_dates.max()
    if pd.isna(latest):
        raise ValueError(f'{fund_label} source has no parseable holdings date')

    latest_date = latest.date()
    run_date = today or datetime.now(timezone.utc).date()
    age_days = (run_date - latest_date).days
    if age_days > max_age_days:
        raise ValueError(
            f'{fund_label} holdings are stale: latest date '
            f'{latest_date.isoformat()} is {age_days} days old'
        )
    return latest_date
