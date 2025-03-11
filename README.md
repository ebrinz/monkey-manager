# Document Processing System

A secure, containerized system for processing various types of documents and media:
- PDF/DOCX sanitization and text extraction
- Audio/Video transcription using OpenAI's Whisper
- YouTube video download and transcription

## Project Structure
```
.
├── Dockerfile.extractor
├── Dockerfile.whisper
├── Dockerfile.youtube
├── Makefile
├── README.md
├── docker-compose.yml
├── .env
├── seccomp.json               # Security profile
│
├── src
│   ├── __init__.py
│   ├── file_renamer.py
│   ├── forensic_analysis.py
│   ├── forensic_logger.py
│   ├── process_files.py.old
│   ├── surveymonkey_enricher.py  # Adds Survey Monkey respondent_id to JSON files
│   ├── surveymonkey_validator.py # Validates processing against Survey Monkey mappings
│   ├── text_extractor.py
│   ├── whisper_service.py
│   └── youtube_service.py
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
- Skip already processed files to save time on re-runs

### 2. Audio Transcription
- Support for WAV, MP3, MP4, and other audio/video formats
- GPU-accelerated processing with Whisper
- High-accuracy transcription to text
- Skip already processed files to improve performance

### 3. YouTube Processing
- Download from YouTube links
- Extract audio streams
- Generate English transcriptions
- Skip already processed videos/URLs on subsequent runs

## Setup

1. **Environment Variables**
   Copy `.env.example` to `.env` and configure:
   ```bash
   # Survey Monkey output file renaming
   ENABLE_FILE_RENAMING=true
   
   # Force reprocessing of existing files (set to true to ignore output files)
   FORCE_REPROCESS=false
   
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
       make prepare-inputs     - Extract any zip files in inputs directory
       make build              - Build all Docker images
       make extract            - Run text extraction (skips already processed files)
       make extract-force      - Run text extraction (reprocesses all files)
       make transcribe         - Run audio/video transcription (skips already processed files)
       make transcribe-force   - Run audio/video transcription (reprocesses all files)
       make youtube            - Process YouTube videos (skips already processed links)
       make youtube-force      - Process YouTube videos (reprocesses all links)
       make surveymonkey-enrich - Enrich JSON files with Survey Monkey respondent IDs
       make surveymonkey-validate - Validate files against Survey Monkey mapping file
       make run                - Run complete pipeline
       make stop               - Stop all containers
       make clean              - Clean up all generated files
       make test               - Run tests
       make help               - Show this help
     ```

## Security Features
- Containerized execution
- Read-only input volumes
- Network isolation where possible
- Custom seccomp profiles
- Resource limits
- Non-root execution

## Usage Examples

0. **Setup**
   ```bash
   make build
   make prepare-inputs
   ```

1. **Document Processing**
   ```bash
   # Skip already processed files (faster)
   make extract
   
   # Force reprocessing of all files
   make extract-force
   ```

2. **Audio Transcription**
   ```bash
   # Skip already processed files (faster)
   make transcribe
   
   # Force reprocessing of all audio/video files
   make transcribe-force
   ```

3. **YouTube Processing**
   ```bash
   # Skip already processed videos/URLs
   make youtube
   
   # Force reprocessing of all YouTube links
   make youtube-force
   ```
   
4. **Single File Processing**
   ```bash
   # Process a single file (skip if already processed)
   make process-audio-file FILE=/path/to/audio.mp3
   
   # Process a single file (force reprocessing)
   make process-audio-file FILE=/path/to/audio.mp3 FORCE=1
   ```

5. **Survey Monkey Processing**
   ```bash
   # Add respondent IDs to JSON files from Survey Monkey mapping
   make surveymonkey-enrich
   
   # Validate all files in Survey Monkey mapping were processed
   make surveymonkey-validate
   ```

## Cleanup
```bash
# Stop all containers
make stop

# Clean all generated files
make clean
```