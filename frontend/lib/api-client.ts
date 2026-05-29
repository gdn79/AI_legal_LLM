import type {
  AuditEntry,
  CaseCreateInput,
  CaseDetailModel,
  CaseDocument,
  CaseFact,
  CaseSummary,
  Checklist,
  CourtImportJob,
  CourtSubmissionPackage,
  DashboardModel,
  DocumentVersion,
  DraftDocument,
  Employee,
  ExternalCourtCase,
  FnsLookupLog,
  IntegrationApproval,
  IntegrationCredentialsStatus,
  IntegrationRequestLog,
  LoginInput,
  Organization,
  OrganizationSnapshot,
  PilotCaseMetrics,
  PilotFeedback,
  PilotMetricsSummary,
  PilotReport,
  PilotTimelineEvent,
  PostalDispatch,
  PostalProofCheck,
  ProviderConnectionCheck,
  PowerOfAttorney,
  RagCitation,
  RagSource,
  Role,
  SandboxReadiness,
  SettingItem,
  Signatory,
  SignatoryAuthorityCheck,
  SystemStatus,
  UserProfile,
} from "./types";
import {
  mockAuditEntries,
  mockAuthorityChecks,
  mockCaseDetails,
  mockCases,
  mockCourtImportJobs,
  mockEmployees,
  mockExternalCourtCases,
  mockFnsLookupLogs,
  mockIntegrationApprovals,
  mockIntegrationCredentialsStatus,
  mockIntegrationLogs,
  mockOrganizations,
  mockOrganizationSnapshots,
  mockPilotCaseMetrics,
  mockPilotFeedback,
  mockPilotMetricsSummary,
  mockPilotReport,
  mockPilotTimelines,
  mockPostalDispatches,
  mockPostalProofChecks,
  mockPowersOfAttorney,
  mockSettings,
  mockSandboxReadiness,
  mockSignatories,
  mockSystemStatus,
  mockUsers,
} from "./mock-data";

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const USE_MOCK = !API_URL;
const TOKEN_KEY = "legal-claim-ai-token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}

