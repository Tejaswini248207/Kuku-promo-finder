# Kuku Promo Finder — Problem 1

A reusable, screenplay-first promo shortlist tool.

## What it does
- Reads the assignment's timestamped `.txt` screenplay format.
- Extracts episode number, logline, and timestamped camera/action/dialogue/sound events.
- Generates continuous windows between 20 and 60 seconds.
- Scores opening 3 seconds for hook cues and final 5 seconds for cliffhanger cues.
- Adds a weak standalone-context proxy, ranks candidates, and suppresses overlapping near-duplicates.
- Exports CSV/JSON results.

## Run locally (batch)
1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. Put screenplay `.txt` files in a folder, for example `screenplays/`.
4. Run:
   `python promo_finder.py --input-dir screenplays --output-dir outputs`

## Run the Streamlit interface
`streamlit run app.py`

Upload one or more `.txt` files. The app shows the top 20 and lets you download the ranked shortlist.

## Scoring and limitations
The score is a deterministic heuristic, **not a probability** and not trained on editor labels. It is based on:
- hook-like words / punctuation in the first 3 seconds,
- cliffhanger-like words / punctuation in the final 5 seconds,
- screenplay visual/action event evidence,
- a small standalone-context proxy,
- duration fit.

It can over-score generic questions, threats that are actually resolved, or keywords used in ordinary dialogue. It cannot inspect facial expressions, pacing, sound, shot quality, or what happens immediately after the cut. The current version returns one continuous segment from one episode; cross-episode stitching and multi-segment promos are not implemented. An editor must review every finalist against the actual video.

## Swapping in a stronger model
The parser and candidate generator are separate from scoring. Replace or augment `score()` in `promo_finder.py` with a model-backed reviewer that receives candidate evidence and returns structured hook, cliffhanger, and standalone-clarity judgments. Keep the heuristic as a fallback; validate the model on editor-labelled examples before using it at scale.

## Input privacy
The supplied screenplay pack is not included in this repository. Upload the pack locally when running the tool.

## Revision (final)
- Duplicate rule: two clips from the same episode are duplicates when they overlap by more than 40% of the shorter clip (same rule documented above), applied within each episode and again across the final list.
- Ending excerpts keep the last 450 characters of the final 5 seconds, so the cliffhanger line is shown; opening excerpts are cut at full sentences. Shortened text is marked in `data_notes`.
- Rationales quote each promo's own opening and ending lines together with the scores.
- Run: python promo_finder.py --input-dir <folder with the 50 .txt files> --output-dir outputs

## Deploy (free)
- **Streamlit Community Cloud:** push this folder to a public GitHub repo, then create an app at share.streamlit.io pointing to `app.py`.
- **Hugging Face Spaces:** create a Streamlit Space and upload these files.
The screenplay pack is not included. Upload your own .txt files in the app, or run the CLI locally.
