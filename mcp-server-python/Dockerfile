FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

# Expose port for HTTP service
EXPOSE 8888

# Run the MCP server
CMD ["python", "main.py"]