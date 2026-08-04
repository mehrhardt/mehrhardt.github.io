#!/usr/bin/env python3
"""
build_publications.py
=====================
Reads BibTeX files and writes generated HTML fragments to:
    data/generated/publications.html
    data/generated/presentations.html

Usage:
    python build_publications.py
"""

import html
import pathlib
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser

LOCAL_BIB_DIR = pathlib.Path("data/bib")
LEGACY_BIB_DIR = pathlib.Path("/Users/me549/Library/CloudStorage/OneDrive-UniversityofBath/MyOneDrive/personal/cv/latex/bib")
CV_TEX_FILE = pathlib.Path("/Users/me549/Library/CloudStorage/OneDrive-UniversityofBath/MyOneDrive/personal/cv/latex/cv.tex")
PUBLICATIONS_OUTPUT_FILE = pathlib.Path("data/generated/publications.html")
PRESENTATIONS_OUTPUT_FILE = pathlib.Path("data/generated/presentations.html")

PUBLICATION_SECTION_FILES = {
    "Peer-Reviewed Publications": ["journals.bib", "proceedings.bib", "bookchapters.bib"],
    "Preprints": ["preprints.bib"],
    "Miscellaneous": ["misc.bib"],
}

PRESENTATION_SECTION_FILES = {
    "Oral Presentations at Conferences, Workshops and Seminars": ["conferences.bib", "seminars.bib"],
    "Poster Presentations": ["posters.bib"],
}

_LATEX_CHAR = [
    (r'{\\"u}', 'ü'), (r'\\"u', 'ü'), (r'{\"u}', 'ü'), (r'\"u', 'ü'),
    (r'{\\"U}', 'Ü'), (r'\\"U', 'Ü'), (r'{\"U}', 'Ü'), (r'\"U', 'Ü'),
    (r'{\\"o}', 'ö'), (r'\\"o', 'ö'), (r'{\"o}', 'ö'), (r'\"o', 'ö'),
    (r'{\\"O}', 'Ö'), (r'\\"O', 'Ö'), (r'{\"O}', 'Ö'), (r'\"O', 'Ö'),
    (r'{\\"a}', 'ä'), (r'\\"a', 'ä'), (r'{\"a}', 'ä'), (r'\"a', 'ä'),
    (r"{\\'e}", 'é'), (r"\\'{e}", 'é'), (r"{\\'E}", 'É'),
    (r"{\\'o}", 'ó'), (r"\\'{o}", 'ó'),
    (r"{\\'a}", 'á'), (r"\\'{a}", 'á'),
    (r"{\\'i}", 'í'), (r"\\'{i}", 'í'),
    (r"{\\v{z}}", 'ž'), (r"\\v{Z}", 'Ž'), (r"\\v{z}", 'ž'),
    (r"{\\v{S}}", 'Š'), (r"\\v{s}", 'š'),
    (r"{\\v{Z}}", 'Ž'),
    (r"{\\'n}", 'ń'), (r"\\'{n}", 'ń'),
    (r"\\~{n}", 'ñ'), (r"{\\~n}", 'ñ'),
    (r"\\~u", 'ũ'), (r"{\\~u}", 'ũ'), (r"\~u", 'ũ'), (r"{\~u}", 'ũ'),
    (r"\\~U", 'Ũ'), (r"{\\~U}", 'Ũ'), (r"\~U", 'Ũ'), (r"{\~U}", 'Ũ'),
    (r"{\\'c}", 'ć'),
    (r"\\c{c}", 'ç'), (r"{\\c{c}}", 'ç'),
    (r"{\\ss}", 'ß'), (r"\\ss", 'ß'),
    (r"\\&", '&'), (r"\&", '&'),
    (r"\\#", '#'),
    (r"\\%", '%'),
    (r'\\ ', ' '),
]

_BADGE_LABELS = {"print", "preprint", "code", "slides", "poster", "video", "abstract"}


def resolve_bib_dir() -> pathlib.Path:
    for candidate in (LOCAL_BIB_DIR, LEGACY_BIB_DIR):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not find a BibTeX directory. Checked: {LOCAL_BIB_DIR} and {LEGACY_BIB_DIR}"
    )


BIB_DIR = resolve_bib_dir()


