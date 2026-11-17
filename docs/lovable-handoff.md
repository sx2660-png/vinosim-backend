# VinoSim: handing the front end to Lovable

The Lovable project (`sx2660-png/vino-wisdom-trainer`, TanStack Start + Tailwind + shadcn) has the design we want,
but every screen runs on hard-coded local state. These prompts connect it to the VinoSim back end and bring in the
features built in `feature/levels-medals`. Paste them into Lovable **one round at a time**, check the preview, then send
the next one.

**Before round 1:** the back end in this repo (branch `feature/levels-medals`) must be deployed to Railway, or the new
endpoints below will return 404.

---

## Round 1: foundation (connect to the API, age gate, real content)

```text
We are now connecting VinoSim to its real back end. This replaces the "client-state only, no backend" rule.

1. Update AGENTS.md: remove the rule that VinoSim is a client-state-only experience. New rule: all learning content,
   quiz questions, tasting sheets, progress and medals come from the VinoSim API described below. Keep the existing
   visual design (eyebrows, serif titles, photos, phone shell, bottom navigation) exactly as it is.

2. Add a small API client in src/lib/api.ts:
   - Base URL: import.meta.env.VITE_API_BASE, falling back to "https://vinosim-backend-production.up.railway.app".
   - A user id stored in localStorage under "vinosim_user_id" (create "user_" + 8 random base-36 chars if missing).
     Only touch localStorage in the browser (inside effects or event handlers), never during server rendering.
   - All calls run on the client (useEffect or @tanstack/react-query). JSON in, JSON out. On a non-2xx response,
     read the JSON "detail" string if present and show it in a quiet error message.

3. Age gate: on first open, before anything else, show a full screen in the same style: title "Before we pour.",
   text "VinoSim is for adults of legal drinking age where you live (21 or older in the US).", a soft card "Tasting
   is about small sips. Spitting is completely fine, and so is learning without drinking at all.", and two buttons:
   "I'm of legal age" (store vinosim_age_ok = "yes" in localStorage and continue) and "I'm not" (show "Come back
   later." and do not let them in).

4. Study and Home articles: replace the four hard-coded articles with GET {BASE}/articles?user_id={id}.
   Response: { "articles": [ { "id", "title", "category" ("Term" | "Region" | "New" | "Bonus" | other), "content",
   "image" (may be "" or a path like "/media/bordeaux.jpg" — prefix relative paths with BASE), "match": string[] } ] }.
   Split "content" into paragraphs on blank lines. Use the first sentence as the card subtitle. If "match" is not
   empty, show a small line "Because you asked about {first three items}" on the card. Home shows the first three
   non-Bonus articles. Keep the existing filter tabs and add a "Bonus" tab later (round 3).

5. Do not invent tasting observations anywhere. Empty means empty.
```

## Round 2: Tutor and the four-line tasting sheet

