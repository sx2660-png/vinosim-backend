-- Seed data for quiz + articles. wine_docs are seeded separately by scripts/ingest.py
-- (they need embeddings computed via the Gemini API).

INSERT INTO quiz_questions (question, options, correct_answer, explanation, category) VALUES
('Which grape is the primary variety of Burgundy''s red wines?',
 '["A. Cabernet Sauvignon", "B. Pinot Noir", "C. Merlot", "D. Syrah"]',
 'B', 'Red Burgundy is made almost entirely from Pinot Noir.', 'region'),
('What sensation do tannins create in the mouth?',
 '["A. Sweetness", "B. Fizziness", "C. Drying / astringency", "D. Saltiness"]',
 'C', 'Tannins bind to saliva proteins and create a drying, astringent feel.', 'term'),
('Orange wine is produced by...',
 '["A. Adding orange peel", "B. Skin contact on white grapes", "C. Blending red and white", "D. Oxidising rose"]',
 'B', 'Orange (amber) wine is a white wine fermented with extended skin contact.', 'style'),
('Chianti Classico comes from which Italian region?',
 '["A. Piedmont", "B. Veneto", "C. Tuscany", "D. Sicily"]',
 'C', 'Chianti Classico is in Tuscany, based on the Sangiovese grape.', 'region'),
('Which term describes a wine''s perceived weight on the palate?',
 '["A. Acidity", "B. Body", "C. Finish", "D. Bouquet"]',
 'B', 'Body refers to the perceived weight/fullness of the wine in the mouth.', 'term');

INSERT INTO articles (title, category, content, image) VALUES
('The Art of Wine Tasting', 'Term',
 'A systematic tasting looks at Appearance, Nose, Palate and Conclusion. Learn to read structure: acidity, tannin, alcohol, body and finish.', ''),
('Understanding Bordeaux', 'Region',
 'Left Bank (Cabernet-dominant, gravel soils) versus Right Bank (Merlot-dominant, clay/limestone). The classic Bordeaux blend and why it ages.', ''),
('Natural Wine Movement', 'New',
 'Minimal-intervention winemaking: organic farming, native yeasts, little or no added sulfites. What changes in the glass and why it divides drinkers.', ''),
('Tuscany & Sangiovese', 'Region',
 'From Chianti Classico to Brunello di Montalcino: the heart of Italian red wine and its high-acid, savoury signature grape.', '');
