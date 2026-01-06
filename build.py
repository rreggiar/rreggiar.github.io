# !/usr/bin/env python3

import os
import markdown
from pathlib import Path
from jinja2 import Template
import shutil
from datetime import datetime
from pyzotero import zotero
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directories
VAULT_DIR = Path("vault")
OUTPUT_DIR = Path("docs")
TEMPLATE_DIR = Path("templates")
STATIC_DIR = Path("static")

# Extensions for markdown
MD_EXTENSIONS = ["meta", "fenced_code", "tables", "toc"]


def fetch_zotero_publications():
    """Fetch publications from Zotero API"""
    user_id = os.getenv("ZOTERO_USER_ID")
    api_key = os.getenv("ZOTERO_API_KEY")
    collection_key = os.getenv("ZOTERO_COLLECTION_KEY")
    your_last_name = os.getenv("YOUR_LAST_NAME", "Reggiardo")

    if not all([user_id, api_key, collection_key]):
        print("Warning: Zotero credentials not found in .env, skipping publications")
        return [], []

    print(f"Fetching publications from Zotero collection...")

    # Initialize Zotero client
    zot = zotero.Zotero(user_id, "user", api_key)

    # Fetch items from specific collection
    items = zot.collection_items(collection_key)

    publications = []

    for item in items:
        data = item["data"]

        # Skip non-publication items
        if data["itemType"] not in [
            "journalArticle",
            "conferencePaper",
            "bookSection",
            "book",
        ]:
            continue

        # Extract creators - separate authors and editors
        authors = []
        editors = []
        if "creators" in data:
            for creator in data["creators"]:
                last = creator.get("lastName", "")
                first = creator.get("firstName", "")
                name = f"{first} {last}".strip()

                if creator.get("creatorType") == "author":
                    authors.append(name)
                elif creator.get("creatorType") == "editor":
                    editors.append(name)

        # Check if you're first author
        is_first_author = False
        if authors and your_last_name.lower() in authors[0].lower():
            is_first_author = True

        # Extract DOI
        doi = data.get("DOI", "")

        # Get publication venue based on type
        venue = ""
        if data["itemType"] == "journalArticle":
            venue = data.get("publicationTitle", "")
        elif data["itemType"] == "conferencePaper":
            venue = data.get("proceedingsTitle", data.get("publicationTitle", ""))
        elif data["itemType"] == "bookSection":
            venue = data.get("bookTitle", "")
        elif data["itemType"] == "book":
            venue = data.get("publisher", "")

        # Build publication dict
        pub = {
            "title": data.get("title", "Untitled"),
            "authors": authors,
            "editors": editors,
            "author_string": ", ".join(authors),
            "editor_string": ", ".join(editors),
            "year": data.get("date", "")[:4] if data.get("date") else "",
            "venue": venue,
            "journal": data.get("publicationTitle", ""),  # Keep for backwards compat
            "volume": data.get("volume", ""),
            "pages": data.get("pages", ""),
            "doi": doi,
            "url": data.get("url", ""),
            "abstract": data.get("abstractNote", ""),
            "is_first_author": is_first_author,
            "item_type": data["itemType"],
            "publisher": data.get("publisher", ""),
        }

        publications.append(pub)
        print(f"  Found: {pub['title'][:60]}...")

    # Sort by year, newest first
    publications.sort(key=lambda x: x["year"], reverse=True)

    # Split into featured (first author) and collaborations
    featured = [p for p in publications if p["is_first_author"]]
    collaborations = [p for p in publications if not p["is_first_author"]]

    print(
        f"✓ Fetched {len(featured)} featured publications, {len(collaborations)} collaborations"
    )

    return featured, collaborations


