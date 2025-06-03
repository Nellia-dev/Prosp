FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download and install Playwright browsers
RUN playwright install --with-deps chromium 

COPY . .

EXPOSE 7777

CMD ["python", "harvester.py"] 