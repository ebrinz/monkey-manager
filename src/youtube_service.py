import os
import sys
import pandas as pd
import json
import datetime
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from forensic_logger import ForensicLogger
from file_renamer import FilenamingUtility

class YouTubeProcessor:
    def __init__(self, links_file, output_dir, video_input_dir, mapping_file=None, force_reprocess=False):
        self.links_file = links_file
        self.output_dir = output_dir
        self.video_input_dir = video_input_dir
        self.logger = ForensicLogger("/output/logs")
        self.force_reprocess = force_reprocess
        
        # Initialize filename utility
        enable_renaming = os.environ.get('ENABLE_FILE_RENAMING', 'true').lower() == 'true'
        self.filename_util = FilenamingUtility(mapping_file, enable_renaming)
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(video_input_dir, exist_ok=True)
        
    def get_video_id(self, url):
        """Extract video ID from YouTube URL."""
        try:
            parsed_url = urlparse(url)
            if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
                if parsed_url.path == '/watch':
                    return parse_qs(parsed_url.query)['v'][0]
                elif parsed_url.path.startswith('/v/'):
                    return parsed_url.path.split('/')[2]
            elif parsed_url.hostname == 'youtu.be':
                return parsed_url.path[1:]
            return None
        except Exception as e:
            self.logger.log_anomaly('url_parse_error', {
                'url': url,
                'error': str(e)
            })
            return None

    def get_transcript(self, video_id):
        """Try to get transcript using youtube_transcript_api."""
        try:
            # First try to list available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get English transcript first
            try:
                transcript = transcript_list.find_transcript(['en'])
            except:
                # If no English, get auto-generated English or first available
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    # Get first available transcript and translate to English
                    transcript = transcript_list.find_manually_created_transcript()
                    transcript = transcript.translate('en')
            
            # Get the transcript and format it as plain text
            transcript_data = transcript.fetch()
            formatter = TextFormatter()
            return formatter.format_transcript(transcript_data)
            
        except Exception as e:
            self.logger.log_anomaly('transcript_api_error', {
                'video_id': video_id,
                'error': str(e)
            })
            return None

    def download_video(self, url, output_path):
        """Download video from YouTube URL."""
        ydl_opts = {
            'format': 'mp4',
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

    def read_youtube_links(self):
        """Read YouTube URLs from Excel or CSV file."""
        try:
            if self.links_file.endswith('.csv'):
                df = pd.read_csv(self.links_file)
            else:  # Excel
                df = pd.read_excel(self.links_file)
            
            # Get the first column, assuming it contains URLs
            return df.iloc[:, 0].dropna().tolist()
            
        except Exception as e:
            self.logger.log_anomaly('links_file_error', {
                'file': self.links_file,
                'error': str(e)
            })
            return []

    def process_youtube_links(self):
        """Main processing function."""
        self.logger.log_system_state()

        links = self.read_youtube_links()
        if not links:
            self.logger.log_anomaly('no_youtube_links', {
                'file': self.links_file
            })
            return

        for i, url in enumerate(links, 1):
            video_id = self.get_video_id(url)
            if not video_id:
                continue

            # Calculate expected output path
            output_filename = self.filename_util.get_output_filename(f"youtube_{video_id}.json")
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Check if output already exists
            if os.path.exists(output_path) and not self.force_reprocess:
                self.logger.log_file_event('skip_existing_output', url, {
                    'output_path': output_path,
                    'video_id': video_id
                })
                continue
            
            # Try to get transcript first
            transcript = self.get_transcript(video_id)
            
            if transcript:
                # Create JSON document
                doc = {
                    'text': transcript,
                    'filename': f"youtube_{video_id}",
                    'filetype': 'youtube',
                    'video_id': video_id,
                    'url': url,
                    'extraction_timestamp': datetime.datetime.now().isoformat()
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                
                self.logger.log_file_event('youtube_transcript_json_saved', output_path)
                
            else:
                # Calculate expected video output path
                video_filename = self.filename_util.get_output_filename(f"youtube_{video_id}.mp4")
                video_path = os.path.join(self.video_input_dir, video_filename)
                
                # Check if video already exists (don't download again if it was already downloaded)
                if os.path.exists(video_path) and not self.force_reprocess:
                    self.logger.log_file_event('skip_existing_video', url, {
                        'video_path': video_path,
                        'video_id': video_id
                    })
                    continue
                
                # Download video for later processing by whisper service
                success, title = self.download_video(url, video_path)
                if not success:
                    self.logger.log_anomaly('video_processing_failed', {
                        'url': url,
                        'video_id': video_id
                    })

        self.logger.log_system_state()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process YouTube links for transcription.")
    parser.add_argument("links_file", help="Excel or CSV file containing YouTube links")
    parser.add_argument("output_dir", help="Directory for transcript outputs")
    parser.add_argument("video_input_dir", help="Directory for downloaded videos")
    parser.add_argument("--force", "-f", action="store_true", help="Force reprocessing of videos that already have outputs")
    parser.add_argument("--mapping", "-m", help="Path to mapping file for filename conversion")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.links_file):
        print(f"Error: Links file '{args.links_file}' does not exist.")
        sys.exit(1)

    processor = YouTubeProcessor(
        args.links_file, 
        args.output_dir, 
        args.video_input_dir,
        mapping_file=args.mapping,
        force_reprocess=args.force
    )
    processor.process_youtube_links()