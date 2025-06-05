# Database Migration Fix for Dockerized Environment

## Problem
The backend service in the dockerized environment was failing with the error:
```
ERROR: relation "users" does not exist at character 386
```

This occurred because the database migrations were not being run automatically when the Docker container started, resulting in an empty database without the required tables.

## Root Cause Analysis
1. **Direct Application Start**: The Dockerfile was starting the application directly with `node dist/main.js` without running migrations first.
2. **Missing Migration Step**: No mechanism existed to ensure database schema was initialized before the application attempted to connect.
3. **Race Condition**: The application was trying to query tables that didn't exist because migrations hadn't been executed.

## Solution Implemented

### 1. Created Startup Script (`webapp/backend/start.sh`)
A comprehensive startup script that:
- Waits for database connectivity (with timeout protection)
- Runs TypeORM migrations before starting the application
- Provides clear logging for debugging
- Fails fast if migrations fail

Key features:
```bash
# Database connectivity check with timeout
while ! node -e "..." ; do
  # Wait logic with counter
done

# Run migrations
npm run migration:run

# Start application only after successful migration
exec node dist/main.js
```

### 2. Updated Dockerfile (`webapp/backend/Dockerfile`)
Modified the production stage to:
- Install bash for script execution
- Include all dependencies (including dev dependencies for TypeORM CLI)
- Copy source files and TypeScript configuration (required for migrations)
- Use the startup script instead of direct application start

Key changes:
```dockerfile
# Install bash
RUN apk add --no-cache dumb-init curl bash

# Include dev dependencies for TypeORM CLI
RUN npm ci && npm cache clean --force

# Copy source files needed for migrations
COPY --from=build --chown=nestjs:nodejs /app/src ./src
COPY --from=build --chown=nestjs:nodejs /app/tsconfig.json ./tsconfig.json

# Use startup script
CMD ["./start.sh"]
```

### 3. Migration Configuration
The existing migration configuration in `database.config.ts` was already properly set up with:
- Correct migration file paths
- Proper entity registration
- Environment-based configuration

### 4. Available Migrations
Two migrations are already defined:
- `1699000000000-InitialMigration.ts`: Creates all core tables including users, agents, leads, etc.
- `1699000000001-SeedAgents.ts`: Seeds initial agent data

## Files Modified

1. **`webapp/backend/start.sh`** (NEW)
   - Startup script with database wait logic and migration execution

2. **`webapp/backend/Dockerfile`**
   - Added bash installation
   - Modified dependencies to include dev packages
   - Added source file copying for TypeORM CLI
   - Changed CMD to use startup script

3. **`webapp/backend/src/modules/metrics/metrics.service.ts`**
   - Fixed column name mismatch: `roi_potential` → `roi_potential_score`
   - Updated all query builders to use correct column names

4. **`test-migration-fix.sh`** (NEW)
   - Comprehensive test script to verify the fix works

## Testing

The fix includes a test script that:
1. Stops existing containers
2. Cleans up old volumes
3. Builds the backend image
4. Starts PostgreSQL and waits for readiness
5. Starts the backend and waits for readiness
6. Verifies that the users table exists
7. Cleans up after testing

Run the test with:
```bash
./test-migration-fix.sh
```

## Benefits

1. **Automatic Schema Management**: Database schema is automatically created on first run
2. **Idempotent Operations**: Migrations are safe to run multiple times
3. **Proper Error Handling**: Clear error messages if migrations fail
4. **Production Ready**: Works in both development and production environments
5. **Debugging Support**: Comprehensive logging for troubleshooting

## Future Considerations

1. **Migration Rollback**: Consider adding rollback capabilities for production deployments
2. **Health Checks**: The startup script could be enhanced to perform additional health checks
3. **Backup Strategy**: Implement backup procedures before running migrations in production
4. **Zero-Downtime Deployments**: For high-availability scenarios, consider blue-green deployment strategies

## Usage

After applying this fix:

1. **Development**: `docker-compose up` will automatically run migrations
2. **Production**: Same behavior - migrations run before application start
3. **Manual Migration**: Use `npm run migration:run` inside the container if needed
4. **Migration Status**: Use `npm run migration:show` to check migration status

The fix ensures that your dockerized backend will always have the correct database schema, eliminating the "relation does not exist" errors.
