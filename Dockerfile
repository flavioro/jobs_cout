FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends     libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0     libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1     libxrandr2 libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .
RUN mkdir -p data/raw_html

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
