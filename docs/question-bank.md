# VinoSim question bank (Level 1 and Level 2)

Source of truth: `sql/005_level_question_bank.sql`. This document lists the content for review.

## 1. What 005 adds, and how to apply it

- Four new tag columns on `quiz_questions`: `app_level` (1 or 2), `wset_ref` (e.g. `L1-LO2`), `sheet_line` (`appearance`, `nose`, `palate`, `like`, `context`, `none`) and `item_type` (`sensation`, `cause`, `knowledge`, `label`, `service`, `pairing`).
- Tags for the 7 existing questions from 002 and 003, matched by exact question text.
- **63 new Level 1** and **90 new Level 2** graded multiple-choice questions, in the same format as the existing rows (options `"A. ..."` to `"D. ..."`, `correct_answer` is the letter, `image = ''`). Totals including the re-tagged rows: Level 1 = 65, Level 2 = 95.
- A new `tasting_prompts` table with 10 open, ungraded prompts (no correct answer, so they are kept out of `quiz_questions`).
- A new `level_exams` table holding per-level exam settings (provisional, see section 4).

The file is wrapped in a transaction and is idempotent: columns use `ADD COLUMN IF NOT EXISTS`, question inserts are guarded by `WHERE NOT EXISTS` on the question text, prompts use `ON CONFLICT (prompt) DO NOTHING`, and exam rows use `ON CONFLICT (app_level) DO NOTHING`. Running it twice leaves row counts unchanged.

