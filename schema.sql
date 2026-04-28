DROP TABLE IF EXISTS skin_pack_tags;
DROP TABLE IF EXISTS downloads;
DROP TABLE IF EXISTS skin_packs;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS compatibility_versions;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS creators;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'viewer'))
);

CREATE TABLE creators (
    creator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_name TEXT NOT NULL UNIQUE,
    platform_name TEXT NOT NULL,
    country_name TEXT NOT NULL
);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    mood_style TEXT NOT NULL
);

CREATE TABLE compatibility_versions (
    compatibility_id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_name TEXT NOT NULL UNIQUE,
    base_game_required INTEGER NOT NULL CHECK (base_game_required IN (0, 1))
);

CREATE TABLE skin_packs (
    pack_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_name TEXT NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    compatibility_id INTEGER NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    release_date TEXT NOT NULL,
    description TEXT NOT NULL,
    is_default INTEGER NOT NULL CHECK (is_default IN (0, 1)),
    FOREIGN KEY (creator_id) REFERENCES creators (creator_id),
    FOREIGN KEY (category_id) REFERENCES categories (category_id),
    FOREIGN KEY (compatibility_id) REFERENCES compatibility_versions (compatibility_id)
);

CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL UNIQUE
);

CREATE TABLE skin_pack_tags (
    pack_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (pack_id, tag_id),
    FOREIGN KEY (pack_id) REFERENCES skin_packs (pack_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (tag_id) ON DELETE CASCADE
);

CREATE TABLE downloads (
    download_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id INTEGER NOT NULL,
    download_month TEXT NOT NULL,
    download_count INTEGER NOT NULL CHECK (download_count >= 0),
    FOREIGN KEY (pack_id) REFERENCES skin_packs (pack_id) ON DELETE CASCADE
);

INSERT INTO creators (creator_name, platform_name, country_name) VALUES
('Luna Sims Studio', 'Patreon', 'United States'),
('Maple Pixel', 'Tumblr', 'Canada'),
('Sunberry CC', 'CurseForge', 'United Kingdom'),
('Velvet Mod House', 'Patreon', 'South Korea');

INSERT INTO categories (category_name, mood_style) VALUES
('Maxis Match', 'Soft and cartoony'),
('Alpha', 'Realistic and glossy'),
('Fantasy', 'Ethereal and dramatic'),
('Everyday', 'Natural and wearable');

INSERT INTO compatibility_versions (version_name, base_game_required) VALUES
('Patch 1.109', 1),
('Patch 1.108', 1),
('Patch 1.107', 1);

INSERT INTO tags (tag_name) VALUES
('freckles'),
('melanin'),
('overlay'),
('default replacement'),
('non-default'),
('face details');

INSERT INTO skin_packs
(pack_name, creator_id, category_id, compatibility_id, price, release_date, description, is_default) VALUES
('Honey Glow Collection', 1, 4, 1, 0.00, '2025-10-12', 'Warm-toned skin overlays for everyday gameplay.', 0),
('Moonlit Realism Pack', 2, 2, 1, 3.99, '2026-01-18', 'Alpha-style skin set with detailed highlights and pores.', 0),
('Fawn Dust Defaults', 3, 1, 2, 1.99, '2025-11-03', 'Default replacement skin with a softer Maxis Match finish.', 1),
('Stardrop Fantasy Blend', 4, 3, 3, 2.49, '2025-08-27', 'Fantasy skin pack designed for occult and storytelling saves.', 0);

INSERT INTO skin_pack_tags (pack_id, tag_id) VALUES
(1, 2),
(1, 5),
(2, 3),
(2, 6),
(3, 4),
(4, 1),
(4, 3);

INSERT INTO downloads (pack_id, download_month, download_count) VALUES
(1, '2026-01', 220),
(1, '2026-02', 250),
(2, '2026-01', 310),
(2, '2026-02', 280),
(3, '2026-01', 400),
(3, '2026-02', 420),
(4, '2026-01', 180),
(4, '2026-02', 205);
