"""Extract step: load the raw ICA catastrophe list and the ABS CPI series (via RBA G1)."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ICA_FILE = RAW_DIR / "ICA-Historical-Normalised-Catastrophe-2026_09.xlsx"
CPI_FILE = RAW_DIR / "g01hist.xlsx"

ICA_SHEET = "ICA_DETAILED_HISTORICAL_CATASTR"
CPI_SERIES_ID = "GCPIAG"  # Consumer price index; All groups (quarterly)


def _check_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")


def load_ica(path: Path = ICA_FILE) -> pd.DataFrame:
    """Read the detailed catastrophe sheet. Column headers are on Excel row 11."""
    _check_exists(path)
    return pd.read_excel(path, sheet_name=ICA_SHEET, header=10)


def load_cpi(path: Path = CPI_FILE) -> pd.DataFrame:
    """Return the quarterly All Groups CPI as two columns: quarter_end, cpi."""
    _check_exists(path)
    raw = pd.read_excel(path, sheet_name="Data", header=None)

    # Row 11 in Excel (index 10) holds the series IDs; make sure column B is the right series
    if raw.iloc[10, 1] != CPI_SERIES_ID:
        raise ValueError(f"Expected series {CPI_SERIES_ID} in column B, found {raw.iloc[10, 1]}")

    cpi = raw.iloc[11:, [0, 1]].copy()  # data starts on Excel row 12
    cpi.columns = ["quarter_end", "cpi"]
    cpi = cpi.dropna(subset=["cpi"])  # future quarters are blank
    cpi["quarter_end"] = pd.to_datetime(cpi["quarter_end"])
    cpi["cpi"] = cpi["cpi"].astype(float)
    return cpi.reset_index(drop=True)


if __name__ == "__main__":
    ica = load_ica()
    print(f"ICA: {len(ica):,} events, {ica.shape[1]} columns")
    cpi = load_cpi()
    print(
        f"CPI: {len(cpi):,} quarters, "
        f"{cpi['quarter_end'].min():%b %Y} to {cpi['quarter_end'].max():%b %Y}"
    )