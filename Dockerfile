# Use Debian slim (not Alpine) for better Deno + yt-dlp EJS compatibility
FROM python:3.12-slim

# Install system dependencies: curl, unzip, ffmpeg, aria2, build tools, mp4decrypt deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl unzip ffmpeg aria2 \
    gcc g++ make cmake wget git \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (JS runtime for yt-dlp EJS challenge solving)
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

# Build Bento4 (mp4decrypt)
RUN wget -q https://github.com/axiomatic-systems/Bento4/archive/v1.6.0-639.zip && \
    unzip v1.6.0-639.zip && \
    cd Bento4-1.6.0-639 && \
    mkdir build && cd build && cmake .. && make -j$(nproc) && \
    cp mp4decrypt /usr/local/bin/ && \
    cd ../.. && rm -rf Bento4-1.6.0-639 v1.6.0-639.zip

# Set the working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
# yt-dlp[default] includes EJS scripts for n-challenge solving (crucial!)
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir --upgrade -r sainibots.txt \
    && pip3 install --no-cache-dir "yt-dlp[default]" \
    && pip3 install --no-cache-dir bgutil-ytdlp-pot-provider

# Expose the port Render expects
EXPOSE 8000

# Set the command to run the application
# Render provides the PORT environment variable
CMD ["sh", "-c", "rm -f bot.session bot.session-journal && gunicorn --bind 0.0.0.0:${PORT:-8000} app:app & python3 modules/main.py"]
