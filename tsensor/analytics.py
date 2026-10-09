"""Exploratory trends, not validated nutrient or disease predictions."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select

from tsensor.db import Reading

FIELDS = ["moisture", "temperature", "ec", "ph", "nitrogen", "phosphorus", "potassium"]


def monitoring_report(session, org_id, device_id, hours=24, now=None):
    now = now or datetime.now(timezone.utc)
    rows = session.scalars(
        select(Reading)
        .where(
            Reading.org_id == org_id,
            Reading.device_id == device_id,
            Reading.observed_at >= now - timedelta(hours=hours),
            Reading.observed_at <= now,
        )
        .order_by(Reading.observed_at.desc())
        .limit(2000)
    ).all()
    notice = "Exploratory rules; thresholds and probe calibration need field validation."
    if not rows:
        return {"sample_count": 0, "flags": [], "notice": notice}
    data = pd.DataFrame(
        [
            {"observed_at": row.observed_at, **{field: getattr(row, field) for field in FIELDS}}
            for row in reversed(rows)
        ]
    )
    data["observed_at"] = pd.to_datetime(data["observed_at"], utc=True)
    data = data.set_index("observed_at")
    latest = data.iloc[-1]
    recent = data.loc[data.index >= data.index[-1] - pd.Timedelta(minutes=30)]
    flags = []
    sustained = len(recent) >= 3 and (recent.index[-1] - recent.index[0]).total_seconds() >= 27 * 60
    if sustained and np.all((recent["moisture"] >= 70) & recent["temperature"].between(18, 30)):
        flags.append(
            {
                "rule": "warm_wet_watch",
                "reason": "Sustained warm and wet readings; inspect site conditions.",
            }
        )
    trend = data.loc[data.index >= data.index[-1] - pd.Timedelta(hours=2)]
    if len(trend) >= 3 and (trend.index[-1] - trend.index[0]).total_seconds() >= 30 * 60:
        first, last = trend.iloc[0], trend.iloc[-1]
        if (
            first["ec"] > 0
            and last["moisture"] - first["moisture"] >= 10
            and (last["ec"] <= first["ec"] * 0.8)
        ):
            flags.append(
                {
                    "rule": "dilution_leaching_watch",
                    "reason": "Moisture rose while EC fell; check irrigation and calibration.",
                }
            )
    mean = data[FIELDS].rolling("1h", min_periods=1).mean().iloc[-1]
    return {
        "sample_count": len(data),
        "window_hours": hours,
        "sample_limit_reached": len(rows) == 2000,
        "latest": {key: round(float(latest[key]), 3) for key in FIELDS},
        "latest_observed_at": data.index[-1].isoformat(),
        "rolling_hour_means": {key: round(float(mean[key]), 3) for key in FIELDS},
        "nutrient_changes_in_window": {
            key: float(data.iloc[-1][key] - data.iloc[0][key])
            for key in ["nitrogen", "phosphorus", "potassium"]
        },
        "flags": flags,
        "notice": notice,
    }
