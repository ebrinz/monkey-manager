# Document Processing System

A secure, containerized system for processing various types of documents and media:
- PDF/DOCX sanitization and text extraction
- Audio transcription using OpenAI's Whisper
- YouTube video download and transcription

## Project Structure
```
.
├── Dockerfile.extractor
├── Dockerfile.renamer
├── Dockerfile.whisper
├── Dockerfile.youtube
├── Makefile
├── .env
├── README.md
├── docker-compose.yml
├── seccomp.json               # Security profile
│
├── src
│   ├── __init__.py
│   ├── file_renamer.py
│   ├── forensic_analysis.py
│   ├── forensic_logger.py
│   ├── process_files.py
│   ├── text_extractor.py
│   ├── whisper_service.py
│   └── youtube_service.py
│
├── inputs/                    # Input files directory
│   └── .gitkeep
├── outputs/                   # Processed outputs
│   └── .gitkeep
├── mappings/                  # File mapping spreadsheets
│   └── .gitkeep
└── tmp/                      # Temporary processing directory
    └── .gitkeep
```

## Features

### 1. Document Processing
- Secure PDF and DOCX sanitization
- Text extraction with macro detection
- File renaming based on mapping spreadsheet

### 2. Audio Transcription
- Support for WAV, MP3, and other audio formats
- GPU-accelerated processing with Whisper
- High-accuracy transcription to text

### 3. YouTube Processing
- Download from YouTube links
- Extract audio streams
- Generate English transcriptions

## Setup

1. **Environment Variables**
   Copy `.env.example` to `.env` and configure:
   ```bash
   INPUT_DIR=./inputs
   OUTPUT_DIR=./outputs
   MAPPING_FILE=./mappings/mapping.xlsx
   MAPPING_DIR=./mappings
   AUDIO_INPUT=./inputs/audio
   YOUTUBE_LINKS=./inputs/youtube
   TMP_DIR=./tmp
   ```

2. **Build Containers**
   ```bash
   make build
   ```

3. **Run Services**
   - Document processing:
     ```bash
     make run
     ```
   - Audio transcription:
     ```bash
     make transcribe
     ```
   - YouTube processing:
     ```bash
     make youtube
     ```

## Security Features
- Containerized execution
- Read-only input volumes
- Network isolation where possible
- Custom seccomp profiles
- Resource limits
- Non-root execution

## Usage Examples

1. **Document Processing**
   ```bash
   # Place files in inputs/
   # Put mapping file in mappings/
   make run
   ```

2. **Audio Transcription**
   ```bash
   # Place audio files in inputs/audio/
   make transcribe
   ```

3. **YouTube Processing**
   ```bash
   # Create inputs/youtube/links.txt with URLs
   make youtube
   ```

## Cleanup
```bash
# Stop all containers
make stop

# Clean all generated files
make clean
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License
MIT License