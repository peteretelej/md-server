#!/bin/bash
set -e

PORT=${1:-8080}
IMAGE_NAME="md-server"
CONTAINER_NAME="md-server"

echo "Building $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

echo "Stopping existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "Starting $IMAGE_NAME on port $PORT..."
docker run -d --name $CONTAINER_NAME -p $PORT:8080 $IMAGE_NAME

echo "✓ Server running at http://localhost:$PORT"
echo "  View logs: docker logs -f $CONTAINER_NAME"
echo "  Stop: docker stop $CONTAINER_NAME"