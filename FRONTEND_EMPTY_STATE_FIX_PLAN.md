# Frontend Empty State Fix & Asynchronous Prospect Process Implementation Plan

## Current Issues Identified

### 1. Frontend Query Failures
- **Issue**: Frontend expects leads and agents to not be empty but queries return `undefined`
- **Affected queries**: `["agents","list"]` and `["metrics","dashboard"]`
- **Root cause**: Backend services might be returning `undefined` instead of empty arrays/objects
- **Impact**: Users cannot login to dashboard when no data exists

### 2. Missing Graceful Empty State Handling
- **Issue**: Dashboard components crash when no leads/agents exist
- **Current behavior**: Application fails to load
- **Expected behavior**: Dashboard should show onboarding/setup flow

### 3. Missing Asynchronous Prospect Process Integration
- **Issue**: No integration between webapp and prospect harvester
- **Current state**: Prospect process runs independently
- **Needed**: Async job system to trigger prospect process from dashboard, respecting user quotas.

## Project Architecture Analysis

### Current Structure
```
webapp/
├── backend/ (NestJS)
│   ├── modules/
│   │   ├── agents/ (Agent management)
│   │   ├── leads/ (Lead management)  
│   │   ├── metrics/ (Dashboard metrics)
│   │   ├── business-context/ (User business setup)
│   │   ├── users/ (User management - to be enhanced for plans)
│   │   ├── quota/ (Quota management - new module)
│   │   ├── queue/ (Bull queue for async jobs)
│   │   └── mcp/ (MCP server integration)
│   └── database/entities/
│       ├── user.entity.ts (To be enhanced)
│       └── lead.entity.ts (To be enhanced)
└── frontend/ (React + TanStack Query)
    ├── hooks/api/ (React Query hooks)
    ├── components/ (Dashboard components)
    └── pages/ (Dashboard pages)

prospect/ (Python)
├── harvester.py (Google search & data extraction - to be enhanced for lead limits)
├── agents/ (AI processing agents)
├── mcp-server/ (MCP integration layer - to be enhanced for lead limits)
└── data_models/ (Lead structures)
```
*Note: `LeadEntity` in `webapp/backend/database/entities/` will need a `userId` field and relation to `UserEntity`. `UserEntity` will need fields for plan and quota tracking.*

### Key Components Analysis

#### Frontend Issues
1. **useAgents hook**: Returns `undefined` when no agents exist
2. **useLeads hook**: Returns `undefined` when no leads exist  
3. **useDashboardMetrics hook**: Returns `undefined` when no metrics exist
4. **Index.tsx**: Has mock data fallback but still crashes on API failures

#### Backend Issues
1. **AgentsService.findAll()**: May return empty array but API might not handle it properly
2. **LeadsService.findAll()**: Returns `{data: [], total: 0}` structure but frontend expects array
3. **MetricsService**: No proper fallback for empty metrics

#### Missing Integration
1. **Harvester Integration**: No API endpoint to trigger prospect process that respects user context and quotas.
2. **Queue System**: Exists but not connected to prospect process in a user-aware manner.
3. **Business Context Flow**: Exists but not integrated with prospect triggering.
4. **User Plans & Quotas**: System for managing user subscription plans and lead generation limits is missing.

## User Plans, Quotas, and Lead Ownership (New System)

This new system will manage user subscriptions, define lead generation quotas, and ensure leads are correctly attributed to users.

### A. Database Schema Design

**1. User Entity (`UserEntity` in `webapp/backend/database/entities/user.entity.ts`) Enhancements:**
   - `plan`: `ENUM` (e.g., 'free', 'starter', 'pro', 'enterprise') - Default to 'free'.
   - `currentLeadQuotaUsed`: `INTEGER` - Number of leads generated in the current period. Default 0.
   - `lastQuotaResetAt`: `TIMESTAMP` - When the quota was last reset.
   - `prospectingJobId`: `STRING` (nullable, unique) - ID of the currently active prospecting job for this user (to prevent concurrent jobs).
   - Add `OneToMany` relation to `LeadEntity`.