function normalizeCaseId(id: number | string | null | undefined): string | null {
  if (id === null || id === undefined) return null;
  const value = String(id);
  return USE_MOCK && !value.startsWith("case-") ? `case-${value}` : value;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (USE_MOCK) return mockRequest<T>(path, init);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = `API error ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function mockRequest<T>(path: string, init?: RequestInit): Promise<T> {
  if (path === "/auth/login" && init?.method === "POST") {
    const body = JSON.parse(String(init.body ?? "{}")) as LoginInput;
    const matchedRole =
      Object.values(mockUsers).find((item) => item.email.toLowerCase() === body.email.toLowerCase())?.role ??
      body.role ??
      "initiator";
    return { access_token: `mock-${matchedRole}` } as T;
  }
  if (path === "/users/me") {
    const token = getToken()?.replace("mock-", "") as keyof typeof mockUsers;
    return mockUsers[token || "initiator"] as T;
  }
  if (path === "/cases" && (!init || init.method === "GET")) return [...mockCases] as T;
  if (path === "/cases" && init?.method === "POST") {
    const body = JSON.parse(String(init.body ?? "{}")) as CaseCreateInput;
    const created: CaseSummary = {
      id: `case-${Date.now()}`,
      title: body.title,
      plaintiff: body.plaintiff,
      defendant: body.defendant,
      amount: body.amount,
      responsibleLawyer: body.responsibleLawyerId,
      status: "NEW",
      updatedAt: new Date().toISOString(),
    };
    mockCases.unshift(created);
    mockCaseDetails[created.id] = { ...created, description: body.description, documents: [], facts: [], pretension: null, claim: null, checklist: { id: "1", caseId: created.id, status: "open", items: [] }, citations: [] };
    return created as T;
  }
  if (/^\/cases\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[2];
    const item = mockCaseDetails[caseId];
    if (!item) throw new Error("Case not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      title: item.title,
      description: item.description,
      claimant_name: item.plaintiff,
      respondent_name: item.defendant,
      claim_amount: Number(String(item.amount).replace(/[^\d.,-]/g, "").replace(/\s/g, "").replace(",", ".")) || 0,
      status: item.status,
      assigned_lawyer_id: item.responsibleLawyer ? 2 : null,
      created_at: item.updatedAt,
    } as T;
  }
  if (/^\/documents\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[2];
    return (mockCaseDetails[caseId]?.documents ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      case_id: Number(item.caseId.replace(/\D/g, "")),
      filename: item.fileName,
      content_type: item.mimeType,
      sha256: item.sha256,
      extracted_text: item.extractedText,
      is_approved: item.approved,
      created_at: item.createdAt,
    })) as T;
  }
  if (/^\/pretensions\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[2];
    const item = mockCaseDetails[caseId]?.pretension;
    if (!item) throw new Error("Pretension not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: Number(item.caseId.replace(/\D/g, "")),
      content: item.content,
      approved: item.approved,
      updated_at: item.updatedAt,
    } as T;
  }
  if (/^\/claims\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[2];
    const item = mockCaseDetails[caseId]?.claim;
    if (!item) throw new Error("Claim not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: Number(item.caseId.replace(/\D/g, "")),
      content: item.content,
      approved: item.approved,
      updated_at: item.updatedAt,
    } as T;
  }
  if (/^\/checklists\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[2];
    const item = mockCaseDetails[caseId]?.checklist;
    if (!item) throw new Error("Checklist not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: Number(item.caseId.replace(/\D/g, "")),
      status: item.status,
      items: item.items.map((check) => ({
        id: Number(check.id.replace(/\D/g, "")),
        title: check.title,
        is_completed: check.isCompleted,
        notes: check.notes,
      })),
    } as T;
  }
  if (/^\/rag\/citations\/[^/]+$/.test(path) && (!init || init.method === "GET")) {
    const caseId = path.split("/")[3];
    return (mockCaseDetails[caseId]?.citations ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      source_id: Number(item.sourceId.replace(/\D/g, "")),
      case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
      target_type: item.targetType,
      target_id: item.targetId ? Number(item.targetId.replace(/\D/g, "")) : null,
      quote: item.quote,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/documents/") && init?.method === "POST") {
    const caseId = path.split("/")[2];
    const document: CaseDocument = { id: `doc-${Date.now()}`, caseId, fileName: "mock.txt", mimeType: "text/plain", sha256: "mock-sha256", extractedText: "Mock extracted text", approved: false, createdAt: new Date().toISOString(), status: "uploaded" };
    mockCaseDetails[caseId].documents.push(document);
    return document as T;
  }
  if (path === "/dashboard") {
    const token = getToken()?.replace("mock-", "") as keyof typeof mockUsers;
    return { user_role: token || "initiator", total_cases: mockCases.length } as T;
  }
  if (path === "/system/status") {
    return {
      backend: mockSystemStatus.backend,
      database: mockSystemStatus.database,
      storage: mockSystemStatus.storage,
      redis: mockSystemStatus.redis,
      worker: mockSystemStatus.worker,
      vector_db: mockSystemStatus.vectorDb,
      llm: mockSystemStatus.llm,
      fns_provider: mockSystemStatus.fnsProvider,
      fns_mode: mockSystemStatus.fnsMode,
      fns_sandbox_enabled: mockSystemStatus.fnsSandboxEnabled,
      real_fns_enabled: mockSystemStatus.realFnsEnabled,
      russian_post_provider: mockSystemStatus.russianPostProvider,
      russian_post_mode: mockSystemStatus.russianPostMode,
      russian_post_sandbox_enabled: mockSystemStatus.russianPostSandboxEnabled,
      real_post_send_enabled: mockSystemStatus.realPostSendEnabled,
      court_arbitr_provider: mockSystemStatus.courtArbitrProvider,
      court_arbitr_mode: mockSystemStatus.courtArbitrMode,
      court_sandbox_enabled: mockSystemStatus.courtSandboxEnabled,
      real_court_search_enabled: mockSystemStatus.realCourtSearchEnabled,
      public_kad_search_enabled: mockSystemStatus.publicKadSearchEnabled,
      court_submission_enabled: mockSystemStatus.courtSubmissionEnabled,
    } as T;
  }
  if (path === "/integration-readiness/sandbox") {
    return {
      fns: {
        sandbox_flag: mockSandboxReadiness.fns.sandboxFlag,
        credentials_present: mockSandboxReadiness.fns.credentialsPresent,
        test_connection_status: mockSandboxReadiness.fns.testConnectionStatus,
        ready_for_sandbox: mockSandboxReadiness.fns.readyForSandbox,
        blocking_reasons: mockSandboxReadiness.fns.blockingReasons,
        mode: mockSandboxReadiness.fns.mode,
        provider: mockSandboxReadiness.fns.provider,
        approval_status: mockSandboxReadiness.fns.approvalStatus,
        active_approval: mockSandboxReadiness.fns.activeApproval ?? false,
        approval_expires_at: mockSandboxReadiness.fns.approvalExpiresAt ?? null,
      },
      russian_post: {
        sandbox_flag: mockSandboxReadiness.russianPost.sandboxFlag,
        credentials_present: mockSandboxReadiness.russianPost.credentialsPresent,
        test_connection_status: mockSandboxReadiness.russianPost.testConnectionStatus,
        ready_for_sandbox: mockSandboxReadiness.russianPost.readyForSandbox,
        blocking_reasons: mockSandboxReadiness.russianPost.blockingReasons,
        mode: mockSandboxReadiness.russianPost.mode,
        provider: mockSandboxReadiness.russianPost.provider,
        approval_status: mockSandboxReadiness.russianPost.approvalStatus,
        active_approval: mockSandboxReadiness.russianPost.activeApproval ?? false,
        approval_expires_at: mockSandboxReadiness.russianPost.approvalExpiresAt ?? null,
      },
      court: {
        sandbox_flag: mockSandboxReadiness.court.sandboxFlag,
        credentials_present: mockSandboxReadiness.court.credentialsPresent,
        test_connection_status: mockSandboxReadiness.court.testConnectionStatus,
        ready_for_sandbox: mockSandboxReadiness.court.readyForSandbox,
        blocking_reasons: mockSandboxReadiness.court.blockingReasons,
        mode: mockSandboxReadiness.court.mode,
        provider: mockSandboxReadiness.court.provider,
        approval_status: mockSandboxReadiness.court.approvalStatus,
        active_approval: mockSandboxReadiness.court.activeApproval ?? false,
        approval_expires_at: mockSandboxReadiness.court.approvalExpiresAt ?? null,
      },
    } as T;
  }
  if (path === "/integration-readiness/credentials") {
    return {
      fns: {
        sandbox_credentials_present: mockIntegrationCredentialsStatus.fns.sandboxCredentialsPresent,
        production_credentials_present: mockIntegrationCredentialsStatus.fns.productionCredentialsPresent,
      },
      russian_post: {
        sandbox_credentials_present: mockIntegrationCredentialsStatus.russianPost.sandboxCredentialsPresent,
        production_credentials_present: mockIntegrationCredentialsStatus.russianPost.productionCredentialsPresent,
      },
      court_arbitr: {
        sandbox_credentials_present: mockIntegrationCredentialsStatus.courtArbitr.sandboxCredentialsPresent,
        production_credentials_present: mockIntegrationCredentialsStatus.courtArbitr.productionCredentialsPresent,
      },
    } as T;
  }
  if (path === "/integration-approvals/active" && (!init || init.method === "GET")) {
    return mockIntegrationApprovals
      .filter((item) => item.status === "APPROVED" && item.environment === "SANDBOX")
      .map(mapMockApproval) as T;
  }
  if (path.startsWith("/integration-approvals?") && (!init || init.method === "GET")) {
    const url = new URL(`http://mock${path}`);
    const integrationName = url.searchParams.get("integration_name");
    const environment = url.searchParams.get("environment");
    const status = url.searchParams.get("status");
    return mockIntegrationApprovals
      .filter(
        (item) =>
          (!integrationName || item.integrationName === integrationName) &&
          (!environment || item.environment === environment) &&
          (!status || item.status === status),
      )
      .map(mapMockApproval) as T;
  }
  if (path === "/integration-approvals" && (!init || init.method === "GET")) {
    return mockIntegrationApprovals.map(mapMockApproval) as T;
  }
  if (path === "/integration-approvals" && init?.method === "POST") {
    const token = getToken()?.replace("mock-", "") as keyof typeof mockUsers;
    const actor = mockUsers[token || "admin"];
    const body = JSON.parse(String(init.body ?? "{}")) as {
      integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR";
      environment: "SANDBOX" | "PRODUCTION";
      reason: string;
      expires_at?: string | null;
    };
    const created: IntegrationApproval = {
      id: `approval-${Date.now()}`,
      integrationName: body.integration_name,
      environment: body.environment,
      requestedById: actor.id,
      approvedById: null,
      status: body.environment === "PRODUCTION" ? "REJECTED" : "REQUESTED",
      reason: body.reason,
      approvedAt: null,
      expiresAt: body.expires_at ?? null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockIntegrationApprovals.unshift(created);
    return mapMockApproval(created) as T;
  }
  if (/^\/integration-approvals\/\d+$/.test(path) && (!init || init.method === "GET")) {
    const approvalId = path.split("/")[2];
    const item = mockIntegrationApprovals.find((entry) => entry.id === `approval-${approvalId}` || entry.id === approvalId);
    if (!item) throw new Error("Integration approval not found");
    return mapMockApproval(item) as T;
  }
  if (/^\/integration-approvals\/\d+\/(approve|reject|revoke)$/.test(path) && init?.method === "POST") {
    const [, , approvalId, action] = path.split("/");
    const token = getToken()?.replace("mock-", "") as keyof typeof mockUsers;
    const actor = mockUsers[token || "admin"];
    const item = mockIntegrationApprovals.find((entry) => entry.id === `approval-${approvalId}` || entry.id === approvalId);
    if (!item) throw new Error("Integration approval not found");
    const body = JSON.parse(String(init.body ?? "{}")) as { reason?: string };
    item.approvedById = actor.id;
    item.updatedAt = new Date().toISOString();
    if (body.reason) item.reason = body.reason;
    if (action === "approve") {
      item.status = item.environment === "PRODUCTION" ? "REJECTED" : "APPROVED";
      item.approvedAt = item.environment === "PRODUCTION" ? null : item.updatedAt;
    } else if (action === "reject") {
      item.status = "REJECTED";
    } else {
      item.status = "REVOKED";
    }
    return mapMockApproval(item) as T;
  }
  if (path.startsWith("/integration-logs")) {
    const url = new URL(`http://mock${path}`);
    const integrationName = url.searchParams.get("integration_name");
    const operation = url.searchParams.get("operation");
    const status = url.searchParams.get("status");
    return mockIntegrationLogs
      .filter((item) => (!integrationName || item.integrationName === integrationName) && (!operation || item.operation === operation) && (!status || item.status === status))
      .map((item) => ({
        id: Number(item.id.replace(/\D/g, "")),
        integration_name: item.integrationName,
        provider: item.provider,
        mode: item.mode,
        operation: item.operation,
        request_id: item.requestId,
        idempotency_key: item.idempotencyKey,
        status: item.status,
        http_status: item.httpStatus ?? null,
        started_at: item.startedAt,
        finished_at: item.finishedAt ?? null,
        duration_ms: item.durationMs ?? null,
        error_code: item.errorCode,
        error_message: item.errorMessage,
        safe_request_metadata_json: item.safeRequestMetadataJson,
        safe_response_metadata_json: item.safeResponseMetadataJson,
        created_by_id: item.createdById ? Number(item.createdById.replace(/\D/g, "")) : null,
        case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
        organization_id: item.organizationId ? Number(item.organizationId.replace(/\D/g, "")) : null,
        created_at: item.createdAt,
      })) as T;
  }
  if (path.startsWith("/pilot-feedback") && (!init || init.method === "GET") && !/^\/pilot-feedback\/\d+/.test(path)) {
    const url = new URL(`http://mock${path}`);
    const caseId = url.searchParams.get("case_id");
    const feedbackModule = url.searchParams.get("module");
    const severity = url.searchParams.get("severity");
    const status = url.searchParams.get("status");
    return mockPilotFeedback
      .filter(
        (item) =>
          (!caseId || item.caseId === `case-${caseId}` || item.caseId === caseId) &&
          (!feedbackModule || item.module === feedbackModule) &&
          (!severity || item.severity === severity) &&
          (!status || item.status === status),
      )
      .map((item) => ({
        id: Number(item.id.replace(/\D/g, "")),
        case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
        user_id: Number(item.userId.replace(/\D/g, "")),
        role: item.role,
        module: item.module,
        severity: item.severity,
        title: item.title,
        description: item.description,
        expected_behavior: item.expectedBehavior,
        actual_behavior: item.actualBehavior,
        screenshot_document_id: item.screenshotDocumentId ? Number(item.screenshotDocumentId.replace(/\D/g, "")) : null,
        status: item.status,
        created_at: item.createdAt,
        updated_at: item.updatedAt,
      })) as T;
  }
  if (path === "/pilot-feedback" && init?.method === "POST") {
    const token = getToken()?.replace("mock-", "") as keyof typeof mockUsers;
    const actor = mockUsers[token || "lawyer"];
    const body = JSON.parse(String(init.body ?? "{}")) as {
      case_id?: number | null;
      module: string;
      severity: string;
      title: string;
      description?: string;
      expected_behavior?: string;
      actual_behavior?: string;
    };
    const created = {
      id: `feedback-${Date.now()}`,
      caseId: body.case_id ? `case-${body.case_id}` : null,
      userId: actor.id,
      role: actor.role,
      module: body.module,
      severity: body.severity,
      title: body.title,
      description: body.description ?? "",
      expectedBehavior: body.expected_behavior ?? "",
      actualBehavior: body.actual_behavior ?? "",
      screenshotDocumentId: null,
      status: "NEW",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    } satisfies PilotFeedback;
    mockPilotFeedback.unshift(created);
    return {
      id: Number(created.id.replace(/\D/g, "")),
      case_id: created.caseId ? Number(created.caseId.replace(/\D/g, "")) : null,
      user_id: Number(created.userId.replace(/\D/g, "")),
      role: created.role,
      module: created.module,
      severity: created.severity,
      title: created.title,
      description: created.description,
      expected_behavior: created.expectedBehavior,
      actual_behavior: created.actualBehavior,
      screenshot_document_id: null,
      status: created.status,
      created_at: created.createdAt,
      updated_at: created.updatedAt,
    } as T;
  }
  if (/^\/pilot-feedback\/\d+$/.test(path) && (!init || init.method === "GET")) {
    const feedbackId = path.split("/")[2];
    const item = mockPilotFeedback.find((entry) => entry.id === `feedback-${feedbackId}` || entry.id === feedbackId);
    if (!item) throw new Error("Pilot feedback not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
      user_id: Number(item.userId.replace(/\D/g, "")),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expected_behavior: item.expectedBehavior,
      actual_behavior: item.actualBehavior,
      screenshot_document_id: item.screenshotDocumentId ? Number(item.screenshotDocumentId.replace(/\D/g, "")) : null,
      status: item.status,
      created_at: item.createdAt,
      updated_at: item.updatedAt,
    } as T;
  }
  if (/^\/pilot-feedback\/\d+$/.test(path) && init?.method === "PATCH") {
    const feedbackId = path.split("/")[2];
    const item = mockPilotFeedback.find((entry) => entry.id === `feedback-${feedbackId}` || entry.id === feedbackId);
    if (!item) throw new Error("Pilot feedback not found");
    const body = JSON.parse(String(init.body ?? "{}")) as Record<string, string | undefined>;
    if (body.module) item.module = body.module;
    if (body.severity) item.severity = body.severity;
    if (body.title) item.title = body.title;
    if (body.description) item.description = body.description;
    if (body.expected_behavior) item.expectedBehavior = body.expected_behavior;
    if (body.actual_behavior) item.actualBehavior = body.actual_behavior;
    if (body.status) item.status = body.status;
    item.updatedAt = new Date().toISOString();
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
      user_id: Number(item.userId.replace(/\D/g, "")),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expected_behavior: item.expectedBehavior,
      actual_behavior: item.actualBehavior,
      screenshot_document_id: item.screenshotDocumentId ? Number(item.screenshotDocumentId.replace(/\D/g, "")) : null,
      status: item.status,
      created_at: item.createdAt,
      updated_at: item.updatedAt,
    } as T;
  }
  if (/^\/pilot-feedback\/\d+\/attach-screenshot$/.test(path) && init?.method === "POST") {
    const feedbackId = path.split("/")[2];
    const item = mockPilotFeedback.find((entry) => entry.id === `feedback-${feedbackId}` || entry.id === feedbackId);
    if (!item) throw new Error("Pilot feedback not found");
    const body = JSON.parse(String(init.body ?? "{}")) as { screenshot_document_id: number };
    item.screenshotDocumentId = `doc-${body.screenshot_document_id}`;
    item.updatedAt = new Date().toISOString();
    return {
      id: Number(item.id.replace(/\D/g, "")),
      case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
      user_id: Number(item.userId.replace(/\D/g, "")),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expected_behavior: item.expectedBehavior,
      actual_behavior: item.actualBehavior,
      screenshot_document_id: body.screenshot_document_id,
      status: item.status,
      created_at: item.createdAt,
      updated_at: item.updatedAt,
    } as T;
  }
  if (path === "/pilot-metrics/summary") {
    return {
      total_cases: mockPilotMetricsSummary.totalCases,
      completed_happy_path_cases: mockPilotMetricsSummary.completedHappyPathCases,
      blocked_cases: mockPilotMetricsSummary.blockedCases,
      total_feedback_items: mockPilotMetricsSummary.totalFeedbackItems,
      blocker_feedback_items: mockPilotMetricsSummary.blockerFeedbackItems,
      high_feedback_items: mockPilotMetricsSummary.highFeedbackItems,
      feedback_by_severity_total: mockPilotMetricsSummary.feedbackBySeverityTotal,
      feedback_by_severity_unresolved: mockPilotMetricsSummary.feedbackBySeverityUnresolved,
      average_pretension_draft_minutes: mockPilotMetricsSummary.averagePretensionDraftMinutes,
      average_pretension_draft_data_status: mockPilotMetricsSummary.averagePretensionDraftDataStatus,
      average_claim_draft_minutes: mockPilotMetricsSummary.averageClaimDraftMinutes,
      total_rag_warnings: mockPilotMetricsSummary.totalRagWarnings,
      total_authority_warnings: mockPilotMetricsSummary.totalAuthorityWarnings,
      total_authority_invalids: mockPilotMetricsSummary.totalAuthorityInvalids,
      total_authority_checks: mockPilotMetricsSummary.totalAuthorityChecks,
      total_blocked_actions: mockPilotMetricsSummary.totalBlockedActions,
      authority: {
        checks_total: mockPilotMetricsSummary.authority.checksTotal,
        valid_count: mockPilotMetricsSummary.authority.validCount,
        warning_count: mockPilotMetricsSummary.authority.warningCount,
        invalid_count: mockPilotMetricsSummary.authority.invalidCount,
        blocked_actions_count: mockPilotMetricsSummary.authority.blockedActionsCount,
      },
      authority_by_case: mockPilotMetricsSummary.authorityByCase.map((item) => ({
        case_id: Number(item.caseId.replace(/\D/g, "")),
        title: item.title,
        checks_total: item.checksTotal,
        valid_count: item.validCount,
        warning_count: item.warningCount,
        invalid_count: item.invalidCount,
        blocked_actions_count: item.blockedActionsCount,
      })),
      cases: mockPilotMetricsSummary.cases.map((item) => ({
        case_id: Number(item.caseId.replace(/\D/g, "")),
        title: item.title,
        status: item.status,
        facts_ready_minutes: item.factsReadyMinutes ?? null,
        pretension_draft_minutes: item.pretensionDraftMinutes ?? null,
        pretension_review_minutes: item.pretensionReviewMinutes ?? null,
        claim_draft_minutes: item.claimDraftMinutes ?? null,
        claim_review_minutes: item.claimReviewMinutes ?? null,
        pretension_edits: item.pretensionEdits,
        claim_edits: item.claimEdits,
        rag_warnings: item.ragWarnings,
        authority_warnings: item.authorityWarnings,
        authority_invalids: item.authorityInvalids,
        authority_checks_total: item.authorityChecksTotal,
        authority: {
          checks_total: item.authority.checksTotal,
          valid_count: item.authority.validCount,
          warning_count: item.authority.warningCount,
          invalid_count: item.authority.invalidCount,
          blocked_actions_count: item.authority.blockedActionsCount,
        },
        blocked_actions: item.blockedActions,
        feedback_items: item.feedbackItems,
        pretension_draft_data_status: item.pretensionDraftDataStatus ?? "ok",
      })),
    } as T;
  }
  if (/^\/pilot-metrics\/cases\/[^/]+$/.test(path)) {
    const caseId = path.split("/")[3];
    const item = mockPilotCaseMetrics.find((entry) => entry.caseId === `case-${caseId}` || entry.caseId === caseId);
    if (!item) throw new Error("Pilot metrics not found");
    return {
      case_id: Number(item.caseId.replace(/\D/g, "")),
      title: item.title,
      status: item.status,
      facts_ready_minutes: item.factsReadyMinutes ?? null,
      pretension_draft_minutes: item.pretensionDraftMinutes ?? null,
      pretension_review_minutes: item.pretensionReviewMinutes ?? null,
      claim_draft_minutes: item.claimDraftMinutes ?? null,
      claim_review_minutes: item.claimReviewMinutes ?? null,
      pretension_edits: item.pretensionEdits,
      claim_edits: item.claimEdits,
      rag_warnings: item.ragWarnings,
      authority_warnings: item.authorityWarnings,
      authority_invalids: item.authorityInvalids,
      authority_checks_total: item.authorityChecksTotal,
      authority: {
        checks_total: item.authority.checksTotal,
        valid_count: item.authority.validCount,
        warning_count: item.authority.warningCount,
        invalid_count: item.authority.invalidCount,
        blocked_actions_count: item.authority.blockedActionsCount,
      },
      blocked_actions: item.blockedActions,
      feedback_items: item.feedbackItems,
    } as T;
  }
  if (/^\/pilot-metrics\/cases\/[^/]+\/timeline$/.test(path)) {
    const caseId = path.split("/")[3];
    const normalizedCaseId = normalizeCaseId(caseId) ?? caseId;
    return {
      case_id: Number(normalizedCaseId.replace(/\D/g, "")),
      timeline: (mockPilotTimelines[normalizedCaseId] ?? []).map((item) => ({
        id: item.id,
        case_id: Number(item.caseId.replace(/\D/g, "")),
        event_type: item.eventType,
        title: item.title,
        description: item.description,
        created_at: item.createdAt,
        actor_user_id: item.actorUserId ? Number(item.actorUserId.replace(/\D/g, "")) : null,
        actor_role: item.actorRole ?? null,
        source: item.source,
        severity: item.severity,
        related_entity_type: item.relatedEntityType,
        related_entity_id: item.relatedEntityId,
      })),
    } as T;
  }
  if (path.startsWith("/pilot-report")) {
    return {
      period: mockPilotReport.period,
      date_from: mockPilotReport.dateFrom ?? null,
      date_to: mockPilotReport.dateTo ?? null,
      total_cases: mockPilotReport.totalCases,
      case_statuses: mockPilotReport.caseStatuses,
      feedback_total: mockPilotReport.feedbackTotal,
      feedback_by_severity_total: mockPilotReport.feedbackBySeverityTotal,
      feedback_by_severity_unresolved: mockPilotReport.feedbackBySeverityUnresolved,
      average_pretension_draft_minutes: mockPilotReport.averagePretensionDraftMinutes,
      average_pretension_draft_data_status: mockPilotReport.averagePretensionDraftDataStatus,
      average_claim_draft_minutes: mockPilotReport.averageClaimDraftMinutes,
      ai_rag_warnings: mockPilotReport.aiRagWarnings,
      authority_warnings: mockPilotReport.authorityWarnings,
      authority_invalids: mockPilotReport.authorityInvalids,
      authority_checks_total: mockPilotReport.authorityChecksTotal,
      blocked_actions: mockPilotReport.blockedActions,
      exports_generated: mockPilotReport.exportsGenerated,
      exported_case_ids: mockPilotReport.exportedCaseIds.map((item) => Number(item.replace(/\D/g, ""))),
      unresolved_items: mockPilotReport.unresolvedItems,
      timeline_summary: mockPilotReport.timelineSummary,
      recommendation: mockPilotReport.recommendation,
    } as T;
  }
  if (path.startsWith("/fns/test-connection") && init?.method === "POST") {
    const sandbox = path.includes("sandbox=true");
    return {
      provider: "fns",
      mode: sandbox ? mockSandboxReadiness.fns.mode : mockSystemStatus.fnsMode,
      status: sandbox ? mockSandboxReadiness.fns.testConnectionStatus : "ok",
      ok: sandbox ? mockSandboxReadiness.fns.readyForSandbox : true,
      detail: sandbox ? "Sandbox FNS readiness check executed without external calls." : "Mock FNS provider is available. No external calls were made.",
      external_calls: false,
      sandbox,
      credentials_present: sandbox ? mockSandboxReadiness.fns.credentialsPresent : false,
    } as T;
  }
  if (path.startsWith("/russian-post/test-connection") && init?.method === "POST") {
    const sandbox = path.includes("sandbox=true");
    return {
      provider: "russian_post",
      mode: sandbox ? mockSandboxReadiness.russianPost.mode : mockSystemStatus.russianPostMode,
      status: sandbox ? mockSandboxReadiness.russianPost.testConnectionStatus : "ok",
      ok: sandbox ? mockSandboxReadiness.russianPost.readyForSandbox : true,
      detail: sandbox ? "Sandbox Russian Post readiness check executed without external calls." : "Mock Russian Post provider is available. No letters were sent.",
      external_calls: false,
      sandbox,
      credentials_present: sandbox ? mockSandboxReadiness.russianPost.credentialsPresent : false,
    } as T;
  }
  if (path.startsWith("/court-arbitr/test-connection") && init?.method === "POST") {
    const sandbox = path.includes("sandbox=true");
    return {
      provider: "court_arbitr",
      mode: sandbox ? mockSandboxReadiness.court.mode : mockSystemStatus.courtArbitrMode,
      status: sandbox ? mockSandboxReadiness.court.testConnectionStatus : "ok",
      ok: sandbox ? mockSandboxReadiness.court.readyForSandbox : true,
      detail: sandbox ? "Sandbox court readiness check executed without external calls." : "Mock court provider is available. No external search or scraping was performed.",
      external_calls: false,
      sandbox,
      credentials_present: sandbox ? mockSandboxReadiness.court.credentialsPresent : false,
    } as T;
  }
  if (path === "/organizations") {
    return mockOrganizations.map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      inn: item.inn,
      kpp: item.kpp,
      short_name: item.shortName,
      full_name: item.fullName,
      ogrn: item.ogrn,
      legal_address: item.legalAddress,
      current_director_name: item.currentDirectorName,
      current_director_position: item.currentDirectorPosition,
      review_status: item.reviewStatus,
      source: item.source,
      actual_at: item.actualAt,
      created_at: item.createdAt,
      updated_at: item.updatedAt,
    })) as T;
  }
  if (path.startsWith("/organizations/") && path.endsWith("/snapshots")) {
    const organizationId = path.split("/")[2];
    return (mockOrganizationSnapshots[organizationId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      source: item.source,
      actual_at: item.actualAt,
      raw_payload: item.rawPayload,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/organizations/") && path.endsWith("/lookup-logs")) {
    const organizationId = path.split("/")[2];
    return (mockFnsLookupLogs[organizationId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      organization_id: item.organizationId ? Number(item.organizationId.replace(/\D/g, "")) : null,
      inn: item.inn,
      provider_mode: item.providerMode,
      source: item.source,
      review_status: item.reviewStatus,
      request_payload: item.requestPayload,
      response_payload: item.responsePayload,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/organizations/") && path.endsWith("/employees")) {
    const organizationId = path.split("/")[2];
    return (mockEmployees[organizationId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      user_id: item.userId ? Number(item.userId.replace(/\D/g, "")) : null,
      full_name: item.fullName,
      position: item.position,
      email: item.email,
      is_active: item.isActive,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/organizations/") && path.endsWith("/signatories")) {
    const organizationId = path.split("/")[2];
    return (mockSignatories[organizationId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      employee_id: item.employeeId ? Number(item.employeeId.replace(/\D/g, "")) : null,
      signatory_type: item.signatoryType,
      full_name: item.fullName,
      authority_basis: item.authorityBasis,
      is_active: item.isActive,
      created_at: item.createdAt,
    })) as T;
  }
  if (/^\/organizations\/[^/]+$/.test(path)) {
    const organizationId = path.split("/")[2];
    const item = mockOrganizations.find((entry) => entry.id === organizationId);
    if (!item) throw new Error("Organization not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      inn: item.inn,
      kpp: item.kpp,
      short_name: item.shortName,
      full_name: item.fullName,
      ogrn: item.ogrn,
      legal_address: item.legalAddress,
      current_director_name: item.currentDirectorName,
      current_director_position: item.currentDirectorPosition,
      review_status: item.reviewStatus,
      source: item.source,
      actual_at: item.actualAt,
      created_at: item.createdAt,
      updated_at: item.updatedAt,
    } as T;
  }
  if (path.startsWith("/signatories/") && path.endsWith("/authority-checks")) {
    const signatoryId = path.split("/")[2];
    return (mockAuthorityChecks[signatoryId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      signatory_id: Number(item.signatoryId.replace(/\D/g, "")),
      case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
      power_of_attorney_id: item.powerOfAttorneyId ? Number(item.powerOfAttorneyId.replace(/\D/g, "")) : null,
      document_kind: item.documentKind,
      required_scopes: item.requiredScopes,
      result: item.result,
      reason: item.reason,
      checked_at: item.checkedAt,
    })) as T;
  }
  if (/^\/authority-checks\/cases\/[^/]+$/.test(path)) {
    const caseId = path.split("/")[3];
    return Object.values(mockAuthorityChecks)
      .flat()
      .filter((item) => item.caseId === caseId)
      .map((item) => ({
        id: Number(item.id.replace(/\D/g, "")),
        signatory_id: Number(item.signatoryId.replace(/\D/g, "")),
        case_id: item.caseId ? Number(item.caseId.replace(/\D/g, "")) : null,
        power_of_attorney_id: item.powerOfAttorneyId ? Number(item.powerOfAttorneyId.replace(/\D/g, "")) : null,
        document_kind: item.documentKind,
        required_scopes: item.requiredScopes,
        result: item.result,
        reason: item.reason,
        checked_at: item.checkedAt,
      })) as T;
  }
  if (path.startsWith("/employees/") && path.endsWith("/powers-of-attorney")) {
    const employeeId = path.split("/")[2];
    return (mockPowersOfAttorney[employeeId] ?? []).map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      employee_id: Number(item.employeeId.replace(/\D/g, "")),
      user_id: item.userId ? Number(item.userId.replace(/\D/g, "")) : null,
      number: item.number,
      issued_at: item.issuedAt,
      expires_at: item.expiresAt,
      file_path: item.filePath,
      status: item.status,
      authority_scope: item.authorityScope,
      revoked_at: item.revokedAt,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/postal-dispatches")) {
    const caseIdMatch = /case_id=([^&]+)/.exec(path);
    const caseId = caseIdMatch?.[1];
    return mockPostalDispatches
      .filter((item) => !caseId || item.caseId === caseId)
      .map((item) => ({
        id: Number(item.id.replace(/\D/g, "")),
        case_id: Number(item.caseId.replace(/\D/g, "")),
        organization_id: Number(item.organizationId.replace(/\D/g, "")),
        dispatch_kind: item.dispatchKind,
        provider_mode: item.providerMode,
        recipient_name: item.recipientName,
        recipient_address: item.recipientAddress,
        status: item.status,
        tracking_number: item.trackingNumber,
        external_dispatch_id: item.externalDispatchId,
        source: item.source,
        status_payload: item.statusPayload,
        created_by_id: Number(item.createdById.replace(/\D/g, "")),
        created_at: item.createdAt,
      })) as T;
  }
  if (path.startsWith("/russian-post/cases/") && path.endsWith("/claim-copy-proof")) {
    const caseId = path.split("/")[3];
    const normalizedCaseId = mockPostalProofChecks[caseId] ? caseId : `case-${caseId}`;
    const item = mockPostalProofChecks[normalizedCaseId] ?? { caseId: normalizedCaseId, hasClaimCopyProof: false, dispatchIds: [] };
    return {
      case_id: Number(item.caseId.replace(/\D/g, "")),
      has_claim_copy_proof: item.hasClaimCopyProof,
      dispatch_ids: item.dispatchIds.map((entry) => Number(entry.replace(/\D/g, ""))),
    } as T;
  }
  if (path === "/court-import/jobs" && (!init || init.method === "GET")) {
    return mockCourtImportJobs.map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      inn: item.inn,
      date_from: item.dateFrom,
      date_to: item.dateTo,
      participation_role: item.participationRole,
      provider_mode: item.providerMode,
      status: item.status,
      source: item.source,
      result_count: item.resultCount,
      created_by_id: Number(item.createdById.replace(/\D/g, "")),
      created_at: item.createdAt,
    })) as T;
  }
  if (path === "/court-import/jobs" && init?.method === "POST") {
    const body = JSON.parse(String(init.body ?? "{}")) as {
      organization_id: number;
      inn: string;
      date_from: string;
      date_to: string;
      participation_role: string;
      provider_mode?: string;
    };
    const nextJobId = `job-${mockCourtImportJobs.length + 1}`;
    const nextExternalCaseId = `ext-${mockExternalCourtCases.length + 1}`;
    const createdAt = new Date().toISOString();
    const job = {
      id: nextJobId,
      organizationId: `org-${body.organization_id}`,
      inn: body.inn,
      dateFrom: body.date_from,
      dateTo: body.date_to,
      participationRole: body.participation_role,
      providerMode: body.provider_mode ?? "MOCK_FOR_DEV",
      status: "COMPLETED",
      source: "MOCK_COURT_PROVIDER",
      resultCount: 1,
      createdById: "u4",
      createdAt,
    };
    mockCourtImportJobs.unshift(job);
    mockExternalCourtCases.unshift({
      id: nextExternalCaseId,
      importJobId: nextJobId,
      organizationId: `org-${body.organization_id}`,
      externalCaseUid: `kad-${mockExternalCourtCases.length + 1}`,
      caseNumber: `А40-${10000 + mockExternalCourtCases.length}/2026`,
      courtName: "Арбитражный суд города Москвы",
      participantRole: body.participation_role,
      claimSubject: "Взыскание задолженности",
      caseDate: body.date_from,
      linkedCaseId: "case-1004",
      source: "MOCK_COURT_PROVIDER",
      payloadHash: `mock-payload-hash-${mockExternalCourtCases.length + 1}`,
      createdAt,
      events: [{ id: `event-${mockExternalCourtCases.length + 1}`, eventDate: body.date_from, eventType: "registered", description: "Карточка дела создана.", createdAt }],
      snapshots: [{ id: `snapshot-${mockExternalCourtCases.length + 1}`, source: "MOCK_COURT_PROVIDER", snapshotPayload: `{"case_number":"А40-${10000 + mockExternalCourtCases.length}/2026"}`, snapshotHash: `mock-snapshot-hash-${mockExternalCourtCases.length + 1}`, createdAt }],
    });
    return {
      id: Number(nextJobId.replace(/\D/g, "")),
      organization_id: body.organization_id,
      inn: body.inn,
      date_from: body.date_from,
      date_to: body.date_to,
      participation_role: body.participation_role,
      provider_mode: body.provider_mode ?? "MOCK_FOR_DEV",
      status: "COMPLETED",
      source: "MOCK_COURT_PROVIDER",
      result_count: 1,
      created_by_id: 4,
      created_at: createdAt,
    } as T;
  }
  if (path.startsWith("/court-import/jobs/") && path.endsWith("/cases")) {
    return mockExternalCourtCases.map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      import_job_id: Number(item.importJobId.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      external_case_uid: item.externalCaseUid,
      case_number: item.caseNumber,
      court_name: item.courtName,
      participant_role: item.participantRole,
      claim_subject: item.claimSubject,
      case_date: item.caseDate,
      linked_case_id: item.linkedCaseId ? Number(item.linkedCaseId.replace(/\D/g, "")) : null,
      source: item.source,
      payload_hash: item.payloadHash,
      created_at: item.createdAt,
      events: item.events.map((event) => ({ id: Number(event.id.replace(/\D/g, "")), event_date: event.eventDate, event_type: event.eventType, description: event.description, created_at: event.createdAt })),
      snapshots: item.snapshots.map((snapshot) => ({ id: Number(snapshot.id.replace(/\D/g, "")), source: snapshot.source, snapshot_payload: snapshot.snapshotPayload, snapshot_hash: snapshot.snapshotHash, created_at: snapshot.createdAt })),
    })) as T;
  }
  if (path === "/external-court-cases") {
    return mockExternalCourtCases.map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      import_job_id: Number(item.importJobId.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      external_case_uid: item.externalCaseUid,
      case_number: item.caseNumber,
      court_name: item.courtName,
      participant_role: item.participantRole,
      claim_subject: item.claimSubject,
      case_date: item.caseDate,
      linked_case_id: item.linkedCaseId ? Number(item.linkedCaseId.replace(/\D/g, "")) : null,
      source: item.source,
      payload_hash: item.payloadHash,
      created_at: item.createdAt,
      events: item.events.map((event) => ({ id: Number(event.id.replace(/\D/g, "")), event_date: event.eventDate, event_type: event.eventType, description: event.description, created_at: event.createdAt })),
      snapshots: item.snapshots.map((snapshot) => ({ id: Number(snapshot.id.replace(/\D/g, "")), source: snapshot.source, snapshot_payload: snapshot.snapshotPayload, snapshot_hash: snapshot.snapshotHash, created_at: snapshot.createdAt })),
    })) as T;
  }
  if (/^\/external-court-cases\/[^/]+$/.test(path)) {
    const externalCaseId = path.split("/")[2];
    const item = mockExternalCourtCases.find((entry) => entry.id === externalCaseId || entry.id === `ext-${externalCaseId}`);
    if (!item) throw new Error("External court case not found");
    return {
      id: Number(item.id.replace(/\D/g, "")),
      import_job_id: Number(item.importJobId.replace(/\D/g, "")),
      organization_id: Number(item.organizationId.replace(/\D/g, "")),
      external_case_uid: item.externalCaseUid,
      case_number: item.caseNumber,
      court_name: item.courtName,
      participant_role: item.participantRole,
      claim_subject: item.claimSubject,
      case_date: item.caseDate,
      linked_case_id: item.linkedCaseId ? Number(item.linkedCaseId.replace(/\D/g, "")) : null,
      source: item.source,
      payload_hash: item.payloadHash,
      created_at: item.createdAt,
      events: item.events.map((event) => ({ id: Number(event.id.replace(/\D/g, "")), event_date: event.eventDate, event_type: event.eventType, description: event.description, created_at: event.createdAt })),
      snapshots: item.snapshots.map((snapshot) => ({ id: Number(snapshot.id.replace(/\D/g, "")), source: snapshot.source, snapshot_payload: snapshot.snapshotPayload, snapshot_hash: snapshot.snapshotHash, created_at: snapshot.createdAt })),
    } as T;
  }
  if (path.startsWith("/settings")) return mockSettings as T;
  if (path === "/audit") {
    return mockAuditEntries.map((item) => ({
      id: Number(item.id.replace(/\D/g, "")),
      actor_user_id: item.actorUserId ? Number(item.actorUserId.replace(/\D/g, "")) : null,
      action: item.action,
      entity_type: item.entityType,
      entity_id: item.entityId,
      details: item.details,
      request_id: item.requestId,
      created_at: item.createdAt,
    })) as T;
  }
  if (path.startsWith("/court-submission") && init?.method === "POST") {
    return {
      id: 1,
      case_id: 1004,
      organization_id: 1,
      external_court_case_id: 1,
      status: "READY_FOR_MANUAL_SUBMISSION",
      package_path: "mock/court-package.zip",
      created_by_id: 4,
      note: "Prepared from frontend MVP",
      created_at: new Date().toISOString(),
    } as T;
  }
  if (path.startsWith("/export/") && init?.method === "POST") {
    const caseId = path.split("/")[2];
    const proof = mockPostalProofChecks[caseId] ?? mockPostalProofChecks[`case-${caseId}`];
    if (!proof?.hasClaimCopyProof) {
      throw new Error("Нельзя сформировать судебный комплект: отсутствует доказательство направления копии иска ответчику.");
    }
    return { id: 1, archive_path: `mock/exports/${caseId}.zip` } as T;
  }
  throw new Error(`Mock endpoint not implemented: ${path}`);
}

