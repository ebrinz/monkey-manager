# Document Processing System

A secure, containerized system for processing various types of documents and media:
- PDF/DOCX sanitization and text extraction
- Audio transcription using OpenAI's Whisper
- YouTube video download and transcription

## Project Structure
```
.
├── Dockerfile.extractor
├── Dockerfile.whisper
├── Dockerfile.youtube
├── Makefile
├── README.md
├── docker-compose.ym
├── .env
├── seccomp.json               # Security profile
│
├── src
│   ├── __init__.py
│   ├── file_renamer.py
│   ├── forensic_analysis.py
│   ├── forensic_logger.py
│   ├── process_files.py.old
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
- Support for WAV, MP3, MP4, and other audio/video formats
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
   # Survey Monkey output file renaming
   ENABLE_FILE_RENAMING=true
   # Mapping File
   MAPPING_FILE=./inputs/.../.xlsx
   YOUTUBE_LINKS_FILE=./inputs/.../youtube_links.csv


   # Input Directories
   DOCS_INPUT=./inputs/...
   AUDIO_INPUT=./inputs/...
   VIDEO_INPUT=./inputs/...


   # Output Directories
   DOCS_OUTPUT=../outputs/...
   AUDIO_OUTPUT=./outputs/...
   VIDEO_OUTPUT=./outputs/...
   YOUTUBE_OUTPUT=./outputs/...

   # Temporary Directory
   TMP_DIR=./tmp
   ```

2. **Run Services**
   - Document processing:
     ```bash
     Available targets:
       make prepare-inputs - Extract any zip files in inputs directory
       make init-files    - Initialize necessary Python files
       make build         - Build all Docker images
       make extract       - Run text extraction
       make transcribe    - Run audio/video transcription
       make youtube       - Process YouTube videos
       make run           - Run complete pipeline
       make stop          - Stop all containers
       make clean         - Clean up all generated files
       make test          - Run tests
       make help          - Show this help
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
