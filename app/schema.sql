CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    domain      TEXT NOT NULL UNIQUE,
    orientation TEXT NOT NULL CHECK (orientation IN ('left', 'center', 'right'))
);

CREATE TABLE IF NOT EXISTS stories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,
    summary    TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           INTEGER NOT NULL REFERENCES sources (id),
    story_id            INTEGER REFERENCES stories (id),
    url                 TEXT NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    published_at        TIMESTAMP,
    body                TEXT,
    snippet             TEXT,
    embedding           BLOB,
    sentiment_score     REAL,
    sentiment_magnitude REAL,
    fetched_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_ideology_aggregates (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id       INTEGER NOT NULL REFERENCES stories (id),
    orientation    TEXT NOT NULL CHECK (orientation IN ('left', 'center', 'right')),
    coverage_count INTEGER NOT NULL DEFAULT 0,
    avg_sentiment  REAL,
    framing        TEXT,
    UNIQUE (story_id, orientation)
);

CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles (source_id);
CREATE INDEX IF NOT EXISTS idx_articles_story_id ON articles (story_id);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at);
