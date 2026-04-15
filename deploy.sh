#!/bin/bash
set -e

IMAGE=${1:-"charlie82610/capstone-app:latest"}
BLUE_NAME="capstone-app-blue"
GREEN_NAME="capstone-app-green"
BLUE_PORT=5000
GREEN_PORT=5001

echo "Pulling new image: $IMAGE"
docker pull $IMAGE

echo "Starting GREEN container on port $GREEN_PORT..."
docker run -d \
  --name $GREEN_NAME \
  --restart unless-stopped \
  -p $GREEN_PORT:5000 \
  $IMAGE

echo "Waiting for GREEN to be healthy..."
sleep 10
curl -f http://localhost:$GREEN_PORT/health || {
  echo "GREEN health check failed — rolling back"
  docker stop $GREEN_NAME && docker rm $GREEN_NAME
  exit 1
}

echo "GREEN is healthy. Switching Nginx to GREEN..."
sudo sed -i "s/proxy_pass http:\/\/127.0.0.1:$BLUE_PORT/proxy_pass http:\/\/127.0.0.1:$GREEN_PORT/" \
  /etc/nginx/sites-available/capstone
sudo nginx -t && sudo systemctl reload nginx

echo "Stopping and removing BLUE container..."
docker stop $BLUE_NAME 2>/dev/null || true
docker rm $BLUE_NAME 2>/dev/null || true

echo "Renaming GREEN to BLUE for next deployment..."
docker rename $GREEN_NAME $BLUE_NAME

sudo sed -i "s/proxy_pass http:\/\/127.0.0.1:$GREEN_PORT/proxy_pass http:\/\/127.0.0.1:$BLUE_PORT/" \
  /etc/nginx/sites-available/capstone
sudo systemctl reload nginx

echo "Deployment complete! App is running on port $BLUE_PORT"