**2. Lead Entity (`LeadEntity` in `webapp/backend/database/entities/lead.entity.ts`) Enhancements:**
   - `userId`: `UUID` (or appropriate type) - Foreign key referencing `UserEntity.id`.
   - Add a `ManyToOne` relation from `LeadEntity` to `UserEntity`. Mark as non-nullable.

**3. Subscription Plan Configuration (Constants or Separate Table):**
   - Define plan details (id, name, quota amount, quota period - 'day'/'week', price, features).
   - Start with constants in `webapp/backend/src/config/plans.config.ts`.
   ```typescript
   // Example: webapp/backend/src/config/plans.config.ts
   export type PlanId = 'free' | 'starter' | 'pro' | 'enterprise';
   export interface PlanDetails {
     id: PlanId;
     name: string;
     quota: number; // Max leads
     period: 'day' | 'week' | 'month'; // Quota reset period
     price: number | null; // Price in smallest currency unit (e.g., cents) or null for custom
   }
   export const PLANS: Record<PlanId, PlanDetails> = {
     free: { id: 'free', name: 'Free', quota: 10, period: 'week', price: 0 },
     starter: { id: 'starter', name: 'Starter', quota: 75, period: 'day', price: 4900 },
     pro: { id: 'pro', name: 'PRO', quota: 500, period: 'day', price: 19900 },
     enterprise: { id: 'enterprise', name: 'Enterprise', quota: Infinity, period: 'month', price: null },
   };
   ```

### B. Backend Logic & Services

**1. User Service (`UserService` in `webapp/backend/src/modules/users/users.service.ts` - may need creation or enhancement):**
   - `updateUserPlan(userId: string, newPlanId: PlanId)`: Updates user's plan.
   - `getUserById(userId: string)`: Retrieves user details including plan.
   - `recordProspectingJobStart(userId: string, jobId: string)`: Sets `prospectingJobId` on user.
   - `clearProspectingJob(userId: string)`: Clears `prospectingJobId` on user.

**2. Quota Management Service (`QuotaService` in `webapp/backend/src/modules/quota/quota.service.ts` - new module):**
   - Dependencies: `UserService`, `ConfigService` (for `PLANS`).
   - `getPlanDetails(planId: PlanId): PlanDetails`.
   - `resetQuotaIfApplicable(user: UserEntity)`: Checks `lastQuotaResetAt` against current time and plan period. If reset is due, sets `currentLeadQuotaUsed` to 0 and updates `lastQuotaResetAt`. Saves user.
   - `getRemainingQuota(userId: string)`:
     - Fetches user, calls `resetQuotaIfApplicable`.
     - Gets plan details for `user.plan`.
     - Returns `plan.quota - user.currentLeadQuotaUsed`. For `Infinity` quota, returns a very large number or a special indicator.
   - `consumeQuota(userId: string, leadsGenerated: number)`: Fetches user, calls `resetQuotaIfApplicable`, then increments `currentLeadQuotaUsed`. Saves user.
   - `canStartProspecting(userId: string)`: Calls `getRemainingQuota`. Returns true if > 0.
   - `getMaxLeadsToRequest(userId: string)`: Returns `getRemainingQuota(userId)`, capped at a reasonable batch size (e.g., 50-100) to avoid overly large single requests to MCP, even if quota is very high. This is the value to pass to MCP.

**3. Authentication & Authorization:**
   - Ensure all prospect-related endpoints are authenticated.
   - `userId` should be reliably obtained from the authenticated user session/token (e.g., `req.user.id` from a JWT guard).

### C. API Endpoints

**1. User Plan Status Endpoint (e.g., in `UserController` or a new `SubscriptionController`):**
   - `GET /api/users/me/plan-status` or `/api/subscription/status`:
     - Uses `QuotaService` to return current plan details, total quota for period, quota used, quota remaining, and next (approximate) reset date.