def format_publication_html(pub):
    """Format a single publication as HTML"""
    html = f'<div class="publication">\n'
    html += f"  <strong>{pub['title']}</strong><br>\n"

    # Authors only (not editors)
    if pub["author_string"]:
        html += f'  <span class="authors">{pub["author_string"]}</span><br>\n'

    # Venue info based on item type
    venue_parts = []

    if pub["item_type"] == "journalArticle":
        # Journal article: Journal Name Volume, Pages (Year)
        venue = pub["venue"]
        if pub["volume"]:
            venue += f" {pub['volume']}"
        if pub["pages"]:
            venue += f", {pub['pages']}"
        venue_parts.append(f"<em>{venue}</em>")

    elif pub["item_type"] == "bookSection":
        # Book chapter: In: Book Title, Pages (Year)
        venue = f"In: {pub['venue']}"
        if pub["pages"]:
            venue += f", pp. {pub['pages']}"
        venue_parts.append(f"<em>{venue}</em>")

    elif pub["item_type"] == "conferencePaper":
        # Conference: Proceedings Name (Year)
        venue_parts.append(f"<em>{pub['venue']}</em>")

    elif pub["item_type"] == "book":
        # Book: Publisher (Year)
        if pub["publisher"]:
            venue_parts.append(f"<em>{pub['publisher']}</em>")

    # Add year
    if pub["year"]:
        venue_parts.append(f"({pub['year']})")

    if venue_parts:
        html += f"  {' '.join(venue_parts)}<br>\n"

    # Editors (if any)
    if pub["editor_string"]:
        html += (
            f'  <span class="editors">Edited by: {pub["editor_string"]}</span><br>\n'
        )

    # Links
    links = []
    if pub["doi"]:
        links.append(f'<a href="https://doi.org/{pub["doi"]}">DOI</a>')
    if pub["url"] and not pub["doi"]:
        links.append(f'<a href="{pub["url"]}">Link</a>')

    if links:
        html += f"  {' • '.join(links)}\n"

    html += "</div>\n"
    return html


def read_template(name):
    template_path = TEMPLATE_DIR / name
    print(f"Reading template: {template_path}")
    if not template_path.exists():
        print(f"ERROR: Template not found: {template_path}")
        return ""
    return template_path.read_text()


def parse_markdown(filepath):
    """Parse markdown file with frontmatter"""
    print(f"Parsing markdown: {filepath}")
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    content = filepath.read_text()

    html = md.convert(content)
    meta = (
        {k: v[0] if len(v) == 1 else v for k, v in md.Meta.items()}
        if hasattr(md, "Meta")
        else {}
    )

    return html, meta


def build_index():
    """Build main index page with publications"""
    index_md = VAULT_DIR / "index.md"

    if not index_md.exists():
        print(f"ERROR: {index_md} not found!")
        return

    html_content, meta = parse_markdown(index_md)

    # Fetch publications from Zotero
    featured, collaborations = fetch_zotero_publications()

    # Format publications as HTML
    featured_html = ""
    if featured:
        featured_html = (
            '<section id="featured-publications">\n<h2>Featured Publications</h2>\n'
        )
        for pub in featured:
            featured_html += format_publication_html(pub)
        featured_html += "</section>\n"

    collab_html = ""
    if collaborations:
        collab_html = '<section id="collaborations">\n<h2>Collaborations</h2>\n'
        for pub in collaborations:
            collab_html += format_publication_html(pub)
        collab_html += "</section>\n"

    template = Template(read_template("index.html"))

    rendered = template.render(
        content=html_content,
        featured_publications=featured_html,
        collaborations=collab_html,
        posts=[],
        title=meta.get("title", "Home"),
        subtitle=meta.get("subtitle", ""),
        current_year=datetime.now().year,
    )

    output_file = OUTPUT_DIR / "index.html"
    output_file.write_text(rendered)
    print(f"✓ Built: {output_file}")


def copy_static():
    """Copy static files to output"""
    if not STATIC_DIR.exists():
        print(f"Warning: {STATIC_DIR} doesn't exist, skipping static files")
        return

    for item in STATIC_DIR.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(STATIC_DIR)
            dest = OUTPUT_DIR / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            print(f"Copied: {rel_path}")


def main():
    print("Starting build...\n")

    # Clean output
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()
    print(f"Created output dir: {OUTPUT_DIR}\n")

    # Build index with publications
    build_index()

    # Copy static assets
    copy_static()

    print("\n✓ Build complete!")
    print(f"\nGenerated files:")
    for f in OUTPUT_DIR.rglob("*"):
        if f.is_file():
            print(f"  {f}")


if __name__ == "__main__":
    main()
