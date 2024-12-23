# Use a lightweight Python base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy the Python script into the container
COPY process_files.py /app/

# Install necessary Python libraries
RUN pip install --no-cache-dir PyMuPDF oletools python-docx pandas openpyxl

# Define default command
CMD ["python", "/app/process_files.py", "/files", "/output", "/mapping/mapping_file.xlsx"]