## Comprehensive Fix Plan

### Phase 1: Fix Empty State Handling (Immediate)
(No changes to this phase based on new requirements)

... (Content of Phase 1.1, 1.2, 1.3 remains the same) ...

### Phase 2: Business Context & Onboarding Flow
(No changes to this phase based on new requirements, but Business Context might become user-specific later)

... (Content of Phase 2.1, 2.2 remains the same) ...

### Phase 3: Asynchronous Prospect Process Integration (Enhanced for Quotas & User Ownership)

#### 3.1 Prospect Process API Endpoints (User-Aware)

**Update `StartProspectingDto` (e.g., in `prospect.service.ts` or shared types):**
```typescript
// webapp/backend/src/modules/prospect/prospect.service.ts or shared DTO
export class StartProspectingDto {
  // userId will be extracted from authenticated request, not part of DTO from client
  searchQuery: string;
  maxSites?: number; // Max sites for harvester to crawl
}
```

**Update `HarvesterJobData` (job payload for BullMQ):**
```typescript
// webapp/backend/src/modules/prospect/prospect.service.ts
export interface HarvesterJobData {
  userId: string; // ID of the user who initiated the job
  searchQuery: string;
  maxSites: number;
  maxLeadsToReturn: number; // Calculated based on user's remaining quota
  businessContextId?: string; // If business context becomes user-specific
  timestamp: string;
}
```

**Prospect Controller (`prospect.controller.ts`) Updates:**
- Inject `QuotaService`.
- `startProspecting(@Req() request, @Body() dto: StartProspectingDto)`:
  - Extract `userId` from `request.user.id` (assuming JWT auth).
  - Call `prospectService.startProspectingProcess(userId, dto)`.

**Prospect Service (`prospect.service.ts`) Updates:**
- Inject `UserService` and `QuotaService`.
- `async startProspectingProcess(userId: string, dto: StartProspectingDto): Promise<Job>`:
  - **Step 1: Validate Business Context:** (As before, potentially user-specific if `businessContextId` is used).
    ```typescript
    const context = await this.businessContextService.getContextForMcp(/* pass user-specific contextId if applicable */);
    if (!context) throw new BadRequestException('Business context not set up or found.');
    // Or use isReadyForProspecting if it's adapted for user-specific contexts
    ```
  - **Step 2: Check User Quota & Concurrent Jobs:**
    ```typescript
    const user = await this.userService.getUserById(userId);
    if (user.prospectingJobId) { // Check if a job is already running for this user
        const existingJob = await this.prospectQueue.getJob(user.prospectingJobId);
        if (existingJob && ['active', 'waiting', 'delayed'].includes(await existingJob.getState())) {
            throw new ConflictException('A prospecting job is already running for your account.');
        } else {
            await this.userService.clearProspectingJob(userId); // Clear stale job ID
        }
    }

    const maxLeadsUserCanRequest = await this.quotaService.getMaxLeadsToRequest(userId);
    if (maxLeadsUserCanRequest <= 0) {
      throw new ForbiddenException('Lead generation quota exceeded or no quota remaining for this request.');
    }
    ```
  - **Step 3: Prepare Job Data:**
    ```typescript
    const jobData: HarvesterJobData = {
      userId: userId,
      searchQuery: dto.searchQuery,
      maxSites: dto.maxSites || 10, // Default or user input
      maxLeadsToReturn: maxLeadsUserCanRequest, // Key: limit for MCP
      // businessContextId: context.id, // If context is specific
      timestamp: new Date().toISOString(),
    };
    ```
  - **Step 4: Add Job to Queue & Record Job ID on User:**
    ```typescript
    const job = await this.prospectQueue.add('run-harvester', jobData, { /* ...options... */ });
    await this.userService.recordProspectingJobStart(userId, job.id.toString()); // Store active job ID
    return job;
    ```
