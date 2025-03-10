import os
import sys
import json
import pandas as pd
import glob
import re
from pathlib import Path
from forensic_logger import ForensicLogger

class SurveyMonkeyEnricher:
    """
    Enriches JSON documents with metadata from a Survey Monkey mapping file.
    This is a final step that adds respondent_id and other Survey Monkey specific attributes
    from the mapping file to the extracted JSON documents.
    """
    
    def __init__(self, mapping_file, output_dirs, logger_path="/output/logs"):
        """
        Initialize the enricher with mapping file and output directories.
        
        Args:
            mapping_file: Path to the Excel mapping file
            output_dirs: List of directories containing JSON files to enrich
            logger_path: Path for forensic logger output
        """
        self.mapping_file = mapping_file
        self.output_dirs = output_dirs if isinstance(output_dirs, list) else [output_dirs]
        self.logger = ForensicLogger(logger_path)
        
    def normalize_filename(self, filename):
        """Normalize filename for comparison by removing extensions and special characters."""
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
            
    def find_json_files(self):
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
        
        return json_files
        
    def enrich_json_files(self):
        """
        Main method to enrich JSON files with metadata from mapping file.
        For each file in the mapping, find corresponding JSON and add metadata.
        """
        mapping_df = self.load_mapping_data()
        if mapping_df is None:
            return
        
        json_files = self.find_json_files()
        if not json_files:
            self.logger.log_anomaly('no_json_files_found', {
                'directories': self.output_dirs
            })
            return
            
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
        
        # Get file columns from mapping (looking for columns like "File 1", "File 2", etc.)
        file_columns = [col for col in mapping_df.columns if re.match(r'file\s*\d+', col.lower())]
        
        # For each row in mapping file
        enrichment_count = 0
        for _, row in mapping_df.iterrows():
            respondent_id = row.get('respondent_id', row.get('Respondent ID', None))
            if not respondent_id:
                continue
                
            # Extract useful metadata columns (exclude file columns)
            metadata = {}
            for col in mapping_df.columns:
                if col.lower() not in [c.lower() for c in file_columns]:
                    if pd.notna(row[col]) and row[col] != '':
                        metadata[col] = row[col]
            
            # Look for files associated with this respondent
            for file_col in file_columns:
                if pd.isna(row[file_col]) or row[file_col] == '':
                    continue
                    
                filename = str(row[file_col])
                norm_name = self.normalize_filename(filename)
                
                # Find matching JSON file
                matching_file = json_file_dict.get(norm_name)
                if matching_file:
                    try:
                        # Read JSON
                        with open(matching_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Add metadata
                        data['respondent_id'] = respondent_id
                        for key, value in metadata.items():
                            # Convert any non-string values to strings
                            if isinstance(value, (pd.Timestamp, pd.Period)):
                                value = value.strftime('%Y-%m-%d')
                            elif not isinstance(value, (str, int, float, bool)):
                                value = str(value)
                                
                            data[key] = value
                        
                        # Write back
                        with open(matching_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                            
                        enrichment_count += 1
                        self.logger.log_file_event('json_enriched', matching_file, {
                            'respondent_id': respondent_id,
                            'original_filename': filename
                        })
                    except Exception as e:
                        self.logger.log_anomaly('json_enrichment_error', {
                            'file': matching_file,
                            'error': str(e)
                        })
        
        self.logger.log_file_event('enrichment_complete', {
            'files_enriched': enrichment_count,
            'total_files': len(json_files)
        })
        
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python surveymonkey_enricher.py <mapping_file> <output_dir1> [<output_dir2> ...]")
        sys.exit(1)
        
    mapping_file = sys.argv[1]
    output_dirs = sys.argv[2:]
    
    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file '{mapping_file}' does not exist.")
        sys.exit(1)
        
    enricher = SurveyMonkeyEnricher(mapping_file, output_dirs)
    enricher.enrich_json_files()