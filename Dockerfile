# Use a Python 3.12.3 Alpine base image
FROM python:3.12-alpine3.20

# Install Deno (JS runtime for yt-dlp PO token generation)
# Official installer auto-picks correct musl binary for Alpine
RUN apk add --no-cache curl unzip \
    && curl -fsSL https://deno.land/install.sh | sh \
    && mv /root/.deno/bin/deno /usr/local/bin/deno \
    && chmod +x /usr/local/bin/deno \
    && rm -rf /root/.deno

# Set the working directory
WORKDIR /app

# Install necessary system dependencies
RUN apk add --no-cache \
    gcc \
    libffi-dev \
    musl-dev \
    ffmpeg \
    aria2 \
    make \
    g++ \
    cmake \
    wget \
    unzip \
    git

# Build Bento4 (mp4decrypt)
RUN wget -q https://github.com/axiomatic-systems/Bento4/archive/v1.6.0-639.zip && \
    unzip v1.6.0-639.zip && \
    cd Bento4-1.6.0-639 && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make -j$(nproc) && \
    cp mp4decrypt /usr/local/bin/ &&\
    cd ../.. && \
    rm -rf Bento4-1.6.0-639 v1.6.0-639.zip

# Copy application files
COPY . .

# Install Python dependencies
# Added setuptools to fix 'pkg_resources' error on Render/Alpine
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir --upgrade -r sainibots.txt \
    && python3 -m pip install -U yt-dlp \
    && pip3 install -U bgutil-ytdlp-pot-provider

# Expose the port Render expects
EXPOSE 8000

# Set the command to run the application
# Render provides the PORT environment variable
CMD ["sh", "-c", "rm -f bot.session bot.session-journal && gunicorn --bind 0.0.0.0:${PORT:-8000} app:app & python3 modules/main.py"]
