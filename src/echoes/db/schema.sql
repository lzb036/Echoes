CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY,
    term TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    phonetic TEXT NOT NULL DEFAULT '',
    example TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY,
    word_id INTEGER NOT NULL,
    card_type TEXT NOT NULL,
    pass_count INTEGER NOT NULL DEFAULT 0,
    next_review_turn INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_word_type
ON cards(word_id, card_type);

CREATE INDEX IF NOT EXISTS idx_cards_completion
ON cards(completed_at, next_review_turn, pass_count, id);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL,
    elapsed_ms INTEGER,
    pass_count_before INTEGER NOT NULL,
    pass_count_after INTEGER NOT NULL,
    review_turn INTEGER NOT NULL,
    next_review_turn INTEGER,
    is_manual INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviews_card_time
ON reviews(card_id, reviewed_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
