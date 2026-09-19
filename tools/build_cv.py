#!/usr/bin/env python3
"""Build the résumé/CV suite from data/profile.yaml + data/*.csv.

Usage:
    python3 tools/build_cv.py               # build HTML + PDF for all 3 docs
    python3 tools/build_cv.py --no-pdf       # HTML only (fast iteration)
    python3 tools/build_cv.py --only resume-international

Data sources (edit these, then re-run this script):
    data/profile.yaml     — identity, contact, metrics, skills, education,
                             career arc, achievement clusters, experience,
                             society memberships, leadership/service roles,
                             and Google Scholar citation metrics
    data/publications.csv — journal / industry / conference / preprint / thesis,
                             split verbatim from the master Complete_Works.csv
    data/patents.csv      — granted + pending patents, same source
    data/awards.csv       — competitive/granted awards and scholarships only
                             (Year, Type, Result, Title, Body, Category, Notes, Featured)
    data/recognition.csv  — non-competitive recognition: media features,
                             corporate/team recognition (Year, Type, Title,
                             Venue, Notes, Featured)
    data/service.csv      — professional service to societies/conferences/
                             journals: TPC membership, session chair, peer
                             review, judging, editorial roles (Year, Society,
                             Role, Activity, Category, Notes, Featured)
    data/projects.csv     — software projects you developed or substantively
                             contributed to (not forks you never touched):
                             (Name, Role, Org, URL, Description, Stack,
                             Dates, Notes, Featured)

publications.csv and patents.csv keep the master file's original column
names (Category, Title, "Authors / Inventors", "Publication Date", "Venue /
Publisher / Assignee", DOI, etc.) plus a few optional enrichment columns
(Featured, Venue Short, Display Authors, Role Tag, Family Short) used only
to pick and lightly style the handful of items shown on the two-page
résumés — every original value is preserved as-is. awards.csv,
recognition.csv and service.csv use their own simple schemas (see above)
since they don't come from that master file. This script normalizes
headers into clean field names for the templates; it does not rewrite
the CSVs.

Society memberships and internal leadership roles (founding a body,
chairing a council) live in profile.yaml, not a CSV — they're standing
status (a paid membership, a role you held) rather than a dated,
repeatable event. Professional *service* — a TPC seat, a reviewing
assignment, a session you chaired — is inherently one row per
appointment and you may hold several over time, so it's tabular data
in data/service.csv instead.

Output:
    site/resume-international.html + .pdf
    site/resume-saudi-residency.html + .pdf
    site/cv-extended.html + .pdf
    (site/assets/ — style.css and headshot are static, not generated)
"""
import argparse
import csv
import html
import re
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


