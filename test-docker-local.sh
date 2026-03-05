#!/bin/bash
set -e

# ============================================================================
# Local Docker Testing Script
# ============================================================================
# This script builds and runs your Docker container locally to test
# before deploying to Google Cloud Run.
# ============================================================================

echo "======================================"
echo "Local Docker Testing"
echo "======================================"

# Configuration
IMAGE_NAME="adai-fastapi-local"
CONTAINER_NAME="adai-fastapi-test"
PORT=8080

# Step 1: Build Docker image
echo ""
echo "Step 1: Building Docker image..."
docker build -t ${IMAGE_NAME}:latest .

# Step 2: Stop and remove existing container if running
echo ""
echo "Step 2: Cleaning up existing container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Step 3: Run container
echo ""
echo "Step 3: Starting container..."
echo ""
echo "IMPORTANT: The container will use environment variables from your .env file"
echo "Make sure your .env file contains all required variables."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Create a .env file with your configuration before running."
    exit 1
fi

# Run container with .env file
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:8080 \
    --env-file .env \
    ${IMAGE_NAME}:latest

echo ""
echo "======================================"
echo "✅ Container started successfully!"
echo "======================================"
echo ""
echo "Container is running at: http://localhost:${PORT}"
echo ""
echo "Test endpoints:"
echo "  curl http://localhost:${PORT}/health"
echo "  curl http://localhost:${PORT}/"
echo ""
echo "View container logs:"
echo "  docker logs -f ${CONTAINER_NAME}"
echo ""
echo "Stop container:"
echo "  docker stop ${CONTAINER_NAME}"
echo ""
echo "Remove container:"
echo "  docker rm ${CONTAINER_NAME}"
echo ""
echo "======================================"

# Follow logs
echo "Following container logs (Press Ctrl+C to exit)..."
echo ""
docker logs -f ${CONTAINER_NAME}