function formatAmount(value: number | string): string {
  const number = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(number)) return String(value);
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 2 }).format(number);
}

function mapCaseSummary(item: { id: number; title: string; claimant_name: string; respondent_name: string; claim_amount: number; status: string; assigned_lawyer_id: number | null; created_at: string }): CaseSummary {
  return { id: String(item.id), title: item.title, plaintiff: item.claimant_name, defendant: item.respondent_name, amount: formatAmount(item.claim_amount), responsibleLawyer: item.assigned_lawyer_id ? `lawyer#${item.assigned_lawyer_id}` : undefined, status: item.status as CaseSummary["status"], updatedAt: item.created_at };
}

function mapDraft(item: { id: number; case_id: number; content: string; approved: boolean; updated_at: string }): DraftDocument {
  return { id: String(item.id), caseId: String(item.case_id), content: item.content, approved: item.approved, updatedAt: item.updated_at };
}

function mapDocument(item: { id: number; case_id: number; filename: string; content_type: string; sha256: string; extracted_text: string; is_approved: boolean; created_at: string }): CaseDocument {
  return { id: String(item.id), caseId: String(item.case_id), fileName: item.filename, mimeType: item.content_type, sha256: item.sha256, extractedText: item.extracted_text, approved: item.is_approved, createdAt: item.created_at, status: item.extracted_text ? "parsed" : "uploaded" };
}

