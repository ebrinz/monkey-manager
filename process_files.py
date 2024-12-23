import os
import sys
import pandas as pd
import fitz  # PyMuPDF
from oletools.olevba import VBA_Parser
from docx import Document

def sanitize_pdf(input_file):
    try:
        doc = fitz.open(input_file)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error processing PDF {input_file}: {e}")
        return None

def sanitize_docx(input_file):
    try:
        vba_parser = VBA_Parser(input_file)
        if vba_parser.detect_vba_macros():
            print(f"Warning: Macros detected in {input_file}. Proceeding with text extraction.")
        doc = Document(input_file)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text
    except Exception as e:
        print(f"Error processing DOCX {input_file}: {e}")
        return None

def process_files(input_dir, output_dir, mapping_file):
    # Load the spreadsheet
    if mapping_file.endswith(".csv"):
        data = pd.read_csv(mapping_file, sep="\t")
    elif mapping_file.endswith(".xlsx"):
        data = pd.read_excel(mapping_file)
    else:
        print("Error: Unsupported file format for mapping file. Use .csv or .xlsx.")
        return

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate over rows in the spreadsheet
    for index, row in data.iterrows():
        respondent_id = row["Respondent ID"]
        files = [f"File#{i}" for i in range(1, 21)]

        file_counter = 0
        for file_column in files:
            file_name = row.get(file_column, None)
            if pd.isna(file_name) or not file_name:
                continue

            input_file = os.path.join(input_dir, file_name)
            if not os.path.exists(input_file):
                print(f"Warning: File {input_file} not found for Respondent ID {respondent_id}. Skipping.")
                continue

            if file_name.endswith(".pdf"):
                text = sanitize_pdf(input_file)
            elif file_name.endswith(".docx"):
                text = sanitize_docx(input_file)
            else:
                print(f"Unsupported file format: {file_name}")
                continue

            if text:
                file_counter += 1
                output_file = os.path.join(
                    output_dir, f"{respondent_id}-{chr(96 + file_counter)}.txt"
                )
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Saved sanitized text to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python process_files.py <input_dir> <output_dir> <mapping_file>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    mapping_file = sys.argv[3]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} does not exist.")
        sys.exit(1)

    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file {mapping_file} does not exist.")
        sys.exit(1)

    process_files(input_dir, output_dir, mapping_file)
