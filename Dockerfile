FROM python:3.12-slim

WORKDIR /app

# Install dependencies (paths relative to repo root build context)
COPY flow/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY flow/server.py .
COPY flow/static/ static/

EXPOSE 8765

CMD ["python", "server.py"]
