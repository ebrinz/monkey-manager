import os
import pandas as pd
from typing import Optional, Tuple

class FilenamingUtility:
    def __init__(self, mapping_file: str = None, enable_renaming: bool = True):
        self.enable_renaming = enable_renaming
        self.lookup = {}
        
        if enable_renaming and mapping_file:
            self._build_lookup(mapping_file)

    def _build_lookup(self, mapping_file: str) -> None:
        try:
            # Read mapping file
            if mapping_file.endswith('.csv'):
                df = pd.read_csv(mapping_file, sep="\t")
            elif mapping_file.endswith('.xlsx'):
                df = pd.read_excel(mapping_file)
            else:
                raise ValueError("Unsupported mapping file format")

            # Build lookup dictionary
            for _, row in df.iterrows():
                if pd.isna(row.get("Respondent ID")):
                    continue

                respondent_id = str(int(float(row["Respondent ID"])))
                
                # Check both formats of column names
                for i in range(1, 21):
                    col_variants = [f"File#{i}", f"File #{i}"]
                    
                    for col_name in col_variants:
                        if col_name in df.columns:
                            val = row.get(col_name)
                            if isinstance(val, str) and val.strip():
                                col_num = str(i)
                                fname = val.strip()
                                # Store filename variants
                                self.lookup[fname] = (respondent_id, col_num)
                                self.lookup[fname.replace(' ', '%20')] = (respondent_id, col_num)
                                self.lookup[fname.replace('%20', ' ')] = (respondent_id, col_num)
                                
                                # Also store with and without .pdf/.txt extensions
                                for ext in ['.pdf', '.txt', '.docx']:
                                    if not fname.lower().endswith(ext):
                                        self.lookup[fname + ext] = (respondent_id, col_num)
                                        self.lookup[fname.replace(' ', '%20') + ext] = (respondent_id, col_num)

                print(f"Added mappings for respondent {respondent_id}")

        except Exception as e:
            print(f"Error building filename lookup: {e}")
            self.enable_renaming = False

    def get_output_filename(self, input_filename: str, output_ext: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Generate output filename and return respondent info if available.
        
        Args:
            input_filename: Original filename
            output_ext: Optional new extension (e.g., '.txt' for text output)
        
        Returns:
            Tuple of (output_filename, respondent_id, column_number)
            - output_filename uses the original name with optional new extension
            - respondent_id will be None if no mapping exists
            - column_number will be None if no mapping exists
        """
        # Get base name and extension
        base, ext = os.path.splitext(input_filename)
        if output_ext:
            ext = output_ext
            
        # Create output filename (preserve original name)
        output_filename = f"{base}{ext}"
        
        # Look up respondent ID but don't modify filename
        match = self.lookup.get(input_filename)
        
        if match:
            respondent_id, col_num = match
            return output_filename, respondent_id, col_num
        else:
            return output_filename, None, None