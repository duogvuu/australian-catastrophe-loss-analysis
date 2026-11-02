"""Transform step: clean the ICA catastrophe list and add derived fields."""

import pandas as pd

from extract import PROJECT_ROOT, load_cpi, load_ica
from locations import assign_states

OVERRIDES_FILE = PROJECT_ROOT / "data" / "reference" / "state_overrides.csv"

COLUMNS = {
    "CAT Name": "cat_name",
    "Event Name": "event_name",
    "Event Start": "event_start",
    "Event Finish": "event_finish",
    "State": "state_raw",
    "Town": "town",
    "Description": "description",
    "Type": "peril",
    "Postcode": "postcode",
    "ORIGINAL LOSS VALUE": "original_loss",
    "NORMALISED LOSS VALUE (2022)": "normalised_loss_2022",
    "TOTAL CLAIMS RECEIVED": "total_claims",
}

EXCLUDED_PERILS = {"Man-made"}  # not a natural hazard
CPI_BASE_YEAR = 2022  # match ICA's normalisation base year


def make_event_id(df: pd.DataFrame) -> pd.Series:
    """Declared events keep ICA's code (e.g. CAT264); undeclared ones get UND-<start date>-<n>."""
    start = df["event_start"].dt.strftime("%Y%m%d")
    seq = df.groupby(start).cumcount() + 1
    undeclared_id = "UND-" + start + "-" + seq.astype(str)
    return df["cat_name"].where(df["cat_name"] != "Undeclared", undeclared_id)


def add_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["event_finish"] = pd.to_datetime(df["event_finish"], errors="coerce")
    df["year"] = df["event_start"].dt.year
    # Australian financial year ends 30 June: July-December belongs to the next FY
    fy = df["year"] + (df["event_start"].dt.month > 6).astype(int)
    df["financial_year"] = "FY" + fy.astype(str)
    df["decade"] = df["year"] // 10 * 10
    return df


def add_cpi_adjusted_loss(df: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    """Restate original losses in 2022 dollars using the CPI of the event's quarter."""
    df["quarter_end"] = df["event_start"] + pd.offsets.QuarterEnd(0)
    df = df.merge(cpi, on="quarter_end", how="left")
    base_cpi = cpi.loc[cpi["quarter_end"].dt.year == CPI_BASE_YEAR, "cpi"].mean()
    df["cpi_adjusted_loss_2022"] = df["original_loss"] * base_cpi / df["cpi"]
    return df.drop(columns=["quarter_end"])


def transform(ica: pd.DataFrame, cpi: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    df = ica.rename(columns=COLUMNS)[list(COLUMNS.values())]
    df = df[~df["peril"].isin(EXCLUDED_PERILS)].copy()

    df["event_id"] = make_event_id(df)
    df["event_category"] = (
        df["cat_name"].str[:2]
        .map({"CA": "Declared CAT", "SE": "Significant event"})
        .fillna("Undeclared")
    )
    df["has_loss"] = df["original_loss"].notna()

    df = add_dates(df)
    df = add_cpi_adjusted_loss(df, cpi)
    df = assign_states(df, overrides)
    return df.sort_values("event_start").reset_index(drop=True)


if __name__ == "__main__":
    overrides = pd.read_csv(OVERRIDES_FILE)
    events = transform(load_ica(), load_cpi(), overrides)
    print(f"Events: {len(events):,}")
    losses = events[events["has_loss"]]
    print("\nState source (events with a loss):")
    print(losses["state_source"].value_counts())
    print("\nState group (events with a loss):")
    print(losses["state_group"].value_counts())