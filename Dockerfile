# Use Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Node.js, Mermaid, and Puppeteer (Chrome)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    fonts-liberation \
    lsb-release \
    xdg-utils \
    wget \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @mermaid-js/mermaid-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir faiss-cpu sentence-transformers

# Copy the entire project
COPY . .

# Create a proper health check script
RUN printf "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n@app.get('/')\nasync def health():\n    return {'status': 'worker_running'}\nif __name__ == '__main__':\n    uvicorn.run(app, host='0.0.0.0', port=7860)\n" > hf_health_check.py

# Create a startup script that runs both the worker and the health check
RUN echo "#!/bin/bash\npython hf_health_check.py & python -m srs_engine.worker\nwait" > start_hf.sh
RUN chmod +x start_hf.sh

# Hugging Face Spaces always use port 7860
EXPOSE 7860

# Start the application
CMD ["./start_hf.sh"]
