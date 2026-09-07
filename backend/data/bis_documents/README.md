# backend/data/bis_documents/

Drop your **real** BIS documents here. Supported formats: `.pdf`, `.txt`, `.json`.

This folder is currently empty — no sample/fake BIS content has been
placed here, since real documents will be provided separately.

## How to add documents

Just copy files in. Then run, from `backend/`:

```bash
python -m rag.ingestion
```

Re-running the command later only processes new or changed files
(tracked via a hash cache) — it won't re-embed everything from scratch
every time.

To force a full rebuild of the vector index:

```bash
python -m rag.ingestion --force
```

## Attaching proper source metadata

PDFs and plain text files don't carry structured fields like "official
title" or "source". To make sure citations shown to users are accurate
(not just derived from the filename), create a `metadata.json` file in
this folder — see `metadata.example.json` for the format — mapping each
filename to its real title, source, URL, and category:

```json
{
  "is_302_household_appliances.pdf": {
    "title": "IS 302 - Safety of Household Electrical Appliances",
    "source": "Bureau of Indian Standards",
    "url": "https://bis.gov.in/path-to-actual-document",
    "category": "Product Standard"
  }
}
```

If a file has no entry in `metadata.json`, the ingestion script will:
- derive a title from the filename,
- mark the source as "Unknown source - please update metadata.json",
- print a notice in the terminal so you know to fill it in.

This is intentional: **the system never invents a real BIS source name.**
An unlabeled/uncertain source stays visibly unlabeled rather than being
disguised as an authoritative one.

## JSON document format

If you have structured BIS data (e.g. scraped or exported), `.json`
files can look like any of these:

**Single document:**
```json
{
  "title": "IS 302 Part 1",
  "source": "Bureau of Indian Standards",
  "url": "https://bis.gov.in/...",
  "category": "Product Standard",
  "content": "Full text of the document goes here..."
}
```

**Single document, split by page** (page numbers will show in citations):
```json
{
  "title": "IS 302 Part 1",
  "source": "Bureau of Indian Standards",
  "category": "Product Standard",
  "pages": [
    { "page": 1, "text": "Text of page 1..." },
    { "page": 2, "text": "Text of page 2..." }
  ]
}
```

**Multiple documents in one file:**
```json
[
  { "title": "Doc A", "source": "BIS", "content": "..." },
  { "title": "Doc B", "source": "BIS", "content": "..." }
]
```

## What NOT to put here

Do not add fabricated or placeholder BIS content and pass it off as
real. If you need something in the pipeline for a quick UI test before
real documents arrive, clearly mark it, e.g. `DEMO_only_sample.txt`
starting with a line like `[DEMO DATA - NOT AN OFFICIAL BIS DOCUMENT]`,
and remove it before the actual demo.
