FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

EXPOSE 3001

# Run with reload for development, remove --reload for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001", "--reload"]