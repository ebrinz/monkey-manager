import os
import sys
import fitz  # PyMuPDF
from oletools.olevba import VBA_Parser
from docx import Document
from forensic_logger import ForensicLogger
from file_renamer import FilenamingUtility

class TextExtractor:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = ForensicLogger("/output/logs")
        
        # Initialize filename utility with mapping file
        enable_renaming = os.environ.get('ENABLE_FILE_RENAMING', 'true').lower() == 'true'
        self.filename_util = FilenamingUtility("/mapping/mapping_file.xlsx", enable_renaming)
        
        os.makedirs(output_dir, exist_ok=True)

    def process_files(self):
        """Process all files in the input directory."""
        self.logger.log_system_state()

        for root, _, files in os.walk(self.input_dir):
            for fname in files:
                if fname.startswith('.') or fname in [".DS_Store", ".gitkeep"]:
                    continue

                file_path = os.path.join(root, fname)
                base, ext = os.path.splitext(fname)
                ext_lower = ext.lower()

                # Process based on extension
                text = None
                if ext_lower == '.pdf':
                    text = self.sanitize_pdf(file_path)
                elif ext_lower == '.docx':
                    text = self.sanitize_docx(file_path)

                # Save extracted text
                if text:
                    # Get new filename based on mapping
                    new_filename = self.filename_util.get_output_filename(fname, '.txt')
                    txt_path = os.path.join(self.output_dir, new_filename)
                    
                    with open(txt_path, "w", encoding="utf-8") as out_f:
                        out_f.write(text)
                    self.logger.log_file_event('text_saved', txt_path, {
                        'original_file': file_path,
                        'text_length': len(text)
                    })

    def sanitize_pdf(self, input_file):
        """Extract text from PDF while logging operations."""
        try:
            self.logger.log_file_event('pdf_start', input_file)
            doc = fitz.open(input_file)
            text = ""
            for page in doc:
                text += page.get_text()
            self.logger.log_file_event('pdf_success', input_file, {
                'pages': len(doc),
                'text_length': len(text)
            })
            return text
        except Exception as e:
            self.logger.log_anomaly('pdf_error', {
                'file': input_file,
                'error': str(e)
            })
            return None

    def sanitize_docx(self, input_file):
        """Extract text from DOCX while checking for macros."""
        try:
            self.logger.log_file_event('docx_start', input_file)
            
            # Check for macros
            vba_parser = VBA_Parser(input_file)
            has_macros = vba_parser.detect_vba_macros()
            if has_macros:
                self.logger.log_anomaly('macro_detected', {
                    'file': input_file
                })
            
            # Extract text
            doc = Document(input_file)
            text = "\n".join(p.text for p in doc.paragraphs)
            
            self.logger.log_file_event('docx_success', input_file, {
                'paragraphs': len(doc.paragraphs),
                'has_macros': has_macros,
                'text_length': len(text)
            })
            return text
        except Exception as e:
            self.logger.log_anomaly('docx_error', {
                'file': input_file,
                'error': str(e)
            })
            return None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python text_extractor.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    extractor = TextExtractor(input_dir, output_dir)
    extractor.process_files()