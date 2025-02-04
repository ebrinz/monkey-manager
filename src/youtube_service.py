import os
import sys
import whisper
import pandas as pd
import yt_dlp
from pathlib import Path
from forensic_logger import ForensicLogger

class YouTubeProcessor:
    def __init__(self, input_dir, output_dir, temp_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.logger = ForensicLogger("/output/logs")
        self.model = whisper.load_model("base")
        
        # Create directories
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    def find_youtube_list(self):
        """Find Excel or CSV files containing YouTube URLs."""
        files = []
        for ext in ['.xlsx', '.csv']:
            files.extend(Path(self.input_dir).glob(f'**/*{ext}'))
        return files

    def read_youtube_links(self, file_path):
        """Extract YouTube URLs from Excel or CSV file."""
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:  # Excel
                df = pd.read_excel(file_path)
            
            # Try common column names for URLs
            url_columns = ['url', 'link', 'youtube_url', 'youtube_link']
            for col in url_columns:
                if col in df.columns:
                    return df[col].dropna().tolist()
            
            # If no known column found, use first column
            return df.iloc[:, 0].dropna().tolist()
            
        except Exception as e:
            self.logger.log_anomaly('youtube_list_error', {
                'file': str(file_path),
                'error': str(e)
            })
            return []

    def download_audio(self, url, output_path):
        """Download audio from YouTube URL."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True
        }
        
        try:
            self.logger.log_file_event('youtube_download_start', url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'unknown')
            self.logger.log_file_event('youtube_download_complete', output_path, {
                'title': title,
                'duration': info.get('duration', 0)
            })
            return True, title
        except Exception as e:
            self.logger.log_anomaly('youtube_download_error', {
                'url': url,
                'error': str(e)
            })
            return False, None

    def transcribe_audio(self, audio_path, output_path):
        """Transcribe downloaded audio using Whisper."""
        try:
            self.logger.log_file_event('transcription_start', audio_path)
            
            # Transcribe
            result = self.model.transcribe(audio_path)
            
            # Write transcription
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["text"])
            
            self.logger.log_file_event('transcription_complete', output_path, {
                'duration': result.get('duration', 0),
                'language': result.get('language', 'unknown')
            })
            return True
        except Exception as e:
            self.logger.log_anomaly('transcription_error', {
                'file': audio_path,
                'error': str(e)
            })
            return False

    def process_youtube_links(self):
        """Main processing function."""
        self.logger.log_system_state()

        youtube_files = self.find_youtube_list()
        if not youtube_files:
            self.logger.log_anomaly('no_youtube_list', {
                'input_dir': self.input_dir
            })
            return

        for file_path in youtube_files:
            links = self.read_youtube_links(file_path)
            if not links:
                continue

            for i, url in enumerate(links, 1):
                # Create unique names for files
                base_name = f"youtube_{Path(file_path).stem}_{i}"
                audio_path = os.path.join(self.temp_dir, f"{base_name}.wav")
                text_path = os.path.join(self.output_dir, f"{base_name}.txt")

                # Download and process
                success, title = self.download_audio(url, audio_path)
                if success:
                    if self.transcribe_audio(audio_path, text_path):
                        # Update filename with video title if available
                        if title:
                            safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:100]
                            new_text_path = os.path.join(self.output_dir, f"{safe_title}.txt")
                            try:
                                os.rename(text_path, new_text_path)
                                text_path = new_text_path
                            except Exception as e:
                                self.logger.log_anomaly('rename_error', {
                                    'old_path': text_path,
                                    'new_path': new_text_path,
                                    'error': str(e)
                                })

                    # Clean up temp audio file
                    try:
                        os.remove(audio_path)
                    except Exception as e:
                        self.logger.log_anomaly('cleanup_error', {
                            'file': audio_path,
                            'error': str(e)
                        })

        self.logger.log_system_state()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python youtube_service.py <input_dir> <output_dir> <temp_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    temp_dir = sys.argv[3]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    processor = YouTubeProcessor(input_dir, output_dir, temp_dir)
    processor.process_youtube_links()