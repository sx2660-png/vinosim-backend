-- Learner preference distilled after each tutor turn, plus topic tags for article ranking.
-- Safe to run more than once.

CREATE TABLE IF NOT EXISTS learner_profiles (
    user_id          TEXT PRIMARY KEY,
    weak_topics      JSONB NOT NULL DEFAULT '{}'::jsonb,
    mentioned_topics JSONB NOT NULL DEFAULT '{}'::jsonb,
    summaries        JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE articles ADD COLUMN IF NOT EXISTS topics TEXT[] NOT NULL DEFAULT '{}';

UPDATE articles SET topics = ARRAY['tasting','appearance','nose','palate','finish','acidity','tannin','body']
WHERE title = 'The Art of Wine Tasting';

UPDATE articles SET topics = ARRAY['bordeaux','cabernet','merlot']
WHERE title = 'Understanding Bordeaux';

UPDATE articles SET topics = ARRAY['natural','orange']
WHERE title = 'Natural Wine Movement';

UPDATE articles SET topics = ARRAY['sangiovese','tuscany','acidity','tannin']
WHERE title = 'Tuscany & Sangiovese';

UPDATE articles SET topics = ARRAY['label','pinot']
WHERE title = 'Reading a Pinot Noir label';

UPDATE articles SET topics = ARRAY['label','bordeaux','cabernet']
WHERE title = 'Reading a Margaux label';

INSERT INTO articles (title, category, content, image, topics)
SELECT 'Judging whether a wine is any good', 'Term', $c$
A quality note is not a score. After you have looked, smelled, and tasted, ask four questions. Is it balanced, or is alcohol, acid, tannin, or fruit shouting over the rest? How intense is the flavor? How many separate things can you name? How long does flavor stay after you swallow?

A simple wine can still be pleasant. Typicity is a separate question: does it taste like its grape and place, or could it be any red. Write the judgment in one sentence, and keep the number off the page until you can say why.
$c$, '', ARRAY['quality','balance','finish','tasting','palate']
WHERE NOT EXISTS (SELECT 1 FROM articles WHERE title = 'Judging whether a wine is any good');

INSERT INTO articles (title, category, content, image, topics)
SELECT 'Naming what you smell', 'Term', $c$
Start with the family, not the perfect noun. Fresh grass, leaf, or green pepper is the herbaceous family. Jam, baked berry, or raisin is ripe or dried fruit, not a fresh berry. Vanilla, toast, cedar, and pencil shavings usually point at oak, or at the cedar-and-graphite side of Cabernet.

Say the family out loud first. The specific word can come later. If you cannot place it, say what it is not. That is still a tasting note.
$c$, '', ARRAY['aroma','nose','tasting','cabernet']
WHERE NOT EXISTS (SELECT 1 FROM articles WHERE title = 'Naming what you smell');
