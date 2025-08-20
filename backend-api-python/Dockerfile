FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

EXPOSE 8004

# Use the new v2 backend with proper logging
# Remove --reload for production deployment
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004", "--reload", "--log-level", "info", "--access-log"]