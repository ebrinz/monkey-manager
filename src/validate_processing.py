#!/usr/bin/env python3
import os
import sys
import re
import pandas as pd
import json
import glob
from pathlib import Path
from forensic_logger import ForensicLogger

class ProcessingValidator:
    """
    Validates that all files referenced in the mapping file have corresponding
    JSON output files, and reports any missing or problematic files.
    """
    
    def __init__(self, mapping_file, output_dirs, logger_path="/output/logs"):
        """
        Initialize the validator with mapping file and output directories.
        
        Args:
            mapping_file: Path to the Excel mapping file
            output_dirs: List of directories containing JSON files to check
            logger_path: Path for forensic logger output
        """
        self.mapping_file = mapping_file
        self.output_dirs = output_dirs if isinstance(output_dirs, list) else [output_dirs]
        self.logger = ForensicLogger(logger_path)
        
    def normalize_filename(self, filename):
        """Normalize filename for comparison by removing extensions and special characters."""
        if not filename or not isinstance(filename, str):
            return ""
        # Remove extension
        name = os.path.splitext(os.path.basename(filename))[0]
        # Remove special characters, convert to lowercase
        name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
        return name
        
    def load_mapping_data(self):
        """Load mapping file into a DataFrame."""
        try:
            if self.mapping_file.endswith('.csv'):
                mapping_df = pd.read_csv(self.mapping_file)
            else:
                mapping_df = pd.read_excel(self.mapping_file)
                
            self.logger.log_file_event('mapping_file_loaded', self.mapping_file, {
                'rows': len(mapping_df),
                'columns': list(mapping_df.columns)
            })
            
            return mapping_df
        except Exception as e:
            self.logger.log_anomaly('mapping_file_error', {
                'file': self.mapping_file,
                'error': str(e)
            })
            return None
            
    def get_all_json_files(self):
        """Find all JSON files in the output directories."""
        json_files = []
        for dir_path in self.output_dirs:
            if os.path.exists(dir_path):
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.json'):
                            json_files.append(os.path.join(root, file))
        
        self.logger.log_file_event('json_files_found', {
            'count': len(json_files),
            'directories': self.output_dirs
        })
        
        # Create a dictionary of normalized filenames to JSON file paths
        json_file_dict = {}
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # Get original filename from JSON
                orig_filename = json_data.get('filename', '')
                if orig_filename:
                    # Normalize for comparison
                    norm_name = self.normalize_filename(orig_filename)
                    json_file_dict[norm_name] = file_path
            except Exception as e:
                self.logger.log_anomaly('json_read_error', {
                    'file': file_path,
                    'error': str(e)
                })
                
        return json_file_dict
            
    def validate_processing(self):
        """
        Main validation method. Checks if all files in the mapping file 
        have corresponding JSON files in the output directories.
        """
        mapping_df = self.load_mapping_data()
        if mapping_df is None:
            print("Error: Could not load mapping file.")
            return False
        
        json_files = self.get_all_json_files()
        if not json_files:
            print("Warning: No JSON files found in output directories.")
            return False
            
        # Get file columns from mapping (looking for columns like "File 1", "File 2", etc.)
        file_columns = [col for col in mapping_df.columns if re.match(r'file\s*\d+', col.lower())]
        if not file_columns:
            print("Error: No file columns found in mapping file. Expected columns like 'File 1', 'File 2', etc.")
            return False
        
        print(f"Found {len(file_columns)} file columns in mapping file: {', '.join(file_columns)}")
        print(f"Found {len(json_files)} JSON files in output directories")
        
        # Track missing files
        missing_files = []
        found_files = []
        
        # For each row in mapping file
        for idx, row in mapping_df.iterrows():
            respondent_id = row.get('respondent_id', row.get('Respondent ID', f"Row {idx+2}"))
            
            # Look for files associated with this respondent
            for file_col in file_columns:
                if pd.isna(row[file_col]) or row[file_col] == '':
                    continue
                    
                filename = str(row[file_col])
                norm_name = self.normalize_filename(filename)
                
                # Check if there's a JSON file for this filename
                if norm_name and norm_name in json_files:
                    found_files.append({
                        'respondent_id': respondent_id,
                        'original_filename': filename,
                        'json_file': json_files[norm_name]
                    })
                else:
                    missing_files.append({
                        'respondent_id': respondent_id,
                        'original_filename': filename,
                        'column': file_col
                    })
        
        # Report results
        total_expected = len(found_files) + len(missing_files)
        
        print("\n=== Processing Validation Report ===")
        print(f"Total files in mapping: {total_expected}")
        print(f"Successfully processed: {len(found_files)} ({len(found_files)/total_expected*100:.1f}%)")
        print(f"Missing files: {len(missing_files)} ({len(missing_files)/total_expected*100:.1f}%)")
        
        if missing_files:
            print("\nMissing files:")
            for i, missing in enumerate(missing_files, 1):
                print(f"{i}. Respondent: {missing['respondent_id']}, File: {missing['original_filename']}, Column: {missing['column']}")
        
        # Log the validation results
        self.logger.log_file_event('processing_validation', {
            'total_expected': total_expected,
            'processed_successfully': len(found_files),
            'missing_files': len(missing_files)
        })
        
        return len(missing_files) == 0
        
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python validate_processing.py <mapping_file> <output_dir1> [<output_dir2> ...]")
        sys.exit(1)
        
    mapping_file = sys.argv[1]
    output_dirs = sys.argv[2:]
    
    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file '{mapping_file}' does not exist.")
        sys.exit(1)
        
    validator = ProcessingValidator(mapping_file, output_dirs)
    success = validator.validate_processing()
    
    sys.exit(0 if success else 1)  # Return non-zero exit code if validation fails