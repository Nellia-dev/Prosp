# Multi-stage Dockerfile for Nellia Prospector Frontend
FROM node:22-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    curl \
    dumb-init

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# ===================================
# Development Stage
# ===================================
FROM base AS development

# Install all dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Development command with hot reload
CMD ["npm", "run", "dev"]

# ===================================
# Build Stage
# ===================================
FROM base AS build

# Install all dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# ===================================
# Production Stage
# ===================================
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built app from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create non-root user
RUN addgroup -g 1001 -S frontend
RUN adduser -S react -u 1001 -G frontend

# Change ownership of nginx directories
RUN chown -R react:frontend /var/cache/nginx /var/run /var/log/nginx /usr/share/nginx/html
RUN chmod -R 755 /var/cache/nginx /var/run /var/log/nginx

# Switch to non-root user
USER react

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]