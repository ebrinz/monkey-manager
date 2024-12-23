# monkey-manager
Automating Survey Monkey response processing



## Setup Instructions

## 5. Add questionable PDFs and DOCXs to input folder and adjust the .env mapping file name as necessary

.env:
INPUT_DIR=./inputs
OUTPUT_DIR=./outputs
MAPPING_FILE=./mappings/Channeled\ Content\ and\ ETI\ 12_17_24.xlsx

## notice escaped spaces on filename

Build and Load arm64:

bash```
docker buildx build --platform linux/arm64 -t sandbox-image --load .
```

Build and Load amd64:

bash```
docker buildx build --platform linux/amd64 -t sandbox-image --load .
```

bash```
docker-compose up --remove-orphans --exit-code-from sandbox

```
