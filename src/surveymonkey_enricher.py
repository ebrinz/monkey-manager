import os
import sys
import json
import pandas as pd
import glob
import re
import pexpect
import tempfile
from pathlib import Path
from typing import List, Optional, Dict
from forensic_logger import ForensicLogger

class SurveyMonkeyEnricher:
    """
    Enriches JSON documents with metadata from a Survey Monkey mapping file.
    This is a final step that adds respondent_id and other Survey Monkey specific attributes
    from the mapping file to the extracted JSON documents.
    """
    
    def __init__(self, mapping_file, output_dirs, logger_path="/output/logs", 
                 selected_columns: Optional[List[str]] = None, 
                 interactive: bool = True):
        """
        Initialize the enricher with mapping file and output directories.
        
        Args:
            mapping_file: Path to the Excel mapping file
            output_dirs: List of directories containing JSON files to enrich
            logger_path: Path for forensic logger output
            selected_columns: Predefined list of columns to include from mapping file
            interactive: Whether to interactively ask user which columns to include
        """
        self.mapping_file = mapping_file
        self.output_dirs = output_dirs if isinstance(output_dirs, list) else [output_dirs]
        self.logger = ForensicLogger(logger_path)
        self.selected_columns = selected_columns
        self.interactive = interactive
        self.exclude_columns = []  # Will be populated with file columns
        
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
    
    def interactive_column_selection(self, mapping_df, file_columns):
        """
        Interactively ask user which columns from the mapping file to include as attributes
        using pexpect to handle the interactive session.
        
        Args:
            mapping_df: DataFrame containing mapping data
            file_columns: List of file columns to exclude from selection
            
        Returns:
            List of selected column names to include as attributes
        """
        # Always include respondent_id
        selected = ["respondent_id", "Respondent ID"]
        
        # Get available columns (excluding file columns)
        available_columns = [col for col in mapping_df.columns 
                            if col.lower() not in [c.lower() for c in file_columns]
                            and col not in selected]
        
        if not available_columns:
            self.logger.log_file_event('no_metadata_columns', {
                'reason': 'Only file columns found in mapping file'
            })
            return selected
        
        if not self.interactive:
            if self.selected_columns:
                return selected + self.selected_columns
            else:
                # Default to including all columns
                return selected + available_columns
        
        # Create a temporary script for the interactive session
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py') as temp:
            temp.write("""
import sys

def main():
    cols = sys.argv[1].split(',')
    print("\\nAvailable columns in mapping file:\\n")
    
    for i, col in enumerate(cols, 1):
        print(f"{i}. {col}")
    
    print("\\nEnter column numbers to include (comma-separated, 'all' for all, 'none' for none):")
    selection = input("> ")
    
    if selection.lower() == 'all':
        print(','.join(cols))
    elif selection.lower() == 'none':
        print('')
    else:
        try:
            indices = [int(i.strip()) - 1 for i in selection.split(',')]
            selected = [cols[i] for i in indices if 0 <= i < len(cols)]
            print(','.join(selected))
        except:
            print('')

if __name__ == "__main__":
    main()
""")
            script_path = temp.name
        
        try:
            # Run the interactive script
            cmd = f"python {script_path} {','.join(available_columns)}"
            child = pexpect.spawn(cmd)
            child.expect("> ")
            
            # Send empty line to get the prompt
            child.sendline("")
            
            # Capture the output
            child.expect(pexpect.EOF)
            output = child.before.decode().strip().split('\n')[-1]
            
            # Process selected columns
            if output:
                additional_columns = output.split(',')
                self.logger.log_file_event('columns_selected', {
                    'selected_columns': additional_columns
                })
                return selected + additional_columns
            else:
                self.logger.log_file_event('no_columns_selected', {})
                return selected
                
        except Exception as e:
            self.logger.log_anomaly('column_selection_error', {
                'error': str(e)
            })
            # Default to just respondent_id on error
            return selected
        finally:
            # Clean up the temporary script
            try:
                os.unlink(script_path)
            except:
                pass
            
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
        
        # Get file columns from mapping using more flexible patterns
        # Match patterns like "File 1", "File#1", "File #2", etc. or just "File"
        file_columns = [col for col in mapping_df.columns 
                       if re.match(r'file\s*#?\s*\d+', col.lower()) or 
                       re.match(r'file', col.lower())]
        
        self.exclude_columns = file_columns
        
        if not file_columns:
            self.logger.log_anomaly('no_file_columns_found', {
                'available_columns': list(mapping_df.columns)
            })
            print("Warning: No file columns found in mapping file. Expected columns containing 'File' text.")
            return
            
        # Interactive column selection
        selected_columns = self.interactive_column_selection(mapping_df, file_columns)
        self.logger.log_file_event('column_selection_complete', {
            'selected_columns': selected_columns
        })
        
        # For each row in mapping file
        enrichment_count = 0
        for _, row in mapping_df.iterrows():
            respondent_id = row.get('respondent_id', row.get('Respondent ID', None))
            if not respondent_id:
                continue
                
            # Extract selected metadata columns (exclude file columns)
            metadata = {}
            for col in selected_columns:
                if col in mapping_df.columns and pd.notna(row.get(col)) and row.get(col) != '':
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich extracted JSON files with Survey Monkey metadata")
    parser.add_argument("mapping_file", help="Path to Survey Monkey mapping file (Excel or CSV)")
    parser.add_argument("output_dirs", nargs="+", help="One or more directories containing JSON files to enrich")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive column selection")
    parser.add_argument("--columns", nargs="+", help="Specific columns to include (if not using interactive mode)")
    parser.add_argument("--log-path", default="/output/logs", help="Path for forensic logs")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.mapping_file):
        print(f"Error: Mapping file '{args.mapping_file}' does not exist.")
        sys.exit(1)
        
    enricher = SurveyMonkeyEnricher(
        mapping_file=args.mapping_file,
        output_dirs=args.output_dirs,
        logger_path=args.log_path,
        selected_columns=args.columns,
        interactive=not args.non_interactive
    )
    
    enricher.enrich_json_files()