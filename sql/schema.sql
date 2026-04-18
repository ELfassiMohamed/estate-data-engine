CREATE TABLE IF NOT EXISTS listings (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    source TEXT NOT NULL CHECK (source IN ('avito', 'mubawab')),
    url TEXT NOT NULL,
    type_bien TEXT,
    city TEXT,
    price NUMERIC(14,2),
    surface NUMERIC(10,2),
    description TEXT,
    contact_info TEXT,
    date_publication TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_listings_source ON listings (source);
CREATE INDEX IF NOT EXISTS idx_listings_scraped_at ON listings (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_city ON listings (city);
CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_url_unique ON listings (url);

