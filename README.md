# AWS PDF Parser

A Python tool that converts AWS PDF documentation to LLM-readable text files, with each chapter split into separate files for optimal processing.

## Features

- Downloads PDFs from URLs
- Uses LangChain for intelligent PDF structure analysis
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
# Parse a PDF from URL
parse-pdf https://example.com/aws-doc.pdf

# This will create separate text files for each chapter
```

## Requirements

- Python 3.13+
- UV package manager
- Internet connection for downloading PDFs
