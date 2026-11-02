"""Run the full pipeline: extract -> transform -> validate -> save -> load."""

import pandas as pd

from extract import PROJECT_ROOT, load_cpi, load_ica
from load import DB_FILE, load_to_sqlite
from transform import OVERRIDES_FILE, transform
from validate import run_all_checks

OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "events.csv"


def main() -> None:
    print("1/5 Extracting raw data...")
    ica = load_ica()
    cpi = load_cpi()
    overrides = pd.read_csv(OVERRIDES_FILE)

    print("2/5 Transforming...")
    events = transform(ica, cpi, overrides)

    print("3/5 Running data quality checks...")
    run_all_checks(events, overrides)

    print("4/5 Saving...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(OUTPUT_FILE, index=False)
    print(f"  Saved {len(events):,} events to {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")

    print("5/5 Loading into SQLite...")
    load_to_sqlite(events, cpi)
    print(f"  Database ready: {DB_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()