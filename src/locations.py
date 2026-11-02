"""Assign Australian states/territories to each catastrophe event.

ICA's State and Postcode columns are sparse and inconsistent, so states are
derived from several sources, in order of reliability:

1. manual overrides (analyst-reviewed lookup table)
2. postcodes (Australian postcodes map to states by numeric range)
3. the State column (regional codes such as FNQ/SEQ standardised)
4. place names in the event name or town
5. place names in the free-text description
"""

import re

import pandas as pd

# Regional codes used in ICA's State column
STATE_CODES = {
    "FNQ": "QLD", "SEQ": "QLD", "SWQ": "QLD", "QLD": "QLD",
    "NSW": "NSW", "VIC": "VIC", "WA": "WA", "SA": "SA",
    "NT": "NT", "TAS": "TAS", "ACT": "ACT",
}

# Place names that identify a state when found in event names or descriptions
PLACE_KEYWORDS = {
    "NSW": ["new south wales", "nsw", "sydney", "newcastle", "wollongong", "blue mountains",
            "central coast", "hunter", "lismore", "northern rivers", "illawarra",
            "hawkesbury", "tamworth", "dubbo", "coffs harbour", "port macquarie", "albury",
            "wagga", "bathurst", "armidale", "lake macquarie", "shoalhaven", "grafton",
            "broken hill", "port stephens"],
    "QLD": ["queensland", "qld", "brisbane", "gold coast", "sunshine coast", "townsville",
            "cairns", "bundaberg", "rockhampton", "ipswich", "toowoomba", "mackay",
            "gladstone", "logan", "maryborough", "hervey bay", "innisfail", "mount isa",
            "gympie", "whitsunday", "gulf of carpentaria", "cape york", "yeppoon", "lockyer"],
    "VIC": ["victoria", "vic", "melbourne", "geelong", "ballarat", "bendigo", "gippsland",
            "mansfield", "mildura", "shepparton", "wangaratta", "dandenong", "mornington",
            "ash wednesday", "grampians", "orbost", "ararat"],
    "WA": ["western australia", "perth", "port hedland", "port headland", "carnarvon",
           "canarvon", "kimberley", "geraldton", "exmouth", "kalgoorlie", "pilbara", "broome",
           "karratha", "onslow", "bunbury", "esperance", "albany", "meckering", "roebourne",
           "kimberly", "wa", "pardoo", "moora", "toodyay"],
    "SA": ["south australia", "adelaide", "kangaroo island", "port lincoln",
           "eyre peninsula", "riverland", "mount gambier"],
    "TAS": ["tasmania", "tas", "hobart", "launceston", "devonport", "burnie"],
    "NT": ["northern territory", "darwin", "katherine", "alice springs", "groote", "arnhem",
           "tiwi", "nhulunbuy", "tennant creek", "kakadu"],
    "ACT": ["canberra", "australian capital territory"],  # not "act": too common a word
}


def postcode_to_state(postcode: int) -> str | None:
    """Map one Australian postcode to its state using Australia Post's numeric ranges."""
    if 200 <= postcode <= 299 or 2600 <= postcode <= 2618 or 2900 <= postcode <= 2920:
        return "ACT"
    if 800 <= postcode <= 999:
        return "NT"
    if 1000 <= postcode <= 2999:
        return "NSW"
    if 3000 <= postcode <= 3999 or 8000 <= postcode <= 8999:
        return "VIC"
    if 4000 <= postcode <= 4999 or 9000 <= postcode <= 9999:
        return "QLD"
    if 5000 <= postcode <= 5999:
        return "SA"
    if 6000 <= postcode <= 6999:
        return "WA"
    if 7000 <= postcode <= 7999:
        return "TAS"
    return None


def states_from_postcodes(value) -> set[str]:
    """Postcode cells hold comma-separated lists, e.g. '4000, 4005, 4006'."""
    if pd.isna(value):
        return set()
    postcodes = re.findall(r"\d{3,4}", str(value))
    return {postcode_to_state(int(p)) for p in postcodes} - {None}


def states_from_state_column(value) -> set[str]:
    """Standardise values such as 'FNQ', 'Vic', 'NSW, QLD' or 'NSW and SEQ'."""
    if pd.isna(value):
        return set()
    parts = re.split(r",|\band\b", str(value))
    return {STATE_CODES.get(p.strip().upper()) for p in parts} - {None}


def states_from_text(text) -> set[str]:
    """Find states whose place names appear as whole words in the text."""
    if pd.isna(text):
        return set()
    text = str(text).lower()
    found = set()
    for state, places in PLACE_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(place)}\b", text) for place in places):
            found.add(state)
    return found


def assign_states(events: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Add `states` (sorted, '|'-separated), `state_group` and `state_source` columns."""
    override_map = dict(zip(overrides["event_id"], overrides["states"]))

    def resolve(row):
        if row["event_id"] in override_map:
            return set(override_map[row["event_id"]].split("|")), "manual"
        name_town = " ".join(str(row[c]) for c in ["event_name", "town"] if pd.notna(row[c]))
        candidates = [
            (states_from_postcodes(row["postcode"]), "postcode"),
            (states_from_state_column(row["state_raw"]), "state_column"),
            (states_from_text(name_town), "name_or_town"),
            (states_from_text(row["description"]), "description"),
        ]
        for states, source in candidates:
            if states:
                return states, source
        return set(), "unresolved"

    resolved = events.apply(resolve, axis=1)
    events = events.copy()
    events["states"] = resolved.map(lambda r: "|".join(sorted(r[0])) or None)
    events["state_source"] = resolved.map(lambda r: r[1])
    events["state_group"] = resolved.map(
        lambda r: next(iter(r[0])) if len(r[0]) == 1 else ("Multi-state" if r[0] else "Unknown")
    )
    return events


if __name__ == "__main__":
    # Quick checks with known answers
    print(states_from_postcodes("4000, 4005, 2000"))      # expect {'QLD', 'NSW'}
    print(states_from_postcodes("6084, 7000"))            # expect {'WA', 'TAS'}
    print(states_from_state_column("NSW and SEQ"))        # expect {'NSW', 'QLD'}
    print(states_from_text("Hailstorm hit Sydney's east"))  # expect {'NSW'}
    print(states_from_text("Insurers had to act quickly"))  # expect set()