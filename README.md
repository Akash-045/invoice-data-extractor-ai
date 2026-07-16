# 📄 AI Invoice Data Extractor
 
AI-powered pipeline that extracts, validates, and stores structured data from PDF invoices — built for German small businesses to automate manual bookkeeping while enforcing German VAT compliance rules.
 
🔗 **Live App:** [invoice-data-extractor-ai.streamlit.app](https://invoice-data-extractor-ai-yh4igpwewqmu7dwbrgbcg8.streamlit.app)
💻 **GitHub:** [github.com/Akash-045/invoice-data-extractor-ai](https://github.com/Akash-045/invoice-data-extractor-ai)
 
---
 
## Overview
 
Small businesses lose hours manually re-typing invoice data into spreadsheets and accounting software. This project automates that process end-to-end:
 
**PDF invoice → text extraction → AI structured extraction → validation → database storage → dashboard**
 
Instead of a rigid, template-specific parser, the pipeline uses the **Claude API** to read invoices the way a human bookkeeper would — generalizing across different vendor layouts — while a deterministic validation layer double-checks the AI's output against real German invoicing rules (correct VAT math, valid VAT rates, valid dates) before anything is trusted or stored.
 
## Why this project
 
Most "AI chatbot" portfolio projects show that someone can call an API. This project instead tackles a real, unglamorous business pain point — bookkeeping — and treats AI output the way a production system should: **verify before you trust it.** It also reflects specific German business context: VAT rates (19%/7%), invoice requirements under §14 UStG, and the ongoing shift toward mandatory e-invoicing (XRechnung/ZUGFeRD from 2027–2028).
 
## Architecture
 
```
PDF Invoice
    │
    ▼
[1] Text Extraction (pdfplumber)
    │
    ▼
[2] Structured Extraction (Claude API → JSON)
    │
    ▼
[3] Validation (VAT math, date checks, business rules)
    │
    ▼
[4] Storage (SQLite)
    │
    ▼
[5] Streamlit Dashboard (upload, view, filter, export)
```
 
## Tech Stack
 
| Layer | Tools |
|---|---|
| PDF parsing | `pdfplumber` |
| AI extraction | Claude API (`anthropic`) |
| Validation | Python (custom business rules) |
| Storage | SQLite |
| Data handling | `pandas` |
| Web app | `Streamlit` |
| Secrets management | `python-dotenv` (local) / Streamlit Secrets (cloud) |
 
## Project Structure
 
```
invoice-data-extractor-ai/
├── 01_extract_text.ipynb      # PDF → raw text
├── 02_extract_fields.ipynb    # raw text → structured JSON (Claude API)
├── 03_validate.ipynb          # validate extracted data against business rules
├── 04_store_data.ipynb        # store validated data in SQLite
├── app.py                     # Streamlit web app (full pipeline, live)
├── requirements.txt
├── data/
│   ├── raw_invoices/           # sample PDF invoices
│   └── processed/
│       ├── raw_text/           # extracted text
│       ├── extracted_json/     # structured AI output
│       ├── validated/          # validated records with status
│       └── invoices.db         # SQLite database
└── README.md
```
 
## Key Features
 
- ✅ **AI-powered extraction** — generalizes across different invoice layouts without custom templates
- ✅ **Built-in validation layer** — catches VAT math errors, invalid dates, and unusual rates *before* data is trusted
- ✅ **Full audit trail** — every invoice keeps its validation status, errors, and warnings
- ✅ **German VAT compliance logic** — checks against real §14 UStG-relevant rules (19%/7% VAT rates, VAT math, totals)
- ✅ **Live, interactive dashboard** — upload invoices, see KPIs, filter by status, export to CSV
- ✅ **Secure key handling** — no hardcoded API keys; uses `.env` locally and Streamlit Secrets in production
## Validation Rules
 
The pipeline doesn't blindly trust AI output. Each invoice is checked for:
- Required fields present (vendor, invoice number, date, amounts, currency)
- VAT rate is a valid German rate (0%, 7%, 19%)
- VAT amount math is correct (`net × vat_rate/100 ≈ vat_amount`)
- Total math is correct (`net + vat ≈ total`)
- Invoice date is valid and not in the future
- Amounts are non-negative
Invoices are classified as **Passed**, **Warning**, or **Failed** — so a human only needs to review flagged exceptions, not every invoice.
 
## Running Locally
 
```bash
# Clone the repo
git clone https://github.com/Akash-045/invoice-data-extractor-ai.git
cd invoice-data-extractor-ai
 
# Install dependencies
pip install -r requirements.txt
 
# Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env
 
# Run the app
streamlit run app.py
```
 
## Future Improvements
 
- OCR support for scanned invoices (not just digital PDFs)
- Support for XRechnung/ZUGFeRD e-invoice formats, ahead of Germany's 2027–2028 mandatory e-invoicing rollout
- Multi-currency and multi-country VAT rule sets
- Duplicate invoice detection
- Export directly to DATEV-compatible format for accountants
## Author
 
**Akash Samantray**
Data Analyst | Ironhack Berlin Data Analytics Bootcamp
[LinkedIn](https://linkedin.com/in/akash-samantray) · [GitHub](https://github.com/Akash-045)