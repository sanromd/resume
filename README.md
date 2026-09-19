# CV / Résumé Builder

Three documents, built from shared data:

| File | Purpose |
|---|---|
| `site/resume-international.pdf` | 2-page résumé, no photo — LinkedIn, recruiters, general applications |
| `site/resume-saudi-residency.pdf` | 2-page CV with photo — Saudi Premium Residency application |
| `site/cv-extended.pdf` | Full record — every publication, patent, award |

## Editing content

Everything lives in `data/`. Edit these, then re-run the builder — never edit
the generated files in `site/` directly (they're overwritten on every build).

- **`data/profile.yaml`** — identity, contact info, headline metrics, skills,
  education, career narrative, achievement clusters, professional experience.
  Structured lists (jobs, degrees, clusters) are YAML; prose fields are plain
  strings that support light Markdown (`**bold**`, `*italic*`, `[text](url)`).
  The `variants:` block holds the two résumés' differing summary/framing —
  everything else (experience, clusters, education) is shared so it can't
  drift out of sync between documents.

- **`data/publications.csv`**, **`data/patents.csv`**, **`data/awards.csv`**
  — one row per item, split from the original master
  `San_Roman_Alerigi_Complete_Works.csv` with its columns preserved as-is
  (Category, Title, Authors / Inventors, Publication Date, DOI, etc.). To add
  a new publication/patent/award, add a row with the same columns.

  A few extra columns control how the two-page résumés use this data —
  everything else is only used by the Extended CV:
  - **`Featured`** (`yes`/`no`) — include this row in the concise résumés'
    "Selected" sections. Leave `no` for anything that should only appear in
    the Extended CV (i.e. almost everything — the résumés show ~6 of each).
  - **`Venue Short`** / **`Display Authors`** (publications only) — optional
    short forms for the concise citation line (e.g. "Khan *et al.*"
    instead of the full six-author list). Leave blank to just use the full
    `Authors / Inventors` field.
  - **`Role Tag`** / **`Family Short`** (patents only) — optional short
    inventor-role tag (e.g. "Lead inventor") and abbreviated jurisdiction
    list (e.g. "EP / WO / CN / SA") shown next to featured patents.

  Tags like "First author", "Sole inventor", "Lead article" are derived
  automatically from the `Notes` column (it already has these as ALL-CAPS
  flags) — no separate tag column to keep in sync.

## Building

```bash
python3 tools/build_cv.py              # build HTML + PDF for all 3 docs
python3 tools/build_cv.py --no-pdf     # HTML only, faster iteration
python3 tools/build_cv.py --only resume-international
```

Requires `pyyaml` and `jinja2` (`pip install pyyaml jinja2`) and a Chromium
binary for the PDF step — the script points at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; edit the `CHROMIUM`
constant at the top of `tools/build_cv.py` if yours lives elsewhere.

## How it fits together

```
data/profile.yaml   ─┐
data/publications.csv├─► tools/build_cv.py ─► site/*.html ─► (headless Chromium) ─► site/*.pdf
data/patents.csv     │        ▲
data/awards.csv     ─┘        │
                       templates/*.html.j2  (Jinja2; shared design in site/assets/style.css)
```

No LaTeX involved — the design is HTML/CSS rendered to print-quality PDF via
headless Chromium's `--print-to-pdf`.
