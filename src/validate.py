"""Data quality checks for the cleaned catastrophe events table."""

import pandas as pd

VALID_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"}
NORMALISATION_BASE_YEAR = 2022
MAX_UNRESOLVED_LOSS_EVENTS = 5


def check_unique_event_ids(events: pd.DataFrame) -> None:
    dupes = events["event_id"].duplicated().sum()
    if dupes > 0:
        raise ValueError(f"{dupes} duplicate event IDs")


def check_overrides(events: pd.DataFrame, overrides: pd.DataFrame) -> None:
    """Every manual override must point to a real event and use valid state codes."""
    unknown_ids = overrides.loc[~overrides["event_id"].isin(events["event_id"]), "event_id"]
    if not unknown_ids.empty:
        raise ValueError(f"Overrides reference unknown event IDs: {list(unknown_ids)}")

    used_states = set(overrides["states"].str.split("|").explode())
    invalid = used_states - VALID_STATES
    if invalid:
        raise ValueError(f"Overrides use invalid state codes: {invalid}")


def check_no_negative_losses(events: pd.DataFrame) -> None:
    cols = ["original_loss", "normalised_loss_2022"]
    negatives = (events[cols] < 0).sum().sum()
    if negatives > 0:
        raise ValueError(f"{negatives} negative loss values")


def check_normalisation_base_year(events: pd.DataFrame) -> None:
    """From the base year onwards, ICA's normalised loss should equal the original loss."""
    recent = events[(events["year"] >= NORMALISATION_BASE_YEAR) & events["has_loss"]]
    diff = (recent["normalised_loss_2022"] - recent["original_loss"]).abs()
    if (diff > 1).any():
        raise ValueError(f"{(diff > 1).sum()} recent events have normalised != original loss")


def check_cpi_coverage(events: pd.DataFrame) -> None:
    missing = events.loc[events["has_loss"], "cpi"].isna().sum()
    if missing > 0:
        raise ValueError(f"{missing} loss events could not be matched to a CPI quarter")


def check_state_coverage(events: pd.DataFrame) -> int:
    unresolved = (events["has_loss"] & (events["state_group"] == "Unknown")).sum()
    if unresolved > MAX_UNRESOLVED_LOSS_EVENTS:
        raise ValueError(f"{unresolved} loss events have no state (max {MAX_UNRESOLVED_LOSS_EVENTS})")
    return unresolved


def run_all_checks(events: pd.DataFrame, overrides: pd.DataFrame) -> None:
    check_unique_event_ids(events)
    check_overrides(events, overrides)
    check_no_negative_losses(events)
    check_normalisation_base_year(events)
    check_cpi_coverage(events)
    unresolved = check_state_coverage(events)

    no_normalised = (events["has_loss"] & events["normalised_loss_2022"].isna()).sum()
    print(f"  All checks passed ({unresolved} loss events without a state)")
    print(f"  Note: {no_normalised} loss events have no normalised value from ICA")