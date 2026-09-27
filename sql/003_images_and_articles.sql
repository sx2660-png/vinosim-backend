-- Photos and longer study notes. Safe to run more than once.
-- Does not re-insert the original quiz or article rows.

ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS image TEXT NOT NULL DEFAULT '';

UPDATE articles SET
  image = '/media/tasting.jpg',
  content = $c$
A tasting is a sequence, not a guess. Hold the glass against something pale and name what you see: purple at the rim usually means a young red, brick means it has aged. Then smell, before a swirl and after. Swirling lifts aroma off the surface.

On the palate, check four things. Acidity makes your mouth water. Tannin dries your gums. Alcohol feels warm. Body is the weight of the wine, from skim milk to cream. The finish is how long the flavor stays after you swallow.

The conclusion is one sentence that ties those notes together: which grape, which kind of place, and whether the wine is ready to drink.
$c$
WHERE title = 'The Art of Wine Tasting';

UPDATE articles SET
  image = '/media/bordeaux.jpg',
  content = $c$
Bordeaux is a blend region shaped by two banks of the Gironde. The Left Bank, including the Médoc, sits on gravel and is led by Cabernet Sauvignon: dark, firm, and built to age. The Right Bank, Saint-Émilion and Pomerol, sits on clay and limestone and leans on Merlot: rounder, and often ready sooner.

A classic red mixes Cabernet Sauvignon, Merlot, and Cabernet Franc so no single grape has to do every job. Village names such as Margaux, Pauillac, Saint-Julien, and Saint-Estèphe are places, not grapes. "Grand Cru Classé" on a Médoc label points to the 1855 ranking of estates. It does not tell you the grape.
$c$
WHERE title = 'Understanding Bordeaux';

UPDATE articles SET
  image = '/media/orange-glass.jpg',
  content = $c$
Natural wine is a way of working, not a legal grade. The fruit is farmed with little or no synthetic spray. Fermentation usually starts from yeasts that arrived on the grapes. The cellar adds little, and some bottles get no sulfur at all.

What reaches the glass can be less polished: a haze, a cider-like edge, or a flavor that sits outside the textbook. Orange wine often shows up in the same conversation, but it is a method of its own. White grapes are fermented on their skins, the way red wine is, and the wine turns amber.

The argument is about intervention. One side wants the cellar quiet. The other wants the bottle stable on a shop shelf. Both can make something worth drinking.
$c$
WHERE title = 'Natural Wine Movement';

UPDATE articles SET
  image = '/media/sangiovese.jpg',
  content = $c$
Sangiovese is the red grape of Tuscany. It runs high in acid, with sour cherry, dried herbs, and a savory edge, rather than sweet jam. Chianti Classico is the hill country between Florence and Siena. The black rooster on the neck marks that zone, and the wine has to be mostly Sangiovese.

Further south, the same grape grown ripe around Montalcino becomes Brunello: darker, more tannic, and meant to wait. A glass that feels sharp and savory, not soft and sweet, is Sangiovese doing what it does.
$c$
WHERE title = 'Tuscany & Sangiovese';

INSERT INTO articles (title, category, content, image)
SELECT 'Reading a Pinot Noir label', 'Term', $c$
The largest words on a label are not always the place. On this bottle the producer is Nelson Hill. Pinot Noir, the grape, is written in script underneath. Anderson Valley is the appellation, a cool stretch of Mendocino County, California. The year 2013 is the vintage: the year those grapes were picked.

Read a label as four separate facts. Who made it. Which grape. Where it grew. Which year. The drawing of a vat is a trademark. It is not one of those four facts.
$c$, '/media/nelson-hill.jpg'
WHERE NOT EXISTS (SELECT 1 FROM articles WHERE title = 'Reading a Pinot Noir label');

INSERT INTO articles (title, category, content, image)
SELECT 'Reading a Margaux label', 'Region', $c$
Château Marquis d'Alesme is the producer. Margaux, set under the château name, is a village on Bordeaux's Left Bank. The vintage printed here is 2012. "Grand Cru Classé" means the estate sits on the 1855 list of Médoc châteaux. It is a rank, not a grape and not a village.

A red from Margaux is almost always a Cabernet-led blend. The engraving of the house is a trademark. Read the place name and the classification before you read the picture.
$c$, '/media/marquis-alesme.jpg'
WHERE NOT EXISTS (SELECT 1 FROM articles WHERE title = 'Reading a Margaux label');

UPDATE quiz_questions SET image = '/media/pinot.jpg'
WHERE question = 'Which grape is the primary variety of Burgundy''s red wines?';

UPDATE quiz_questions SET image = '/media/red-glass.jpg'
WHERE question = 'What sensation do tannins create in the mouth?';

UPDATE quiz_questions SET image = '/media/orange.jpg'
WHERE question = 'Orange wine is produced by...';

UPDATE quiz_questions SET image = '/media/chianti.jpg'
WHERE question = 'Chianti Classico comes from which Italian region?';

UPDATE quiz_questions SET image = '/media/tasting.jpg'
WHERE question = 'Which term describes a wine''s perceived weight on the palate?';

INSERT INTO quiz_questions (question, options, correct_answer, explanation, category, image)
SELECT
  'Which grape variety is named on this label?',
  '["A. Cabernet Sauvignon", "B. Pinot Noir", "C. Merlot", "D. Sangiovese"]',
  'B',
  'The script under Nelson Hill reads Pinot Noir. Anderson Valley is the place, not the grape.',
  'label',
  '/media/nelson-hill.jpg'
WHERE NOT EXISTS (
  SELECT 1 FROM quiz_questions WHERE question = 'Which grape variety is named on this label?'
);

INSERT INTO quiz_questions (question, options, correct_answer, explanation, category, image)
SELECT
  'Which appellation is printed on this label?',
  '["A. Pauillac", "B. Pomerol", "C. Margaux", "D. Saint-Émilion"]',
  'C',
  'Margaux is the village under the château name. Grand Cru Classé is a ranking, not the place.',
  'label',
  '/media/marquis-alesme.jpg'
WHERE NOT EXISTS (
  SELECT 1 FROM quiz_questions WHERE question = 'Which appellation is printed on this label?'
);
