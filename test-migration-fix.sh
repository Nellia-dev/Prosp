#!/bin/bash

set -e

echo "🧪 Testing migration fix..."

# Stop any running containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove any existing volumes to start fresh
echo "🗑️  Removing old volumes..."
docker volume rm $(docker volume ls -q | grep nellia) 2>/dev/null || true

# Build the backend image
echo "🔨 Building backend image..."
docker-compose build backend

# Start PostgreSQL first and wait for it to be ready
echo "🐘 Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
while ! docker-compose exec postgres pg_isready -U postgres >/dev/null 2>&1; do
  counter=$((counter + 1))
  if [ $counter -gt $timeout ]; then
    echo "❌ PostgreSQL readiness timeout"
    exit 1
  fi
  echo "Waiting for PostgreSQL... (${counter}/${timeout})"
  sleep 1
done

echo "✅ PostgreSQL is ready"

# Start the backend
echo "🚀 Starting backend..."
docker-compose up -d backend

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
timeout=120
counter=0
while ! curl -f http://localhost:3001/api/v1/health >/dev/null 2>&1; do
  counter=$((counter + 1))
  if [ $counter -gt $timeout ]; then
    echo "❌ Backend readiness timeout"
    echo "📋 Backend logs:"
    docker-compose logs backend
    exit 1
  fi
  echo "Waiting for backend... (${counter}/${timeout})"
  sleep 2
done

echo "✅ Backend is ready"

# Check if tables exist
echo "🔍 Checking if users table exists..."
if docker-compose exec postgres psql -U postgres -d nellia_prospector -c "\dt users" | grep -q "users"; then
  echo "✅ Users table exists! Migration successful!"
else
  echo "❌ Users table does not exist! Migration failed!"
  echo "📋 Backend logs:"
  docker-compose logs backend
  exit 1
fi

echo "🎉 Test passed! Migration fix is working correctly."
echo "🧹 Cleaning up..."
docker-compose down
