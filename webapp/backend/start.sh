#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Nellia Prospector Backend..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
timeout=60
counter=0

while ! node -e "
const { Client } = require('pg');
const client = new Client({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USERNAME || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_DATABASE || 'nellia_prospector'
});
client.connect()
  .then(() => {
    console.log('Database connection successful');
    client.end();
    process.exit(0);
  })
  .catch(err => {
    console.log('Database connection failed:', err.message);
    process.exit(1);
  });
" 2>/dev/null; do
  counter=$((counter + 1))
  if [ $counter -gt $timeout ]; then
    echo "❌ Database connection timeout after ${timeout} seconds"
    exit 1
  fi
  echo "⏳ Waiting for database... (${counter}/${timeout})"
  sleep 1
done

echo "✅ Database connection established"

# Run migrations
echo "🔄 Running database migrations..."
npm run migration:run

if [ $? -eq 0 ]; then
  echo "✅ Migrations completed successfully"
else
  echo "❌ Migration failed"
  exit 1
fi

# Start the application
echo "🚀 Starting the application..."
exec node dist/main.js
