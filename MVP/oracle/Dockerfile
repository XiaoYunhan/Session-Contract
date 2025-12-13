FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run oracle (default to sim mode)
CMD ["python", "oracle.py", "--mode", "sim", "--session-id", "demo", "--backend-url", "http://backend:8000"]
