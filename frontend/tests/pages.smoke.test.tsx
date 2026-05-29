import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let mockRole: "admin" | "lawyer" | "manager" | "initiator" | "service_agent" = "admin";
let mockParams: Record<string, string> = { id: "1", job_id: "job-1" };

vi.mock("next/navigation", () => ({
  useParams: () => mockParams,
  usePathname: () => "/",
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("C:/Users/User/Desktop/AI_legal2/frontend/components/providers.tsx", () => ({
  useAuth: () => ({ user: { id: "1", email: "tester@example.com", role: mockRole }, loading: false }),
  canRole: (_user: unknown, allowed: string[]) => allowed.includes(mockRole),
  AuthGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  ShellNav: () => <div data-testid="shell-nav">nav</div>,
  RoleGuard: ({ allowed, children, fallback }: { allowed: string[]; children: React.ReactNode; fallback?: React.ReactNode }) =>
    allowed.includes(mockRole) ? <>{children}</> : <>{fallback ?? <div>forbidden</div>}</>,
}));

vi.mock("C:/Users/User/Desktop/AI_legal2/frontend/lib/api-client.ts", () => ({
  apiClient: {
    listOrganizations: vi.fn(async () => [{ id: "1", inn: "7701", kpp: "7701", shortName: "Test Org", fullName: "Test Org", ogrn: "ogrn", legalAddress: "addr", currentDirectorName: "Dir", currentDirectorPosition: "CEO", reviewStatus: "VERIFIED", source: "MOCK", actualAt: "2026-05-29", createdAt: "2026-05-29", updatedAt: "2026-05-29" }]),
    getOrganization: vi.fn(async () => ({ id: "1", inn: "7701", kpp: "7701", shortName: "Test Org", fullName: "Test Org", ogrn: "ogrn", legalAddress: "addr", currentDirectorName: "Dir", currentDirectorPosition: "CEO", reviewStatus: "VERIFIED", source: "MOCK", actualAt: "2026-05-29", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    listOrganizationSnapshots: vi.fn(async () => []),
    listFnsLookupLogs: vi.fn(async () => []),
    listEmployees: vi.fn(async () => [{ id: "10", organizationId: "1", fullName: "Employee A", position: "Lawyer", email: "a@example.com", isActive: true, createdAt: "2026-05-29", userId: null }]),
    listSignatories: vi.fn(async () => [{ id: "20", organizationId: "1", employeeId: "10", signatoryType: "AUTHORIZED_EMPLOYEE", fullName: "Employee A", authorityBasis: "POWER_OF_ATTORNEY", isActive: true, createdAt: "2026-05-29" }]),
    listSignatoryChecks: vi.fn(async () => []),
    listPowersForEmployee: vi.fn(async () => [{ id: "30", organizationId: "1", employeeId: "10", userId: null, number: "POA-1", issuedAt: "2026-05-01", expiresAt: "2026-12-31", filePath: "/tmp/poa.pdf", status: "ACTIVE", authorityScope: ["SIGN_CLAIM"], revokedAt: null, createdAt: "2026-05-29" }]),
    listPostalDispatches: vi.fn(async () => [{ id: "40", caseId: "1", organizationId: "1", dispatchKind: "claim_copy", providerMode: "MOCK_FOR_DEV", recipientName: "Respondent", recipientAddress: "Address", status: "DELIVERED", trackingNumber: "TRK1", externalDispatchId: "EXT1", source: "MOCK", statusPayload: "{}", createdById: "2", createdAt: "2026-05-29" }]),
    listExternalCourtCases: vi.fn(async () => [{ id: "50", importJobId: "job-1", organizationId: "1", externalCaseUid: "UID1", caseNumber: "A40-1/2026", courtName: "АС", participantRole: "claimant", claimSubject: "Debt", caseDate: "2026-05-01", linkedCaseId: "1", source: "MOCK", payloadHash: "hash", createdAt: "2026-05-29", events: [], snapshots: [] }]),
    listCourtImportJobs: vi.fn(async () => [{ id: "job-1", organizationId: "1", inn: "7701", dateFrom: "2026-05-01", dateTo: "2026-05-31", participationRole: "claimant", providerMode: "MOCK_FOR_DEV", status: "COMPLETED", source: "MOCK", resultCount: 1, createdById: "1", createdAt: "2026-05-29" }]),
    createCourtImportJob: vi.fn(async () => ({ id: "job-2", organizationId: "1", inn: "7701", dateFrom: "2026-05-01", dateTo: "2026-05-31", participationRole: "claimant", providerMode: "MOCK_FOR_DEV", status: "COMPLETED", source: "MOCK", resultCount: 1, createdById: "1", createdAt: "2026-05-29" })),
    getCourtImportJob: vi.fn(async () => ({ id: "job-1", organizationId: "1", inn: "7701", dateFrom: "2026-05-01", dateTo: "2026-05-31", participationRole: "claimant", providerMode: "MOCK_FOR_DEV", status: "COMPLETED", source: "MOCK", resultCount: 1, createdById: "1", createdAt: "2026-05-29" })),
    listCourtImportCases: vi.fn(async () => [{ id: "50", importJobId: "job-1", organizationId: "1", externalCaseUid: "UID1", caseNumber: "A40-1/2026", courtName: "АС", participantRole: "claimant", claimSubject: "Debt", caseDate: "2026-05-01", linkedCaseId: "1", source: "MOCK", payloadHash: "hash", createdAt: "2026-05-29", events: [], snapshots: [] }]),
    getExternalCourtCase: vi.fn(async () => ({ id: "50", importJobId: "job-1", organizationId: "1", externalCaseUid: "UID1", caseNumber: "A40-1/2026", courtName: "АС", participantRole: "claimant", claimSubject: "Debt", caseDate: "2026-05-01", linkedCaseId: "1", source: "MOCK", payloadHash: "hash", createdAt: "2026-05-29", events: [], snapshots: [] })),
    listSettings: vi.fn(async () => [{ key: "RUSSIAN_POST_MODE", value: "MOCK_FOR_DEV", description: "mode" }, { key: "FNS_PROVIDER_MODE", value: "MOCK_FOR_DEV", description: "mode" }]),
    getSystemStatus: vi.fn(async () => ({ backend: "ok", database: "ok", storage: "ok", redis: "ok", worker: "ok", vectorDb: "ok", llm: "mock", fnsProvider: "mock_fns_adapter", fnsMode: "MOCK_FOR_DEV", fnsSandboxEnabled: false, realFnsEnabled: false, russianPostProvider: "mock_russian_post_adapter", russianPostMode: "MOCK_FOR_DEV", russianPostSandboxEnabled: false, realPostSendEnabled: false, courtArbitrProvider: "mock_court_arbitr_adapter", courtArbitrMode: "MOCK_FOR_DEV", courtSandboxEnabled: false, realCourtSearchEnabled: false, publicKadSearchEnabled: false, courtSubmissionEnabled: false })),
    getSandboxReadiness: vi.fn(async () => ({ fns: { sandboxFlag: false, credentialsPresent: false, testConnectionStatus: "disabled", readyForSandbox: false, blockingReasons: ["sandbox_flag_disabled"], mode: "FNS_SANDBOX_DISABLED", provider: "sandbox_fns_adapter", approvalStatus: "REQUESTED" }, russianPost: { sandboxFlag: false, credentialsPresent: false, testConnectionStatus: "disabled", readyForSandbox: false, blockingReasons: ["sandbox_flag_disabled"], mode: "RUSSIAN_POST_SANDBOX_DISABLED", provider: "sandbox_russian_post_adapter", approvalStatus: "REQUESTED" }, court: { sandboxFlag: false, credentialsPresent: false, testConnectionStatus: "disabled", readyForSandbox: false, blockingReasons: ["sandbox_flag_disabled"], mode: "COURT_SANDBOX_DISABLED", provider: "sandbox_court_arbitr_adapter", approvalStatus: "REQUESTED" } })),
    getIntegrationCredentialsStatus: vi.fn(async () => ({ fns: { sandboxCredentialsPresent: false, productionCredentialsPresent: false }, russianPost: { sandboxCredentialsPresent: false, productionCredentialsPresent: false }, courtArbitr: { sandboxCredentialsPresent: false, productionCredentialsPresent: false } })),
    listIntegrationApprovals: vi.fn(async () => [{ id: "1", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: null, status: "REQUESTED", reason: "Sandbox request", approvedAt: null, expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" }]),
    listActiveIntegrationApprovals: vi.fn(async () => []),
    getIntegrationApproval: vi.fn(async () => ({ id: "1", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: null, status: "REQUESTED", reason: "Sandbox request", approvedAt: null, expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    createIntegrationApproval: vi.fn(async () => ({ id: "2", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: null, status: "REQUESTED", reason: "Sandbox request", approvedAt: null, expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    approveIntegrationApproval: vi.fn(async () => ({ id: "1", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: "1", status: "APPROVED", reason: "Approved", approvedAt: "2026-05-29", expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    rejectIntegrationApproval: vi.fn(async () => ({ id: "1", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: "1", status: "REJECTED", reason: "Rejected", approvedAt: null, expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    revokeIntegrationApproval: vi.fn(async () => ({ id: "1", integrationName: "FNS", environment: "SANDBOX", requestedById: "1", approvedById: "1", status: "REVOKED", reason: "Revoked", approvedAt: "2026-05-29", expiresAt: "2026-06-30T12:00:00Z", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    listIntegrationLogs: vi.fn(async () => []),
    listPilotFeedback: vi.fn(async () => [{ id: "feedback-1", caseId: "1", userId: "2", role: "lawyer", module: "AUTHORITY", severity: "MEDIUM", title: "Authority issue", description: "desc", expectedBehavior: "expected", actualBehavior: "actual", screenshotDocumentId: null, status: "NEW", createdAt: "2026-05-29", updatedAt: "2026-05-29" }]),
    createPilotFeedback: vi.fn(async () => ({ id: "feedback-2", caseId: "1", userId: "2", role: "lawyer", module: "UI", severity: "LOW", title: "Saved", description: "desc", expectedBehavior: "expected", actualBehavior: "actual", screenshotDocumentId: null, status: "NEW", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    updatePilotFeedback: vi.fn(async () => ({ id: "feedback-1", caseId: "1", userId: "2", role: "lawyer", module: "AUTHORITY", severity: "MEDIUM", title: "Authority issue", description: "desc", expectedBehavior: "expected", actualBehavior: "actual", screenshotDocumentId: null, status: "FIXED", createdAt: "2026-05-29", updatedAt: "2026-05-29" })),
    getPilotMetricsSummary: vi.fn(async () => ({ totalCases: 3, completedHappyPathCases: 2, blockedCases: 1, totalFeedbackItems: 1, blockerFeedbackItems: 0, highFeedbackItems: 0, feedbackBySeverityTotal: { BLOCKER: 1, MEDIUM: 1 }, feedbackBySeverityUnresolved: { BLOCKER: 0, MEDIUM: 1 }, averagePretensionDraftMinutes: 10, averagePretensionDraftDataStatus: "ok", averageClaimDraftMinutes: 15, totalRagWarnings: 1, totalAuthorityWarnings: 0, totalAuthorityInvalids: 1, totalAuthorityChecks: 3, totalBlockedActions: 1, authority: { checksTotal: 3, validCount: 2, warningCount: 0, invalidCount: 1, blockedActionsCount: 1 }, authorityByCase: [{ caseId: "case-1003", title: "Authority blocked", checksTotal: 1, validCount: 0, warningCount: 0, invalidCount: 1, blockedActionsCount: 1 }], cases: [{ caseId: "case-1001", title: "Case", status: "COURT_PACKAGE_READY", factsReadyMinutes: 5, pretensionDraftMinutes: 10, pretensionReviewMinutes: 12, claimDraftMinutes: 15, claimReviewMinutes: 9, pretensionEdits: 1, claimEdits: 1, ragWarnings: 0, authorityWarnings: 0, authorityInvalids: 0, authorityChecksTotal: 1, authority: { checksTotal: 1, validCount: 1, warningCount: 0, invalidCount: 0, blockedActionsCount: 0 }, blockedActions: 0, feedbackItems: 0, pretensionDraftDataStatus: "ok" }] })),
    getPilotCaseTimeline: vi.fn(async () => [{ id: "timeline-1", caseId: "case-1001", eventType: "CASE_CREATED", title: "Case created", description: "Case", createdAt: "2026-05-29T10:00:00Z", actorUserId: "1", actorRole: "initiator", source: "case", severity: "info", relatedEntityType: "case", relatedEntityId: "1" }]),
    getPilotReport: vi.fn(async () => ({ period: "internal pilot", dateFrom: "2026-05-01", dateTo: "2026-05-31", totalCases: 3, caseStatuses: { COURT_PACKAGE_READY: 2 }, feedbackTotal: 1, feedbackBySeverityTotal: { BLOCKER: 1, MEDIUM: 1 }, feedbackBySeverityUnresolved: { BLOCKER: 0, MEDIUM: 1 }, averagePretensionDraftMinutes: 10, averagePretensionDraftDataStatus: "ok", averageClaimDraftMinutes: 15, aiRagWarnings: 1, authorityWarnings: 0, authorityInvalids: 1, authorityChecksTotal: 3, blockedActions: 1, exportsGenerated: 2, exportedCaseIds: ["case-1001", "case-1004"], unresolvedItems: [], timelineSummary: { CASE_CREATED: 3, CLAIM_APPROVED: 2 }, recommendation: "go" })),
    testFnsConnection: vi.fn(async () => ({ provider: "fns", mode: "MOCK_FOR_DEV", status: "SUCCESS", ok: true, detail: "ok", externalCalls: false })),
    testRussianPostConnection: vi.fn(async () => ({ provider: "russian_post", mode: "MOCK_FOR_DEV", status: "SUCCESS", ok: true, detail: "ok", externalCalls: false })),
    testCourtArbitrConnection: vi.fn(async () => ({ provider: "court_arbitr", mode: "MOCK_FOR_DEV", status: "SUCCESS", ok: true, detail: "ok", externalCalls: false })),
    getCase: vi.fn(async () => ({ id: "1", title: "Case", plaintiff: "A", defendant: "B", amount: "100", status: "NEW", updatedAt: "2026-05-29", description: "desc", documents: [], facts: [], checklist: null, pretension: null, claim: null, citations: [] })),
    prepareCourtSubmission: vi.fn(async () => ({ id: "pkg-1", caseId: "1", organizationId: "1", status: "READY_FOR_MANUAL_SUBMISSION", packagePath: "/tmp/pkg.txt", createdById: "1", note: "", createdAt: "2026-05-29", externalCourtCaseId: null })),
  },
}));

describe("frontend sprint smoke pages", () => {
  beforeEach(() => {
    mockRole = "admin";
    mockParams = { id: "1", job_id: "job-1" };
  });

  it("organizations page renders", async () => {
    const { default: Page } = await import("../app/organizations/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText("Test Org")).toBeInTheDocument());
  });

  it("case postal page renders", async () => {
    const { default: Page } = await import("../app/cases/[id]/postal-dispatches/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText("claim_copy")).toBeInTheDocument());
  });

  it("court import page renders", async () => {
    const { default: Page } = await import("../app/court-import/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText(/Job #job-1/)).toBeInTheDocument());
  });

  it("admin settings page role-gated for admin", async () => {
    const { default: Page } = await import("../app/settings/russian-post/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText(/Integration status/i)).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: /Sandbox readiness/i })).toBeInTheDocument();
  });

  it("fns settings page renders", async () => {
    const { default: Page } = await import("../app/settings/fns/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText(/Integration status/i)).toBeInTheDocument());
  });

  it("non-admin cannot access integration settings", async () => {
    mockRole = "manager";
    const { default: Page } = await import("../app/settings/russian-post/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByText(/admin only/i)).toBeInTheDocument());
  });

  it("system status page renders", async () => {
    const { default: Page } = await import("../app/system/status/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("system-status-loaded")).toBeInTheDocument());
    expect(screen.getByText(/fns_sandbox_enabled/i)).toBeInTheDocument();
  });

  it("pilot feedback page renders", async () => {
    const { default: Page } = await import("../app/pilot-feedback/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("pilot-feedback-list")).toBeInTheDocument());
  });

  it("pilot metrics page renders", async () => {
    const { default: Page } = await import("../app/pilot-metrics/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("pilot-metrics-page")).toBeInTheDocument());
  });

  it("case timeline page renders", async () => {
    mockParams = { id: "1", job_id: "job-1" };
    const { default: Page } = await import("../app/cases/[id]/timeline/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("case-timeline-page")).toBeInTheDocument());
  });

  it("integration approvals page renders", async () => {
    const { default: Page } = await import("../app/settings/integrations/approvals/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("integration-approvals-page")).toBeInTheDocument());
  });

  it("integration approval detail page renders", async () => {
    mockParams = { id: "1", job_id: "job-1" };
    const { default: Page } = await import("../app/settings/integrations/approvals/[id]/page");
    render(<Page />);
    await waitFor(() => expect(screen.getByTestId("integration-approval-detail-page")).toBeInTheDocument());
  });
});
