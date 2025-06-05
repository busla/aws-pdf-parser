#!/usr/bin/env python3
"""
AWS PDF Parser - Main entry point for parsing AWS PDFs into
LLM-readable text files.
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
import requests
import tempfile
import os
from typing import List, Dict, Any


def download_pdf(url: str, output_path: Path) -> None:
    """Download PDF from URL to local file."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded PDF to: {output_path}")
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        sys.exit(1)


def parse_pdf_with_langchain(pdf_path: Path) -> List[Dict[str, Any]]:
    """Parse PDF using LangChain to extract structured content."""
    try:
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        chapters = []
        current_chapter = {
            "title": "Introduction",
            "content": "",
            "page_start": 1
        }

        for i, doc in enumerate(documents):
            content = doc.page_content
            page_num = i + 1

            lines = content.split("\n")

            for line in lines:
                line = line.strip()
                if (
                    line.startswith("Chapter ")
                    or line.startswith("CHAPTER ")
                    or (len(line.split()) <= 5 and line.isupper() and
                        len(line) > 10)
                    or line.startswith("# ")
                    or (line.endswith("Overview") and len(line.split()) <= 3)
                ):

                    if current_chapter["content"].strip():
                        chapters.append(current_chapter.copy())

                    current_chapter = {
                        "title": line.replace("#", "").strip(),
                        "content": "",
                        "page_start": page_num,
                    }

                    break

            current_chapter["content"] += (
                f"\n--- Page {page_num} ---\n{content}\n"
            )

        if current_chapter["content"].strip():
            chapters.append(current_chapter)

        if not chapters:
            all_content = "\n".join([doc.page_content for doc in documents])
            chapters = [{
                "title": "Complete Document",
                "content": all_content,
                "page_start": 1
            }]

        return chapters

    except ImportError:
        print("LangChain dependencies not found. Please install them first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        sys.exit(1)


def save_chapters_to_files(chapters: List[Dict[str, Any]],
                           output_dir: Path) -> None:
    """Save each chapter to a separate text file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, chapter in enumerate(chapters):
        title = chapter["title"]
        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_")

        filename = f"{i+1:02d}_{safe_title}.txt"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {chapter['title']}\n\n")
            f.write(f"Starting from page: {chapter['page_start']}\n\n")
            f.write("=" * 80 + "\n\n")
            f.write(chapter["content"])

        print(f"Saved chapter: {filepath}")


def main():
    """Main entry point for the PDF parser."""
    parser = argparse.ArgumentParser(
        description="Parse AWS PDF documentation into LLM-readable text files"
    )
    parser.add_argument("pdf_url", help="URL of the PDF to parse")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("./parsed_chapters"),
        help="Output directory for chapter files (default: ./parsed_chapters)",
    )

    args = parser.parse_args()

    parsed_url = urlparse(args.pdf_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        print("Error: Please provide a valid URL")
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        print(f"Downloading PDF from: {args.pdf_url}")
        download_pdf(args.pdf_url, tmp_path)

        print("Parsing PDF structure...")
        chapters = parse_pdf_with_langchain(tmp_path)

        print(f"Found {len(chapters)} chapters")

        print(f"Saving chapters to: {args.output}")
        save_chapters_to_files(chapters, args.output)

        print(f"\nCompleted! {len(chapters)} chapter files created in "
              f"{args.output}")

    finally:
        if tmp_path.exists():
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()
