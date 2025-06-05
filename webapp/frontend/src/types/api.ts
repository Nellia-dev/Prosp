// Base API Response types
export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface ApiError {
  message: string;
  statusCode: number;
  error?: string;
  timestamp: string;
  path: string;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: 'admin' | 'user';
    isActive: boolean;
    lastLogin: string;
  };
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// Agent API types
export interface AgentResponse {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'processing' | 'error';
  currentTask?: string;
  queueDepth: number;
  throughput: number;
  successRate: number;
  processingTime: number;
  llmTokenUsage: number;
  llmTokenLimit: number;
  createdAt: string;
  updatedAt: string;
}

export interface StartAgentRequest {
  agentId: string;
}

export interface StopAgentRequest {
  agentId: string;
}

// Lead API types
export interface LeadFilters {
  search?: string;
  sector?: string;
  qualificationTier?: 'A' | 'B' | 'C';
  processingStage?: string;
  minScore?: number;
  maxScore?: number;
  offset?: number;
  limit?: number;
}

export interface CreateLeadRequest {
  companyName: string;
  website: string;
  sector: string;
  description?: string;
}

export interface UpdateLeadRequest {
  companyName?: string;
  website?: string;
  sector?: string;
  description?: string;
  qualificationTier?: 'A' | 'B' | 'C';
  relevanceScore?: number;
  roiPotential?: number;
  brazilianMarketFit?: number;
  processingStage?: string;
  painPoints?: string[];
  triggers?: string[];
  personaInsights?: Record<string, unknown>;
}

export interface UpdateLeadStageRequest {
  stage: string;
}

export interface LeadResponse {
  id: string;
  companyName: string;
  website: string;
  sector: string;
  description?: string;
  qualificationTier: 'A' | 'B' | 'C';
  relevanceScore: number;
  roiPotential: number;
  brazilianMarketFit: number;
  processingStage: string;
  painPoints: string[];
  triggers: string[];
  personaInsights?: Record<string, unknown>;
  likelyContactRole?: string;
  decisionMakerProbability?: number;
  createdAt: string;
  updatedAt: string;
}

export interface LeadsByStageResponse {
  [stage: string]: LeadResponse[];
}

export interface BulkLeadOperation {
  operation: 'create' | 'update' | 'delete' | 'process';
  leads: (CreateLeadRequest | UpdateLeadRequest)[];
}

// Business Context API types
export interface BusinessContextRequest {
  businessDescription: string;
  targetMarket: string;
  valueProposition: string;
  idealCustomer: string;
  painPointsSolved: string[];
  industryFocus: string[];
}

export interface BusinessContextResponse {
  id: string;
  businessDescription: string;
  targetMarket: string;
  valueProposition: string;
  idealCustomer: string;
  painPointsSolved: string[];
  industryFocus: string[];
  createdAt: string;
  updatedAt: string;
}

// Chat API types
export interface ChatMessageRequest {
  agentId: string;
  message: string;
  attachments?: string[];
}

export interface ChatMessageResponse {
  id: string;
  agentId: string;
  message: string;
  sender: 'user' | 'agent';
  attachments: string[];
  createdAt: string;
}

// Metrics API types
export interface DashboardMetricsResponse {
  totalLeads: number;
  processedLeads: number;
  averageROI: number;
  successRate: number;
  activeAgents: number;
  averageProcessingTime: number;
}

export interface PerformanceMetricsResponse {
  timeRange: string;
  throughputData: Array<{
    timestamp: string;
    value: number;
  }>;
  processingTimeData: Array<{
    timestamp: string;
    value: number;
  }>;
}

export interface AgentPerformanceResponse {
  agentId: string;
  agentName: string;
  successCount: number;
  errorCount: number;
  averageProcessingTime: number;
  throughput: number;
}

export interface LeadStatsResponse {
  stage: string;
  count: number;
  averageROI: number;
  highPotentialCount: number;
}

export interface MetricsSummaryResponse {
  overview: DashboardMetricsResponse;
  performance: PerformanceMetricsResponse;
  agentPerformance: AgentPerformanceResponse[];
  leadStats: LeadStatsResponse[];
}
