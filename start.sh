#!/bin/bash

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

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating one from .env.example..."
    cp .env.example .env
    echo "✅ .env file created."
    echo "⚠️  IMPORTANT: Please open the .env file and add your GOOGLE_API_KEY before continuing."
    echo "   (You can edit it in VS Code)"
    read -p "Press Enter once you have added your API Key..."
fi

# Run Docker Compose
echo "🏗️  Building and starting services..."
# Try 'docker compose' (V2) first, then fallback to 'docker-compose' (V1)
if docker compose version &> /dev/null; then
    docker compose up --build
else
    docker-compose up --build
fi
