import os
import sys
import whisper
import subprocess
from pathlib import Path
from forensic_logger import ForensicLogger
from file_renamer import FilenamingUtility

class WhisperTranscriber:
    def __init__(self, audio_input_dir, video_input_dir, audio_output_dir, video_output_dir, mapping_file=None):
        self.audio_input_dir = audio_input_dir
        self.video_input_dir = video_input_dir
        self.audio_output_dir = audio_output_dir
        self.video_output_dir = video_output_dir
        self.logger = ForensicLogger("/output/logs")
        
        # Initialize filename utility
        enable_renaming = os.environ.get('ENABLE_FILE_RENAMING', 'true').lower() == 'true'
        self.filename_util = FilenamingUtility(mapping_file, enable_renaming)
        
        # Initialize whisper model
        self.model = whisper.load_model("base")
        
        # Create necessary directories
        os.makedirs(audio_output_dir, exist_ok=True)
        os.makedirs(video_output_dir, exist_ok=True)
        os.makedirs("/tmp/audio_processing", exist_ok=True)

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

    def transcribe_audio(self, audio_path, output_path):
        """Transcribe audio file using Whisper."""
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

    def process_audio_file(self, file_path, output_dir):
        """Process a single audio file."""
        try:
            fname = os.path.basename(file_path)
            new_filename = self.filename_util.get_output_filename(fname, '.txt')
            output_path = os.path.join(output_dir, new_filename)
            
            return self.transcribe_audio(file_path, output_path)
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
            temp_audio = os.path.join("/tmp/audio_processing", f"{base_name}.wav")
            
            # Extract audio
            if not self.extract_audio_from_video(str(file_path), temp_audio):
                return False
            
            # Transcribe
            new_filename = self.filename_util.get_output_filename(fname, '.txt')
            output_path = os.path.join(output_dir, new_filename)
            success = self.transcribe_audio(temp_audio, output_path)
            
            # Cleanup
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

        # Process audio directory
        if os.path.exists(self.audio_input_dir):
            self.process_directory(self.audio_input_dir, self.audio_output_dir, audio_formats)
        
        # Process video directory
        if os.path.exists(self.video_input_dir):
            self.process_directory(self.video_input_dir, self.video_output_dir, video_formats)

        self.logger.log_system_state()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python whisper_service.py <audio_input_dir> <video_input_dir> <audio_output_dir> <video_output_dir>")
        sys.exit(1)

    audio_input_dir = sys.argv[1]
    video_input_dir = sys.argv[2]
    audio_output_dir = sys.argv[3]
    video_output_dir = sys.argv[4]

    if not os.path.exists(audio_input_dir) and not os.path.exists(video_input_dir):
        print(f"Error: Neither audio input directory '{audio_input_dir}' nor video input directory '{video_input_dir}' exist.")
        sys.exit(1)

    transcriber = WhisperTranscriber(audio_input_dir, video_input_dir, audio_output_dir, video_output_dir)
    transcriber.process_files()