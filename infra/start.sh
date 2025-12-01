#!/bin/bash

# Navigate to the directory where this script resides (infra/)
cd "$(dirname "$0")"

echo "🚀 Starting ListingLens..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "Please install Docker Desktop for Mac: https://docs.docker.com/desktop/install/mac-install/"
    echo "After installing, open the Docker app to start the engine, then run this script again."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker is installed but not running."
    echo "Please open the Docker Desktop app to start the Docker engine."
    exit 1
fi

echo "✅ Docker is up and running."

# Check for encrypted .env file and decrypt if it exists
if [ -f .env.encrypted ]; then
    echo " decrypting .env file..."
    python3 decrypt.py
    echo "✅ .env file decrypted."
fi

# Run Docker Compose
echo "🏗️  Building and starting services..."
# Try 'docker compose' (V2) first, then fallback to 'docker-compose' (V1)
if docker compose version &> /dev/null; then
    docker compose up --build
else
    docker-compose up --build
fi
