import os
import sys
import pandas as pd
import shutil
from datetime import datetime
import csv
from pathlib import Path
from forensic_logger import ForensicLogger

class FileRenamer:
    def __init__(self, input_dir, output_dir, mapping_file):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.mapping_file = mapping_file
        self.logger = ForensicLogger("/output/logs")
        os.makedirs(output_dir, exist_ok=True)

    def possible_filenames(self, name: str):
        """Generate possible filename variants."""
        yield name
        if '%20' in name:
            yield name.replace('%20', ' ')
        if ' ' in name:
            yield name.replace(' ', '%20')

    def parse_column_number(self, col_name: str) -> str:
        """Extract number from column name."""
        return col_name.replace("File#", "")

    def build_spreadsheet_lookup(self, df):
        """Build filename to respondent ID mapping."""
        lookup = {}
        for _, row in df.iterrows():
            if pd.isna(row["Respondent ID"]):
                self.logger.log_anomaly('missing_respondent_id', {
                    'row': row.to_dict()
                })
                continue

            respondent_id = int(float(row["Respondent ID"]))
            
            for i in range(1, 21):
                col_name = f"File#{i}"
                val = row.get(col_name, None)
                if isinstance(val, str) and val.strip():
                    col_num = self.parse_column_number(col_name)
                    for variant in self.possible_filenames(val.strip()):
                        lookup[variant] = (respondent_id, col_num)
        return lookup

    def rename_files(self):
        """Main file renaming function."""
        self.logger.log_system_state()

        # Read mapping file
        try:
            if self.mapping_file.endswith(".csv"):
                df = pd.read_csv(self.mapping_file, sep="\t")
            elif self.mapping_file.endswith(".xlsx"):
                df = pd.read_excel(self.mapping_file)
            else:
                self.logger.log_anomaly('invalid_mapping_file', {
                    'file': self.mapping_file,
                    'error': 'Unsupported file format'
                })
                return

            # Build lookup dictionary
            spreadsheet_lookup = self.build_spreadsheet_lookup(df)
            
            # Track filename mappings
            filename_mappings = []
            
            # Process files
            for root, _, files in os.walk(self.input_dir):
                for fname in files:
                    if fname in [".DS_Store", ".gitkeep"]:
                        continue

                    if fname.startswith('.'):
                        self.logger.log_file_event('skip_hidden_file', fname)
                        filename_mappings.append((fname, "SKIPPED (hidden/system)"))
                        continue

                    file_path = os.path.join(root, fname)
                    base, ext = os.path.splitext(fname)

                    # Check if file is in spreadsheet
                    match = spreadsheet_lookup.get(fname, None)
                    if match:
                        respondent_id, col_num = match
                        new_name = f"R{respondent_id}-{col_num}{ext}"
                    else:
                        cleaned_fname = base.replace(" ", "_") + ext
                        new_name = f"NORESPID_{cleaned_fname}"

                    # Create output path preserving directory structure
                    rel_path = os.path.relpath(root, self.input_dir)
                    output_subdir = os.path.join(self.output_dir, rel_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    new_path = os.path.join(output_subdir, new_name)

                    # Copy file with new name
                    try:
                        shutil.copy2(file_path, new_path)
                        self.logger.log_file_event('file_renamed', new_path, {
                            'original': file_path,
                            'has_mapping': bool(match)
                        })
                        filename_mappings.append((fname, new_name))
                    except Exception as e:
                        self.logger.log_anomaly('rename_error', {
                            'file': file_path,
                            'new_name': new_name,
                            'error': str(e)
                        })

            # Write mapping CSV
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            csv_path = os.path.join(self.output_dir, f"rename_mapping_{timestamp}.csv")
            
            with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Original Filename", "New Filename"])
                for orig, new in filename_mappings:
                    writer.writerow([orig, new])
            
            self.logger.log_file_event('mapping_saved', csv_path, {
                'total_files': len(filename_mappings)
            })

        except Exception as e:
            self.logger.log_anomaly('process_error', {
                'error': str(e)
            })

        self.logger.log_system_state()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python file_renamer.py <input_dir> <output_dir> <mapping_file>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    mapping_file = sys.argv[3]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file '{mapping_file}' does not exist.")
        sys.exit(1)

    renamer = FileRenamer(input_dir, output_dir, mapping_file)
    renamer.rename_files()