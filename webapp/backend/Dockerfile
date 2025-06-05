# Multi-stage Dockerfile for Nellia Prospector Backend
FROM node:22-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    curl \
    dumb-init

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# ===================================
# Development Stage
# ===================================
FROM base AS development

# Install all dependencies (including dev dependencies)
RUN npm ci

# Copy source code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 3001

# Development command with hot reload
CMD ["npm", "run", "start:dev"]

# ===================================
# Build Stage
# ===================================
FROM base AS build

# Install all dependencies for building
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# ===================================
# Production Stage
# ===================================
FROM node:22-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init curl

# Create app directory
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nestjs -u 1001

# Copy package files and install production dependencies
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy built application from build stage
COPY --from=build --chown=nestjs:nodejs /app/dist ./dist

# Create uploads directory
RUN mkdir -p uploads && chown nestjs:nodejs uploads

# Switch to non-root user
USER nestjs

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3001/api/v1/health || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "dist/main.js"]