# ---------------------------------------------------------------------------
# Inline Markdown: **bold**, *italic*, [text](url), plus literal <i>/<em>
# already present in a couple of Display Authors overrides. Escapes raw text
# first, so stray & < > in source data are always rendered safely.
# ---------------------------------------------------------------------------
def md(text):
    if not text:
        return Markup("")
    text = html.escape(str(text).strip(), quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return Markup(text)


YEAR_RE = re.compile(r"(19|20)\d{2}")


def first_year(date_str):
    m = YEAR_RE.search(date_str or "")
    return m.group(0) if m else (date_str or "")


def doi_link(doi):
    """Build a clickable link from a bare DOI, a full URL, or return None."""
    if not doi:
        return None
    doi = doi.strip()
    if doi.startswith("http"):
        return doi
    if doi.startswith("10."):
        return f"https://doi.org/{doi}"
    return None


def load_profile():
    with open(DATA / "profile.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# Map the master CSV's human-readable headers to clean, stable field names.
PUB_HEADER_MAP = {
    "Category": "category", "Sub-Category": "subcategory", "Title": "title",
    "Authors / Inventors": "authors", "Publication Date": "date",
    "Venue / Publisher / Assignee": "venue", "Publication Link": "link",
    "DOI": "doi", "Patent / Paper Number(s)": "number",
    "Family & Related Numbers": "family", "Verification Status": "verification",
    "Notes": "notes", "Featured": "featured", "Venue Short": "venue_short",
    "Display Authors": "display_authors",
}
PATENT_HEADER_MAP = dict(PUB_HEADER_MAP, **{
    "Role Tag": "role_tag", "Family Short": "family_short",
})


FAMILY_PREFIX_RE = re.compile(r"^FAMILY:\s*", re.IGNORECASE)


def derive_tag(notes):
    """Turn the source Notes flags (FIRST AUTHOR., SOLE AUTHOR., LEAD ARTICLE,
    Senior/last author, Featured in Laser Focus World, KEY MILESTONE) into a
    short display tag, so the résumé doesn't need a separate hand-maintained
    tag column duplicating what Notes already says."""
    u = (notes or "").upper()
    tags = []
    if "FIRST AUTHOR" in u:
        tags.append("First author")
    if "SOLE AUTHOR" in u:
        tags.append("Sole author")
    if "SOLE INVENTOR" in u:
        tags.append("Sole inventor")
    if "LEAD INVENTOR" in u:
        tags.append("Lead inventor")
    if "SENIOR" in u and "AUTHOR" in u:
        tags.append("Senior author")
    if "LEAD ARTICLE" in u:
        tags.append("Lead article")
    if "FEATURED" in u and "LASER FOCUS WORLD" in u:
        tags.append("Featured, Laser Focus World")
    if "KEY MILESTONE" in u:
        tags.append("Key milestone")
    return " · ".join(tags)


def load_csv(name, header_map):
    with open(DATA / name, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    normalized = []
    for r in rows:
        row = {header_map.get(k, k): v for k, v in r.items()}
        row["year"] = first_year(row.get("date", ""))
        row["doi_url"] = doi_link(row.get("doi") or row.get("link"))
        if row.get("family"):
            row["family"] = FAMILY_PREFIX_RE.sub("", row["family"])
        # For a featured publication with an explicit Venue Short, derive the
        # trailing volume/page detail by stripping that exact prefix from the
        # full Venue string (deterministic string op, not a parse/guess).
        venue, short = row.get("venue", ""), row.get("venue_short", "")
        row["venue_detail"] = venue[len(short):].split(";")[0].strip(" ,") if short and venue.startswith(short) else ""
        row["tag"] = derive_tag(row.get("notes", ""))
        normalized.append(row)
    return normalized


def load_simple_csv(name):
    """Load a CSV with its own clean schema (awards.csv, recognition.csv) —
    unlike load_csv, no header-renaming map needed: just lowercase/underscore
    the headers as-authored."""
    with open(DATA / name, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [{k.strip().lower().replace(" ", "_"): v for k, v in r.items()} for r in rows]


def is_yes(row):
    return (row.get("featured") or "").strip().lower() == "yes"


def build_env():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True,
                       trim_blocks=True, lstrip_blocks=True)
    env.filters["md"] = md
    return env


def render_pdf(html_path: Path, pdf_path: Path):
    cmd = [
        CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", f"file://{html_path}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not pdf_path.exists():
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"PDF render failed for {html_path.name}")


def build(targets, make_pdf=True):
    profile = load_profile()
    publications = load_csv("publications.csv", PUB_HEADER_MAP)
    patents = load_csv("patents.csv", PATENT_HEADER_MAP)
    awards = load_simple_csv("awards.csv")
    recognition = load_simple_csv("recognition.csv")
    service = load_simple_csv("service.csv")
    projects = load_simple_csv("projects.csv")

    env = build_env()
    SITE.mkdir(exist_ok=True)

    common = dict(
        identity=profile["identity"], contact=profile["contact"], metrics=profile["metrics"],
        languages=profile["languages"], skills=profile["skills"], toolkit=profile["toolkit"],
        education=profile["education"], experience=profile["experience"],
        achievement_clusters=profile["achievement_clusters"], career_arc=profile["career_arc"],
        early_fellowships=profile["early_fellowships"], collaboration_network=profile["collaboration_network"],
        certifications=profile["certifications"], totals=profile["portfolio_totals"],
        memberships=profile["memberships"], leadership=profile["leadership"],
    )

    featured_patents = [p for p in patents if is_yes(p)]
    featured_pubs = [p for p in publications if is_yes(p)]
    featured_awards = [a for a in awards if is_yes(a)]
    featured_recognition = [r for r in recognition if is_yes(r)]
    featured_service = [s for s in service if is_yes(s)]
    featured_projects = [p for p in projects if is_yes(p)]

    resume_tmpl = env.get_template("resume.html.j2")
    for variant_key, out_name in [
        ("international", "resume-international"),
        ("saudi_residency", "resume-saudi-residency"),
    ]:
        if out_name not in targets:
            continue
        html_out = resume_tmpl.render(
            variant=profile["variants"][variant_key],
            patents=featured_patents, publications=featured_pubs,
            awards=featured_awards, recognition=featured_recognition,
            service=featured_service, projects=featured_projects,
            **common,
        )
        (SITE / f"{out_name}.html").write_text(html_out, encoding="utf-8")
        print(f"wrote site/{out_name}.html")

    if "cv-extended" in targets:
        ext_tmpl = env.get_template("cv_extended.html.j2")
        pubs_by_cat = {cat: [p for p in publications if p["category"] == cat]
                       for cat in ("Journal Article", "Conference Paper", "Pre-Print", "Thesis")}
        journal = [p for p in pubs_by_cat["Journal Article"] if p["subcategory"] == "Peer-reviewed"]
        industry = [p for p in pubs_by_cat["Journal Article"] if p["subcategory"] == "Industry / Technical Magazine"]
        pats_by_status = {s: [p for p in patents if p["subcategory"] == s]
                           for s in ("Granted", "Application (pending)")}
        html_out = ext_tmpl.render(
            journal=journal, industry=industry, conference=pubs_by_cat["Conference Paper"],
            preprint=pubs_by_cat["Pre-Print"], thesis=pubs_by_cat["Thesis"],
            granted=pats_by_status["Granted"], pending=pats_by_status["Application (pending)"],
            awards=awards, recognition=recognition, service=service, projects=projects,
            **common,
        )
        (SITE / "cv-extended.html").write_text(html_out, encoding="utf-8")
        print("wrote site/cv-extended.html")

    if make_pdf:
        for name in targets:
            html_path = SITE / f"{name}.html"
            if not html_path.exists():
                continue
            pdf_path = SITE / f"{name}.pdf"
            render_pdf(html_path, pdf_path)
            print(f"wrote site/{name}.pdf")


ALL_TARGETS = ["resume-international", "resume-saudi-residency", "cv-extended"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pdf", action="store_true", help="Only write HTML, skip PDF render")
    parser.add_argument("--only", choices=ALL_TARGETS, help="Build a single document")
    args = parser.parse_args()
    targets = [args.only] if args.only else ALL_TARGETS
    build(targets, make_pdf=not args.no_pdf)
