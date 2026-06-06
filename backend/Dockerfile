FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN test -f /app/scripts/docker_start.sh && chmod +x /app/scripts/docker_start.sh

EXPOSE 8000

CMD ["sh", "/app/scripts/docker_start.sh"]
