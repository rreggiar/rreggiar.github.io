#!/usr/bin/env python3
import os
import markdown
from pathlib import Path
from jinja2 import Template
import shutil
import yaml
from datetime import datetime

# Directories
VAULT_DIR = Path("vault")
OUTPUT_DIR = Path("docs")
TEMPLATE_DIR = Path("templates")
STATIC_DIR = Path("static")

# Extensions for markdown
MD_EXTENSIONS = ["meta", "fenced_code", "tables", "toc", "codehilite"]


def read_template(name):
    return (TEMPLATE_DIR / name).read_text()


def parse_markdown(filepath):
    """Parse markdown file with frontmatter"""
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    content = filepath.read_text()

    html = md.convert(content)
    meta = (
        {k: v[0] if len(v) == 1 else v for k, v in md.Meta.items()}
        if hasattr(md, "Meta")
        else {}
    )

    return html, meta


def build_page(md_path, template_name="base.html"):
    """Convert a markdown file to HTML"""
    html_content, meta = parse_markdown(md_path)

    template = Template(read_template(template_name))

    # Determine output path
    rel_path = md_path.relative_to(VAULT_DIR)
    out_path = OUTPUT_DIR / rel_path.with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Render template
    rendered = template.render(
        content=html_content,
        title=meta.get("title", rel_path.stem),
        date=meta.get("date", ""),
        **meta,
    )

    out_path.write_text(rendered)
    print(f"Built: {out_path}")
    return out_path, meta


def collect_posts():
    """Collect all posts with metadata for index"""
    posts = []
    posts_dir = VAULT_DIR / "posts"

    if posts_dir.exists():
        for md_file in posts_dir.glob("*.md"):
            _, meta = parse_markdown(md_file)
            posts.append(
                {
                    "title": meta.get("title", md_file.stem),
                    "date": meta.get("date", ""),
                    "url": f"posts/{md_file.stem}.html",
                    "description": meta.get("description", ""),
                }
            )

    # Sort by date, newest first
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


def build_index():
    """Build main index page"""
    index_md = VAULT_DIR / "index.md"

    if not index_md.exists():
        print(f"ERROR: {index_md} not found!")
        return

    html_content, meta = parse_markdown(index_md)
    template = Template(read_template("index.html"))

    rendered = template.render(
        content=html_content,
        posts=[],
        title=meta.get("title", "Home"),  # Get from meta or use default
        subtitle=meta.get("subtitle", ""),
        current_year=datetime.now().year,  # Add this
        # Don't unpack meta here to avoid conflicts
    )

    output_file = OUTPUT_DIR / "index.html"
    output_file.write_text(rendered)
    print(f"✓ Built: {output_file}")


def copy_static():
    """Copy static files to output"""
    if STATIC_DIR.exists():
        for item in STATIC_DIR.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(STATIC_DIR)
                dest = OUTPUT_DIR / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
        print("Copied static files")


def main():
    # Clean output
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()

    # Build all markdown files
    for md_file in VAULT_DIR.rglob("*.md"):
        if md_file.name != "index.md":
            build_page(md_file)

    # Build index separately (includes post list)
    build_index()

    # Copy static assets
    copy_static()

    print("\n✓ Build complete!")


if __name__ == "__main__":
    main()