- `getJobStatus(jobId: string, userId: string)`: Ensure job belongs to the user.
- `getRecentJobs(userId: string)`: Fetch jobs only for the authenticated user.

#### 3.2 Queue Processor for Prospect Jobs (User & Quota Aware)

**Prospect Queue Processor (`prospect.processor.ts`) Updates:**
- Inject `QuotaService` and `UserService`.
- `async handleHarvesterProcess(job: Job<HarvesterJobData>)`:
  - Extract `userId`, `searchQuery`, `maxSites`, `maxLeadsToReturn`, `businessContextId` from `job.data`.
  - **Fetch Business Context:** (As before, potentially user-specific).
  - **Execute Harvester:**
    ```typescript
    // Pass maxLeadsToReturn to executeHarvester, which passes it to McpService.runHarvester
    const harvesterResults = await this.executeHarvester({
      query: enhancedQuery,
      maxSites: maxSites,
      context: context,
      maxLeadsToReturn: maxLeadsToReturn, // IMPORTANT
      userId: userId // Pass for logging or if MCP needs it
    });
    ```
  - **Process Harvester Results:**
    ```typescript
    // processHarvesterResults should also be mindful of not exceeding maxLeadsToReturn
    // although McpService.processRawDataToLead should ideally handle this per item if MCP returns more than requested.
    const processedLeadDtos = await this.processHarvesterResults(harvesterResults, context, userId, maxLeadsToReturn);
    ```
  - **Save Leads to Database:**
    ```typescript
    // Ensure leads are saved with the correct userId.
    // The CreateLeadDto should now include userId.
    const savedLeads = await this.saveLeadsToDatabase(processedLeadDtosWithUserId, userId);
    ```
  - **Update User Quota:**
    ```typescript
    if (savedLeads.length > 0) {
      await this.quotaService.consumeQuota(userId, savedLeads.length);
    }
    ```
  - **Clear Prospecting Job ID on User (in `finally` block or on success/failure):**
    ```typescript
    // In a finally block or after job completion/failure logic
    await this.userService.clearProspectingJob(userId);
    ```
  - Return object should include `userId`.

**Update `executeHarvester` method in `ProspectProcessor`:**
- It should accept `maxLeadsToReturn` and `userId` and pass them to `this.mcpService.runHarvester` and `this.executeHarvesterDirect`.

**Update `executeHarvesterDirect` method in `ProspectProcessor`:**
- Add `--max-leads` and `--user-id` arguments when spawning `harvester.py`.

**Update `processHarvesterResults` method in `ProspectProcessor`:**
- Accept `userId` and `maxLeadsToReturn`.
- Ensure `CreateLeadDto` instances are populated with `userId`.
- Stop processing more results than `maxLeadsToReturn`.

**Update `saveLeadsToDatabase` method in `ProspectProcessor`:**
- Accept `userId`. Ensure `LeadsService.create` handles `userId` (either via DTO or separate param).

#### 3.2.1 MCP Server Enhancements (Python `prospect` project)

**1. `prospect/harvester.py` Modifications:**
   - Add command-line arguments:
     - `--max-leads N`: The maximum number of *processed/qualified* leads the harvester (or its subsequent MCP agent chain) should aim to return.
     - `--user-id USER_ID`: (Optional but recommended) The ID of the user initiating the request, for logging, or if MCP agents need user-specific context.
   - The harvester script itself might still find many raw URLs/sites, but the processing pipeline (either within harvester or MCP agents called by it) should stop generating final lead objects once `max-leads` is hit.
   - If `harvester.py` directly calls processing agents, it needs to track the count of successfully processed leads and stop early.

