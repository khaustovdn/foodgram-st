# backend/Dockerfile

FROM python:3.10

WORKDIR /app

# Install Python dependencies
RUN pip install gunicorn==20.1.0
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir

# Set environment variables
ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0:8000"

# Run Gunicorn
COPY . .
CMD ["gunicorn", "foodgram.wsgi:application"]