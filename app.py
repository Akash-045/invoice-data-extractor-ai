import streamlit as st
import pdfplumber
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv
from anthropic import Anthropic
import streamlit as st

load_dotenv()

# --- Setup ---
DB_PATH = Path("data/processed/invoices.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY"))
client = Anthropic(api_key=api_key)
VALID_VAT_RATES = [0, 7, 19]

EXTRACTION_PROMPT = """You are an invoice data extraction system for German businesses.

Extract the following fields from the invoice text below. Return ONLY valid JSON,
no explanation, no markdown formatting, no code fences.

Fields to extract:
- vendor: company/sender name
- invoice_number: the invoice/Rechnungsnummer
- invoice_date: in format YYYY-MM-DD
- net_amount: number, no currency symbol
- vat_rate: number (e.g. 19 or 7)
- vat_amount: number, no currency symbol
- total_amount: number, no currency symbol
- currency: 3-letter code (e.g. EUR)

If a field cannot be found, set its value to null.

Invoice text:
---
{invoice_text}
---

Return only the JSON object."""


# --- Pipeline functions ---
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_fields_from_text(invoice_text):
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(invoice_text=invoice_text)}]
    )
    raw_response = message.content[0].text.strip()
    raw_response = re.sub(r"^```json\s*|\s*```$", "", raw_response).strip()
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        return None


def validate_invoice(data):
    errors, warnings = [], []
    required_fields = ["vendor", "invoice_number", "invoice_date",
                        "net_amount", "vat_rate", "vat_amount",
                        "total_amount", "currency"]
    for field in required_fields:
        if data.get(field) is None:
            errors.append(f"Missing field: {field}")
    if errors:
        return errors, warnings

    if data["vat_rate"] not in VALID_VAT_RATES:
        warnings.append(f"Unusual VAT rate: {data['vat_rate']}%")

    expected_vat = round(data["net_amount"] * data["vat_rate"] / 100, 2)
    if abs(expected_vat - data["vat_amount"]) > 0.02:
        errors.append(f"VAT mismatch: expected {expected_vat}, got {data['vat_amount']}")

    expected_total = round(data["net_amount"] + data["vat_amount"], 2)
    if abs(expected_total - data["total_amount"]) > 0.02:
        errors.append(f"Total mismatch: expected {expected_total}, got {data['total_amount']}")

    try:
        parsed_date = datetime.strptime(data["invoice_date"], "%Y-%m-%d")
        if parsed_date > datetime.now():
            warnings.append(f"Date is in the future: {data['invoice_date']}")
    except (ValueError, TypeError):
        errors.append(f"Invalid date format: {data.get('invoice_date')}")

    for f in ["net_amount", "vat_amount", "total_amount"]:
        if data[f] < 0:
            errors.append(f"Negative value in {f}")

    return errors, warnings


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            vendor TEXT, invoice_number TEXT, invoice_date TEXT,
            net_amount REAL, vat_rate REAL, vat_amount REAL, total_amount REAL,
            currency TEXT, status TEXT, errors TEXT, warnings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def store_invoice(filename, data, status, errors, warnings):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO invoices
        (filename, vendor, invoice_number, invoice_date, net_amount, vat_rate,
         vat_amount, total_amount, currency, status, errors, warnings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename, data.get("vendor"), data.get("invoice_number"), data.get("invoice_date"),
        data.get("net_amount"), data.get("vat_rate"), data.get("vat_amount"),
        data.get("total_amount"), data.get("currency"), status,
        json.dumps(errors, ensure_ascii=False), json.dumps(warnings, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()


def load_all_invoices():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM invoices ORDER BY created_at DESC", conn)
    conn.close()
    return df


# --- Streamlit UI ---
st.set_page_config(page_title="AI Invoice Extractor", page_icon="📄", layout="wide")
create_table()

st.title("📄 AI Invoice Data Extractor")
st.caption("Upload German invoices → AI extracts structured data → validated & stored automatically")

tab1, tab2 = st.tabs(["Upload & Process", "Stored Invoices"])

with tab1:
    uploaded_files = st.file_uploader(
        "Upload invoice PDF(s)", type="pdf", accept_multiple_files=True
    )

    if uploaded_files and st.button("Process Invoices"):
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                text = extract_text_from_pdf(uploaded_file)
                data = extract_fields_from_text(text)

                if data is None:
                    st.error(f"❌ Failed to extract fields from {uploaded_file.name}")
                    continue

                errors, warnings = validate_invoice(data)
                status = "FAILED" if errors else ("WARNING" if warnings else "PASSED")
                store_invoice(uploaded_file.name, data, status, errors, warnings)

                if status == "PASSED":
                    st.success(f"✅ {uploaded_file.name} — Passed")
                elif status == "WARNING":
                    st.warning(f"⚠️ {uploaded_file.name} — Warning: {warnings}")
                else:
                    st.error(f"❌ {uploaded_file.name} — Failed: {errors}")

                st.json(data)

with tab2:
    df = load_all_invoices()

    if df.empty:
        st.info("No invoices processed yet. Upload some in the first tab.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invoices", len(df))
        col2.metric("Total Net Amount", f"{df['net_amount'].sum():.2f} EUR")
        col3.metric("Total VAT", f"{df['vat_amount'].sum():.2f} EUR")

        status_filter = st.multiselect(
            "Filter by status", options=df["status"].unique(), default=df["status"].unique()
        )
        filtered_df = df[df["status"].isin(status_filter)]

        st.dataframe(filtered_df, use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download as CSV", csv, "invoices_export.csv", "text/csv")
