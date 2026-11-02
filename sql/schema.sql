-- SQLite schema for the ICA catastrophe loss analysis

DROP TABLE IF EXISTS event_states;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS cpi;

-- One row per catastrophe event
CREATE TABLE events (
    event_id               TEXT PRIMARY KEY,  -- ICA code (e.g. CAT264) or UND-<date>-<n>
    event_name             TEXT,
    peril                  TEXT NOT NULL,     -- Cyclone, Storm, Flood, Bushfire, Hail, Earthquake
    event_category         TEXT NOT NULL,     -- Declared CAT, Significant event, Undeclared
    event_start            TEXT NOT NULL,     -- ISO date
    event_finish           TEXT,
    year                   INTEGER NOT NULL,
    financial_year         TEXT NOT NULL,     -- Australian FY, e.g. FY2026
    decade                 INTEGER NOT NULL,
    state_group            TEXT NOT NULL,     -- single state, 'Multi-state' or 'Unknown'
    state_source           TEXT NOT NULL,     -- how the state was derived
    has_loss               INTEGER NOT NULL CHECK (has_loss IN (0, 1)),
    original_loss          REAL,              -- AUD, as reported at the time
    cpi_adjusted_loss_2022 REAL,              -- AUD, 2022 prices (inflation only)
    normalised_loss_2022   REAL,              -- AUD, ICA normalised to 2022 (inflation + exposure)
    total_claims           REAL
);

-- Bridge table: an event can affect several states, and a state has many events
CREATE TABLE event_states (
    event_id TEXT NOT NULL REFERENCES events (event_id),
    state    TEXT NOT NULL,
    PRIMARY KEY (event_id, state)
);

-- Quarterly All Groups CPI (ABS, via RBA G1)
CREATE TABLE cpi (
    quarter_end TEXT PRIMARY KEY,
    cpi         REAL NOT NULL
);