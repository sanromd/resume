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
  education, career narrative, achievement clusters, professional experience,
  society **memberships**, internal **leadership** roles, and Google Scholar
  **citation_metrics** (citations, h-index, i10-index). Structured lists
  (jobs, degrees, clusters, memberships) are YAML; prose fields are plain
  strings that support light Markdown (`**bold**`, `*italic*`, `[text](url)`).
  The `variants:` block holds the two résumés' differing summary/framing —
  everything else (experience, clusters, education) is shared so it can't
  drift out of sync between documents.

  Memberships and leadership roles live here, not in a CSV, because they're
  standing status you hold (a paid membership, a role you held) rather than
  a one-off dated event like an award or a press mention. Update
  `citation_metrics` whenever you refresh the numbers from your
  [Google Scholar profile](https://scholar.google.com/citations?user=fKRPXQIAAAAJ) —
  it feeds both the résumé sidebar and the Extended CV's companion blurb.

- **`data/publications.csv`**, **`data/patents.csv`** — one row per item,
  split from the original master `San_Roman_Alerigi_Complete_Works.csv` with
  its columns preserved as-is (Category, Title, Authors / Inventors,
  Publication Date, DOI, etc.). To add a new publication/patent, add a row
  with the same columns.

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

- **`data/awards.csv`** — competitive or granted awards and scholarships
  only, one row per award (not per ceremony): `Year, Type, Result, Title,
  Body, Category, Notes, Featured`. `Result` is `Winner` or `Finalist`;
  `Body` is the awarding organization; `Category` is the specific award
  category when the body gives several (e.g. a technology-awards program).
  Two technologies named finalists in the same year for different
  categories are two rows, not one.

- **`data/recognition.csv`** — non-competitive recognition that isn't an
  "award": media features, corporate/team recognition. Schema: `Year, Type,
  Title, Venue, Notes, Featured`. If something was won/awarded by a body
  with a named category, it belongs in `awards.csv` instead.

- **`data/service.csv`** — professional service to societies, conferences
  and journals: technical program committee membership, session chairing,
  peer review, editorial roles, judging/panels. Schema: `Year, Society,
  Role, Activity, Category, Notes, Featured`.
  - `Year` — a single year or a range for one continuous appointment
    (`2021–2023`).
  - `Society` — the owning organization (`Society of Petroleum Engineers
    (SPE)`, `Optica`, `IEEE`).
  - `Role` — the specific capacity (`Technical Program Committee Member`,
    `Session Chair`, `Journal Reviewer`, `Guest Editor`, `Judge`, `Panelist`).
  - `Activity` — the specific conference/journal/committee, if applicable
    (blank for a society-level role with no single event attached).
  - `Category` — coarse grouping for the Extended CV (`Conference
    Committee`, `Journal Service`, `Judging/Panels`, `Governance`) — kept as
    its own column rather than parsed out of `Role` text.

  One row per distinct (Society, Role, Activity) combination for a
  continuous period. If the role changes — TPC member one year, session
  chair the next, for the same conference — that's two rows, not one,
  since it's a different fact each time. This file starts empty (header
  only): nothing in it is fabricated, so it only shows real entries you add.
  Both templates hide the "Professional Service" section entirely when the
  file has no rows, so an empty file doesn't leave an empty heading behind.

- **`data/projects.csv`** — software you built or substantively contributed
  to: personal projects, an org's tooling, an open-source library. Schema:
  `Name, Role, Org, URL, Description, Stack, Dates, Notes, Featured`.
  - `Role` — `Sole Developer`, `Co-Founder & Lead Developer`, `Core
    Contributor`, `Contributor`, etc. Be precise; this is what distinguishes
    a project you built from one you merely forked.
  - `Org` — the owning account/organization the repo lives under, if not
    your personal account.
  - `Stack` — primary language(s)/frameworks, shown as a tag in the
    Extended CV.
  - A GitHub fork with no real commits/PRs from you does **not** belong
    here — only list projects you actually developed or meaningfully
    contributed to. This file starts empty for the same reason
    `service.csv` does: nothing is added until you confirm it's real.
    Both templates hide the section when the file has no rows.

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
data/profile.yaml     ─┐
data/publications.csv  │
data/patents.csv       ├─► tools/build_cv.py ─► site/*.html ─► (headless Chromium) ─► site/*.pdf
data/awards.csv        │        ▲
data/recognition.csv   │        │
data/service.csv       │        │
data/projects.csv     ─┘        │
                         templates/*.html.j2  (Jinja2; shared design in site/assets/style.css)
```

No LaTeX involved — the design is HTML/CSS rendered to print-quality PDF via
headless Chromium's `--print-to-pdf`.
