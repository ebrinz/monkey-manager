# Makefile for Document Processing System

# Configuration
DOCKER_COMPOSE = docker-compose
DOCKER = docker
VERSION = 1.0.0

# Directories
DIRS = tmp outputs outputs/logs

.PHONY: all build clean run test help extract transcribe youtube prepare-inputs init-files logs status prune rebuild check-env single-service single-file surveymonkey-enrich surveymonkey-validate

all: prepare-inputs build run

# Create necessary directories
$(DIRS):
	mkdir -p $@

# Check environment setup
check-env:
	@echo "Checking environment configuration..."
	@test -f .env || { echo "Error: .env file not found. Copy .env.example to .env and configure it."; exit 1; }
	@grep -q "DOCS_INPUT" .env || echo "Warning: DOCS_INPUT not configured in .env"
	@grep -q "DOCS_OUTPUT" .env || echo "Warning: DOCS_OUTPUT not configured in .env"

# Check and extract zips if needed
prepare-inputs: check-env $(DIRS)
	@echo "Checking for zip files in inputs directory..."
	@find inputs -name "*.zip" -type f -exec sh -c ' \
		echo "Extracting $$0..."; \
		unzip -o -d "$${0%/*}" "$$0"; \
		echo "Removing $$0..."; \
		rm "$$0"' {} \;

# Initialize necessary Python files
init-files:
	@echo "Initializing necessary files..."
	@touch $(DIRS)

# Build all containers
build: $(DIRS) init-files
	@echo "Building containers..."
	$(DOCKER) build -t text-extractor -f Dockerfile.extractor .
	$(DOCKER) build -t whisper-service -f Dockerfile.whisper .
	$(DOCKER) build -t youtube-dl -f Dockerfile.youtube .

# Rebuild single container
rebuild-service:
	@echo "Usage: make rebuild-service SERVICE=<service-name>"
	@if [ "$(SERVICE)" = "text-extractor" ]; then \
		$(DOCKER) build -t text-extractor -f Dockerfile.extractor .; \
	elif [ "$(SERVICE)" = "whisper-service" ]; then \
		$(DOCKER) build -t whisper-service -f Dockerfile.whisper .; \
	elif [ "$(SERVICE)" = "youtube-dl" ]; then \
		$(DOCKER) build -t youtube-dl -f Dockerfile.youtube .; \
	else \
		echo "Error: SERVICE parameter required. Use SERVICE=text-extractor, SERVICE=whisper-service, or SERVICE=youtube-dl"; \
	fi

# Run text extraction
extract: prepare-inputs
	$(DOCKER_COMPOSE) up -d text-extractor
	$(DOCKER_COMPOSE) logs -f text-extractor

# Force run text extraction (reprocess all files)
extract-force: prepare-inputs
	$(DOCKER_COMPOSE) run --rm text-extractor python /app/text_extractor.py "/files" "/output" --force
	
# Run audio/video transcription
transcribe: prepare-inputs
	$(DOCKER_COMPOSE) up -d whisper-service
	$(DOCKER_COMPOSE) logs -f whisper-service

# Force run audio/video transcription (reprocess all files)
transcribe-force: prepare-inputs
	$(DOCKER_COMPOSE) run --rm whisper-service python3 /app/whisper_service.py "/audio" "/video" "/audio_out" "/video_out" --force

# Download and process YouTube
youtube: prepare-inputs
	$(DOCKER_COMPOSE) up -d youtube-dl
	$(DOCKER_COMPOSE) logs -f youtube-dl
	
# Force download and process YouTube (reprocess all links)
youtube-force: prepare-inputs
	$(DOCKER_COMPOSE) run --rm youtube-dl python3 /app/youtube_service.py "/youtube/links.xlsx" "/output/youtube" "/video" --force

# Process a single file with Whisper
process-audio-file:
	@echo "Usage: make process-audio-file FILE=/path/to/audio/file.mp3 [FORCE=1]"
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required"; \
	elif [ "$(FORCE)" = "1" ]; then \
		$(DOCKER_COMPOSE) run --rm whisper-service python3 /app/whisper_service.py "/audio/$(notdir $(FILE))" "" "/audio_out" "" --force; \
	else \
		$(DOCKER_COMPOSE) run --rm whisper-service python3 /app/whisper_service.py "/audio/$(notdir $(FILE))" "" "/audio_out" ""; \
	fi

