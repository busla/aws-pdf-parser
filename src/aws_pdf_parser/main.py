#!/usr/bin/env python3
"""
AWS PDF Parser - Main entry point for parsing AWS PDFs into
LLM-readable text files.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests


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


def parse_pdf_with_unstructured(pdf_path: Path) -> List[Dict[str, Any]]:
    """Parse PDF using UnstructuredLoader for better layout analysis."""
    try:
        from langchain_unstructured import UnstructuredLoader  # type: ignore

        loader = UnstructuredLoader(str(pdf_path), strategy="hi_res")
        documents = loader.load()

        chapters = []

        all_content = ""
        for doc in documents:
            all_content += doc.page_content + "\n"

        sections = []
        current_section = ""
        current_title = "Introduction"

        lines = all_content.split("\n")
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            is_new_section = False
            new_title = None

            if line_stripped.startswith(("POST /", "GET /", "PUT /", "DELETE /")) and (
                "HTTP/1.1" in line_stripped or "/" in line_stripped
            ):
                is_new_section = True
                new_title = (
                    f"API_{line_stripped.split()[1].replace('/', '_').strip('_')}"
                )

            elif (
                len(line_stripped) > 0
                and line_stripped[0].isupper()
                and any(c.isupper() for c in line_stripped[1:])
                and not line_stripped.startswith(("HTTP", "Content-", "Amazon Bedrock"))
                and len(line_stripped.split()) == 1
                and len(line_stripped) > 5
                and not line_stripped.endswith((".", ":", ";"))
            ):
                is_new_section = True
                new_title = line_stripped

            elif line_stripped.endswith(
                (" Reference", " API")
            ) and not line_stripped.startswith("Amazon Bedrock API Reference"):
                is_new_section = True
                new_title = line_stripped

            elif line_stripped in ["Data Types", "Actions", "Errors", "Examples"]:
                is_new_section = True
                new_title = line_stripped

            if is_new_section and current_section.strip():
                sections.append(
                    {"title": current_title, "content": current_section.strip()}
                )
                current_section = ""
                current_title = new_title or line_stripped

            current_section += line + "\n"

        if current_section.strip():
            sections.append(
                {"title": current_title, "content": current_section.strip()}
            )

        page_counter = 1
        for i, section in enumerate(sections):
            content_lines = len(section["content"].split("\n"))

            if content_lines < 50 and i < len(sections) - 1:
                sections[i + 1]["content"] = (
                    section["content"] + "\n\n" + sections[i + 1]["content"]
                )
                sections[i + 1]["title"] = (
                    f"{section['title']} - {sections[i + 1]['title']}"
                )
                continue

            chapters.append(
                {
                    "title": section["title"],
                    "content": section["content"],
                    "page_start": page_counter,
                }
            )

            page_counter += max(1, content_lines // 40)

        if not chapters:
            chapters = [
                {"title": "Complete Document", "content": all_content, "page_start": 1}
            ]

        return chapters

    except ImportError:
        print("Unstructured dependencies not found. Please install them first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing PDF with UnstructuredLoader: {e}")
        sys.exit(1)


def parse_pdf_with_langchain(pdf_path: Path) -> List[Dict[str, Any]]:
    """Parse PDF using LangChain to extract structured content."""
    try:
        from langchain_community.document_loaders import PyPDFLoader  # type: ignore

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        chapters = []

        all_content = ""
        for doc in documents:
            all_content += doc.page_content + "\n"

        sections = []
        current_section = ""
        current_title = "Introduction"

        lines = all_content.split("\n")
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            is_new_section = False
            new_title = None

            if (
                line_stripped.startswith(("POST /", "GET /", "PUT /", "DELETE /"))
                and "HTTP/1.1" in line_stripped
            ):
                is_new_section = True
                new_title = (
                    f"API_{line_stripped.split()[1].replace('/', '_').strip('_')}"
                )

            elif (
                len(line_stripped) > 0
                and line_stripped[0].isupper()
                and any(c.isupper() for c in line_stripped[1:])
                and not line_stripped.startswith(("HTTP", "Content-", "Amazon Bedrock"))
                and len(line_stripped.split()) == 1
                and len(line_stripped) > 5
            ):
                is_new_section = True
                new_title = line_stripped

            elif line_stripped.endswith(" Reference") and not line_stripped.startswith(
                "Amazon Bedrock API Reference"
            ):
                is_new_section = True
                new_title = line_stripped

            elif (
                line_stripped.startswith("Data Types")
                and len(line_stripped.split()) <= 4
            ):
                is_new_section = True
                new_title = line_stripped

            elif (
                line_stripped.startswith("Actions") and len(line_stripped.split()) <= 3
            ):
                is_new_section = True
                new_title = line_stripped

            elif line_stripped.startswith("Errors") and len(line_stripped.split()) <= 3:
                is_new_section = True
                new_title = line_stripped

            if is_new_section and current_section.strip():
                sections.append(
                    {"title": current_title, "content": current_section.strip()}
                )
                current_section = ""
                current_title = new_title or line_stripped

            current_section += line + "\n"

        if current_section.strip():
            sections.append(
                {"title": current_title, "content": current_section.strip()}
            )

        page_counter = 1
        for i, section in enumerate(sections):
            content_lines = len(section["content"].split("\n"))

            if content_lines < 40 and i < len(sections) - 1:
                sections[i + 1]["content"] = (
                    section["content"] + "\n\n" + sections[i + 1]["content"]
                )
                sections[i + 1]["title"] = (
                    f"{section['title']} - {sections[i + 1]['title']}"
                )
                continue

            chapters.append(
                {
                    "title": section["title"],
                    "content": section["content"],
                    "page_start": page_counter,
                }
            )

            page_counter += max(1, content_lines // 50)

        if not chapters:
            chapters = [
                {"title": "Complete Document", "content": all_content, "page_start": 1}
            ]

        return chapters

    except ImportError:
        print("LangChain dependencies not found. Please install them first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        sys.exit(1)


def remove_repetitive_content(content: str) -> str:
    """Remove repetitive copyright text and headers."""
    lines = content.split("\n")
    seen_lines = set()
    filtered_lines = []

    for line in lines:
        stripped = line.strip()

        if (
            stripped.startswith("Copyright ©")
            or stripped == "AWS Well-Architected Framework Framework"
            or stripped.startswith("Amazon's trademarks")
            or len(stripped) > 50
            and stripped.count("AWS Well-Architected") > 1
        ):
            continue

        if stripped in seen_lines and len(stripped) > 20:
            continue

        seen_lines.add(stripped)
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def is_code_line(line: str) -> bool:
    """Detect if a line is part of a code block."""
    return (
        line.startswith(("{", "}", "POST /", "GET /", "PUT /", "DELETE /", "HTTP/"))
        or "Content-type:" in line
        or line.startswith(("curl ", "aws ", "python ", "$ "))
        or line.endswith(("{", "}"))
        or (line.startswith('"') and line.endswith('"'))
        or "=" in line
        and ("&&" in line or "||" in line)
    )


def is_header_line(line: str, index: int, all_lines: list) -> bool:
    """Improved header detection."""
    if len(line) < 3 or len(line) > 60:
        return False

    next_line = all_lines[index + 1].strip() if index + 1 < len(all_lines) else ""

    return (
        line[0].isupper()
        and len(line.split()) <= 6
        and not line.endswith(".")
        and not line.startswith(("HTTP", "AWS Well-Architected Framework"))
        and not next_line.startswith(line[:10])
    )


def is_list_item(line: str) -> bool:
    """Detect list items."""
    return line.startswith(("• ", "- ", "* ")) or (
        len(line) > 2 and line[0].isdigit() and line[1] in (".", ")")
    )


def format_list_item(line: str) -> str:
    """Format list items consistently."""
    return f"- {line.lstrip('•-* ').lstrip('0123456789. ')}"


def format_content_as_markdown(content: str) -> str:
    """Convert plain text content to markdown with preserved formatting."""
    content = remove_repetitive_content(content)
    lines = content.split("\n")
    formatted_lines = []
    in_code_block = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if in_code_block:
                formatted_lines.append("")
            else:
                formatted_lines.append("")
            i += 1
            continue

        if is_code_line(stripped) and not in_code_block:
            in_code_block = True
            code_block_buffer = ["```"]

            while i < len(lines) and (
                is_code_line(lines[i].strip())
                or lines[i].strip() == ""
                or lines[i].startswith(("  ", "\t"))
            ):
                code_block_buffer.append(lines[i])
                i += 1

            code_block_buffer.append("```")
            formatted_lines.extend(code_block_buffer)
            in_code_block = False
            continue

        if is_header_line(stripped, i, lines):
            formatted_lines.append(f"## {stripped}")
            i += 1
            continue

        if is_list_item(stripped):
            formatted_lines.append(format_list_item(stripped))
            i += 1
            continue

        formatted_lines.append(stripped)
        i += 1

    return "\n".join(formatted_lines)


def save_chapters_to_files(chapters: List[Dict[str, Any]], output_dir: Path) -> None:
    """Save each chapter to a separate markdown file with preserved formatting."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, chapter in enumerate(chapters):
        title = chapter["title"]
        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_")

        filename = f"{i + 1:02d}_{safe_title}.md"
        filepath = output_dir / filename

        formatted_content = format_content_as_markdown(chapter["content"])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {chapter['title']}\n\n")
            f.write(f"**Starting from page:** {chapter['page_start']}\n\n")
            f.write("---\n\n")
            f.write(formatted_content)

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
        help="Output directory for markdown chapter files (default: ./parsed_chapters)",
    )
    parser.add_argument(
        "--strategy",
        choices=["simple", "advanced"],
        default="simple",
        help="Parsing strategy: 'simple' uses PyPDF, 'advanced' uses Unstructured",
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

        print(f"Parsing PDF structure using {args.strategy} strategy...")
        if args.strategy == "advanced":
            chapters = parse_pdf_with_unstructured(tmp_path)
        else:
            chapters = parse_pdf_with_langchain(tmp_path)

        print(f"Found {len(chapters)} chapters")

        print(f"Saving chapters to: {args.output}")
        save_chapters_to_files(chapters, args.output)

        print(f"\nCompleted! {len(chapters)} chapter files created in {args.output}")

    finally:
        if tmp_path.exists():
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()
