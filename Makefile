# Makefile for Document Processing System

# Configuration
DOCKER_COMPOSE = docker-compose
DOCKER = docker
VERSION = 1.0.0

# Directories
DIRS = tmp outputs

.PHONY: all build clean run test help extract transcribe youtube prepare-inputs init-files

all: prepare-inputs build run

# Create necessary directories
$(DIRS):
	mkdir -p $@

# Check and extract zips if needed
prepare-inputs:
	@echo "Checking for zip files in inputs directory..."
	@find inputs -name "*.zip" -type f -exec sh -c ' \
		echo "Extracting $$0..."; \
		unzip -o -d "$${0%/*}" "$$0"; \
		echo "Removing $$0..."; \
		rm "$$0"' {} \;

# Build all containers
build: $(DIRS) init-files
	@echo "Building containers..."
	$(DOCKER) build -t text-extractor -f Dockerfile.extractor .
	$(DOCKER) build -t whisper-service -f Dockerfile.whisper .
	$(DOCKER) build -t youtube-dl -f Dockerfile.youtube .

# Run text extraction
extract: prepare-inputs
	$(DOCKER_COMPOSE) up text-extractor

# Run audio/video transcription
transcribe: prepare-inputs
	$(DOCKER_COMPOSE) up whisper-service

# Download and process YouTube
youtube: prepare-inputs
	$(DOCKER_COMPOSE) up youtube-dl

# Process everything
run: extract youtube transcribe

# Stop all containers
stop:
	$(DOCKER_COMPOSE) down

# Clean up
clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf tmp/*
	rm -rf outputs/*
	find outputs -type f -not -name '.gitkeep' -delete
	rm -f *.py

# Run tests
test:
	python -m pytest tests/

# Help
help:
	@echo "Available targets:"
	@echo "  make prepare-inputs - Extract any zip files in inputs directory"
	@echo "  make init-files    - Initialize necessary Python files"
	@echo "  make build         - Build all Docker images"
	@echo "  make extract       - Run text extraction"
	@echo "  make transcribe    - Run audio/video transcription"
	@echo "  make youtube       - Process YouTube videos"
	@echo "  make run           - Run complete pipeline"
	@echo "  make stop          - Stop all containers"
	@echo "  make clean         - Clean up all generated files"
	@echo "  make test          - Run tests"
	@echo "  make help          - Show this help"