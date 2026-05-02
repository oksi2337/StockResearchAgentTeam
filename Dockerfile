FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY data/ ./data/

CMD ["python", "-u", "scripts/discord_bot.py"]
