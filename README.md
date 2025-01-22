# monkey-manager

**Automating SurveyMonkey response processing**

This repository contains a Docker-based workflow for renaming and sanitizing PDF/DOCX files from SurveyMonkey (or similar) responses. The script also generates a mapping CSV that shows how each file was transformed (old filename → new filename).

---

## Features

1. **Copying/Extracting**  
   - Files in the input directory (`INPUT_DIR`) are copied to a writable work directory (`/tmp/work`).  
   - Any `.zip` archives are automatically extracted into that same work directory.  

2. **PDF/DOCX Sanitization**  
   - PDFs are read with **PyMuPDF** (`fitz`), extracting text.  
   - DOCX files are scanned for macros (using **oletools**), then text is extracted via **python-docx**.  
   - Text is saved as `.txt` files if sanitization is successful.

3. **Spreadsheet Lookup**  
   - A spreadsheet (`MAPPING_FILE`) defines which files are associated with which **Respondent ID** and **File#** columns.  
   - Spaces vs. `%20` are handled (the script tries both “File with spaces” and “File%20with%20spaces”).  
   - Each recognized file is renamed to `R{respondentID}-{columnNumber}.{ext}`.

4. **Single-Pass Renaming**  
   - **Unrecognized** files (not in spreadsheet) are prefixed with `NORESPID_...`.  

5. **Final CSV Log**  
   - For **each** file processed, one line is added to the CSV with **two columns**:  
     1. Original Filename  
     2. Final Filename (or `.txt` if sanitized, or `"SKIPPED (hidden/system)"` for hidden files).  

---

## Setup

1. **Environment Variables**  
   In a `.env` file or environment, define paths for:  
   ```dotenv
   INPUT_DIR=./inputs
   OUTPUT_DIR=./outputs
   MAPPING_FILE=./mappings/YourMappingFile.xlsx
   MAPPING_DIR=./mappings
   ```

2. **Docker Compose**
   
   ```
   services:
     sandbox:
       image: sandbox-image
       volumes:
         - ${INPUT_DIR}:/files:ro    # Input directory (read-only)
         - ${OUTPUT_DIR}:/output     # Output directory (read/write)
         - ${MAPPING_FILE}:/mapping/mapping_file.xlsx:ro
         - ${MAPPING_DIR}:/mapping
       environment:
         - PYTHONUNBUFFERED=1
       network_mode: none
       security_opt:
         - no-new-privileges:true
         - seccomp=unconfined
         - apparmor:docker-default
       command: ["python", "/app/process_files.py", "/files", "/output", "/mapping", "/mapping/mapping_file.xlsx"]
       restart: "no"
    ```

3. **Building and Running**
   
   - Build for ARM64 or AMD64 (example):
     ```
     docker buildx build --platform linux/arm64 -t sandbox-image --load .
     docker buildx build --platform linux/amd64 -t sandbox-image --load .
     ```

   - Run with Docker Compose:
     ```
     docker-compose up --remove-orphans --exit-code-from sandbox
     ```

   - The script processes files in /files (read-only mount), writes outputs and .txt files to /output, and reads the spreadsheet from /mapping/mapping_file.xlsx.

4. **Usage Flow**

   a. Place original files (PDF/DOCX/ZIP) in INPUT_DIR.
   b. Map them in MAPPING_FILE (XLSX or CSV), listing each Respondent ID and File#n columns.
   c. Run docker-compose up.
   d. Outputs appear in OUTPUT_DIR:
       - Possibly renamed files.
       - Any sanitized .txt outputs.
       - A CSV log (in MAPPING_DIR) with columns Original Filename, New Filename.

   Example CSV line for a recognized PDF:
   ```
   Original Filename       | New Filename
   ------------------------------------------------
   myrespondentFile.pdf    | R114719606389-1.txt
   ```

   And for an unrecognized file:
   ```
   someRandomFile.pdf      | NORESPID_someRandomFile.pdf
   ```

## Notes:

#### Macros in DOCX
If macros are detected, the script warns and proceeds with extraction.
Hidden Files
Files starting with . are logged as "SKIPPED (hidden/system)" in the CSV, while .DS_Store and .gitkeep are completely ignored.