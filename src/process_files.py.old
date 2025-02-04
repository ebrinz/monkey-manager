import os
import sys
import zipfile
import shutil
import pandas as pd
import fitz  # PyMuPDF
from oletools.olevba import VBA_Parser
from docx import Document
import datetime
import csv

###############################################################################
# 1. File copying / extraction
###############################################################################

def extract_zip_file(zip_file_path, extract_dir):
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"Extracted {zip_file_path} into {extract_dir}")
    except Exception as e:
        print(f"Error extracting {zip_file_path}: {e}")

def prepare_input_files(input_dir, work_dir):
    """
    Copies or extracts all files from `input_dir` (read-only) into `work_dir` (writable).
    """
    for root, dirs, files in os.walk(input_dir):
        rel_path = os.path.relpath(root, input_dir)
        target_root = os.path.join(work_dir, rel_path)
        os.makedirs(target_root, exist_ok=True)

        for fname in files:
            src_path = os.path.join(root, fname)
            # If it's a ZIP, extract it; otherwise, just copy
            if fname.lower().endswith('.zip'):
                extract_zip_file(src_path, target_root)
            else:
                dest_path = os.path.join(target_root, fname)
                shutil.copy2(src_path, dest_path)
                print(f"Copied {fname} to {dest_path}")

###############################################################################
# 2. PDF/DOCX sanitization
###############################################################################

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
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"Error processing DOCX {input_file}: {e}")
        return None

###############################################################################
# 3. Spreadsheet Utility
###############################################################################

def possible_filenames(name: str):
    """
    Generate possible variants:
      - The raw name
      - If '%20' in name => yield name with '%20' replaced by space
      - If ' ' in name => yield name with ' ' replaced by '%20'
    """
    yield name
    if '%20' in name:
        yield name.replace('%20', ' ')
    if ' ' in name:
        yield name.replace(' ', '%20')

def parse_column_number(col_name: str) -> str:
    """
    If col_name = 'File#3', returns '3'.
    """
    return col_name.replace("File#", "")

def build_spreadsheet_lookup(df):
    """
    Single dictionary: {filename_variant -> (respondentID, colNum)}
    where filename_variant handles 'spaces' vs '%20'.
    """
    lookup = {}
    for _, row in df.iterrows():
        # Skip any row missing Respondent ID
        if pd.isna(row["Respondent ID"]):
            print("Row missing Respondent ID -> skipping")
            continue

        # Convert respondent ID to int so there's no .0
        respondent_id = int(float(row["Respondent ID"]))

        # For columns File#1..File#20
        for i in range(1, 21):
            col_name = f"File#{i}"
            val = row.get(col_name, None)
            if isinstance(val, str) and val.strip():
                col_num = parse_column_number(col_name)
                # Produce all variants
                for variant in possible_filenames(val.strip()):
                    lookup[variant] = (respondent_id, col_num)
    return lookup

###############################################################################
# 4. Main Process
###############################################################################

