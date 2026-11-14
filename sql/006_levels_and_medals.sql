-- App levels, exams, tasting sheets and medals. Safe to run more than once.
--
-- Level 1 medal = pass the Level 1 exam + 6 complete tasting sheets.
-- Level 2 medal = pass the Level 2 exam + 5 distinct label tasks answered correctly.
-- Bonus medals come from reading optional Bonus articles (not graded).

-- One exam sitting. Questions are fixed at start, graded at submit.
CREATE TABLE IF NOT EXISTS exam_attempts (
    id           BIGSERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL,
    app_level    SMALLINT NOT NULL,
    question_ids BIGINT[] NOT NULL,
    answers      JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {"<question_id>": "B", ...}
    score        INT,
    total        INT NOT NULL,
    passed       BOOLEAN,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS exam_attempts_user_idx ON exam_attempts (user_id, app_level);

-- The four-line tasting sheet. "complete" follows the palate standard:
-- all four lines written, and the palate line names a structure word
-- together with the sensation it refers to (or fills in "because").
CREATE TABLE IF NOT EXISTS tasting_sheets (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    wine_name       TEXT NOT NULL DEFAULT '',
    appearance      TEXT NOT NULL DEFAULT '',
    nose            TEXT NOT NULL DEFAULT '',
    palate          TEXT NOT NULL DEFAULT '',
    palate_because  TEXT NOT NULL DEFAULT '',
    liking          TEXT NOT NULL DEFAULT '',
    structure_words TEXT[] NOT NULL DEFAULT '{}',
    complete        BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tasting_sheets_user_idx ON tasting_sheets (user_id, created_at);

-- Label-reading tasks for the Level 2 medal. task_id is a label quiz id
-- ("label_1".."label_5") or "q<quiz_question_id>" for bank label questions.
CREATE TABLE IF NOT EXISTS label_task_attempts (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL,
    task_id    TEXT NOT NULL,
    correct    BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS label_task_attempts_user_idx ON label_task_attempts (user_id);

-- Medals already awarded: 'level1', 'level2', or 'bonus:<article id>'.
CREATE TABLE IF NOT EXISTS medals (
    user_id    TEXT NOT NULL,
    medal_id   TEXT NOT NULL,
    awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, medal_id)
);

-- Optional Bonus reading (WSET Level 3/4 direction). Not graded.
CREATE TABLE IF NOT EXISTS bonus_reads (
    user_id    TEXT NOT NULL,
    article_id BIGINT NOT NULL REFERENCES articles(id),
    read_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, article_id)
);

-- Bonus articles. Interest content beyond Level 2; marked as still growing in the app.
INSERT INTO articles (title, category, content, image, topics)
SELECT v.title, 'Bonus', v.content, v.image, v.topics
FROM (VALUES
  ('Terroir: why the place shows up in the glass',
   'Terroir is the French word for everything about a place that shapes its grapes: climate, soil, slope, which way the vineyard faces, and nearby water. A cool site ripens grapes slowly, so the wine keeps more acidity and usually feels lighter. A warm site brings riper fruit, more sugar and so more alcohol and body. This is why the same grape, say Chardonnay, can taste lean and citrusy in Chablis and round and tropical in a warmer region. When people say a wine "tastes of its place", this is what they mean.',
   '/media/bordeaux.jpg', ARRAY['acidity','body','quality']::text[]),
  ('How wine changes as it ages in the bottle',
   'Most wines are made to be drunk young, while their fruit is fresh. A smaller group, often with high tannin or high acidity, can improve with years in the bottle. As they age, tannins soften so the wine feels smoother, fresh fruit turns into dried fruit, and new aromas appear: leather, earth and mushroom in reds; honey, nuts and toast in whites. Colour changes too: reds fade from purple towards garnet and brick, whites deepen towards gold. Older is not automatically better; it depends on whether the wine had the structure to age.',
   '/media/red-glass.jpg', ARRAY['tannin','aroma','finish']::text[]),
  ('Blind tasting: what the advanced levels test',
   'From WSET Level 3 upwards, exams include blind tasting: you get a glass without the label and describe it step by step, then judge its quality and whether it is ready to drink or could age. It is the same habit as the four-line sheet in this app, done in more detail and under time pressure. You do not need it to enjoy wine or to join a conversation at dinner. It is here for anyone curious about where the professional path goes next.',
   '/media/tasting.jpg', ARRAY['tasting','quality']::text[])
) AS v(title, content, image, topics)
WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.title = v.title);