def parse_cv_categories() -> dict[str, list[str]]:
    if not CV_TEX_FILE.exists():
        raise FileNotFoundError(f"Could not find CV source file: {CV_TEX_FILE}")
    text = CV_TEX_FILE.read_text(encoding="utf-8")
    categories: dict[str, list[str]] = {}
    for name in ("peerreviewed", "preprints", "misc", "conferences", "posters"):
        match = re.search(rf"\\addtocategory\{{{name}\}}\{{([^}}]*)\}}", text, re.S)
        if not match:
            raise ValueError(f"Could not find CV category '{name}' in {CV_TEX_FILE}")
        categories[name] = [item.strip() for item in match.group(1).split(",") if item.strip()]
    return categories


CV_CATEGORIES = parse_cv_categories()


def parse_cv_bib_resources() -> list[str]:
    text = CV_TEX_FILE.read_text(encoding="utf-8")
    resources = re.findall(r"\\addbibresource\{bib/([^}]+)\}", text)
    if not resources:
        raise ValueError(f"Could not find \\addbibresource entries in {CV_TEX_FILE}")
    return resources


CV_BIB_RESOURCES = parse_cv_bib_resources()


def latex_to_plain(value: str) -> str:
    if not value:
        return value
    out = value
    for latex, char in _LATEX_CHAR:
        out = out.replace(latex, char)
    out = re.sub(r"(?<!\\)~", " ", out).replace("$", "")
    out = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', out)
    out = re.sub(r'\{([^}]*)\}', r'\1', out)
    return out


def latex_to_url(value: str) -> str:
    if not value:
        return value
    out = value.strip()
    out = out.replace(r"\&", "&").replace(r"\#", "#").replace(r"\%", "%")
    out = out.replace("{", "").replace("}", "")
    return out


def extract_href(value: str) -> tuple[str, str]:
    match = re.search(r'\\href\s*\{([^}]+)\}\s*\{([^}]+)\}', value or '')
    if match:
        return match.group(1), latex_to_plain(match.group(2))
    return value, value


def entry_url(entry: dict) -> str:
    doi = entry.get("doi", "").strip()
    if doi:
        if doi.startswith("http"):
            return doi
        return f"https://doi.org/{doi}"
    return entry.get("url", entry.get("html", "")).strip()


def preprint_url(entry: dict) -> str:
    pre = entry.get("preprint", "")
    if pre:
        url, _ = extract_href(pre)
        return url.strip()
    eprint = entry.get("eprint", "").strip()
    if eprint and "arxiv" in entry.get("archiveprefix", "arXiv").strip().lower():
        return f"https://arxiv.org/abs/{eprint}"
    arxivid = entry.get("arxivid", "").strip()
    if arxivid:
        return f"https://arxiv.org/abs/{arxivid}"
    note = entry.get("note", "")
    if note:
        url, _ = extract_href(note)
        if "arxiv" in url.lower() or url.startswith("http"):
            return url.strip()
    return ""


def code_url(entry: dict) -> str:
    return entry.get("code", entry.get("software", "")).strip()


def parse_keyword_links(entry: dict) -> list[tuple[str, str]]:
    raw_keywords = entry.get("keywords", "")
    links: list[tuple[str, str]] = []
    for part in raw_keywords.split(";"):
        item = part.strip().strip(",")
        if not item.startswith("web:"):
            continue
        payload = item[4:]
        if "=" not in payload:
            continue
        label, url = payload.split("=", 1)
        links.append((latex_to_plain(label.strip()), latex_to_url(url.strip())))
    return links


def note_to_html(entry: dict) -> str:
    note = entry.get("note", "").strip()
    if not note:
        return ""
    note = re.sub(r"\\textbf\{([^}]*)\}", r"<b>\1</b>", note)
    return latex_to_plain(note)


_EHRHARDT_RE = re.compile(r"ehrhardt", re.IGNORECASE)


def _last_name(raw: str) -> str:
    plain = latex_to_plain(raw.strip())
    if "," in plain:
        return plain.split(",")[0].strip()
    parts = plain.split()
    return parts[-1] if parts else plain


def _is_alphabetical(authors: list[str]) -> bool:
    last_names = [_last_name(author).lower() for author in authors if author.strip()]
    return last_names == sorted(last_names)


def format_author(raw: str) -> str:
    plain = latex_to_plain(raw.strip())
    if not plain:
        return plain

    if "," in plain:
        last, first = plain.split(",", 1)
        last = last.strip()
        first = first.strip()
    else:
        parts = plain.split()
        if len(parts) >= 2:
            last = parts[-1]
            first = " ".join(parts[:-1])
        else:
            last = plain
            first = ""

    abbrev_parts = []
    for token in first.split():
        if len(token) == 1 or (len(token) == 2 and token.endswith(".")):
            abbrev_parts.append(token if token.endswith(".") else token + ".")
        elif token[0].isupper():
            abbrev_parts.append(token[0] + ".")
        else:
            abbrev_parts.append(token)

    display = f"{' '.join(abbrev_parts)} {last}".strip()
    if _EHRHARDT_RE.search(last):
        display = f"<b>{display}</b>"
    return display