def process_files(input_dir, output_dir, mapping_dir, mapping_file):
    """
    Single-pass approach:
      1) Copy/extract files from `input_dir` => /tmp/work
      2) Read spreadsheet => build single lookup
      3) Single pass:
         - If file is .DS_Store / .gitkeep => skip entirely (don't rename, don't CSV)
         - If file starts with '.' => log "SKIPPED (hidden/system)" in CSV
         - If file in spreadsheet => rename => R<respondentID>-<colNum>.<ext>, sanitize => .txt if PDF/DOCX
         - else => rename => NORESPID_<file>, sanitize => .txt if PDF/DOCX
         - add exactly 1 line to the CSV: old_filename => final_filename
    """

    # 1. Copy everything to /tmp/work
    work_dir = "/tmp/work"
    os.makedirs(work_dir, exist_ok=True)
    prepare_input_files(input_dir, work_dir)

    # 2. Read spreadsheet
    if mapping_file.endswith(".csv"):
        df = pd.read_csv(mapping_file, sep="\t")
    elif mapping_file.endswith(".xlsx"):
        df = pd.read_excel(mapping_file)
    else:
        print("Error: Mapping file must be .csv or .xlsx")
        return

    # Build single dictionary
    spreadsheet_lookup = build_spreadsheet_lookup(df)

    # Ensure output folder exists
    os.makedirs(output_dir, exist_ok=True)

    # We'll record (old_filename, final_filename) here
    filename_mappings = []

    # 3. Single pass: rename + sanitize
    filecount = 0
    for root, dirs, files in os.walk(work_dir):
        for fname in files:
            # 3a. Skip .DS_Store / .gitkeep entirely
            if fname in [".DS_Store", ".gitkeep"]:
                print(f"Skipping {fname} entirely (not in CSV).")
                continue

            filecount += 1
            print(filecount, ": ", fname)

            old_path = os.path.join(root, fname)
            old_name = fname  # For CSV record

            # 3b. If it's hidden/system (starts with '.'), log "SKIPPED" in CSV
            if fname.startswith('.'):
                print(f"Skipping hidden/system file: {old_name}")
                filename_mappings.append((old_name, "SKIPPED (hidden/system)"))
                continue

            base, ext = os.path.splitext(fname)
            ext_lower = ext.lower()

            # 3c. Check if in spreadsheet
            match = spreadsheet_lookup.get(fname, None)
            if match:
                # In spreadsheet => rename => R<respID>-<colNum>.<ext>
                respondent_id, col_num = match
                new_name = f"R{respondent_id}-{col_num}{ext}"
                new_path = os.path.join(root, new_name)
                os.rename(old_path, new_path)

                # Sanitize if PDF/DOCX
                final_name = new_name
                text = None
                if ext_lower == ".pdf":
                    text = sanitize_pdf(new_path)
                elif ext_lower == ".docx":
                    text = sanitize_docx(new_path)

                if text:
                    # final => .txt
                    txt_filename = f"R{respondent_id}-{col_num}.txt"
                    txt_path = os.path.join(output_dir, txt_filename)
                    with open(txt_path, "w", encoding="utf-8") as out_f:
                        out_f.write(text)
                    final_name = txt_filename

                print(f"Renamed {old_name} -> {final_name}")
                filename_mappings.append((old_name, final_name))

            else:
                # Not in spreadsheet => rename => NORESPID_<file>
                cleaned_fname = base.replace(" ", "_") + ext
                new_name = f"NORESPID_{cleaned_fname}"
                new_path = os.path.join(root, new_name)
                os.rename(old_path, new_path)

                # Possibly sanitize
                final_name = new_name
                text = None
                if ext_lower == ".pdf":
                    text = sanitize_pdf(new_path)
                elif ext_lower == ".docx":
                    text = sanitize_docx(new_path)

                if text:
                    txt_filename = f"NORESPID_{base.replace(' ', '_')}.txt"
                    txt_path = os.path.join(output_dir, txt_filename)
                    with open(txt_path, "w", encoding="utf-8") as out_f:
                        out_f.write(text)
                    final_name = txt_filename

                print(f"Renamed {old_name} -> {final_name}")
                filename_mappings.append((old_name, final_name))

    # 4. Write single CSV (old => new)
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    csv_name = f"{timestamp_str}.csv"
    csv_path = os.path.join(mapping_dir, csv_name)  # Save in mapping_dir

    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Original Filename", "New Filename"])
            for orig, new in filename_mappings:
                writer.writerow([orig, new])
        print(f"File mapping log saved to: {csv_path}")
    except Exception as e:
        print(f"Error writing CSV log: {e}")

###############################################################################
# 5. Entry point
###############################################################################

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python process_files.py <input_dir> <output_dir> <mapping_dir> <mapping_file>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    mapping_dir = sys.argv[3]
    mapping_file= sys.argv[4]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file '{mapping_file}' does not exist.")
        sys.exit(1)

    process_files(input_dir, output_dir, mapping_dir, mapping_file)