```text
Rebuild the Tutor's tasting part around a sheet the learner writes themselves. Keep the portrait, the "Take your
time. I'm listening." caption, the step dots and the chat layout.

1. Steps are now Look (观色) → Smell (闻香) → Taste (品尝) → Like it? (喜不喜欢). Replace "Conclude / balanced?".
   For each step show the question, a textarea "What I sense, in my own words", and a line "Common words people use":
   - Look: "What colour is it, and how deep does it look?" — common: "pale · medium · deep — lemon, gold, pink, ruby, garnet"
   - Smell: "What does it smell like to you? There is no wrong answer." — common: "fruit (cherry, citrus, apple),
     flowers, spice, vanilla or toast from oak, earth"
   - Taste: "How does it feel in your mouth? Use one word and say what you felt." — common: "acidity = mouth-watering ·
     tannin = gums feel dry · body = light or heavy · sweetness · alcohol = warmth". Add an optional field "because…".
   - Like it?: "Would you drink it again? Why or why not?" — common: "easy to drink · a bit sharp for me · would be good
     with food — no wrong answer"
   Also an optional "Which wine?" field on the first step. Keep the draft in localStorage so a reload does not lose it.

2. Remove the regex-built tasting grid and its invented values: no hard-coded "Ruby / Garnet", and never turn
   "bitter" or "dry" into "High Tannins". The "Tasting grid" section now simply shows what the learner wrote on each
   line (empty lines show "—").

3. Save the sheet with POST {BASE}/sheets, body { user_id, id? (send it when updating an already-saved sheet),
   wine_name, appearance, nose, palate, palate_because, liking }. Response:
   { "sheet": { "id", "wine_name", "appearance", "nose", "palate", "palate_because", "liking", "structure_words": string[],
   "complete": boolean, "created_at", "updated_at" }, "missing": string[], "new_medals": string[] }.
   Show friendly text for each "missing" key and jump to that step:
   appearance → "Write a few words about how it looks." · nose → "Write what you smell, in any words." ·
   palate → "Write how it feels in your mouth." · liking → "Say whether you like it." ·
   palate_structure_word → "On the palate line, try one word: acidity, tannin, body, sweetness or alcohol." ·
   palate_sensation → "Say what you felt that made you pick that word, or fill in “because”."
   When "complete" is true show "Sheet complete. It counts toward Level 1 and is kept in Cellar." and a "New sheet" button.
   If "new_medals" is not empty, show the medal toast (see round 3; for now a simple toast).

4. Chat: POST {BASE}/agent, body { user_id, mode: "correction", message, step } where step is the current line:
   "appearance" | "nose" | "palate" | "liking". Response: { "answer": string, "sources": string[] }. Show the answer as
   the tutor bubble and, if sources is not empty, a small line "From {sources joined by ', '}". Load earlier messages
   with GET {BASE}/agent/history?user_id={id}&mode=correction → { "messages": [ { "role": "user" | "assistant", "content" } ] }.
   Add an "Ask about this line" button that sends: For the {line} line I wrote: "{text}". Can you help me put it into words?
   Keep the tappable term sheet, but open it for any of Acidity, Tannin, Body, Sweetness, Alcohol mentioned in a tutor
   reply, using these cards (you feel → people say → because):
   - Acidity: "Your mouth waters. It tastes fresh or sharp, like biting a green apple." / "Grapes lose acid as they ripen,
     so wines from cooler places usually keep more of it."
   - Tannin: "Your gums and the inside of your cheeks feel dry, tight or a little rough." / "It comes from grape skins,
     seeds and stems (and some from oak). Red wine sits on its skins, so it has more."
   - Body: "The weight of the wine in your mouth: light like water, or heavier like milk." / "Mostly from alcohol. Riper
     grapes from warmer places make more alcohol, so the wine feels fuller."
   - Sweetness: "A sugary, sometimes sticky feel on the tip of your tongue." / "Sugar that was left when fermentation
     stopped before all of it turned into alcohol."
   - Alcohol: "Warmth at the back of your throat or in your chest after you swallow." / "Yeast turns grape sugar into
     alcohol, so riper, sweeter grapes give stronger wine."

5. Roleplay: add a second Tutor tab "At the table" that posts the same /agent call with mode "roleplay" (no step).
   Response: { "reply": string, "character": string }. Label the other speaker "Guest". Note under the tabs: "Practise
   saying a sentence or two at dinner. Nothing here is graded." Hide the sheet in this tab.

6. Smell step hint: GET {BASE}/prompts?line=nose → { "prompts": [ { "id", "prompt", "examples": string[], "guidance" } ] }.
   Show one random "prompt" under the Smell question. It is never graded.

7. "Read a label": upload a photo with POST {BASE}/scan as multipart form field "file". Response:
   { "producer", "wine_name", "vintage", "region", "grape_varieties": string[], "alcohol", "notes" }. Show the result in the
   existing recognized-bottle card (use the uploaded photo, not the Margaux sample), pre-fill "Which wine?", and offer
   "Save to cellar".
```

## Round 3: levels, quiz, medals, Study and Cellar

