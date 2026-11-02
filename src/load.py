"""Load step: write cleaned events, the event-state bridge table and CPI into SQLite."""

import sqlite3

import pandas as pd

from extract import PROJECT_ROOT

DB_FILE = PROJECT_ROOT / "data" / "processed" / "catastrophes.db"
SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"

EVENT_COLUMNS = [
    "event_id", "event_name", "peril", "event_category", "event_start", "event_finish",
    "year", "financial_year", "decade", "state_group", "state_source", "has_loss",
    "original_loss", "cpi_adjusted_loss_2022", "normalised_loss_2022", "total_claims",
]


def build_event_states(events: pd.DataFrame) -> pd.DataFrame:
    """One row per event and state, e.g. 'NSW|QLD' becomes two rows."""
    pairs = events[["event_id", "states"]].dropna()
    pairs = pairs.assign(state=pairs["states"].str.split("|")).explode("state")
    return pairs[["event_id", "state"]]


def load_to_sqlite(events: pd.DataFrame, cpi: pd.DataFrame, db_path=DB_FILE) -> None:
    table_events = events[EVENT_COLUMNS].copy()
    table_events["event_start"] = table_events["event_start"].dt.strftime("%Y-%m-%d")
    table_events["event_finish"] = table_events["event_finish"].dt.strftime("%Y-%m-%d")
    table_events["has_loss"] = table_events["has_loss"].astype(int)

    table_cpi = cpi.assign(quarter_end=cpi["quarter_end"].dt.strftime("%Y-%m-%d"))

    tables = {  # parent table (events) before the bridge table that references it
        "events": table_events,
        "event_states": build_event_states(events),
        "cpi": table_cpi,
    }

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_FILE.read_text())
        conn.execute("PRAGMA foreign_keys = ON")
        for name, table in tables.items():
            table.to_sql(name, conn, if_exists="append", index=False)
            print(f"  {name}: {len(table):,} rows")
        conn.commit()
    finally:
        conn.close()