def format_author_list(raw_field: str) -> tuple[str, bool]:
    if not raw_field:
        return "", False
    authors = re.split(r"\s+and\s+", raw_field, flags=re.IGNORECASE)
    formatted = [format_author(author) for author in authors if author.strip()]
    return ", ".join(formatted), _is_alphabetical(authors)


def venue_string(entry: dict) -> str:
    parts = []
    venue = latex_to_plain(entry.get("journal", "") or entry.get("booktitle", ""))
    if venue:
        parts.append(f"<i>{venue}</i>")

    vol = entry.get("volume", "").strip()
    num = entry.get("number", "").strip()
    pages = entry.get("pages", "").strip().replace("----", "–").replace("--", "–")
    year = entry.get("year", "").strip()

    citation = ""
    if vol and num:
        citation = f"{vol}({num})"
    elif vol:
        citation = vol
    if citation and pages:
        citation += f", {pages}"
    elif pages:
        citation = pages

    if citation:
        parts.append(citation)
    if year:
        parts.append(year)
    return ", ".join(parts)


def link_badges(entry: dict) -> str:
    badges = []
    pub_url = entry_url(entry)
    if pub_url:
        badges.append(f'[<a href="{pub_url}">print</a>]')
    pre_url = preprint_url(entry)
    if pre_url:
        badges.append(f'[<a href="{pre_url}">preprint</a>]')
    c_url = code_url(entry)
    if c_url:
        badges.append(f'[<a href="{c_url}">code</a>]')
    slides = entry.get("slides", "").strip()
    if slides:
        badges.append(f'[<a href="{slides}">slides</a>]')
    poster = entry.get("poster", "").strip()
    if poster:
        badges.append(f'[<a href="{poster}">poster</a>]')
    return " ".join(badges)


def event_name(entry: dict) -> str:
    return latex_to_plain(entry.get("name2", "") or entry.get("name", ""))


def presentation_badges_and_url(entry: dict) -> tuple[str, str]:
    event_url = ""
    badges = []
    event_names = [event_name(entry).lower()]
    alt_name = latex_to_plain(entry.get("name", "")).lower()
    if alt_name not in event_names:
        event_names.append(alt_name)
    for label, url in parse_keyword_links(entry):
        normalized = label.strip().lower()
        if normalized in _BADGE_LABELS or any(normalized.startswith(f"{name} ") for name in _BADGE_LABELS):
            badges.append(f'[<a href="{url}">{html.escape(label)}</a>]')
        elif not event_url and any(name and (name in normalized or normalized in name) for name in event_names):
            event_url = url
    return event_url, " ".join(badges)


def entry_to_html(entry: dict) -> str:
    authors_html, alphabetical = format_author_list(entry.get("author", ""))
    prefix = "<span>&#8224;</span> " if alphabetical else ""

    title = latex_to_plain(entry.get("title", "").strip("{}"))
    pub_url = entry_url(entry)
    # if pub_url:
    #     title_html = f'<a href="{pub_url}">{title}</a>'
    # else:
    #     pre_url = preprint_url(entry)
    #     title_html = f'<a href="{pre_url}">{title}</a>' if pre_url else title
    title_html = title

    venue = venue_string(entry)
    badges = link_badges(entry)

    line = f"{prefix}{authors_html}, {title_html}"
    if venue:
        line += f", {venue}"
    if badges:
        line += f" {badges}"
    return f"    <li>{line}</li>"


def presentation_sort_key(entry: dict) -> tuple[int, int, str, str]:
    year = int(entry.get("year", 0) or 0)
    month = int(entry.get("month", 0) or 0)
    return (-year, -month, event_name(entry).lower(), latex_to_plain(entry.get("title", "")).lower())


def publication_sort_key(entry: dict) -> tuple[int, str]:
    year = int(entry.get("year", 0) or 0)
    authors = re.split(r"\s+and\s+", entry.get("author", ""), flags=re.IGNORECASE)
    first_last_name = _last_name(authors[0]) if authors else ""
    return -year, first_last_name.lower()


