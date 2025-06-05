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
            
            if (line_stripped.startswith(("POST /", "GET /", "PUT /", "DELETE /")) and 
                ("HTTP/1.1" in line_stripped or "/" in line_stripped)):
                is_new_section = True
                new_title = f"API_{line_stripped.split()[1].replace('/', '_').strip('_')}"
            
            elif (len(line_stripped) > 0 and 
                  line_stripped[0].isupper() and 
                  any(c.isupper() for c in line_stripped[1:]) and
                  not line_stripped.startswith(("HTTP", "Content-", "Amazon Bedrock")) and
                  len(line_stripped.split()) == 1 and
                  len(line_stripped) > 5 and
                  not line_stripped.endswith((".", ":", ";"))):
                is_new_section = True
                new_title = line_stripped
            
            elif (line_stripped.endswith((" Reference", " API")) and 
                  not line_stripped.startswith("Amazon Bedrock API Reference")):
                is_new_section = True
                new_title = line_stripped
            
            elif line_stripped in ["Data Types", "Actions", "Errors", "Examples"]:
                is_new_section = True
                new_title = line_stripped
            
            if is_new_section and current_section.strip():
                sections.append({
                    "title": current_title,
                    "content": current_section.strip()
                })
                current_section = ""
                current_title = new_title or line_stripped
            
            current_section += line + "\n"
        
        if current_section.strip():
            sections.append({
                "title": current_title,
                "content": current_section.strip()
            })
        
        page_counter = 1
        for i, section in enumerate(sections):
            content_lines = len(section["content"].split("\n"))
            
            if content_lines < 15 and i < len(sections) - 1:
                sections[i + 1]["content"] = section["content"] + "\n\n" + sections[i + 1]["content"]
                sections[i + 1]["title"] = f"{section['title']} - {sections[i + 1]['title']}"
                continue
            
            chapters.append({
                "title": section["title"],
                "content": section["content"],
                "page_start": page_counter
            })
            
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
        current_chapter = {"title": "Introduction", "content": "", "page_start": 1}
        
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
            
            if (line_stripped.startswith(("POST /", "GET /", "PUT /", "DELETE /")) and 
                "HTTP/1.1" in line_stripped):
                is_new_section = True
                new_title = f"API_{line_stripped.split()[1].replace('/', '_').strip('_')}"
            
            elif (len(line_stripped) > 0 and 
                  line_stripped[0].isupper() and 
                  any(c.isupper() for c in line_stripped[1:]) and
                  not line_stripped.startswith(("HTTP", "Content-", "Amazon Bedrock")) and
                  len(line_stripped.split()) == 1 and
                  len(line_stripped) > 5):
                is_new_section = True
                new_title = line_stripped
            
            elif (line_stripped.endswith(" Reference") and 
                  not line_stripped.startswith("Amazon Bedrock API Reference")):
                is_new_section = True
                new_title = line_stripped
            
            elif (line_stripped.startswith("Data Types") and len(line_stripped.split()) <= 4):
                is_new_section = True
                new_title = line_stripped
                
            elif (line_stripped.startswith("Actions") and len(line_stripped.split()) <= 3):
                is_new_section = True
                new_title = line_stripped
                
            elif (line_stripped.startswith("Errors") and len(line_stripped.split()) <= 3):
                is_new_section = True
                new_title = line_stripped
            
            if is_new_section and current_section.strip():
                sections.append({
                    "title": current_title,
                    "content": current_section.strip()
                })
                current_section = ""
                current_title = new_title or line_stripped
            
            current_section += line + "\n"
        
        if current_section.strip():
            sections.append({
                "title": current_title,
                "content": current_section.strip()
            })
        
        page_counter = 1
        for i, section in enumerate(sections):
            content_lines = len(section["content"].split("\n"))
            
            if content_lines < 10 and i < len(sections) - 1:
                sections[i + 1]["content"] = section["content"] + "\n\n" + sections[i + 1]["content"]
                sections[i + 1]["title"] = f"{section['title']} - {sections[i + 1]['title']}"
                continue
            
            chapters.append({
                "title": section["title"],
                "content": section["content"],
                "page_start": page_counter
            })
            
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


def format_content_as_markdown(content: str) -> str:
    """Convert plain text content to markdown with preserved formatting."""
    lines = content.split('\n')
    formatted_lines = []
    in_code_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped:
            formatted_lines.append('')
            continue
            
        if (stripped.startswith(('{', 'POST /', 'GET /', 'PUT /', 'DELETE /', 'HTTP/')) or
            stripped.endswith(('{', '}')) or
            'Content-type:' in stripped or
            stripped.startswith(('curl ', 'aws ', 'python '))):
            if not in_code_block:
                formatted_lines.append('```')
                in_code_block = True
            formatted_lines.append(line)
            continue
        elif in_code_block and not stripped.startswith((' ', '\t')):
            formatted_lines.append('```')
            in_code_block = False
        
        if (len(stripped) > 3 and 
            (stripped.isupper() or 
             stripped.endswith((' Reference', ' API', ' Overview')) or
             (stripped[0].isupper() and len(stripped.split()) <= 4 and 
              not stripped.endswith('.')))):
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if (not stripped.startswith(('HTTP', 'AWS', 'AMAZON')) and
                len(stripped) < 60 and
                not next_line.startswith(stripped[:10])):
                formatted_lines.append(f"## {stripped}")
                continue
        
        if (stripped.startswith(('• ', '- ', '* ')) or
            (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ('.', ')'))):
            formatted_lines.append(f"- {stripped.lstrip('•-* ').lstrip('0123456789. ')}")
            continue
            
        if line.startswith(('  • ', '  - ', '    • ', '    - ')):
            formatted_lines.append(f"  - {stripped.lstrip('•-* ')}")
            continue
        
        formatted_lines.append(stripped)
    
    if in_code_block:
        formatted_lines.append('```')
    
    return '\n'.join(formatted_lines)


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