function mapOrganization(item: { id: number; inn: string; kpp: string; short_name: string; full_name: string; ogrn: string; legal_address: string; current_director_name: string; current_director_position: string; review_status: string; source: string; actual_at: string; created_at: string; updated_at: string }): Organization {
  return { id: String(item.id), inn: item.inn, kpp: item.kpp, shortName: item.short_name, fullName: item.full_name, ogrn: item.ogrn, legalAddress: item.legal_address, currentDirectorName: item.current_director_name, currentDirectorPosition: item.current_director_position, reviewStatus: item.review_status, source: item.source, actualAt: item.actual_at, createdAt: item.created_at, updatedAt: item.updated_at };
}

function mapExternalCourtCase(item: { id: number; import_job_id: number; organization_id: number; external_case_uid: string; case_number: string; court_name: string; participant_role: string; claim_subject: string; case_date: string | null; linked_case_id: number | null; source: string; payload_hash: string; created_at: string; events: Array<{ id: number; event_date: string | null; event_type: string; description: string; created_at: string }>; snapshots: Array<{ id: number; source: string; snapshot_payload: string; snapshot_hash: string; created_at: string }> }): ExternalCourtCase {
  return { id: String(item.id), importJobId: String(item.import_job_id), organizationId: String(item.organization_id), externalCaseUid: item.external_case_uid, caseNumber: item.case_number, courtName: item.court_name, participantRole: item.participant_role, claimSubject: item.claim_subject, caseDate: item.case_date, linkedCaseId: item.linked_case_id ? String(item.linked_case_id) : null, source: item.source, payloadHash: item.payload_hash, createdAt: item.created_at, events: item.events.map((event) => ({ id: String(event.id), eventDate: event.event_date, eventType: event.event_type, description: event.description, createdAt: event.created_at })), snapshots: item.snapshots.map((snapshot) => ({ id: String(snapshot.id), source: snapshot.source, snapshotPayload: snapshot.snapshot_payload, snapshotHash: snapshot.snapshot_hash, createdAt: snapshot.created_at })) };
}