# Process a single file with text extractor
process-doc-file:
	@echo "Usage: make process-doc-file FILE=/path/to/doc/file.pdf [FORCE=1]"
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required"; \
	elif [ "$(FORCE)" = "1" ]; then \
		$(DOCKER_COMPOSE) run --rm text-extractor python /app/text_extractor.py "/files/$(notdir $(FILE))" "/output" --force; \
	else \
		$(DOCKER_COMPOSE) run --rm text-extractor python /app/text_extractor.py "/files/$(notdir $(FILE))" "/output"; \
	fi

# Process a single YouTube video
process-youtube:
	@echo "Usage: make process-youtube URL=https://www.youtube.com/watch?v=xxxx [FORCE=1]"
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL parameter required"; \
	elif [ "$(FORCE)" = "1" ]; then \
		$(DOCKER_COMPOSE) run --rm youtube-dl python3 /app/youtube_service.py "/youtube/links.xlsx" "/output/youtube" "/video" --force; \
	else \
		$(DOCKER_COMPOSE) run --rm youtube-dl python3 /app/youtube_service.py "/youtube/links.xlsx" "/output/youtube" "/video"; \
	fi

# Process everything
run: extract youtube transcribe surveymonkey-enrich surveymonkey-validate

# Enrich JSON files with respondent IDs and metadata from Survey Monkey mapping file
surveymonkey-enrich:
	@echo "Enriching JSON files with respondent IDs from Survey Monkey mapping file..."
	$(DOCKER_COMPOSE) run --rm text-extractor python /app/surveymonkey_enricher.py "/mapping/mapping_file.xlsx" "/output" "/audio_out" "/video_out" "/output/youtube"

# Validate processing by checking for missing files against Survey Monkey mapping file
surveymonkey-validate:
	@echo "Validating that all files in Survey Monkey mapping file were processed..."
	$(DOCKER_COMPOSE) run --rm text-extractor python /app/surveymonkey_validator.py "/mapping/mapping_file.xlsx" "/output" "/audio_out" "/video_out" "/output/youtube"

# Display container status
status:
	$(DOCKER_COMPOSE) ps

# View container logs
logs:
	@if [ -z "$(SERVICE)" ]; then \
		$(DOCKER_COMPOSE) logs -f; \
	else \
		$(DOCKER_COMPOSE) logs -f $(SERVICE); \
	fi

# Stop all containers
stop:
	$(DOCKER_COMPOSE) down

# Clean up
clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf tmp/*
	find outputs -type f -not -path "*/logs/*" -not -name '.gitkeep' -delete
	rm -f *.py

# More aggressive cleanup - remove all Docker images and volumes
prune: clean
	$(DOCKER) system prune -af --volumes

# Run tests
test:
	python -m pytest tests/

# Help
help:
	@echo "Available targets:"
	@echo "  make prepare-inputs                - Extract any zip files in inputs directory"
	@echo "  make build                         - Build all Docker images"
	@echo "  make rebuild-service SERVICE=x     - Rebuild specific service (text-extractor, whisper-service, youtube-dl)"
	@echo "  make extract                       - Run text extraction (skips already processed files)"
	@echo "  make extract-force                 - Run text extraction (reprocesses all files)"
	@echo "  make transcribe                    - Run audio/video transcription (skips already processed files)"
	@echo "  make transcribe-force              - Run audio/video transcription (reprocesses all files)"
	@echo "  make youtube                       - Process YouTube videos (skips already processed links)"
	@echo "  make youtube-force                 - Process YouTube videos (reprocesses all links)"
	@echo "  make process-audio-file FILE=x     - Process a single audio file"
	@echo "  make process-doc-file FILE=x       - Process a single document file"
	@echo "  make process-youtube URL=x         - Process a single YouTube URL"
	@echo "  make run                           - Run complete pipeline"
	@echo "  make surveymonkey-enrich           - Enrich JSON files with Survey Monkey respondent IDs"
	@echo "  make surveymonkey-validate         - Validate files against Survey Monkey mapping file"
	@echo "  make status                        - Show status of containers"
	@echo "  make logs [SERVICE=x]              - View logs (optionally for specific service)"
	@echo "  make stop                          - Stop all containers"
	@echo "  make clean                         - Clean up generated files"
	@echo "  make prune                         - Clean up and remove all Docker resources"
	@echo "  make test                          - Run tests"
	@echo "  make help                          - Show this help"