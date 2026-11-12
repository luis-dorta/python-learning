# LAB issue builder

Builds one issue of Luis's AI Brief for beehiiv. The layout is fixed in `build_issue.py`, so every issue looks the same. Only the words and numbers change, and they come from one file: `lab-issues/YYYY-MM-DD.json`.

## Steps for one issue

1. Write `lab-issues/YYYY-MM-DD.json`. Copy the shape of the newest file in `lab-issues/`. Field notes are below.
2. `python3 lab-tools/build_issue.py check lab-issues/YYYY-MM-DD.json` and fix every ERROR. Read every WARN.
3. `python3 lab-tools/build_issue.py images lab-issues/YYYY-MM-DD.json lab-images/YYYY-MM-DD` then delete `_cards.html`, commit and push.
4. Upload each JPG to beehiiv (save_image from the raw GitHub URL pinned to the commit id) and write `urls.json`: `{"mast": "...", "thumb": "...", "bento": "...", "hero": "...", "fig1": "...", "newai": "...", "prompt": "..."}`.
5. `python3 lab-tools/build_issue.py html lab-issues/YYYY-MM-DD.json urls.json out` writes `out/part1.html`, `part2.html` ... and `out/meta.json`.
6. Put the parts into the beehiiv post in order, then run `verify` on the saved post.

## issue.json fields

- `vol`, `no`: numbers. `date_long`: like `Tuesday, November 10, 2026`.
- `subject_hook`: short two-topic hook for the email subject. `subtitle`: one plain sentence.
- `your_turn`: one easy opinion question. `prev_url`, `prev_label`: link to the previous issue (`Read yesterday's issue`, or `Read Friday's issue` on Mondays).
- `stories`: exactly 3. Each has `kicker` (company or topic), `headline`, `teaser_title`, `teaser_line`, `paragraphs` (2), `means`, `clip`, `deeper` (3 to 5 bullets), `sources`, and `fig` (or null).
  - Story 1 also has `hero`: `headline`, `stats` (3 items with `value` and `label`), and `svg` (an inline SVG drawing, or "" for the default art).
  - `fig`: `title` (starts with `Fig. N.`), `rows` (each `label`, `value`, `pct` from 0 to 100 on one zero-based scale, `hi` true for the highlighted bar; `{"gap": true}` adds a space), `note`.
- `newai`: 2 or 3 items with `tags`, `title`, `paragraphs`, `sources`.
- `connectors`: 2 items with `title`, `paragraphs`, `sources`. `worth`: null, or `title`, `paragraphs`, `sources`.
- `prompt`: `title`, `intro`, `weak`, `strong` (plain text, one line per line, bullets start with `- `), `why` (4 items with `title` and `text`), `try`, `sources`.
- `brief`: 3 items with `name`, `text`, `sources`.
- `quiz`: null Monday to Thursday. Fridays: `recap` (paragraphs), `questions` (3, each `question`, `options`, `answer` as a 0-based index, `explain`), `sources`.

Text fields may use only these inline tags: `<strong>`, `<em>`, `<code>`, `<a href="...">`. Write `&amp;` for &, `&lt;` for <.

`parse_artifact.py brief.html issue.json` can fill most fields from a saved copy of the Claude brief page.