**2. `prospect/mcp-server/` (Flask/FastAPI app) Modifications:**
   - **Harvester Endpoint (e.g., `/api/harvester/run` called by `McpService.runHarvester`):**
     - Accept `max_leads_to_return` and `user_id` in the request payload.
     - Pass these parameters to the `harvester.py` script when spawning the child process (as `--max-leads` and `--user-id`).
   - **Raw Data Processing Endpoint (e.g., `/api/mcp/process-raw-to-lead` called by `McpService.processRawDataToLead`):**
     - Accept `user_id` if needed for agent context or logging within MCP.
     - This endpoint is typically called per item. The overall lead limiting logic should primarily reside in the job orchestrator (`ProspectProcessor`) and the initial `runHarvester` call to MCP, which then instructs `harvester.py`.

#### 3.3 Frontend Prospect Integration (User-Aware)

**New Hook: `useUserPlanStatus.ts`**
```typescript
// webapp/frontend/src/hooks/api/useUserPlanStatus.ts
// export const useUserPlanStatus = () => {
//   return useQuery({
//     queryKey: ['user', 'planStatus'],
//     queryFn: () => userApi.getPlanStatus(), // Assumes userApi.getPlanStatus() exists
//   });
// };
```
*(Requires a `userApi.getPlanStatus()` method in `services/api.ts` calling the new backend endpoint)*

**Prospect Dashboard Component (`ProspectDashboard.tsx`) Updates:**
- Use `useUserPlanStatus` to fetch and display current plan, quota usage (e.g., "15/75 leads used this day").
- Disable "Start Prospecting" button if quota is exceeded or `canStartProspecting` is false.
- When starting prospecting, the `userId` is handled by the backend (taken from auth token). The frontend DTO for starting a job does not need `userId`.

... (Content of Phase 4.1 remains largely the same, but WebSocket events for job completion should trigger UI updates for quota display) ...

#### 4.1 WebSocket Integration for Job Updates (User-Specific & Quota Updates)

**Enhanced WebSocket Events (`websocket.gateway.ts`):**
- Emit job progress and completion events specifically to the user who owns the job. This can be done by having the user's client join a user-specific room (e.g., `client.join(\`user-\${userId}\`)`).
  ```typescript
  // Emit job progress updates to specific user room
  async emitJobProgressToUser(userId: string, jobId: string, progress: number, status: string) {
    this.server.to(`user-${userId}`).emit('job-progress', { /* ...payload... */ });
  }

  // Emit job completion to specific user room
  async emitJobCompletedToUser(userId: string, jobId: string, result: any) {
    this.server.to(`user-${userId}`).emit('job-completed', { /* ...payload... */ });
    // Also emit a general 'quota-updated' event or include new quota info in job-completed
    this.server.to(`user-${userId}`).emit('quota-updated', { /* new quota details */ });
  }
  ```
- When a job completes and leads are saved:
  - The `ProspectProcessor` should notify the `WebSocketGateway` (e.g., via an event emitter or direct service call) with the `userId` and the number of leads created.
  - The `WebSocketGateway` then emits an event (e.g., `quota-updated` or include in `job-completed`) to the specific user's client.

**Frontend WebSocket Hook (`useProspectUpdates.ts` or a new `useUserUpdates.ts`):**
- Listen for `quota-updated` events.
- On receiving `quota-updated`, invalidate or update the query for `useUserPlanStatus` to refresh displayed quota information.
  ```typescript
  // In useProspectUpdates.ts or a dedicated user updates hook
  // socket.on('quota-updated', (data) => {
  //   queryClient.invalidateQueries({ queryKey: ['user', 'planStatus'] });
  //   toast.info(`Your lead quota has been updated. ${data.leadsGenerated} new leads!`);
  // });
  ```

... (Content of Phase 5, Timeline, Testing, Risk Mitigation needs review for new features) ...

## Implementation Timeline (Adjusted)

### Week 1-2: Foundations for Plans & Quotas
- [x] **DB Schema:** Update `UserEntity`, `LeadEntity`. Define `PLANS` config.
- [x] **Backend Services:** Implement basic `UserService` (user retrieval, plan update). Implement `QuotaService` (quota calculation, consumption, reset logic).
- [x] **API:** Create `/api/users/me/plan-status` endpoint.
- [x] **Auth:** Ensure `userId` is available in authenticated requests.

