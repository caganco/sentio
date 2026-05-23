CREATE TABLE IF NOT EXISTS macro_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL    NOT NULL,
    volume      INTEGER DEFAULT 0,
    updated_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_macro_date   ON macro_data(date);
CREATE INDEX IF NOT EXISTS idx_macro_symbol ON macro_data(symbol);
CREATE INDEX IF NOT EXISTS idx_macro_ds     ON macro_data(date, symbol);
