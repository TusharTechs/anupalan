"""PDF -> clean text, with OCR fallback for scanned or badly encoded orders."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

SIGNATURE = re.compile(
    r"^.*\n?\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}\s*\nI attest (?:to )?the accuracy and\s*\n(?:integrity of this document|authenticity of this order /\s*\njudgment)\s*$",
    re.M,
)
NOISE_LINES = re.compile(r"^\s*(Whether (?:speaking|reasoned|reportable)[^\n]*|Page \d+ of \d+|\$~\d+|\*+|#+)\s*$", re.I | re.M)


def _pdftotext(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout


def _ocr(pdf: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "200", "-png", str(pdf), f"{tmp}/p"], check=True, capture_output=True)
        pages = sorted(Path(tmp).glob("p*.png"))
        return "\n".join(
            subprocess.run(["tesseract", str(p), "-", "-l", "eng"], capture_output=True, text=True).stdout for p in pages
        )


def readable(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{3,}", text)
    tokens = text.split()
    return len(words) >= 40 and len(words) / max(len(tokens), 1) > 0.45


STAMP = re.compile(r"^.*\n?[ \t]*\d{4}\.\d{2}\.\d{2}[ \t]+\d{2}:\d{2}[^\n]*\n(?:[^\n]{0,4}attest[^\n]*\n?)?(?:[^\n]*(?:document|judgment|order /)[^\n]*\n?){0,2}", re.M | re.I)


def clean(text: str) -> str:
    text = SIGNATURE.sub("", text)
    text = STAMP.sub("\n", text)
    text = re.sub(r"[|T1l!]?\s*attest\s+(?:to\s+)?the\s+accuracy\s+and\s+(?:integrity|authenticity)\s+of\s+this\s+(?:document|order\s*/?\s*judgment|order)", " ", text, flags=re.I)
    text = re.sub(r"(?m)^\s*(?:CWP|COCP|LPA|RSA|CRM-M|CR|CM)[\s\-\d()&OM]*?(?:-\s*\d+\s*-)?\s*(?:\d{4}\s*:\s*PHHC\s*:\s*\d+(?:-DB)?)?\s*\d*\s*$", "", text)
    text = re.sub(r"\b\d{4}\s*:\s*PHHC\s*:\s*\d+(?:-DB)?\b", " ", text)
    text = re.sub(r"I attest (?:to )?the accuracy[\s\S]{0,80}?(?:document|judgment)", "", text)
    text = NOISE_LINES.sub("", text)
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)          # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def pdf_to_text(pdf: str | Path) -> tuple[str, str]:
    """Return (clean_text, method) where method is 'text' or 'ocr'."""
    pdf = Path(pdf)
    raw = _pdftotext(pdf)
    if readable(raw):
        return clean(raw), "text"
    try:
        return clean(_ocr(pdf)), "ocr"
    except (subprocess.CalledProcessError, OSError):
        return clean(raw), "unreadable"


def flow(text: str) -> str:
    """Re-flow hard-wrapped, often double-spaced court text into real paragraphs.

    A new paragraph starts only at a paragraph number ("2.", "[3]", "(iv)") or after a
    line that ends a sentence and is followed by an indented/capitalised short header.
    """
    out, cur = [], []
    para_start = re.compile(r"^\s*(?:\d{1,2}\.|\[\d{1,2}\]|\((?:[ivx]{1,4}|[a-h])\))\s+\S")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if para_start.match(line) and cur:
            out.append(" ".join(cur)); cur = []
        cur.append(line)
    if cur:
        out.append(" ".join(cur))
    return "\n\n".join(re.sub(r"\s{2,}", " ", p) for p in out)
