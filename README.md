# AWS PDF Parser

A Python tool that converts AWS PDF documentation to LLM-readable text files, with each chapter split into separate files for optimal processing.

## Features

- Downloads PDFs from URLs
- Two parsing strategies for different document types:
  - **Simple**: Uses PyPDF for basic text extraction (fast, reliable)
  - **Advanced**: Uses UnstructuredLoader for layout analysis (slower, better structure detection)
- Intelligent chapter detection for API documentation
- Splits content by chapters into separate text files
- Optimized for LLM readability

## Installation

```bash
uv venv --python 3.13
source .venv/bin/activate
uv sync
```

## Usage

```bash
# Parse a PDF from URL using simple strategy (default)
parse-pdf https://example.com/aws-doc.pdf

# Parse using advanced strategy for better layout analysis
parse-pdf https://example.com/aws-doc.pdf --strategy advanced

# Specify custom output directory
parse-pdf https://example.com/aws-doc.pdf -o my_output_dir
```

## Parsing Strategies

### Simple Strategy (Default)
- Uses PyPDF for fast text extraction
- Good for most documents with clear structure
- Faster processing time
- Recommended for large documents

### Advanced Strategy
- Uses UnstructuredLoader with hi-res layout analysis
- Better detection of document structure and sections
- Slower processing but more accurate for complex layouts
- Requires additional system dependencies (poppler-utils)

## Development

This project uses Ruff for linting and formatting:

```bash
# Check code quality
ruff check src/

# Format code
ruff format src/
```

## Requirements

- Python 3.13+
- UV package manager
- Internet connection for downloading PDFs
- poppler-utils (for advanced parsing strategy)
