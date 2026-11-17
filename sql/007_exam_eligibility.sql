-- Which questions may appear in a level exam. Practice can still use all of them.
-- Safe to run more than once.
ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS exam_eligible BOOLEAN NOT NULL DEFAULT true;

-- Orange wine is outside the WSET Level 1/2 ranges: keep it for practice only.
UPDATE quiz_questions SET exam_eligible = false
WHERE question = 'Orange wine is produced by...';
