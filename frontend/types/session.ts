/**
 * TypeScript type definitions for Oxytec Feasibility Platform
 *
 * These types ensure type safety across the frontend and match the backend API responses.
 */

/**
 * Session status enum
 */
export type SessionStatus = "pending" | "processing" | "completed" | "failed";

/**
 * Individual subagent result from parallel execution
 */
export interface SubagentResult {
  agent_name: string;
  instance: string;
  task: string;
  result: string;
  duration_seconds?: number;
  tokens_used?: number;
}

/**
 * Risk item structure from risk assessor
 */
export interface RiskItem {
  category: string;
  description: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  mitigation?: string;
}

/**
 * Risk classification structure
 */
export interface RiskClassification {
  technical_risks: RiskItem[];
  commercial_risks: RiskItem[];
  data_quality_risks: RiskItem[];
}

/**
 * Risk assessment output
 */
export interface RiskAssessment {
  executive_risk_summary: string;
  risk_classification: RiskClassification;
  overall_risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  go_no_go_recommendation: "GO" | "CONDITIONAL_GO" | "NO_GO";
  critical_success_factors: string[];
  mitigation_priorities: string[];
}

/**
 * Complete session result including all agent outputs
 */
export interface SessionResult {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  user_metadata?: {
    company?: string;
    contact?: string;
    requirements?: string;
  };
  final_report?: string;
  subagent_results?: SubagentResult[];
  risk_assessment?: RiskAssessment;
  error?: string;
  errors?: string[];
  warnings?: string[];
}

/**
 * Server-Sent Events event types
 */
export type SSEEventType = "status" | "final" | "error";

/**
 * SSE event structure
 */
export interface SSEEvent {
  type: SSEEventType;
  status?: SessionStatus;
  updated_at?: string;
  result?: SessionResult;
  error?: string;
}

/**
 * Session status response (lightweight)
 */
export interface SessionStatusResponse {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  stream_url: string;
}

/**
 * Document metadata
 */
export interface DocumentMetadata {
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
}

/**
 * Session debug information
 */
export interface SessionDebugInfo {
  session_id: string;
  status: SessionStatus;
  documents: DocumentMetadata[];
  logs: SessionLog[];
  agent_outputs: AgentOutput[];
  errors?: string[];
}

/**
 * Session log entry
 */
export interface SessionLog {
  id: string;
  session_id: string;
  log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
}

/**
 * Agent output entry
 */
export interface AgentOutput {
  id: string;
  session_id: string;
  agent_type: string;
  agent_instance: string;
  output: Record<string, unknown>;
  token_usage?: number;
  duration_seconds?: number;
  created_at: string;
}

/**
 * File upload response
 */
export interface FileUploadResponse {
  session_id: string;
  status: SessionStatus;
  stream_url: string;
  message: string;
}

/**
 * Error response
 */
export interface ErrorResponse {
  detail: string;
  error_id?: string;
}

/**
 * Feasibility rating extracted from report
 */
export type FeasibilityRating = "high" | "medium" | "low" | "unknown";

/**
 * Props interfaces for components
 */
export interface FileUploadProps {
  files: File[];
  setFiles: (files: File[]) => void;
}

export interface ResultsViewerProps {
  result: SessionResult;
  sessionId?: string;
}

export interface AgentVisualizationProps {
  sessionId: string;
  status: SessionStatus;
}

/**
 * Type guard to check if a result has completed successfully
 */
export function isCompletedSession(result: SessionResult): boolean {
  return result.status === "completed" && !!result.final_report;
}

/**
 * Type guard to check if a result has failed
 */
export function isFailedSession(result: SessionResult): boolean {
  return result.status === "failed" || !!result.error;
}

/**
 * Extract feasibility rating from report text
 */
export function extractFeasibilityRating(report: string): FeasibilityRating {
  if (report.includes("🟢") || report.includes("GUT GEEIGNET")) {
    return "high";
  } else if (report.includes("🟡") || report.includes("MACHBAR")) {
    return "medium";
  } else if (report.includes("🔴") || report.includes("SCHWIERIG")) {
    return "low";
  }
  return "unknown";
}
