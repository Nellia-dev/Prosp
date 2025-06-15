# Prospect Button Cooldown Implementation

## Overview
This implementation adds a 24-hour cooldown feature for prospect button activation after pipeline completion for free, starter, and pro plans, while keeping enterprise users enabled without restrictions.

## Backend Changes

### 1. Database Schema Updates
- **Migration**: `1749268814245-AddProspectingCooldown.ts`
  - Added `lastProspectCompletedAt` timestamp field to users table
  - Added `prospectCooldownUntil` timestamp field to users table
  - Created index for performance optimization

### 2. User Entity Updates
- **File**: `webapp/backend/src/database/entities/user.entity.ts`
  - Added cooldown tracking fields to User entity
  - Fields are nullable to support existing users

### 3. Users Service Enhancements
- **File**: `webapp/backend/src/modules/users/users.service.ts`
  - Enhanced `clearProspectingJob()` to set 24-hour cooldown for non-enterprise users
  - Added `isInProspectCooldown()` method to check cooldown status
  - Added `getRemainingCooldownTime()` method to get remaining cooldown duration
  - Added `clearProspectCooldown()` method for admin/testing purposes

### 4. Quota Service Integration
- **File**: `webapp/backend/src/modules/quota/quota.service.ts`
  - Added `canStartProspectingWithCooldown()` method for comprehensive validation
  - Integrates quota and cooldown checks in single method
  - Returns detailed status information including cooldown details

### 5. Prospect Service Updates
- **File**: `webapp/backend/src/modules/prospect/prospect.service.ts`
  - Integrated cooldown checks in `startProspectingProcess()`
  - Provides clear error messages for cooldown violations
  - Mentions enterprise exemption in error messages

### 6. API Endpoint
- **File**: `webapp/backend/src/modules/users/users.controller.ts`
  - New `GET /users/plan-status` endpoint
  - Returns comprehensive user plan status including cooldown information
  - Secured with JWT authentication

### 7. Type Definitions
- **File**: `webapp/backend/src/shared/types/nellia.types.ts`
  - Added `UserPlanStatusResponse` interface with cooldown fields
  - Supports both active and inactive cooldown states

### 8. Enhanced Data Validation
- **File**: `webapp/backend/src/modules/queue/queue.service.ts`
  - Improved `handleLeadEnrichmentEnd()` to extract and save all enrichment data
  - Supports multiple package structures (enhanced vs hybrid)
  - Preserves AI intelligence data, scores, persona info, pain points, etc.
  - Comprehensive data extraction from pipeline orchestrators

## Frontend Changes

### 1. API Service Updates
- **File**: `webapp/frontend/src/services/api.ts`
  - Updated `userApi.getPlanStatus()` to use correct endpoint
  - Added cooldown field support in fallback responses

### 2. Type Definitions
- **File**: `webapp/frontend/src/types/api.ts`
  - Updated `UserPlanStatusResponse` interface to include cooldown information
  - Supports optional cooldown fields for backward compatibility

### 3. Hook Enhancements
- **File**: `webapp/frontend/src/hooks/api/useUnifiedApi.ts`
  - Enhanced `usePlanInfo()` hook to handle cooldown state
  - Added cooldown-related computed properties
  - Updated `canStartProspecting` logic to consider cooldown

### 4. UI Components
- **File**: `webapp/frontend/src/components/ProspectDashboard.tsx`
  - Updated button state logic to handle cooldown
  - Added cooldown-specific button colors (orange for cooldown)
  - Enhanced button text to show remaining cooldown hours
  - Added tooltip with cooldown reason
  - Disabled prospecting during cooldown period

## Plan-Based Behavior

### Free Plan (10 leads/week)
- ✅ 24-hour cooldown after pipeline completion
- ✅ Button disabled with "Cooldown Active (Xh remaining)" message
- ✅ Orange button color during cooldown

### Starter Plan (75 leads/day)
- ✅ 24-hour cooldown after pipeline completion
- ✅ Button disabled with cooldown message
- ✅ Orange button color during cooldown

### Pro Plan (500 leads/day)
- ✅ 24-hour cooldown after pipeline completion
- ✅ Button disabled with cooldown message
- ✅ Orange button color during cooldown

### Enterprise Plan (Unlimited)
- ✅ No cooldown restrictions
- ✅ Can start prospecting immediately after completion
- ✅ Normal button behavior (green when available)

## Data Preservation

### Enhanced Lead Data Extraction
The queue service now comprehensively extracts and saves:

1. **Qualification Data**
   - `qualification_tier`
   - `relevance_score`
   - `roi_potential_score`
   - `brazilian_market_fit`

2. **Company Analysis**
   - `company_sector`
   - `persona` information (role, decision maker probability)
   - `pain_point_analysis`
   - `purchase_triggers`

3. **AI Intelligence**
   - Market fit scores
   - Decision maker likelihood
   - Lead quality scores
   - Recommended approaches

4. **Full Package Preservation**
   - Complete `enrichment_data` with all pipeline outputs
   - Support for both enhanced and hybrid pipeline structures

## Error Handling

### Cooldown Violations
- Clear error messages indicating remaining cooldown time
- Mentions enterprise exemption for plan upgrades
- Proper HTTP status codes (403 Forbidden)

### Data Validation
- Graceful handling of missing or malformed enrichment data
- Fallback extraction strategies for different package structures
- Logging for debugging data extraction issues

## Security Considerations

### Authentication
- All cooldown endpoints require JWT authentication
- User-specific cooldown data isolated by user ID
- No ability to view other users' cooldown status

### Plan Verification
- Cooldown rules enforced server-side
- Plan verification on every prospecting request
- No client-side bypassing possible

## Testing Recommendations

### Backend Testing
1. Test cooldown setting after pipeline completion
2. Verify enterprise users are exempt
3. Test cooldown expiration logic
4. Validate comprehensive data extraction

### Frontend Testing
1. Verify button states during cooldown
2. Test cooldown countdown display
3. Validate enterprise vs. other plan behavior
4. Test UI responsiveness to cooldown changes

### Integration Testing
1. End-to-end pipeline completion to cooldown activation
2. Real-time UI updates via WebSocket
3. Plan upgrade scenarios
4. Data persistence across sessions

## Performance Considerations

### Database Optimizations
- Index on `prospectCooldownUntil` for efficient cooldown queries
- Minimal additional queries for cooldown checks
- Efficient user plan lookup

### Frontend Optimizations
- Cached plan status with appropriate stale times
- Real-time updates only when necessary
- Efficient button state computations

## Deployment Notes

### Migration Requirements
- Run migration `1749268814245-AddProspectingCooldown.ts`
- Existing users will have null cooldown values (no restrictions)
- No data loss or breaking changes

### Configuration
- No additional environment variables required
- Cooldown duration hardcoded to 24 hours (can be made configurable later)
- Enterprise plan ID is 'enterprise' (as per existing config)

This implementation provides a comprehensive solution for prospect button cooldowns while maintaining full data integrity and excellent user experience across all plan types.