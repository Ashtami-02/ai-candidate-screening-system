"""
Run this once per role/book to build that role's knowledge base.

Usage (from the backend/ folder, with your venv active):
    python scripts/build_kb.py --pdf data/knowledge_base/ml_book.pdf --role ai_ml_engineer

You can run this multiple times for multiple roles, e.g.:
    python scripts/build_kb.py --pdf data/knowledge_base/ml_book.pdf --role ai_ml_engineer
    python scripts/build_kb.py --pdf data/knowledge_base/python_ml_book.pdf --role data_scientist
"""

import argparse
import sys
from pathlib import Path

# Allow "from app.xxx import yyy" imports when running this script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.rag.ingest import build_knowledge_base  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to the textbook PDF")
    parser.add_argument("--role", required=True, help="Role name, e.g. ai_ml_engineer")
    args = parser.parse_args()

    if not Path(args.pdf).exists():
        print(f"ERROR: file not found: {args.pdf}")
        sys.exit(1)

    build_knowledge_base(args.pdf, args.role)


if __name__ == "__main__":
    main()
