import os
import sys
import json
import subprocess
import datetime
from pathlib import Path
from forensic_logger import ForensicLogger
from file_renamer import FilenamingUtility

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

class WhisperTranscriber:
    def __init__(self, audio_input_dir, video_input_dir, audio_output_dir, video_output_dir, mapping_file=None, force_reprocess=False):
        self.audio_input_dir = audio_input_dir
        self.video_input_dir = video_input_dir
        self.audio_output_dir = audio_output_dir
        self.video_output_dir = video_output_dir
        self.logger = ForensicLogger("/output/logs")
        self.force_reprocess = force_reprocess
        
        # Initialize filename utility
        enable_renaming = os.environ.get('ENABLE_FILE_RENAMING', 'true').lower() == 'true'
        self.filename_util = FilenamingUtility(mapping_file, enable_renaming)
        
        # Initialize whisper model if available
        if WHISPER_AVAILABLE:
            self.model = whisper.load_model("base")
        else:
            self.model = None
            self.logger.log_anomaly('whisper_not_available', {
                'error': 'Whisper module is not installed'
            })
        
        # Create necessary directories
        os.makedirs(audio_output_dir, exist_ok=True)
        os.makedirs(video_output_dir, exist_ok=True)
        
        # Create temporary directory outside of outputs directory
        self.temp_dir = "/tmp/audio_processing"
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_audio_from_video(self, video_path, audio_path):
        """Extract audio from video file using ffmpeg."""
        try:
            self.logger.log_file_event('video_audio_extraction_start', video_path)
            command = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Disable video
                '-acodec', 'pcm_s16le',  # Audio codec
                '-ar', '16000',  # Sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                audio_path
            ]
            result = subprocess.run(command, check=True, capture_output=True)
            self.logger.log_file_event('video_audio_extraction_complete', audio_path)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.log_anomaly('video_processing_error', {
                'file': video_path,
                'error': str(e),
                'stderr': e.stderr.decode() if e.stderr else None
            })
            return False

    def transcribe_audio(self, audio_path, output_path, file_type="audio", respondent_id=None, col_num=None):
        """Transcribe audio file using Whisper."""
        try:
            self.logger.log_file_event('transcription_start', audio_path)
            
            # Check if whisper is available
            if not WHISPER_AVAILABLE or self.model is None:
                self.logger.log_anomaly('whisper_not_available', {
                    'file': audio_path,
                    'error': 'Whisper module is not installed'
                })
                return False
            
            # Transcribe
            result = self.model.transcribe(audio_path)
            
            # Get original filename
            fname = os.path.basename(audio_path)
            
            # Create JSON document
            doc = {
                'text': result["text"],
                'filename': fname,
                'filetype': os.path.splitext(fname)[1].lower().lstrip('.') if '.' in fname else file_type,
                'duration': result.get('duration', 0),
                'language': result.get('language', 'unknown'),
                'transcription_timestamp': datetime.datetime.now().isoformat()
            }
            
            # Add respondent info if available
            if respondent_id:
                doc['respondent_id'] = respondent_id
                doc['file_column'] = col_num
            
            # Write JSON document
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            
            self.logger.log_file_event('json_transcription_saved', output_path, {
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

    def process_audio_file(self, file_path, output_dir):
        """Process a single audio file."""
        try:
            fname = os.path.basename(file_path)
            ext = os.path.splitext(fname)[1].lower()
            new_filename, respondent_id, col_num = self.filename_util.get_output_filename(fname, '.json')
            output_path = os.path.join(output_dir, str(new_filename))
            
            return self.transcribe_audio(
                file_path, 
                output_path, 
                file_type=ext.lstrip('.'),
                respondent_id=respondent_id,
                col_num=col_num
            )
        except Exception as e:
            self.logger.log_anomaly('audio_processing_error', {
                'file': file_path,
                'error': str(e)
            })
            return False

    def process_video_file(self, file_path, output_dir):
        """Process a single video file."""
        try:
            fname = os.path.basename(file_path)
            base_name = Path(file_path).stem
            temp_audio = os.path.join(self.temp_dir, f"{base_name}.wav")
            ext = os.path.splitext(fname)[1].lower()
            
            # Extract audio
            if not self.extract_audio_from_video(str(file_path), temp_audio):
                return False
            
            # Transcribe
            new_filename, respondent_id, col_num = self.filename_util.get_output_filename(fname, '.json')
            output_path = os.path.join(output_dir, str(new_filename))
            success = self.transcribe_audio(
                temp_audio, 
                output_path, 
                file_type=ext.lstrip('.'),
                respondent_id=respondent_id,
                col_num=col_num
            )
            
            # Cleanup temporary file
            try:
                os.remove(temp_audio)
            except Exception as e:
                self.logger.log_anomaly('cleanup_error', {
                    'file': temp_audio,
                    'error': str(e)
                })
            
            return success
        except Exception as e:
            self.logger.log_anomaly('video_processing_error', {
                'file': file_path,
                'error': str(e)
            })
            return False

    def process_directory(self, input_dir, output_dir, formats):
        """Process all files in a directory with given formats."""
        for root, _, files in os.walk(input_dir):
            for fname in files:
                if fname.startswith('.') or fname in [".DS_Store", ".gitkeep"]:
                    continue

                file_path = os.path.join(root, fname)
                ext = Path(file_path).suffix.lower()
                
                if ext not in formats:
                    continue

                # Get relative path to maintain directory structure
                rel_path = os.path.relpath(root, input_dir)
                output_subdir = os.path.join(output_dir, rel_path)
                os.makedirs(output_subdir, exist_ok=True)
                
                # Ensure only JSON files will be written to output directory
                new_filename, respondent_id, col_num = self.filename_util.get_output_filename(fname, '.json')
                output_path = os.path.join(output_subdir, str(new_filename))
                
                if os.path.exists(output_path) and not self.force_reprocess:
                    self.logger.log_file_event('skip_existing_output', file_path, {
                        'output_path': output_path
                    })
                    continue

                # Process file based on type
                if ext in ['.mp4', '.mov', '.avi', '.mkv']:
                    self.process_video_file(file_path, output_subdir)
                else:  # audio files
                    self.process_audio_file(file_path, output_subdir)

    def process_files(self):
        """Process all audio and video files."""
        self.logger.log_system_state()

        # Define supported formats
        audio_formats = ['.mp3', '.wav', '.m4a']
        video_formats = ['.mp4', '.mov', '.avi', '.mkv']

        try:
            # Process audio directory
            if os.path.exists(self.audio_input_dir):
                self.process_directory(self.audio_input_dir, self.audio_output_dir, audio_formats)
            
            # Process video directory
            if os.path.exists(self.video_input_dir):
                self.process_directory(self.video_input_dir, self.video_output_dir, video_formats)
        finally:
            # Clean up any temporary files
            self.cleanup_temp_files()
            
        self.logger.log_system_state()
        
    def cleanup_temp_files(self):
        """Clean up any temporary files left in the temporary directory."""
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            self.logger.log_file_event('temp_file_removed', file_path)
                    except Exception as e:
                        self.logger.log_anomaly('temp_file_cleanup_error', {
                            'file': file_path,
                            'error': str(e)
                        })
        except Exception as e:
            self.logger.log_anomaly('temp_dir_cleanup_error', {
                'dir': self.temp_dir,
                'error': str(e)
            })

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process audio and video files with Whisper.")
    parser.add_argument("audio_input_dir", help="Directory containing audio files")
    parser.add_argument("video_input_dir", help="Directory containing video files")
    parser.add_argument("audio_output_dir", help="Directory for audio transcription outputs")
    parser.add_argument("video_output_dir", help="Directory for video transcription outputs")
    parser.add_argument("--force", "-f", action="store_true", help="Force reprocessing of files that already have outputs")
    parser.add_argument("--mapping", "-m", help="Path to mapping file for filename conversion")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.audio_input_dir) and not os.path.exists(args.video_input_dir):
        print(f"Error: Neither audio input directory '{args.audio_input_dir}' nor video input directory '{args.video_input_dir}' exist.")
        sys.exit(1)

    transcriber = WhisperTranscriber(
        args.audio_input_dir, 
        args.video_input_dir, 
        args.audio_output_dir, 
        args.video_output_dir,
        mapping_file=args.mapping,
        force_reprocess=args.force
    )
    transcriber.process_files()