### Week 3-4: User-Aware Prospecting Backend
- [x] **DTOs:** Update `StartProspectingDto`, `HarvesterJobData` with `userId`, `maxLeadsToReturn`.
- [x] **ProspectService:** Modify `startProspectingProcess` for quota checks, concurrent job prevention, passing new data to job. Secure other methods by `userId`.
- [x] **ProspectProcessor:**
    - Modify `handleHarvesterProcess` to use `userId`, `maxLeadsToReturn`.
    - Update helper methods (`executeHarvester`, `processHarvesterResults`, `saveLeadsToDatabase`) to handle `userId` and `maxLeadsToReturn`.
    - Integrate `QuotaService.consumeQuota` and `UserService.clearProspectingJob`.
- [x] **McpService:** Update `runHarvester` and `processRawDataToLead` signatures to accept `maxLeadsToReturn` and `userId` if needed by MCP.
- [x] **MCP Server (`prospect/` project):**
    - [x] Update `harvester.py` to accept and use `--max-leads` and `--user-id`.
    - [x] MCP server integration handled via direct Python module calls (no web API endpoints needed).

### Week 5: Frontend Integration for Quotas & User-Aware Prospecting
- [x] **API Service:** Add `userApi.getPlanStatus()` to `services/api.ts`.
- [x] **Hooks:** Create `useUserPlanStatus` hook.
- [x] **ProspectDashboard:**
    - [x] Integrate `useUserPlanStatus` to display plan/quota.
    - [x] Disable/enable prospecting button based on quota.
    - [x] Add PlanStatusCard component with quota visualization.
    - [x] Implement quota-aware button states and messaging.
- [ ] **Testing:** Thoroughly test quota logic, job processing with limits, and lead ownership.

### Week 6: Real-time Quota Updates & Polish
- [x] **WebSocketGateway:** Implement user-specific rooms and `quota-updated` events.
- [x] **ProspectProcessor:** Trigger WebSocket events on job completion/quota consumption.
- [x] **Frontend Hooks:** Update WebSocket hooks to listen for `quota-updated` and refresh plan status.
- [x] UI Polish, error handling improvements related to quotas.

## Testing Strategy (Expanded)

### Unit Tests
- `QuotaService`: Test quota calculation, reset logic, consumption for all plans.
- `ProspectService`: Test quota checks, concurrent job prevention.
- `ProspectProcessor`: Test handling of `maxLeadsToReturn`, `userId` propagation, quota consumption calls.
- `McpService`: Mock MCP server responses for `runHarvester` with limits.

### Integration Tests
- Full prospect process flow for different user plans, verifying lead limits and quota updates.
- API endpoint for plan status.
- WebSocket real-time updates for job status and quota changes.

### User Acceptance Tests
- User onboarding and seeing initial (e.g., free) plan quota.
- Starting prospecting and observing quota decrement.
- Hitting quota limit and being unable to start new prospecting until reset.
- (If plan upgrades are implemented) Upgrading plan and seeing quota increase.

## Risk Mitigation (Expanded)

### Quota System Reliability
- **Atomicity:** Ensure quota consumption and lead saving are atomic or handled with eventual consistency carefully. Database transactions for user quota updates and lead creation where possible.
- **Race Conditions:** Consider potential race conditions if a user could somehow trigger multiple prospecting requests simultaneously before `prospectingJobId` is set (though backend checks should prevent this).
- **Time Zones:** Ensure quota reset logic (daily/weekly) correctly handles time zones, ideally using UTC for all server-side calculations and date storage.

This comprehensive plan addresses all identified issues and provides a robust foundation for the asynchronous prospect process while ensuring users can always access their dashboard regardless of data availability.