function mapMockApproval(item: IntegrationApproval) {
  return {
    id: Number(item.id.replace(/\D/g, "")),
    integration_name: item.integrationName,
    environment: item.environment,
    requested_by_id: item.requestedById ? Number(item.requestedById.replace(/\D/g, "")) : null,
    approved_by_id: item.approvedById ? Number(item.approvedById.replace(/\D/g, "")) : null,
    status: item.status,
    reason: item.reason,
    approved_at: item.approvedAt ?? null,
    expires_at: item.expiresAt ?? null,
    created_at: item.createdAt,
    updated_at: item.updatedAt,
  };
}

function mapIntegrationApproval(item: {
  id: number;
  integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR";
  environment: "SANDBOX" | "PRODUCTION";
  requested_by_id: number | null;
  approved_by_id: number | null;
  status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED";
  reason: string;
  approved_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}): IntegrationApproval {
  return {
    id: String(item.id),
    integrationName: item.integration_name,
    environment: item.environment,
    requestedById: item.requested_by_id ? String(item.requested_by_id) : null,
    approvedById: item.approved_by_id ? String(item.approved_by_id) : null,
    status: item.status,
    reason: item.reason,
    approvedAt: item.approved_at,
    expiresAt: item.expires_at,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

export const apiClient = {
  async login(input: LoginInput) {
    const token = await request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email: input.email, password: input.password }) });
    setToken(token.access_token);
    return this.getMe();
  },
  async getMe() {
    const profile = await request<{ id: number; email: string; full_name: string; role: UserProfile["role"] }>("/users/me");
    return { id: String(profile.id), email: profile.email, fullName: profile.full_name, role: profile.role } satisfies UserProfile;
  },
  async listCases() {
    const cases = await request<Array<{ id: number; title: string; claimant_name: string; respondent_name: string; claim_amount: number; status: string; assigned_lawyer_id: number | null; created_at: string }>>("/cases");
    return cases.map(mapCaseSummary);
  },
  async createCase(input: CaseCreateInput) {
    const item = await request<{ id: number; title: string; claimant_name: string; respondent_name: string; claim_amount: number; status: string; assigned_lawyer_id: number | null; created_at: string }>("/cases", { method: "POST", body: JSON.stringify({ title: input.title, description: input.description, claimant_name: input.plaintiff, respondent_name: input.defendant, claim_amount: Number(input.amount), assigned_lawyer_id: input.responsibleLawyerId ? Number(input.responsibleLawyerId) : null }) });
    return mapCaseSummary(item);
  },
  async listDocuments(caseId: string) {
    const items = await request<Array<{ id: number; case_id: number; filename: string; content_type: string; sha256: string; extracted_text: string; is_approved: boolean; created_at: string }>>(`/documents/${caseId}`);
    return items.map(mapDocument);
  },
  async getCase(id: string): Promise<CaseDetailModel> {
    const item = await request<{ id: number; title: string; description: string; claimant_name: string; respondent_name: string; claim_amount: number; status: string; assigned_lawyer_id: number | null; created_at: string }>(`/cases/${id}`);
    const [documents, pretension, claim, checklist, citations] = await Promise.allSettled([this.listDocuments(id), this.getPretension(id), this.getClaim(id), this.getChecklist(id), this.listCitations(id)]);
    return {
      ...mapCaseSummary({ id: item.id, title: item.title, claimant_name: item.claimant_name, respondent_name: item.respondent_name, claim_amount: item.claim_amount, status: item.status, assigned_lawyer_id: item.assigned_lawyer_id, created_at: item.created_at }),
      description: item.description,
      documents: documents.status === "fulfilled" ? documents.value : [],
      facts: USE_MOCK ? (mockCaseDetails[id]?.facts ?? []) : [],
      pretension: pretension.status === "fulfilled" ? pretension.value : null,
      claim: claim.status === "fulfilled" ? claim.value : null,
      checklist: checklist.status === "fulfilled" ? checklist.value : null,
      citations: citations.status === "fulfilled" ? citations.value : [],
    };
  },
  async uploadDocument(caseId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const item = await request<{ id: number; case_id: number; filename: string; content_type: string; sha256: string; extracted_text: string; is_approved: boolean; created_at: string }>(`/documents/${caseId}`, { method: "POST", body: formData });
    return mapDocument(item);
  },
  async listDocumentVersions(documentId: string) {
    const items = await request<Array<{ id: number; document_id: number; version: number; storage_path: string; sha256: string; extracted_text: string; created_at: string }>>(`/documents/item/${documentId}/versions`);
    return items.map((item) => ({ id: String(item.id), documentId: String(item.document_id), version: item.version, storagePath: item.storage_path, sha256: item.sha256, extractedText: item.extracted_text, createdAt: item.created_at }) satisfies DocumentVersion);
  },
  async runExtraction(caseId: string) {
    const payload = await request<{ facts: Array<{ id: number; fact_type: string; value: string; confidence: number; source_fragment: string }>; warnings: string[]; status: string }>(`/extraction/${caseId}/run`, { method: "POST" });
    return { facts: payload.facts.map((item) => ({ id: String(item.id), title: item.fact_type, value: item.value, confidence: item.confidence, source: item.source_fragment }) satisfies CaseFact), warnings: payload.warnings, status: payload.status };
  },
  async getPretension(caseId: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/pretensions/${caseId}`));
  },
  async generatePretension(caseId: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/pretensions/${caseId}/generate`, { method: "POST" }));
  },
  async updatePretension(caseId: string, content: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/pretensions/${caseId}`, { method: "PUT", body: JSON.stringify({ content }) }));
  },
  async getClaim(caseId: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/claims/${caseId}`));
  },
  async generateClaim(caseId: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/claims/${caseId}/generate`, { method: "POST" }));
  },
  async updateClaim(caseId: string, content: string) {
    return mapDraft(await request<{ id: number; case_id: number; content: string; approved: boolean; updated_at: string }>(`/claims/${caseId}`, { method: "PUT", body: JSON.stringify({ content }) }));
  },
  async approvePretension(caseId: string) {
    return request<{ case_id: number; status: string; approved: boolean }>(`/workflow/${caseId}/approve-pretension`, { method: "POST" });
  },
  async approveClaim(caseId: string) {
    return request<{ case_id: number; status: string; approved: boolean }>(`/workflow/${caseId}/approve-claim`, { method: "POST" });
  },
  async markCourtPackageReady(caseId: string) {
    return request<{ case_id: number; status: string; approved: boolean }>(`/workflow/${caseId}/court-package-ready`, { method: "POST" });
  },
  async exportCase(caseId: string) {
    const item = await request<{ id: number; archive_path: string }>(`/export/${caseId}`, { method: "POST" });
    return { id: String(item.id), filePath: item.archive_path };
  },
  async getChecklist(caseId: string) {
    const item = await request<{ id: number; case_id: number; status: string; items: Array<{ id: number; title: string; is_completed: boolean; notes: string }> }>(`/checklists/${caseId}`);
    return { id: String(item.id), caseId: String(item.case_id), status: item.status, items: item.items.map((check) => ({ id: String(check.id), title: check.title, isCompleted: check.is_completed, notes: check.notes })) } satisfies Checklist;
  },
  async updateChecklistItem(itemId: string, isCompleted: boolean, notes: string) {
    const item = await request<{ id: number; title: string; is_completed: boolean; notes: string }>(`/checklists/items/${itemId}`, { method: "PUT", body: JSON.stringify({ is_completed: isCompleted, notes }) });
    return { id: String(item.id), title: item.title, isCompleted: item.is_completed, notes: item.notes };
  },
  async searchRag(query: string, caseId?: string) {
    const payload = await request<{ query: string; results: Array<{ id: number; case_id: number | null; title: string; source_type: string; document_date: string; jurisdiction: string; category: string; fragment: string; page: number | null; section: string; url_or_internal_path: string; score: number; created_at: string }>; warning: string | null }>("/rag/search", { method: "POST", body: JSON.stringify({ query, case_id: caseId ? Number(caseId) : null, top_k: 5 }) });
    return { warning: payload.warning, results: payload.results.map((item) => ({ id: String(item.id), caseId: item.case_id ? String(item.case_id) : null, title: item.title, sourceType: item.source_type, category: item.category, jurisdiction: item.jurisdiction, fragment: item.fragment, page: item.page, section: item.section, score: item.score, documentDate: item.document_date, path: item.url_or_internal_path, createdAt: item.created_at }) satisfies RagSource) };
  },
  async createRagSource(payload: { title: string; sourceType: string; category: string; jurisdiction?: string; fragment: string; caseId?: string }) {
    const item = await request<{ id: number; case_id: number | null; title: string; source_type: string; document_date: string; jurisdiction: string; category: string; fragment: string; page: number | null; section: string; url_or_internal_path: string; score: number; created_at: string }>("/rag/sources", { method: "POST", body: JSON.stringify({ title: payload.title, source_type: payload.sourceType, category: payload.category, jurisdiction: payload.jurisdiction ?? "", fragment: payload.fragment, case_id: payload.caseId ? Number(payload.caseId) : null }) });
    return { id: String(item.id), caseId: item.case_id ? String(item.case_id) : null, title: item.title, sourceType: item.source_type, category: item.category, jurisdiction: item.jurisdiction, fragment: item.fragment, page: item.page, section: item.section, score: item.score, documentDate: item.document_date, path: item.url_or_internal_path, createdAt: item.created_at } satisfies RagSource;
  },
  async listCitations(caseId: string) {
    const items = await request<Array<{ id: number; source_id: number; case_id: number | null; target_type: string; target_id: number | null; quote: string; created_at: string }>>(`/rag/citations/${caseId}`);
    return items.map((item) => ({ id: String(item.id), sourceId: String(item.source_id), caseId: item.case_id ? String(item.case_id) : null, targetType: item.target_type, targetId: item.target_id ? String(item.target_id) : null, quote: item.quote, createdAt: item.created_at }) satisfies RagCitation);
  },
  async getDashboard() {
    const item = await request<{ user_role: string; total_cases: number }>("/dashboard");
    return { userRole: item.user_role, totalCases: item.total_cases } satisfies DashboardModel;
  },
  async getSystemStatus() {
    const item = await request<{
      backend: string;
      database: string;
      storage: string;
      redis: string;
      worker: string;
      vector_db: string;
      llm: string;
      fns_provider: string;
      fns_mode: string;
      fns_sandbox_enabled: boolean;
      real_fns_enabled: boolean;
      russian_post_provider: string;
      russian_post_mode: string;
      russian_post_sandbox_enabled: boolean;
      real_post_send_enabled: boolean;
      court_arbitr_provider: string;
      court_arbitr_mode: string;
      court_sandbox_enabled: boolean;
      real_court_search_enabled: boolean;
      public_kad_search_enabled: boolean;
      court_submission_enabled: boolean;
    }>("/system/status");
    return {
      backend: item.backend,
      database: item.database,
      storage: item.storage,
      redis: item.redis,
      worker: item.worker,
      vectorDb: item.vector_db,
      llm: item.llm,
      fnsProvider: item.fns_provider,
      fnsMode: item.fns_mode,
      fnsSandboxEnabled: item.fns_sandbox_enabled,
      realFnsEnabled: item.real_fns_enabled,
      russianPostProvider: item.russian_post_provider,
      russianPostMode: item.russian_post_mode,
      russianPostSandboxEnabled: item.russian_post_sandbox_enabled,
      realPostSendEnabled: item.real_post_send_enabled,
      courtArbitrProvider: item.court_arbitr_provider,
      courtArbitrMode: item.court_arbitr_mode,
      courtSandboxEnabled: item.court_sandbox_enabled,
      realCourtSearchEnabled: item.real_court_search_enabled,
      publicKadSearchEnabled: item.public_kad_search_enabled,
      courtSubmissionEnabled: item.court_submission_enabled,
    } satisfies SystemStatus;
  },
  async getSandboxReadiness() {
    const item = await request<{
      fns: { sandbox_flag: boolean; credentials_present: boolean; test_connection_status: string; ready_for_sandbox: boolean; blocking_reasons: string[]; mode: string; provider: string; approval_status: string; active_approval?: boolean; approval_expires_at?: string | null };
      russian_post: { sandbox_flag: boolean; credentials_present: boolean; test_connection_status: string; ready_for_sandbox: boolean; blocking_reasons: string[]; mode: string; provider: string; approval_status: string; active_approval?: boolean; approval_expires_at?: string | null };
      court: { sandbox_flag: boolean; credentials_present: boolean; test_connection_status: string; ready_for_sandbox: boolean; blocking_reasons: string[]; mode: string; provider: string; approval_status: string; active_approval?: boolean; approval_expires_at?: string | null };
    }>("/integration-readiness/sandbox");
    return {
      fns: {
        sandboxFlag: item.fns.sandbox_flag,
        credentialsPresent: item.fns.credentials_present,
        testConnectionStatus: item.fns.test_connection_status,
        readyForSandbox: item.fns.ready_for_sandbox,
        blockingReasons: item.fns.blocking_reasons,
        mode: item.fns.mode,
        provider: item.fns.provider,
        approvalStatus: item.fns.approval_status,
        activeApproval: item.fns.active_approval ?? false,
        approvalExpiresAt: item.fns.approval_expires_at ?? null,
      },
      russianPost: {
        sandboxFlag: item.russian_post.sandbox_flag,
        credentialsPresent: item.russian_post.credentials_present,
        testConnectionStatus: item.russian_post.test_connection_status,
        readyForSandbox: item.russian_post.ready_for_sandbox,
        blockingReasons: item.russian_post.blocking_reasons,
        mode: item.russian_post.mode,
        provider: item.russian_post.provider,
        approvalStatus: item.russian_post.approval_status,
        activeApproval: item.russian_post.active_approval ?? false,
        approvalExpiresAt: item.russian_post.approval_expires_at ?? null,
      },
      court: {
        sandboxFlag: item.court.sandbox_flag,
        credentialsPresent: item.court.credentials_present,
        testConnectionStatus: item.court.test_connection_status,
        readyForSandbox: item.court.ready_for_sandbox,
        blockingReasons: item.court.blocking_reasons,
        mode: item.court.mode,
        provider: item.court.provider,
        approvalStatus: item.court.approval_status,
        activeApproval: item.court.active_approval ?? false,
        approvalExpiresAt: item.court.approval_expires_at ?? null,
      },
    } satisfies SandboxReadiness;
  },
  async getIntegrationCredentialsStatus() {
    const item = await request<{
      fns: { sandbox_credentials_present: boolean; production_credentials_present: boolean };
      russian_post: { sandbox_credentials_present: boolean; production_credentials_present: boolean };
      court_arbitr: { sandbox_credentials_present: boolean; production_credentials_present: boolean };
    }>("/integration-readiness/credentials");
    return {
      fns: {
        sandboxCredentialsPresent: item.fns.sandbox_credentials_present,
        productionCredentialsPresent: item.fns.production_credentials_present,
      },
      russianPost: {
        sandboxCredentialsPresent: item.russian_post.sandbox_credentials_present,
        productionCredentialsPresent: item.russian_post.production_credentials_present,
      },
      courtArbitr: {
        sandboxCredentialsPresent: item.court_arbitr.sandbox_credentials_present,
        productionCredentialsPresent: item.court_arbitr.production_credentials_present,
      },
    } satisfies IntegrationCredentialsStatus;
  },
  async listAudit() {
    const items = await request<Array<{ id: number; actor_user_id: number | null; action: string; entity_type: string; entity_id: string; details: string; request_id: string; created_at: string }>>("/audit");
    return items.map((item) => ({ id: String(item.id), actorUserId: item.actor_user_id ? String(item.actor_user_id) : null, action: item.action, entityType: item.entity_type, entityId: item.entity_id, details: item.details, requestId: item.request_id, createdAt: item.created_at }) satisfies AuditEntry);
  },
  async listSettings() {
    const items = await request<Array<{ key: string; value: string; description: string }>>("/settings");
    return items.map((item) => ({ key: item.key, value: item.value, description: item.description }) satisfies SettingItem);
  },
  async listIntegrationApprovals(filters?: { integrationName?: string; environment?: string; status?: string }) {
    const params = new URLSearchParams();
    if (filters?.integrationName) params.set("integration_name", filters.integrationName);
    if (filters?.environment) params.set("environment", filters.environment);
    if (filters?.status) params.set("status", filters.status);
    const suffix = params.size ? `?${params.toString()}` : "";
    const items = await request<Array<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>>(`/integration-approvals${suffix}`);
    return items.map(mapIntegrationApproval);
  },
  async listActiveIntegrationApprovals() {
    const items = await request<Array<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>>("/integration-approvals/active");
    return items.map(mapIntegrationApproval);
  },
  async getIntegrationApproval(approvalId: string) {
    return mapIntegrationApproval(
      await request<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>(`/integration-approvals/${approvalId.replace(/\D/g, "")}`),
    );
  },
  async createIntegrationApproval(input: { integrationName: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; reason: string; expiresAt?: string | null }) {
    return mapIntegrationApproval(
      await request<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>("/integration-approvals", {
        method: "POST",
        body: JSON.stringify({
          integration_name: input.integrationName,
          environment: input.environment,
          reason: input.reason,
          expires_at: input.expiresAt ?? null,
        }),
      }),
    );
  },
  async approveIntegrationApproval(approvalId: string, reason: string) {
    return mapIntegrationApproval(
      await request<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>(`/integration-approvals/${approvalId.replace(/\D/g, "")}/approve`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    );
  },
  async rejectIntegrationApproval(approvalId: string, reason: string) {
    return mapIntegrationApproval(
      await request<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>(`/integration-approvals/${approvalId.replace(/\D/g, "")}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    );
  },
  async revokeIntegrationApproval(approvalId: string, reason: string) {
    return mapIntegrationApproval(
      await request<{ id: number; integration_name: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR"; environment: "SANDBOX" | "PRODUCTION"; requested_by_id: number | null; approved_by_id: number | null; status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED"; reason: string; approved_at: string | null; expires_at: string | null; created_at: string; updated_at: string }>(`/integration-approvals/${approvalId.replace(/\D/g, "")}/revoke`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    );
  },
  async listPilotFeedback(filters?: { caseId?: string; module?: string; severity?: string; status?: string }) {
    const params = new URLSearchParams();
    if (filters?.caseId) params.set("case_id", filters.caseId.replace(/\D/g, ""));
    if (filters?.module) params.set("module", filters.module);
    if (filters?.severity) params.set("severity", filters.severity);
    if (filters?.status) params.set("status", filters.status);
    const suffix = params.size ? `?${params.toString()}` : "";
    const items = await request<Array<{ id: number; case_id: number | null; user_id: number; role: Role; module: string; severity: string; title: string; description: string; expected_behavior: string; actual_behavior: string; screenshot_document_id: number | null; status: string; created_at: string; updated_at: string }>>(`/pilot-feedback${suffix}`);
    return items.map((item) => ({
      id: String(item.id),
      caseId: normalizeCaseId(item.case_id),
      userId: String(item.user_id),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expectedBehavior: item.expected_behavior,
      actualBehavior: item.actual_behavior,
      screenshotDocumentId: item.screenshot_document_id ? String(item.screenshot_document_id) : null,
      status: item.status,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })) satisfies PilotFeedback[];
  },
  async createPilotFeedback(payload: { caseId?: string; module: string; severity: string; title: string; description?: string; expectedBehavior?: string; actualBehavior?: string }) {
    const item = await request<{ id: number; case_id: number | null; user_id: number; role: Role; module: string; severity: string; title: string; description: string; expected_behavior: string; actual_behavior: string; screenshot_document_id: number | null; status: string; created_at: string; updated_at: string }>("/pilot-feedback", {
      method: "POST",
      body: JSON.stringify({
        case_id: payload.caseId ? Number(payload.caseId.replace(/\D/g, "")) : null,
        module: payload.module,
        severity: payload.severity,
        title: payload.title,
        description: payload.description ?? "",
        expected_behavior: payload.expectedBehavior ?? "",
        actual_behavior: payload.actualBehavior ?? "",
      }),
    });
    return {
      id: String(item.id),
      caseId: normalizeCaseId(item.case_id),
      userId: String(item.user_id),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expectedBehavior: item.expected_behavior,
      actualBehavior: item.actual_behavior,
      screenshotDocumentId: item.screenshot_document_id ? String(item.screenshot_document_id) : null,
      status: item.status,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    } satisfies PilotFeedback;
  },
  async updatePilotFeedback(feedbackId: string, payload: { status?: string; severity?: string; module?: string; title?: string; description?: string }) {
    const item = await request<{ id: number; case_id: number | null; user_id: number; role: Role; module: string; severity: string; title: string; description: string; expected_behavior: string; actual_behavior: string; screenshot_document_id: number | null; status: string; created_at: string; updated_at: string }>(`/pilot-feedback/${feedbackId.replace(/\D/g, "")}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: payload.status,
        severity: payload.severity,
        module: payload.module,
        title: payload.title,
        description: payload.description,
      }),
    });
    return {
      id: String(item.id),
      caseId: normalizeCaseId(item.case_id),
      userId: String(item.user_id),
      role: item.role,
      module: item.module,
      severity: item.severity,
      title: item.title,
      description: item.description,
      expectedBehavior: item.expected_behavior,
      actualBehavior: item.actual_behavior,
      screenshotDocumentId: item.screenshot_document_id ? String(item.screenshot_document_id) : null,
      status: item.status,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    } satisfies PilotFeedback;
  },
  async getPilotMetricsSummary() {
    const item = await request<{ total_cases: number; completed_happy_path_cases: number; blocked_cases: number; total_feedback_items: number; blocker_feedback_items: number; high_feedback_items: number; feedback_by_severity_total: Record<string, number>; feedback_by_severity_unresolved: Record<string, number>; average_pretension_draft_minutes: number; average_pretension_draft_data_status: string; average_claim_draft_minutes: number | null; total_rag_warnings: number; total_authority_warnings: number; total_authority_invalids: number; total_authority_checks: number; total_blocked_actions: number; authority: { checks_total: number; valid_count: number; warning_count: number; invalid_count: number; blocked_actions_count: number }; authority_by_case: Array<{ case_id: number; title: string; checks_total: number; valid_count: number; warning_count: number; invalid_count: number; blocked_actions_count: number }>; cases: Array<{ case_id: number; title: string; status: string; facts_ready_minutes: number | null; pretension_draft_minutes: number | null; pretension_review_minutes: number | null; claim_draft_minutes: number | null; claim_review_minutes: number | null; pretension_edits: number; claim_edits: number; rag_warnings: number; authority_warnings: number; authority_invalids: number; authority_checks_total: number; authority: { checks_total: number; valid_count: number; warning_count: number; invalid_count: number; blocked_actions_count: number }; blocked_actions: number; feedback_items: number; pretension_draft_data_status: string }> }>("/pilot-metrics/summary");
    return {
      totalCases: item.total_cases,
      completedHappyPathCases: item.completed_happy_path_cases,
      blockedCases: item.blocked_cases,
      totalFeedbackItems: item.total_feedback_items,
      blockerFeedbackItems: item.blocker_feedback_items,
      highFeedbackItems: item.high_feedback_items,
      feedbackBySeverityTotal: item.feedback_by_severity_total,
      feedbackBySeverityUnresolved: item.feedback_by_severity_unresolved,
      averagePretensionDraftMinutes: item.average_pretension_draft_minutes,
      averagePretensionDraftDataStatus: item.average_pretension_draft_data_status,
      averageClaimDraftMinutes: item.average_claim_draft_minutes,
      totalRagWarnings: item.total_rag_warnings,
      totalAuthorityWarnings: item.total_authority_warnings,
      totalAuthorityInvalids: item.total_authority_invalids,
      totalAuthorityChecks: item.total_authority_checks,
      totalBlockedActions: item.total_blocked_actions,
      authority: {
        checksTotal: item.authority.checks_total,
        validCount: item.authority.valid_count,
        warningCount: item.authority.warning_count,
        invalidCount: item.authority.invalid_count,
        blockedActionsCount: item.authority.blocked_actions_count,
      },
      authorityByCase: item.authority_by_case.map((entry) => ({
        caseId: normalizeCaseId(entry.case_id) ?? String(entry.case_id),
        title: entry.title,
        checksTotal: entry.checks_total,
        validCount: entry.valid_count,
        warningCount: entry.warning_count,
        invalidCount: entry.invalid_count,
        blockedActionsCount: entry.blocked_actions_count,
      })),
      cases: item.cases.map((entry) => ({
        caseId: normalizeCaseId(entry.case_id) ?? String(entry.case_id),
        title: entry.title,
        status: entry.status,
        factsReadyMinutes: entry.facts_ready_minutes,
        pretensionDraftMinutes: entry.pretension_draft_minutes,
        pretensionReviewMinutes: entry.pretension_review_minutes,
        claimDraftMinutes: entry.claim_draft_minutes,
        claimReviewMinutes: entry.claim_review_minutes,
        pretensionEdits: entry.pretension_edits,
        claimEdits: entry.claim_edits,
        ragWarnings: entry.rag_warnings,
        authorityWarnings: entry.authority_warnings,
        authorityInvalids: entry.authority_invalids,
        authorityChecksTotal: entry.authority_checks_total,
        authority: {
          checksTotal: entry.authority.checks_total,
          validCount: entry.authority.valid_count,
          warningCount: entry.authority.warning_count,
          invalidCount: entry.authority.invalid_count,
          blockedActionsCount: entry.authority.blocked_actions_count,
        },
        blockedActions: entry.blocked_actions,
        feedbackItems: entry.feedback_items,
        pretensionDraftDataStatus: entry.pretension_draft_data_status,
      })),
    } satisfies PilotMetricsSummary;
  },
  async getPilotCaseMetrics(caseId: string) {
    const item = await request<{ case_id: number; title: string; status: string; facts_ready_minutes: number | null; pretension_draft_minutes: number | null; pretension_review_minutes: number | null; claim_draft_minutes: number | null; claim_review_minutes: number | null; pretension_edits: number; claim_edits: number; rag_warnings: number; authority_warnings: number; authority_invalids: number; authority_checks_total: number; authority: { checks_total: number; valid_count: number; warning_count: number; invalid_count: number; blocked_actions_count: number }; blocked_actions: number; feedback_items: number; pretension_draft_data_status: string }>(`/pilot-metrics/cases/${caseId.replace(/\D/g, "")}`);
    return {
      caseId: normalizeCaseId(item.case_id) ?? String(item.case_id),
      title: item.title,
      status: item.status,
      factsReadyMinutes: item.facts_ready_minutes,
      pretensionDraftMinutes: item.pretension_draft_minutes,
      pretensionReviewMinutes: item.pretension_review_minutes,
      claimDraftMinutes: item.claim_draft_minutes,
      claimReviewMinutes: item.claim_review_minutes,
      pretensionEdits: item.pretension_edits,
      claimEdits: item.claim_edits,
      ragWarnings: item.rag_warnings,
      authorityWarnings: item.authority_warnings,
      authorityInvalids: item.authority_invalids,
      authorityChecksTotal: item.authority_checks_total,
      authority: {
        checksTotal: item.authority.checks_total,
        validCount: item.authority.valid_count,
        warningCount: item.authority.warning_count,
        invalidCount: item.authority.invalid_count,
        blockedActionsCount: item.authority.blocked_actions_count,
      },
      blockedActions: item.blocked_actions,
      feedbackItems: item.feedback_items,
      pretensionDraftDataStatus: item.pretension_draft_data_status,
    } satisfies PilotCaseMetrics;
  },
  async getPilotCaseTimeline(caseId: string) {
    const item = await request<{ case_id: number; timeline: Array<{ id: string; case_id: number; event_type: string; title: string; description: string; created_at: string; actor_user_id: number | null; actor_role: string | null; source: string; severity: string; related_entity_type: string; related_entity_id: string }> }>(`/pilot-metrics/cases/${caseId.replace(/\D/g, "")}/timeline`);
    return item.timeline.map((entry) => ({
      id: entry.id,
      caseId: normalizeCaseId(entry.case_id) ?? String(entry.case_id),
      eventType: entry.event_type,
      title: entry.title,
      description: entry.description,
      createdAt: entry.created_at,
      actorUserId: entry.actor_user_id ? String(entry.actor_user_id) : null,
      actorRole: entry.actor_role ?? null,
      source: entry.source,
      severity: entry.severity,
      relatedEntityType: entry.related_entity_type,
      relatedEntityId: entry.related_entity_id,
    })) satisfies PilotTimelineEvent[];
  },
  async getPilotReport(dateFrom?: string, dateTo?: string) {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const suffix = params.size ? `?${params.toString()}` : "";
    const item = await request<{ period: string; date_from: string | null; date_to: string | null; total_cases: number; case_statuses: Record<string, number>; feedback_total: number; feedback_by_severity_total: Record<string, number>; feedback_by_severity_unresolved: Record<string, number>; average_pretension_draft_minutes: number; average_pretension_draft_data_status: string; average_claim_draft_minutes: number | null; ai_rag_warnings: number; authority_warnings: number; authority_invalids: number; authority_checks_total: number; blocked_actions: number; exports_generated: number; exported_case_ids: number[]; unresolved_items: string[]; timeline_summary: Record<string, number>; recommendation: string }>(`/pilot-report${suffix}`);
    return {
      period: item.period,
      dateFrom: item.date_from,
      dateTo: item.date_to,
      totalCases: item.total_cases,
      caseStatuses: item.case_statuses,
      feedbackTotal: item.feedback_total,
      feedbackBySeverityTotal: item.feedback_by_severity_total,
      feedbackBySeverityUnresolved: item.feedback_by_severity_unresolved,
      averagePretensionDraftMinutes: item.average_pretension_draft_minutes,
      averagePretensionDraftDataStatus: item.average_pretension_draft_data_status,
      averageClaimDraftMinutes: item.average_claim_draft_minutes,
      aiRagWarnings: item.ai_rag_warnings,
      authorityWarnings: item.authority_warnings,
      authorityInvalids: item.authority_invalids,
      authorityChecksTotal: item.authority_checks_total,
      blockedActions: item.blocked_actions,
      exportsGenerated: item.exports_generated,
      exportedCaseIds: item.exported_case_ids.map((entry) => normalizeCaseId(entry) ?? String(entry)),
      unresolvedItems: item.unresolved_items,
      timelineSummary: item.timeline_summary,
      recommendation: item.recommendation,
    } satisfies PilotReport;
  },
  async listIntegrationLogs(integrationName?: string, operation?: string, status?: string) {
    const params = new URLSearchParams();
    if (integrationName) params.set("integration_name", integrationName);
    if (operation) params.set("operation", operation);
    if (status) params.set("status", status);
    const suffix = params.size ? `?${params.toString()}` : "";
    const items = await request<Array<{
      id: number;
      integration_name: string;
      provider: string;
      mode: string;
      operation: string;
      request_id: string;
      idempotency_key: string;
      status: string;
      http_status: number | null;
      started_at: string;
      finished_at: string | null;
      duration_ms: number | null;
      error_code: string;
      error_message: string;
      safe_request_metadata_json: string;
      safe_response_metadata_json: string;
      created_by_id: number | null;
      case_id: number | null;
      organization_id: number | null;
      created_at: string;
    }>>(`/integration-logs${suffix}`);
    return items.map((item) => ({
      id: String(item.id),
      integrationName: item.integration_name,
      provider: item.provider,
      mode: item.mode,
      operation: item.operation,
      requestId: item.request_id,
      idempotencyKey: item.idempotency_key,
      status: item.status,
      httpStatus: item.http_status,
      startedAt: item.started_at,
      finishedAt: item.finished_at,
      durationMs: item.duration_ms,
      errorCode: item.error_code,
      errorMessage: item.error_message,
      safeRequestMetadataJson: item.safe_request_metadata_json,
      safeResponseMetadataJson: item.safe_response_metadata_json,
      createdById: item.created_by_id ? String(item.created_by_id) : null,
      caseId: item.case_id ? String(item.case_id) : null,
      organizationId: item.organization_id ? String(item.organization_id) : null,
      createdAt: item.created_at,
    })) satisfies IntegrationRequestLog[];
  },
  async testFnsConnection(sandbox = false) {
    const item = await request<{ provider: string; mode: string; status: string; ok: boolean; detail: string; external_calls: boolean; sandbox?: boolean; credentials_present?: boolean }>(`/fns/test-connection${sandbox ? "?sandbox=true" : ""}`, { method: "POST" });
    return {
      provider: item.provider,
      mode: item.mode,
      status: item.status,
      ok: item.ok,
      detail: item.detail,
      externalCalls: item.external_calls,
      sandbox: item.sandbox ?? sandbox,
      credentialsPresent: item.credentials_present ?? false,
    } satisfies ProviderConnectionCheck;
  },
  async testRussianPostConnection(sandbox = false) {
    const item = await request<{ provider: string; mode: string; status: string; ok: boolean; detail: string; external_calls: boolean; sandbox?: boolean; credentials_present?: boolean }>(`/russian-post/test-connection${sandbox ? "?sandbox=true" : ""}`, { method: "POST" });
    return {
      provider: item.provider,
      mode: item.mode,
      status: item.status,
      ok: item.ok,
      detail: item.detail,
      externalCalls: item.external_calls,
      sandbox: item.sandbox ?? sandbox,
      credentialsPresent: item.credentials_present ?? false,
    } satisfies ProviderConnectionCheck;
  },
  async testCourtArbitrConnection(sandbox = false) {
    const item = await request<{ provider: string; mode: string; status: string; ok: boolean; detail: string; external_calls: boolean; sandbox?: boolean; credentials_present?: boolean }>(`/court-arbitr/test-connection${sandbox ? "?sandbox=true" : ""}`, { method: "POST" });
    return {
      provider: item.provider,
      mode: item.mode,
      status: item.status,
      ok: item.ok,
      detail: item.detail,
      externalCalls: item.external_calls,
      sandbox: item.sandbox ?? sandbox,
      credentialsPresent: item.credentials_present ?? false,
    } satisfies ProviderConnectionCheck;
  },
  async updateSetting(key: string, value: string, description: string) {
    const item = await request<{ key: string; value: string; description: string }>(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value, description }) });
    return { key: item.key, value: item.value, description: item.description } satisfies SettingItem;
  },
  async listOrganizations() {
    return (await request<Array<Parameters<typeof mapOrganization>[0]>>("/organizations")).map(mapOrganization);
  },
  async getOrganization(organizationId: string) {
    return mapOrganization(await request<Parameters<typeof mapOrganization>[0]>(`/organizations/${organizationId}`));
  },
  async listOrganizationSnapshots(organizationId: string) {
    const items = await request<Array<{ id: number; source: string; actual_at: string; raw_payload: string; created_at: string }>>(`/organizations/${organizationId}/snapshots`);
    return items.map((item) => ({ id: String(item.id), source: item.source, actualAt: item.actual_at, rawPayload: item.raw_payload, createdAt: item.created_at }) satisfies OrganizationSnapshot);
  },
  async listFnsLookupLogs(organizationId: string) {
    const items = await request<Array<{ id: number; organization_id: number | null; inn: string; provider_mode: string; source: string; review_status: string; request_payload: string; response_payload: string; created_at: string }>>(`/organizations/${organizationId}/lookup-logs`);
    return items.map((item) => ({ id: String(item.id), organizationId: item.organization_id ? String(item.organization_id) : null, inn: item.inn, providerMode: item.provider_mode, source: item.source, reviewStatus: item.review_status, requestPayload: item.request_payload, responsePayload: item.response_payload, createdAt: item.created_at }) satisfies FnsLookupLog);
  },
  async listEmployees(organizationId: string) {
    const items = await request<Array<{ id: number; organization_id: number; user_id: number | null; full_name: string; position: string; email: string; is_active: boolean; created_at: string }>>(`/organizations/${organizationId}/employees`);
    return items.map((item) => ({ id: String(item.id), organizationId: String(item.organization_id), userId: item.user_id ? String(item.user_id) : null, fullName: item.full_name, position: item.position, email: item.email, isActive: item.is_active, createdAt: item.created_at }) satisfies Employee);
  },
  async listSignatories(organizationId: string) {
    const items = await request<Array<{ id: number; organization_id: number; employee_id: number | null; signatory_type: string; full_name: string; authority_basis: string; is_active: boolean; created_at: string }>>(`/organizations/${organizationId}/signatories`);
    return items.map((item) => ({ id: String(item.id), organizationId: String(item.organization_id), employeeId: item.employee_id ? String(item.employee_id) : null, signatoryType: item.signatory_type, fullName: item.full_name, authorityBasis: item.authority_basis, isActive: item.is_active, createdAt: item.created_at }) satisfies Signatory);
  },
  async listSignatoryChecks(signatoryId: string) {
    const items = await request<Array<{ id: number; signatory_id: number; case_id: number | null; power_of_attorney_id: number | null; document_kind: string; required_scopes: string[]; result: string; reason: string; checked_at: string }>>(`/signatories/${signatoryId}/authority-checks`);
    return items.map((item) => ({ id: String(item.id), signatoryId: String(item.signatory_id), caseId: item.case_id ? String(item.case_id) : null, powerOfAttorneyId: item.power_of_attorney_id ? String(item.power_of_attorney_id) : null, documentKind: item.document_kind, requiredScopes: item.required_scopes, result: item.result, reason: item.reason, checkedAt: item.checked_at }) satisfies SignatoryAuthorityCheck);
  },
  async listPowersForEmployee(employeeId: string) {
    if (USE_MOCK) {
      return [...(mockPowersOfAttorney[employeeId] ?? mockPowersOfAttorney[`emp-${employeeId}`] ?? [])];
    }
    const items = await request<Array<{ id: number; organization_id: number; employee_id: number; user_id: number | null; number: string; issued_at: string; expires_at: string; file_path: string; status: string; authority_scope: string[]; revoked_at: string | null; created_at: string }>>(`/employees/${employeeId}/powers-of-attorney`);
    return items.map((item) => ({ id: String(item.id), organizationId: String(item.organization_id), employeeId: String(item.employee_id), userId: item.user_id ? String(item.user_id) : null, number: item.number, issuedAt: item.issued_at, expiresAt: item.expires_at, filePath: item.file_path, status: item.status, authorityScope: item.authority_scope, revokedAt: item.revoked_at, createdAt: item.created_at }) satisfies PowerOfAttorney);
  },
  async listAuthorityChecksByCase(caseId: string) {
    if (USE_MOCK) {
      const normalizedCaseId = caseId.startsWith("case-") ? caseId : `case-${caseId}`;
      return Object.values(mockAuthorityChecks)
        .flat()
        .filter((item) => item.caseId === normalizedCaseId)
        .map((item) => ({ ...item }));
    }
    return [];
  },
  async listPostalDispatches(caseId?: string) {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : "";
    const items = await request<Array<{ id: number; case_id: number; organization_id: number; dispatch_kind: string; provider_mode: string; recipient_name: string; recipient_address: string; status: string; tracking_number: string; external_dispatch_id: string; source: string; status_payload: string; created_by_id: number; created_at: string }>>(`/postal-dispatches${query}`);
    return items.map((item) => ({ id: String(item.id), caseId: String(item.case_id), organizationId: String(item.organization_id), dispatchKind: item.dispatch_kind, providerMode: item.provider_mode, recipientName: item.recipient_name, recipientAddress: item.recipient_address, status: item.status, trackingNumber: item.tracking_number, externalDispatchId: item.external_dispatch_id, source: item.source, statusPayload: item.status_payload, createdById: String(item.created_by_id), createdAt: item.created_at }) satisfies PostalDispatch);
  },
  async getClaimCopyProof(caseId: string) {
    const item = await request<{ case_id: number; has_claim_copy_proof: boolean; dispatch_ids: number[] }>(`/russian-post/cases/${caseId}/claim-copy-proof`);
    return { caseId: String(item.case_id), hasClaimCopyProof: item.has_claim_copy_proof, dispatchIds: item.dispatch_ids.map((id) => String(id)) } satisfies PostalProofCheck;
  },
  async listCourtImportJobs() {
    const items = await request<Array<{ id: number; organization_id: number; inn: string; date_from: string; date_to: string; participation_role: string; provider_mode: string; status: string; source: string; result_count: number; created_by_id: number; created_at: string }>>("/court-import/jobs");
    return items.map((item) => ({ id: String(item.id), organizationId: String(item.organization_id), inn: item.inn, dateFrom: item.date_from, dateTo: item.date_to, participationRole: item.participation_role, providerMode: item.provider_mode, status: item.status, source: item.source, resultCount: item.result_count, createdById: String(item.created_by_id), createdAt: item.created_at }) satisfies CourtImportJob);
  },
  async getCourtImportJob(jobId: string) {
    return (await this.listCourtImportJobs()).find((item) => item.id === jobId) ?? null;
  },
  async createCourtImportJob(payload: { organizationId: string; inn: string; dateFrom: string; dateTo: string; participationRole: string; providerMode?: string }) {
    const item = await request<{ id: number; organization_id: number; inn: string; date_from: string; date_to: string; participation_role: string; provider_mode: string; status: string; source: string; result_count: number; created_by_id: number; created_at: string }>("/court-import/jobs", { method: "POST", body: JSON.stringify({ organization_id: Number(payload.organizationId), inn: payload.inn, date_from: payload.dateFrom, date_to: payload.dateTo, participation_role: payload.participationRole, provider_mode: payload.providerMode ?? "MOCK_FOR_DEV" }) });
    return { id: String(item.id), organizationId: String(item.organization_id), inn: item.inn, dateFrom: item.date_from, dateTo: item.date_to, participationRole: item.participation_role, providerMode: item.provider_mode, status: item.status, source: item.source, resultCount: item.result_count, createdById: String(item.created_by_id), createdAt: item.created_at } satisfies CourtImportJob;
  },
  async listCourtImportCases(jobId: string) {
    const items = await request<Array<{ id: number; import_job_id: number; organization_id: number; external_case_uid: string; case_number: string; court_name: string; participant_role: string; claim_subject: string; case_date: string | null; linked_case_id: number | null; source: string; payload_hash: string; created_at: string; events: Array<{ id: number; event_date: string | null; event_type: string; description: string; created_at: string }>; snapshots: Array<{ id: number; source: string; snapshot_payload: string; snapshot_hash: string; created_at: string }> }>>(`/court-import/jobs/${jobId}/cases`);
    return items.map(mapExternalCourtCase);
  },
  async listExternalCourtCases() {
    const items = await request<Array<{ id: number; import_job_id: number; organization_id: number; external_case_uid: string; case_number: string; court_name: string; participant_role: string; claim_subject: string; case_date: string | null; linked_case_id: number | null; source: string; payload_hash: string; created_at: string; events: Array<{ id: number; event_date: string | null; event_type: string; description: string; created_at: string }>; snapshots: Array<{ id: number; source: string; snapshot_payload: string; snapshot_hash: string; created_at: string }> }>>("/external-court-cases");
    return items.map(mapExternalCourtCase);
  },
  async getExternalCourtCase(externalCaseId: string) {
    return mapExternalCourtCase(await request<{ id: number; import_job_id: number; organization_id: number; external_case_uid: string; case_number: string; court_name: string; participant_role: string; claim_subject: string; case_date: string | null; linked_case_id: number | null; source: string; payload_hash: string; created_at: string; events: Array<{ id: number; event_date: string | null; event_type: string; description: string; created_at: string }>; snapshots: Array<{ id: number; source: string; snapshot_payload: string; snapshot_hash: string; created_at: string }> }>(`/external-court-cases/${externalCaseId}`));
  },
  async prepareCourtSubmission(payload: { caseId: string; externalCourtCaseId?: string; note?: string }) {
    const item = await request<{ id: number; case_id: number; organization_id: number; external_court_case_id: number | null; status: string; package_path: string; created_by_id: number; note: string; created_at: string }>("/court-submission", { method: "POST", body: JSON.stringify({ case_id: Number(payload.caseId), external_court_case_id: payload.externalCourtCaseId ? Number(payload.externalCourtCaseId) : null, note: payload.note ?? "" }) });
    return { id: String(item.id), caseId: String(item.case_id), organizationId: String(item.organization_id), externalCourtCaseId: item.external_court_case_id ? String(item.external_court_case_id) : null, status: item.status, packagePath: item.package_path, createdById: String(item.created_by_id), note: item.note, createdAt: item.created_at } satisfies CourtSubmissionPackage;
  },
  logout() {
    clearToken();
  },
};
