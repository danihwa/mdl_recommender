CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS dramas (
    id              SERIAL PRIMARY KEY,
    mdl_id          INTEGER UNIQUE NOT NULL,
    mdl_url         TEXT NOT NULL,
    title           TEXT NOT NULL,
    native_title    TEXT,
    synopsis        TEXT,
    country         TEXT,
    episodes        INTEGER,
    content_rating  TEXT,
    network         TEXT,
    year            INTEGER,
    genres          TEXT[],
    tags            TEXT[],
    mdl_score       NUMERIC(3,1),
    watchers        INTEGER,
    embedding       vector(1536),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dramas_mdl_id ON dramas(mdl_id);
CREATE INDEX IF NOT EXISTS idx_dramas_score ON dramas(mdl_score DESC);
CREATE INDEX IF NOT EXISTS idx_dramas_tags ON dramas USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_dramas_genres ON dramas USING GIN(genres);