```text
Add the two learning levels and medals, and connect Quiz, Progress, Study and Cellar to the API.

1. Progress page (the "Progress" button) becomes "Your path": "Two levels, two medals." with the line "Each medal stands
   for something you can now do, not for time spent in the app." Data: GET {BASE}/progress?user_id={id} →
   { "level1": { "exam": null | { "score", "total", "passed", "at" }, "sheets_complete", "sheets_needed", "medal": null | iso date },
     "level2": { "unlocked": boolean, "exam": same shape, "labels_done", "labels_needed", "medal": null | iso date },
     "bonus": { "status": string, "articles": [ { "id", "title", "read", "medal" } ] },
     "course_complete": boolean, "new_medals": string[] }.
   - Level 1 "Talk about the glass": progress bar sheets_complete / sheets_needed (6), exam line, buttons "Write a sheet"
     (Tutor) and "Level 1 exam".
   - Level 2 "Read the bottle": if not unlocked, show it dimmed with "Opens after the Level 1 medal. You can already
     practise Level 2 questions in Quiz." If unlocked: label tasks bar labels_done / labels_needed (5), exam line, buttons
     "Label tasks" and "Level 2 exam".
   - When course_complete: "Both medals earned. If you would like a formal certificate, a WSET Level 1 course is a
     natural next step."
   - Bonus "Going further · not graded": show "status" and each bonus article with "Read" or "New".
   Also show a compact two-row version of this on Home. No streaks, no leaderboards, no time-spent stats.

2. Medal toast: whenever any response contains a non-empty "new_medals" array, show a toast: "New medal" plus one line
   per id: "level1" → "Level 1 medal · Talk about the glass", "level2" → "Level 2 medal · Read the bottle",
   "bonus:<n>" → "Bonus medal", with buttons "See your path" and "Close".

3. Quiz tabs: Practice · Exam · Labels · Photo. Keep the existing card and option styles.
   - Practice: a Level 1 / Level 2 switch. GET {BASE}/quiz?level=1|2 → { "id", "question", "options": ["A. …", "B. …",
     "C. …", "D. …"], "category", "image" (prefix relative paths with BASE), "app_level", "item_type", "sheet_line" }.
     Answer with POST {BASE}/quiz/submit body { user_id, question_id, answer: "A" | "B" | "C" | "D" } → { "correct",
     "correct_answer" (letter), "explanation", "score": { "correct", "total" }, "new_medals" }. Show green/red and the
     explanation, then "Next question".
   - Exam: Level 1 / Level 2 switch. Start screen: "30 questions" (Level 1) or "50 questions" (Level 2), "no time limit",
     pass mark 70% / 55% "like the WSET Level N exam", "You see the explanations when you hand in." POST {BASE}/exam/start
     body { user_id, level } → { "attempt_id", "level", "pass_pct", "time_limit_min", "questions": [ { "id", "question",
     "options", "image" } ] } (no answers are sent). A 403 means Level 2 is locked: show its "detail" text. Show all
     questions on one scrolling page with an "n/total answered" counter, then "Hand in" (confirm if any are blank).
     POST {BASE}/exam/submit body { user_id, attempt_id, answers: { "<question id>": "B", … } } → { "score", "total",
     "pass_pct", "passed", "review": [ { "id", "given", "correct_answer", "correct", "explanation" } ], "new_medals" }.
     Result: banner "{score}/{total} · Passed" or "· Not passed yet" with the pass mark, then "Worth another look": each
     wrong question with its correct option text and explanation, and "Take it again". Scroll to the top after hand-in.
   - Labels: "Answer five different label questions correctly to complete the Level 2 label tasks." GET
     {BASE}/labels/tasks?user_id={id} → { "needed": 5, "done", "tasks": [ { "id", "question", "options", "image", "done" } ] }.
     List them (done ones with a check). Opening one uses the same practice card and /quiz/submit; refresh the list after.
   - Photo: the existing upload-a-label quiz via POST {BASE}/label/decode (multipart "file") → { "question", "options",
     "correct_answer", "explanation" }, checked on the client. Add the note "Practice only: it does not count toward the
     label tasks." Keep the Château Margaux label card as a sample practice item.

4. Study: add tabs "Words" and "Bonus".
   - Words: the five structure cards from round 2, each laid out "You feel" / "People say" (the word, large) / "Because".
   - Bonus: GET {BASE}/bonus?user_id={id} → { "status", "articles": [ { "id", "title", "content", "image", "read" } ] }.
     Intro line: "Optional reading toward the advanced levels. Not graded." plus "status". Opening an unread one calls
     POST {BASE}/bonus/read body { user_id, article_id } → { "ok", "new_medals" } (shows the medal toast).
     Hide Bonus articles from the "All" tab.

5. Cellar "Tasting notes": load from GET {BASE}/sheets?user_id={id} → { "sheets": [ sheet objects as in round 2 ] }.
   Each card: wine name (or "A glass of wine"), a "Complete" or "Draft" badge, then "Looks:", "Smells:",
   "Feels:" (palate plus "because …" if present), "Like it?" and the date. Bottles stay as they are (device only).
```

---

## Quick reference: endpoints

| Method | Path | Used for |
|---|---|---|
| GET | `/health` | API up check |
| GET | `/articles?user_id=` | Study / Home articles (ranked by the learner profile) |
| GET | `/quiz?level=` | One practice question |
| POST | `/quiz/submit` | Score a practice answer (counts label tasks) |
| POST | `/exam/start` | Start a level exam (403 if Level 2 is locked) |
| POST | `/exam/submit` | Grade an exam, return review |
| GET/POST | `/sheets` | List / save tasting sheets |
| GET | `/progress?user_id=` | Levels, medals, bonus (also awards medals) |
| GET | `/labels/tasks?user_id=` | Level 2 label tasks |
| GET | `/bonus?user_id=` · POST `/bonus/read` | Bonus reading |
| GET | `/prompts?line=` | Open, ungraded tasting prompts |
| POST | `/agent` · GET `/agent/history` | Tutor (correction with `step`, or roleplay) |
| POST | `/scan` · `/label/decode` | Label photo → fields / practice question |

CORS is open (`allow_origins=["*"]`), so the Lovable domain can call the API directly.
