FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY entrypoint.sh .
COPY config.example.json .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create config directory
RUN mkdir -p /config

# Expose Streamlit port
EXPOSE 8501

# Use entrypoint script to initialize config
ENTRYPOINT ["./entrypoint.sh"]
