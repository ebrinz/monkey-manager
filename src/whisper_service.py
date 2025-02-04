import os
import sys
import whisper
import subprocess
import tempfile
from pathlib import Path
from forensic_logger import ForensicLogger

class WhisperTranscriber:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = ForensicLogger("/output/logs")
        self.model = whisper.load_model("base")
        os.makedirs(output_dir, exist_ok=True)
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

    def process_media_file(self, file_path, output_dir):
        """Process a single media file."""
        base_name = Path(file_path).stem
        ext = Path(file_path).suffix.lower()
        output_path = os.path.join(output_dir, f"{base_name}.txt")

        # Create temporary audio file if needed
        if ext in ['.mp4', '.mov', '.avi', '.mkv']:
            temp_audio = os.path.join("/tmp/audio_processing", f"{base_name}.wav")
            if not self.extract_audio_from_video(str(file_path), temp_audio):
                return False
            audio_path = temp_audio
        else:
            audio_path = file_path

        # Transcribe
        success = self.transcribe_audio(audio_path, output_path)

        # Cleanup temporary files
        if ext in ['.mp4', '.mov', '.avi', '.mkv']:
            try:
                os.remove(audio_path)
            except Exception as e:
                self.logger.log_anomaly('cleanup_error', {
                    'file': audio_path,
                    'error': str(e)
                })

        return success

    def process_files(self):
        """Process all audio and video files."""
        self.logger.log_system_state()

        # Define supported formats
        supported_formats = ['.mp3', '.wav', '.m4a', '.mp4', '.mov', '.avi', '.mkv']

        for root, _, files in os.walk(self.input_dir):
            for fname in files:
                if fname.startswith('.') or fname in [".DS_Store", ".gitkeep"]:
                    continue

                file_path = os.path.join(root, fname)
                if Path(file_path).suffix.lower() not in supported_formats:
                    continue

                # Get relative path to maintain directory structure
                rel_path = os.path.relpath(root, self.input_dir)
                output_subdir = os.path.join(self.output_dir, rel_path)
                os.makedirs(output_subdir, exist_ok=True)

                self.process_media_file(file_path, output_subdir)

        self.logger.log_system_state()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python whisper_service.py <input_dir> <output_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    transcriber = WhisperTranscriber(input_dir, output_dir)
    transcriber.process_files()