Apply after 001 to 004:

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
psql -d vinosim -v ON_ERROR_STOP=1 -f sql/005_level_question_bank.sql
```

`scripts/setup_db.sh` was not changed: it applies 001, 002 and 004 only, so it will not apply 005 (or 003) on its own. If you apply 005 as your own superuser account, the two new tables will belong to that account, so re-grant to the app role afterwards:

```bash
psql -d vinosim -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO vinosim; GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO vinosim;"
```

**Note for the app:** the current quiz endpoints pick a random row from the whole `quiz_questions` table. After 005 they will mix Level 1 and Level 2 questions until the query filters on `app_level` (e.g. `WHERE app_level = %s`). Every row is still a gradable single-answer MCQ, so nothing breaks in the meantime.

## 2. Counts compared with the WSET exam weighting

Weighting sources:
- **Level 1**: WSET Level 1 Award in Wines Specification, Issue 1.2 (2022), section 4 "Examination Guidance", examination weighting chart: LO1 = 6, LO2 = 18, LO3 = 6 of 30 questions.
- **Level 2**: WSET Level 2 Award in Wines Specification, Issue 2 (2023), section 4 "Examination Guidance", examination weighting chart: LO1 = 5, LO2 = 4, LO3 = 19, LO4 = 12, LO5 = 6, LO6 = 4 of 50 questions.

Counts below include the 7 re-tagged existing questions.

### Level 1: learning outcome x item_type

| wset_ref | sensation | cause | knowledge | label | service | pairing | total | share of pool | WSET exam share |
|---|---|---|---|---|---|---|---|---|---|
| L1-LO1 | 0 | 5 | 8 | 0 | 0 | 0 | 13 | 20% | 20% (6/30) |
| L1-LO2 | 12 | 5 | 21 | 0 | 0 | 0 | 38 | 58% | 60% (18/30) |
| L1-LO3 | 0 | 3 | 0 | 0 | 7 | 4 | 14 | 22% | 20% (6/30) |
| **total** | 12 | 13 | 29 | 0 | 7 | 4 | 65 | 100% | 100% |

### Level 2: learning outcome x item_type

| wset_ref | sensation | cause | knowledge | label | service | pairing | total | share of pool | WSET exam share |
|---|---|---|---|---|---|---|---|---|---|
| L2-LO1 | 0 | 3 | 2 | 6 | 0 | 0 | 11 | 12% | 10% (5/50) |
| L2-LO2 | 0 | 7 | 3 | 0 | 0 | 0 | 10 | 11% | 8% (4/50) |
| L2-LO3 | 0 | 4 | 22 | 8 | 0 | 0 | 34 | 36% | 38% (19/50) |
| L2-LO4 | 0 | 1 | 18 | 2 | 0 | 0 | 21 | 22% | 24% (12/50) |
| L2-LO5 | 0 | 2 | 7 | 3 | 0 | 0 | 12 | 13% | 12% (6/50) |
| L2-LO6 | 0 | 1 | 2 | 0 | 1 | 3 | 7 | 7% | 8% (4/50) |
| **total** | 0 | 18 | 54 | 19 | 1 | 3 | 95 | 100% | 100% |

### Level x sheet_line

| level | appearance | nose | palate | like | context | none | total |
|---|---|---|---|---|---|---|---|
| 1 | 3 | 6 | 29 | 0 | 7 | 20 | 65 |
| 2 | 4 | 12 | 18 | 0 | 52 | 9 | 95 |

`like` is 0 by design: "do you like it" has no right answer, so those items live in `tasting_prompts`.

Level 1 learning-goal check (new questions only): 10 `sensation` items, 3 of them about acidity; 13 `cause` items.

## 3. Correct-letter distribution

| level | A | B | C | D | total |
|---|---|---|---|---|---|
| 1 (all) | 16 | 17 | 17 | 15 | 65 |
| 2 (all) | 23 | 26 | 24 | 22 | 95 |
| 1 (new only) | 16 | 16 | 16 | 15 | 63 |
| 2 (new only) | 23 | 23 | 22 | 22 | 90 |

New questions rotate the correct answer through A, B, C, D in order; the existing rows are mostly B or C, which is why the combined counts lean slightly that way.

## 4. Exam settings (`level_exams`): PROVISIONAL, NOT FINAL

| app_level | question_count | pass_pct | time_limit_min |
|---|---|---|---|
| 1 | 30 | 70 | NULL (no limit) |
| 2 | 50 | 55 | NULL (no limit) |

These defaults copy the WSET exam formats (Level 1: 30 questions, pass at 70%, 45 minutes; Level 2: 50 questions, pass at 55%, 60 minutes). The time limit is left NULL because no decision has been made. **The user has not finalised any of these values.** They are inserted with `ON CONFLICT DO NOTHING`, so to change them later use an `UPDATE`, not a re-run of 005.

Pool size versus exam size: Level 1 has 65 questions for a 30-question exam, and Level 2 has 95 for a 50-question exam. To mirror the WSET weighting, draw per learning outcome (e.g. Level 1: 6 / 18 / 6) rather than uniformly at random.

## 5. Full question list

Format: question, then **correct answer**, then `item_type` / `sheet_line`. Rows marked *(existing)* come from 002 or 003 and are only re-tagged.

### Level 1

#### L1-LO1: Grape growing and winemaking

1. Which part of a black grape gives red wine its colour?  
   **A. The skin** · `knowledge` / `appearance`
2. What does the pulp of a grape mainly contain?  
   **B. Water, sugar and acid** · `knowledge` / `none`
3. Why do red wines have tannin while most white wines have very little?  
   **C. Red wine ferments together with the grape skins, which contain tannin** · `cause` / `palate`
4. Which two things are needed for alcoholic fermentation?  
   **D. Sugar and yeast** · `knowledge` / `none`
5. Where does the alcohol in wine come from?  
   **A. Yeast turning the sugar in grape juice into alcohol** · `cause` / `palate`
6. Besides alcohol, what else does alcoholic fermentation produce?  
   **B. Carbon dioxide** · `knowledge` / `none`
7. Why do wines from cool climates usually taste more acidic than wines from warm climates?  
   **C. Grapes ripen less in cool climates, so they keep more of their acid** · `cause` / `palate`
8. Why do wines from warm climates often have more alcohol?  
   **D. The grapes get riper and build up more sugar, which yeast turns into alcohol** · `cause` / `palate`
9. As grapes ripen on the vine, what happens to their sugar and acid?  
   **A. Sugar goes up and acid goes down** · `knowledge` / `palate`
10. In the vine's yearly cycle, which stage comes before the grapes form?  
   **B. Flowering** · `knowledge` / `none`
11. When making a white wine, when are the grapes pressed?  
   **C. Before fermentation** · `knowledge` / `none`
12. Which order of steps is correct for making a red wine?  
   **D. Crushing, fermentation, draining, pressing, maturation, bottling** · `knowledge` / `none`
13. Why is a rosé wine pink rather than deep red?  
   **A. The juice touches the black grape skins for only a short time** · `cause` / `appearance`

#### L1-LO2: Types, characteristics and styles; principal grapes; example wines

1. What sensation do tannins create in the mouth? *(existing)*  
   **C. Drying / astringency** · `sensation` / `palate`
2. Which term describes a wine's perceived weight on the palate? *(existing)*  
   **B. Body** · `sensation` / `palate`
3. Which feeling tells you a wine has high acidity?  
   **B. It makes your mouth water** · `sensation` / `palate`
4. A wine tastes fresh and sharp, like biting into a green apple. Which structural word fits best?  
   **C. Acidity** · `sensation` / `palate`
5. How does a wine with low acidity usually feel in the mouth?  
   **D. Soft, and sometimes a bit flat** · `sensation` / `palate`
6. You feel a warming or burning sensation at the back of your throat after swallowing. What does this point to?  
   **A. High alcohol** · `sensation` / `palate`
7. A wine smells of ripe fruit, but you cannot taste any sugar in it. How would you describe its sweetness?  
   **B. Dry** · `sensation` / `palate`
8. A wine tastes of honey and leaves a sugary, slightly sticky feel on your tongue. How would you describe its sweetness?  
   **C. Sweet** · `sensation` / `palate`
9. Which of these wines is most likely to leave your gums feeling strongly dry?  
   **D. A young Cabernet Sauvignon** · `sensation` / `palate`
10. A wine feels heavy and mouth-filling, like whole milk compared with skimmed milk. How would you describe it?  
   **A. Full-bodied** · `sensation` / `palate`
11. Which of these wines gives the strongest warming feeling from alcohol?  
   **B. Port** · `sensation` / `palate`
12. Which of these red wines is most likely to feel light-bodied?  
   **C. Beaujolais** · `sensation` / `palate`
13. Which of these usually makes a wine feel fuller in body?  
   **D. More alcohol** · `cause` / `palate`
14. Which of these is a white grape variety?  
   **A. Riesling** · `knowledge` / `none`
15. Syrah is the same black grape as which variety?  
   **B. Shiraz** · `knowledge` / `none`
16. Sancerre is a dry white wine made from which grape?  
   **C. Sauvignon Blanc** · `knowledge` / `context`
17. Chablis is made from which grape?  
   **D. Chardonnay** · `knowledge` / `context`
18. Red Bordeaux is usually made from...  
   **A. A blend of grapes such as Cabernet Sauvignon and Merlot** · `knowledge` / `context`
19. Cava is a sparkling wine from which country?  
   **B. Spain** · `knowledge` / `context`
20. Which of these is a sparkling wine?  
   **C. Champagne** · `knowledge` / `none`
21. Port and Sherry are both examples of which type of wine?  
   **D. Fortified** · `knowledge` / `none`
22. How is Sauternes best described?  
   **A. A sweet white wine** · `knowledge` / `context`
23. White Zinfandel is usually...  
   **B. A pink, medium-sweet wine** · `knowledge` / `appearance`
24. How is a typical Beaujolais described?  
   **C. A light, fruity red with low tannin** · `knowledge` / `palate`
25. Which of these is a red wine from Spain?  
   **D. Rioja** · `knowledge` / `context`
26. Châteauneuf-du-Pape is a red wine from which French region?  
   **A. The Rhône Valley** · `knowledge` / `context`
27. Which aromas are typical of Sauvignon Blanc?  
   **B. Green fruit and grassy, herbal notes** · `knowledge` / `nose`
28. Which fruit aroma is most typical of Cabernet Sauvignon?  
   **C. Blackcurrant** · `knowledge` / `nose`
29. Compared with Cabernet Sauvignon, Pinot Noir usually has...  
   **D. Lower tannin and a paler colour** · `knowledge` / `palate`
30. Which black grape is known for soft, plummy wines and is widely grown in Bordeaux?  
   **A. Merlot** · `knowledge` / `palate`
31. Where do vanilla and toast aromas in a wine usually come from?  
   **B. Oak barrels** · `cause` / `nose`
32. Riesling wines are known for...  
   **C. High acidity and floral, fruity aromas** · `knowledge` / `palate`
33. Pinot Grigio is most often made as...  
   **D. A light-bodied, dry white with delicate fruit** · `knowledge` / `palate`
34. Why can one Chardonnay taste of green apple while another tastes of pineapple?  
   **A. Climate: cool regions give green fruit, warm regions give riper tropical fruit** · `cause` / `nose`
35. Which flavours are typical of Syrah/Shiraz?  
   **B. Black fruit and black pepper** · `knowledge` / `nose`
36. What is a wine called when it has no bubbles and no added spirit?  
   **C. Still** · `knowledge` / `none`
37. Why does Port have more alcohol than most wines?  
   **D. Grape spirit is added to it** · `cause` / `palate`
38. In Champagne, Cava and Prosecco, where do the bubbles come from?  
   **A. Carbon dioxide made by yeast during fermentation, trapped in the wine** · `cause` / `palate`

#### L1-LO3: Storage, service and food

1. Why should bottles closed with a cork be stored lying on their side?  
   **B. It keeps the cork moist so it does not dry out and let air in** · `cause` / `none`
2. Which place is best for storing wine?  
   **C. A cool, dark place with a steady temperature** · `service` / `none`
3. How does a vacuum pump help keep an opened bottle of wine fresh?  
   **D. It removes air from the bottle** · `cause` / `none`
4. How does a "blanket" system preserve an opened bottle of wine?  
   **A. It lays a protective gas over the wine so air cannot reach it** · `service` / `none`
5. At what temperature should Champagne be served?  
   **B. Well chilled** · `service` / `none`
6. How should a full-bodied, oaked white Chardonnay be served?  
   **C. Lightly chilled** · `service` / `none`
7. How can a light-bodied red such as Beaujolais be served?  
   **D. Lightly chilled** · `service` / `none`
8. How should medium- and full-bodied reds such as Bordeaux be served?  
   **A. At room temperature** · `service` / `none`
9. What is the safe way to open a bottle of sparkling wine?  
   **B. Hold the cork, turn the bottle slowly, and point it away from people** · `service` / `none`
10. Why should you look at and smell a wine before serving it to a guest?  
   **C. To check that it is clean and not faulty** · `cause` / `nose`
11. Sweet food tends to make a dry wine taste...  
   **D. More acidic and bitter, and less fruity** · `pairing` / `palate`
12. Salty food tends to make a wine taste...  
   **A. Less bitter and less acidic** · `pairing` / `palate`
13. Food with high acidity, such as a lemony salad dressing, tends to make a wine taste...  
   **B. Less acidic and more fruity** · `pairing` / `palate`
14. What usually happens when a light, delicate wine is served with a strongly flavoured dish?  
   **C. The food overpowers the flavours of the wine** · `pairing` / `palate`

### Level 2

#### L2-LO1: Vineyard, environment and labelling terms for origin

1. What does the term véraison describe?  
   **A. The point when grapes change colour and begin to soften** · `knowledge` / `none`
2. In a cool Northern Hemisphere region, why are vineyards often planted on south-facing slopes?  
   **B. They get more sunlight, which helps the grapes ripen** · `cause` / `context`
3. How does planting a vineyard at high altitude usually affect it?  
   **C. It makes the vineyard cooler** · `cause` / `context`
4. Why is noble rot (botrytis) welcome in some vineyards?  
   **D. It draws water out of the grapes, concentrating their sugar and acid for sweet wine** · `cause` / `palate`
5. Icewine (Eiswein) is made from grapes that are...  
   **A. Picked and pressed while frozen on the vine** · `knowledge` / `context`
6. What does "Vieilles Vignes" mean on a French wine label?  
   **B. Old vines** · `label` / `context`
7. Which French label term is the equivalent of the EU category PGI (Protected Geographical Indication)?  
   **C. IGP** · `label` / `context`
8. Compared with a PGI wine, a PDO wine generally has...  
   **D. Stricter rules on area, grape varieties and winemaking** · `label` / `context`
9. Which Italian label term is the top quality category?  
   **A. DOCG** · `label` / `context`
10. Rioja carries which Spanish quality category, one level above DO?  
   **B. DOCa** · `label` / `context`
11. In Germany, what is Prädikatswein?  
   **C. A top quality category, graded by how ripe the grapes were at harvest** · `label` / `context`

#### L2-LO2: Winemaking and bottle ageing

1. Orange wine is produced by... *(existing)*  
   **B. Skin contact on white grapes** · `knowledge` / `appearance`
2. What does malolactic conversion do to a wine?  
   **D. It softens acidity by turning sharp malic acid into softer lactic acid** · `cause` / `palate`
3. What can leaving a white wine in contact with its lees (dead yeast cells) add?  
   **A. Bread or biscuit flavours and a creamier texture** · `cause` / `nose`
4. Compared with old, large oak barrels, new, small oak barrels give a wine...  
   **B. More oak flavour, such as vanilla and toast** · `cause` / `nose`
5. Why might a winemaker ferment a white wine in stainless steel?  
   **C. To keep fresh, fruity flavours with no oak influence** · `cause` / `nose`
6. How can a winemaker make a red wine with more colour and tannin?  
   **D. Increase extraction, for example by keeping the wine on its skins for longer** · `cause` / `palate`
7. Which is one way to make a sweet wine?  
   **A. Stop the fermentation before all the sugar has turned into alcohol** · `cause` / `palate`
8. As a red wine ages in the bottle, what usually happens to its colour?  
   **B. It becomes paler and turns from purple towards garnet and brown** · `knowledge` / `appearance`
9. With bottle age, the tannins in a red wine typically...  
   **C. Become softer** · `knowledge` / `palate`
10. Why do large wine brands blend wines from many vineyards and regions?  
   **D. To make a consistent style every year** · `cause` / `none`

#### L2-LO3: Principal grape varieties and their GIs

1. Which grape is the primary variety of Burgundy's red wines? *(existing)*  
   **B. Pinot Noir** · `knowledge` / `context`
2. Which grape variety is named on this label? *(existing)*  
   **B. Pinot Noir** · `label` / `context`
3. Which appellation is printed on this label? *(existing)*  
   **C. Margaux** · `label` / `context`
4. Pauillac and Margaux are known for red blends led by which grape?  
   **A. Cabernet Sauvignon** · `knowledge` / `context`
5. Saint-Émilion and Pomerol are known for red wines led by which grape?  
   **B. Merlot** · `knowledge` / `context`
6. Côte Rôtie and Hermitage are Northern Rhône wines made mainly from which grape?  
   **C. Syrah** · `knowledge` / `context`
7. Australia's Barossa Valley is famous for full-bodied, ripe wines from which grape?  
   **D. Shiraz** · `knowledge` / `context`
8. Central Otago and Martinborough in New Zealand are best known for which black grape?  
   **A. Pinot Noir** · `knowledge` / `context`
9. Puligny-Montrachet and Meursault are white Burgundies made from which grape?  
   **B. Chardonnay** · `knowledge` / `context`
10. A Marlborough Sauvignon Blanc typically shows...  
   **C. Pronounced green and tropical aromas, such as gooseberry and passion fruit, with high acidity** · `knowledge` / `nose`
11. Pouilly-Fumé, from the Loire Valley, is made from which grape?  
   **D. Sauvignon Blanc** · `knowledge` / `context`
12. The dry white wines of Graves and Pessac-Léognan often blend Sauvignon Blanc with which grape?  
   **A. Sémillon** · `knowledge` / `context`
13. A Riesling from Germany's Mosel is typically...  
   **B. Light-bodied with high acidity, often low in alcohol and sometimes off-dry** · `knowledge` / `palate`
14. Australia's Clare Valley and Eden Valley are best known for dry wines from which grape?  
   **C. Riesling** · `knowledge` / `context`
15. Why is Riesling rarely aged in new oak?  
   **D. Winemakers want to keep its pure fruit and floral aromas** · `cause` / `nose`
16. Which German Prädikat level is made from the ripest grapes?  
   **A. Trockenbeerenauslese (TBA)** · `label` / `context`
17. What does "Trocken" mean on a German wine label?  
   **B. Dry** · `label` / `context`
18. The German term Spätlese means...  
   **C. Late harvest** · `label` / `context`
19. The Rheingau and the Pfalz are wine regions in which country?  
   **D. Germany** · `knowledge` / `context`
20. In Burgundy, which term is given to the very best vineyards?  
   **A. Grand Cru** · `label` / `context`
21. Cru Bourgeois is a quality classification for châteaux in which part of Bordeaux?  
   **B. The Médoc** · `label` / `context`
22. Compared with a typical Italian Pinot Grigio, an Alsace Pinot Gris is usually...  
   **C. Fuller-bodied and riper, sometimes off-dry** · `knowledge` / `palate`
23. Friuli-Venezia Giulia and Delle Venezie, known for Pinot Grigio, are in which part of Italy?  
   **D. The north-east** · `knowledge` / `context`
24. Why is Cabernet Sauvignon mostly grown in moderate or warm climates?  
   **A. It ripens late and needs plenty of warmth to ripen fully** · `cause` / `nose`
25. Pinot Noir has thin skins. What effect does this have on its wines?  
   **B. They are usually paler in colour with low to medium tannin** · `cause` / `appearance`
26. As a good Pinot Noir ages in bottle, which aromas can it develop?  
   **C. Earthy and mushroom notes** · `knowledge` / `nose`
27. Compared with a Meursault, a typical Chablis is...  
   **D. Leaner, with higher acidity and less obvious oak** · `knowledge` / `palate`
28. Which of these is most likely to be a full-bodied Chardonnay with ripe tropical fruit and oak flavours?  
   **A. A Napa Valley Chardonnay** · `knowledge` / `palate`
29. Compared with a Barossa Valley Shiraz, a Northern Rhône Syrah such as Crozes-Hermitage is often...  
   **B. More peppery and savoury, and less jammy** · `knowledge` / `nose`
30. Why is Merlot often blended with Cabernet Sauvignon?  
   **C. Merlot adds soft, plummy fruit and body that round out Cabernet's firm tannin** · `cause` / `palate`
31. The Central Valley, a large source of fruity Merlot and Cabernet Sauvignon, is in which country?  
   **D. Chile** · `knowledge` / `context`
32. Coonawarra in South Australia is especially known for which grape?  
   **A. Cabernet Sauvignon** · `knowledge` / `context`
33. What does "Pays d'Oc" on a French label tell you?  
   **B. The wine is an IGP (PGI) wine from southern France** · `label` / `context`
34. Stellenbosch is a wine region in which country?  
   **C. South Africa** · `knowledge` / `context`

#### L2-LO4: Regionally important grape varieties

1. Chianti Classico comes from which Italian region? *(existing)*  
   **C. Tuscany** · `knowledge` / `context`
2. Beaujolais is made from which black grape?  
   **D. Gamay** · `knowledge` / `context`
3. Barolo and Barbaresco are made from which grape?  
   **A. Nebbiolo** · `knowledge` / `context`
4. Nebbiolo wines such as Barolo are typically...  
   **B. Fairly pale in colour but high in both tannin and acidity** · `knowledge` / `palate`
5. On a Rioja label, which term shows the longest ageing before release?  
   **C. Gran Reserva** · `label` / `context`
6. Ribera del Duero in Spain is known for red wines from which grape?  
   **D. Tempranillo** · `knowledge` / `context`
7. Which grape is the main variety in most red Châteauneuf-du-Pape?  
   **A. Grenache** · `knowledge` / `context`
8. Brunello di Montalcino is made from which grape?  
   **B. Sangiovese** · `knowledge` / `context`
9. Why is Amarone della Valpolicella so full-bodied and high in alcohol?  
   **C. The grapes are partly dried before fermentation, concentrating their sugar** · `cause` / `palate`
10. Malbec is the signature grape of which region?  
   **D. Mendoza, Argentina** · `knowledge` / `context`
11. Carmenère is especially associated with which country?  
   **A. Chile** · `knowledge` / `context`
12. Pinotage is a black grape most associated with which country?  
   **B. South Africa** · `knowledge` / `context`
13. Zinfandel (California) and Primitivo (Puglia) are...  
   **C. The same grape variety** · `knowledge` / `none`
14. Vouvray, from the Loire Valley, is made from which grape?  
   **D. Chenin Blanc** · `knowledge` / `context`
15. Condrieu, from the Northern Rhône, is made from which white grape?  
   **A. Viognier** · `knowledge` / `context`
16. Alsace Gewurztraminer is known for which aromas?  
   **B. Lychee, rose and sweet spice** · `knowledge` / `nose`
17. Rías Baixas in north-west Spain is known for which white grape?  
   **C. Albariño** · `knowledge` / `context`
18. Tokaji Aszú from Hungary is a sweet wine made mainly from which grape?  
   **D. Furmint** · `knowledge` / `context`
19. Gavi, from Piedmont, is made from which white grape?  
   **A. Cortese** · `knowledge` / `context`
20. Which white grape is the main variety in Sauternes?  
   **B. Sémillon** · `knowledge` / `context`
21. What does "Riserva" usually mean on an Italian label such as Chianti Classico Riserva?  
   **C. The wine was aged for longer before release** · `label` / `context`

#### L2-LO5: Sparkling and fortified wines

1. In Champagne, where does the second fermentation that creates the bubbles take place?  
   **D. In the bottle the wine is sold in** · `knowledge` / `none`
2. Prosecco is made mainly from which grape?  
   **A. Glera** · `knowledge` / `none`
3. For most Prosecco, where does the second fermentation take place?  
   **B. In a large sealed tank** · `knowledge` / `none`
4. Which three grapes are most used for Champagne?  
   **C. Chardonnay, Pinot Noir and Meunier** · `knowledge` / `none`
5. Where do the bread and biscuit flavours in Champagne come from?  
   **D. Long ageing in bottle on the lees (dead yeast) after the second fermentation** · `cause` / `nose`
6. What does "Brut" mean on a sparkling wine label?  
   **A. Dry** · `label` / `context`
7. Asti is best described as...  
   **B. A sweet, low-alcohol sparkling wine with grapey aromas** · `knowledge` / `palate`
8. Fino Sherry ages under a layer of yeast. What is this layer called?  
   **C. Flor** · `knowledge` / `nose`
9. Why is Port naturally sweet?  
   **D. Grape spirit is added during fermentation, which stops the yeast before all the sugar is used** · `cause` / `palate`
10. Which Port style is made from a single, excellent year and is meant to age for many years in bottle?  
   **A. Vintage Port** · `label` / `context`
11. What does "Cap Classique" on a South African label mean?  
   **B. A sparkling wine made by the traditional method** · `label` / `context`
12. Which method is used to make Cava?  
   **C. The traditional method, with a second fermentation in bottle** · `knowledge` / `none`

#### L2-LO6: Storage, service, faults and food pairing

1. Which fault makes a wine smell musty, like damp cardboard or a wet cellar?  
   **D. Cork taint** · `knowledge` / `nose`
2. A wine that has been damaged by heat often tastes...  
   **A. Cooked or stewed, with jammy fruit** · `knowledge` / `palate`
3. Why might you decant an old red wine?  
   **B. To separate the wine from its sediment** · `cause` / `appearance`
4. At what temperature should a light-bodied white such as Sancerre be served?  
   **C. Chilled** · `service` / `none`
5. Umami-rich food, such as mushrooms or aged cheese, tends to make a wine taste...  
   **D. More bitter and acidic, and less fruity** · `pairing` / `palate`
6. Which wine is the best match for a very sweet dessert?  
   **A. A wine that is at least as sweet as the dessert** · `pairing` / `palate`
7. Chilli heat in food tends to make a wine's alcohol feel...  
   **B. More burning** · `pairing` / `palate`

## 6. Tasting prompts (`tasting_prompts`, open and ungraded)

| # | level | sheet_line | prompt | example answers |
|---|---|---|---|---|
| 1 | 1 | appearance | Hold the glass against something white. What colour is the wine, and is it pale or deep? | pale lemon, gold, pink, salmon, purple, ruby, garnet |
| 2 | 1 | nose | Swirl the glass and take a sniff. Which fruit does this wine remind you of? | lemon, green apple, peach, pineapple, strawberry, cherry, blackcurrant, plum |
| 3 | 1 | nose | Does the fruit smell fresh and just-picked, ripe and juicy, or cooked and dried, like jam or raisins? | fresh, ripe, jammy, baked, dried, raisin |
| 4 | 1 | nose | Can you smell anything that is not fruit, such as flowers, herbs or spice? | rose, blossom, grass, mint, black pepper, clove |
| 5 | 1 | nose | Do you notice vanilla, toast, smoke or coconut? These often come from oak. | vanilla, toast, smoke, coconut, cedar, none |
| 6 | 1 | nose | How strong is the smell: faint, medium, or jumping out of the glass? | faint, medium, strong, pronounced |
| 7 | 1 | nose | Does this wine remind you of a food, a place, or a memory? | apple pie, a summer garden, a forest walk, a bakery, a spice rack |
| 8 | 1 | palate | Take a sip. What is the first thing you notice: fruit, sharpness, dryness on the gums, warmth or sweetness? | fruit, sharp, drying, warming, sweet, smooth |
| 9 | 1 | like | Do you like this wine? Say why or why not in one sentence. | I like how fresh it is, too sharp for me, too dry on my gums, nice and fruity, too strong |
| 10 | 1 | like | Would you drink this wine again? When, and with what food? | with pizza, on a hot day, with cheese, with dessert, not again |

By sheet_line: appearance 1, nose 6, palate 1, like 2. Every prompt's `guidance` opens with "There is no wrong answer" and lists descriptors people commonly use.

## 7. Flagged / left out

Written or considered, then left out (not inserted):
- **Where on the tongue acidity or sweetness is felt.** Relies on the "tongue map", which is a myth. Acidity items use the mouth-watering effect instead.
- **"White wines are fermented at lower temperatures than reds"**, **"Which best describes a Tawny Port?"**, **"Service temperature for a sweet wine"**, **"Which wine is fortified? (Port)"**, **"Chablis is a dry white"**, **umami true/false at Level 1.** These are the WSET specs' own published sample questions, so they were left out to avoid near-copies. Related facts are covered from other angles (e.g. Port fortification and sweetness, umami at Level 2).
- **Montepulciano d'Abruzzo vs Vino Nobile di Montepulciano.** Grape vs Tuscan town confusion is too easy to word ambiguously at this level.
- **Effect of fat in food on wine.** In the spec's range, but the effect is not stated simply enough in beginner materials to write one unambiguous answer.
- **Priorat as DOCa.** Priorat's status is usually written DOQ (Catalan), so the DOCa question names only Rioja.
- **Hunter Valley Semillon style, Barbera, Soave/Garganega, Verdicchio, Fiano, Cape Blend as a stand-alone item, Inert-gas systems at Level 2, Halbtrocken, Demi-Sec, LBV, Pale Cream, Amontillado, Oloroso, PX.** In range but cut to keep proportions close to the weighting and to avoid near-duplicates (several are mentioned in explanations instead). Good candidates for a later batch.
- **Gevrey-Chambertin / Pommard to Pinot Noir.** Would near-duplicate the existing "primary variety of Burgundy's red wines" question; Pinot Noir GIs are tested through Central Otago / Martinborough instead.
- **Light-bodied red service temperature.** The specs differ: Level 1 says "lightly chilled", Level 2 says "room temperature or lightly chilled". The Level 1 question therefore offers no "room temperature" option, so it has one unambiguous answer under both specs. No Level 2 question asks this.

Tagging judgement calls on existing rows:
- *Orange wine is produced by...* is outside both WSET ranges. It is tagged `app_level 2 / L2-LO2` (skin contact is a winemaking option) with `sheet_line = appearance`. Consider retiring it from exams or tagging it differently.
- *Primary variety of Burgundy's red wines* is also in Level 1 range (red Burgundy), but is tagged Level 2 (`L2-LO3`) as requested.
- The two label questions are tagged `L2-LO3` (Pinot Noir and Margaux are both principal-variety GIs in the Level 2 spec).

## 8. Originality and copyright

All questions, explanations and prompts are original to VinoSim. The WSET specifications (and their five sample questions each) were used only to set scope (the Range lists), the exam weighting and the general format and difficulty. No WSET question was copied or paraphrased. WSET's specifications and its Systematic Approach to Tasting (SAT) are copyright of the Wine & Spirit Education Trust and may not be reproduced without written permission, so neither is reproduced in the app or in this bank. VinoSim is not affiliated with or endorsed by WSET; "loosely mirrors WSET Level 1/2" should not be presented as WSET certification.
