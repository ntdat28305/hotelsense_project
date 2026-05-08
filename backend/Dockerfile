FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium chromium-driver wget curl \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir PyJWT httpx boto3 undetected-chromedriver tensorflow keras

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]