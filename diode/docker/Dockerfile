FROM python:3.11-slim

WORKDIR /app

# Install htop, procps (top, ps), and curl for direct interactive inspection in Docker Desktop
RUN apt-get update && apt-get install -y --no-install-recommends \
    htop \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the authentic NPPAD datasets and SCADA server script
COPY scada_server.py /app/scada_server.py
COPY nppad_normal.csv /app/nppad_normal.csv
COPY nppad_lof.csv /app/nppad_lof.csv
COPY nppad_loca.csv /app/nppad_loca.csv

ENV PYTHONUNBUFFERED=1

EXPOSE 502
EXPOSE 8080

CMD ["python", "scada_server.py"]