def presentation_entry_to_html(entry: dict) -> str:
    prefix = "* " if "invited" in entry.get("type", "").lower() else ""
    name = html.escape(event_name(entry))
    event_url, badges = presentation_badges_and_url(entry)
    # if event_url:
    #     name_html = f'<a href="{event_url}">{name}</a>'
    # else:
    #     name_html = name
    name_html = name

    location = latex_to_plain(entry.get("location", "").strip())
    country = latex_to_plain(entry.get("country", "").strip())
    details = [html.escape(part) for part in (location, country) if part]
    title = html.escape(latex_to_plain(entry.get("title", "").strip("{}")).rstrip("."))
    year = entry.get("year", "").strip()
    note = note_to_html(entry)

    line = f"{prefix}{name_html}"
    if details:
        line += ", " + ", ".join(details)
    if year:
        line += f", {year}."
    if title:
        line += f" <i>{title}</i>"
    if note:
        line += f" {note}"
    if badges:
        line += f" {badges}"
    return f"    <li>{line}</li>"


def load_bib(filename: str) -> list[dict]:
    path = BIB_DIR / filename
    if not path.exists():
        print(f"  Warning: {path} not found, skipping.")
        return []
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    with path.open(encoding="utf-8") as handle:
        database = bibtexparser.load(handle, parser)
    return database.entries


def load_section(filenames: list[str]) -> list[dict]:
    entries = []
    for filename in filenames:
        entries.extend(load_bib(filename))
    return entries


def load_entries_by_id(filenames: list[str], ids: list[str]) -> list[dict]:
    remaining = set(ids)
    entries_by_id: dict[str, dict] = {}
    for filename in CV_BIB_RESOURCES:
        for entry in load_bib(filename):
            entry_id = entry.get("ID", "")
            if entry_id in remaining:
                entries_by_id[entry_id] = entry

    missing = [entry_id for entry_id in ids if entry_id not in entries_by_id]
    if missing:
        raise KeyError(
            "Missing BibTeX entries referenced by CV categories after searching CV resources: "
            + ", ".join(missing)
        )
    return [entries_by_id[entry_id] for entry_id in ids]


def section_html(entries: list[dict], list_class: str, formatter) -> str:
    items = "\n".join(formatter(entry) for entry in entries)
    return f'<ol reversed class="{list_class}">\n{items}\n</ol>'


# def source_note_html(filenames: list[str]) -> str:
#     joined = ", ".join(html.escape(filename) for filename in filenames)
#     return f'<div class="generated-source">Source: {joined}</div>'


def build_publications_fragment() -> str:
    publication_sources = [
        filename
        for filenames in PUBLICATION_SECTION_FILES.values()
        for filename in filenames
    ]
    blocks = [""]
    for heading, filenames in PUBLICATION_SECTION_FILES.items():
        print(f"Building section '{heading}' from: {', '.join(filenames)}")
        category_name = {
            "Peer-Reviewed Publications": "peerreviewed",
            "Preprints": "preprints",
            "Miscellaneous": "misc",
        }[heading]
        entries = load_entries_by_id(filenames, CV_CATEGORIES[category_name])
        entries.sort(key=publication_sort_key)
        print(f"  {len(entries)} entries loaded.")
        blocks.append(f"<h2>{heading}</h2>")
        blocks.append(section_html(entries, "compact-list", entry_to_html))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def build_presentations_fragment() -> str:
    presentation_sources = [
        filename
        for filenames in PRESENTATION_SECTION_FILES.values()
        for filename in filenames
    ]
    blocks = [""]
    for heading, filenames in PRESENTATION_SECTION_FILES.items():
        print(f"Building section '{heading}' from: {', '.join(filenames)}")
        category_name = {
            "Oral Presentations at Conferences, Workshops and Seminars": "conferences",
            "Poster Presentations": "posters",
        }[heading]
        entries = load_entries_by_id(filenames, CV_CATEGORIES[category_name])
        entries.sort(key=presentation_sort_key)
        print(f"  {len(entries)} entries loaded.")
        blocks.append(f"<h2>{heading}</h2>")
        blocks.append(section_html(entries, "compact-list", presentation_entry_to_html))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def main() -> None:
    print(f"Using BibTeX directory: {BIB_DIR}")
    publications_fragment = build_publications_fragment()
    presentations_fragment = build_presentations_fragment()

    PUBLICATIONS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLICATIONS_OUTPUT_FILE.write_text(publications_fragment, encoding="utf-8")
    PRESENTATIONS_OUTPUT_FILE.write_text(presentations_fragment, encoding="utf-8")

    print(f"\nWritten: {PUBLICATIONS_OUTPUT_FILE}")
    print(f"Written: {PRESENTATIONS_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
