export const roles = ["initiator", "lawyer", "manager", "admin", "service_agent"] as const;
export type Role = (typeof roles)[number];

export type CaseStatus =
  | "NEW"
  | "DOCUMENTS_UPLOADED"
  | "EXTRACTION_IN_PROGRESS"
  | "FACTS_EXTRACTED"
  | "PRETENSION_DRAFT_READY"
  | "PRETENSION_REVIEW"
  | "PRETENSION_APPROVED"
  | "WAITING_PAYMENT"
  | "CLAIM_DRAFT_READY"
  | "LAWYER_REVIEW"
  | "RETURNED_FOR_REVISION"
  | "APPROVED_BY_LAWYER"
  | "COURT_PACKAGE_READY"
  | "EXPORTED"
  | "CLOSED"
  | "ERROR_MANUAL_REVIEW";

export type UserProfile = {
  id: string;
  email: string;
  fullName?: string;
  role: Role;
};

export type LoginInput = {
  email: string;
  password: string;
  role?: Role;
};

export type CaseSummary = {
  id: string;
  title: string;
  plaintiff: string;
  defendant: string;
  amount: string;
  status: CaseStatus;
  updatedAt: string;
  responsibleLawyer?: string;
};

export type CaseCreateInput = {
  title: string;
  plaintiff: string;
  defendant: string;
  amount: string;
  responsibleLawyerId?: string;
  description: string;
};

export type CaseDocument = {
  id: string;
  caseId: string;
  fileName: string;
  mimeType: string;
  sha256: string;
  extractedText: string;
  approved: boolean;
  createdAt: string;
  status: "uploaded" | "parsed" | "queued";
};

export type DocumentVersion = {
  id: string;
  documentId: string;
  version: number;
  storagePath: string;
  sha256: string;
  extractedText: string;
  createdAt: string;
};

export type CaseFact = {
  id: string;
  title: string;
  value: string;
  confidence: number;
  source: string;
};

export type DraftDocument = {
  id: string;
  caseId: string;
  content: string;
  approved: boolean;
  updatedAt: string;
};

export type RagSource = {
  id: string;
  caseId?: string | null;
  title: string;
  sourceType: string;
  category: string;
  jurisdiction: string;
  fragment: string;
  page?: number | null;
  section: string;
  score: number;
  documentDate: string;
  path: string;
  createdAt: string;
};

export type RagCitation = {
  id: string;
  sourceId: string;
  caseId?: string | null;
  targetType: string;
  targetId?: string | null;
  quote: string;
  createdAt: string;
};

export type ChecklistItem = {
  id: string;
  title: string;
  isCompleted: boolean;
  notes: string;
};

export type Checklist = {
  id: string;
  caseId: string;
  status: string;
  items: ChecklistItem[];
};

export type AuditEntry = {
  id: string;
  actorUserId?: string | null;
  action: string;
  entityType: string;
  entityId: string;
  details: string;
  requestId: string;
  createdAt: string;
};

export type SettingItem = {
  key: string;
  value: string;
  description: string;
};

export type ProviderConnectionCheck = {
  provider: string;
  mode: string;
  status: string;
  ok: boolean;
  detail: string;
  externalCalls: boolean;
  sandbox?: boolean;
  credentialsPresent?: boolean;
};

export type IntegrationRequestLog = {
  id: string;
  integrationName: string;
  provider: string;
  mode: string;
  operation: string;
  requestId: string;
  idempotencyKey: string;
  status: string;
  httpStatus?: number | null;
  startedAt: string;
  finishedAt?: string | null;
  durationMs?: number | null;
  errorCode: string;
  errorMessage: string;
  safeRequestMetadataJson: string;
  safeResponseMetadataJson: string;
  createdById?: string | null;
  caseId?: string | null;
  organizationId?: string | null;
  createdAt: string;
};

export type SystemStatus = {
  backend: string;
  database: string;
  storage: string;
  redis: string;
  worker: string;
  vectorDb: string;
  llm: string;
  fnsProvider: string;
  fnsMode: string;
  fnsSandboxEnabled: boolean;
  realFnsEnabled: boolean;
  russianPostProvider: string;
  russianPostMode: string;
  russianPostSandboxEnabled: boolean;
  realPostSendEnabled: boolean;
  courtArbitrProvider: string;
  courtArbitrMode: string;
  courtSandboxEnabled: boolean;
  realCourtSearchEnabled: boolean;
  publicKadSearchEnabled: boolean;
  courtSubmissionEnabled: boolean;
};

export type SandboxReadinessItem = {
  sandboxFlag: boolean;
  credentialsPresent: boolean;
  testConnectionStatus: string;
  readyForSandbox: boolean;
  blockingReasons: string[];
  mode: string;
  provider: string;
  approvalStatus: string;
  activeApproval?: boolean;
  approvalExpiresAt?: string | null;
};

export type SandboxReadiness = {
  fns: SandboxReadinessItem;
  russianPost: SandboxReadinessItem;
  court: SandboxReadinessItem;
};

export type IntegrationCredentialsStatusItem = {
  sandboxCredentialsPresent: boolean;
  productionCredentialsPresent: boolean;
};

export type IntegrationCredentialsStatus = {
  fns: IntegrationCredentialsStatusItem;
  russianPost: IntegrationCredentialsStatusItem;
  courtArbitr: IntegrationCredentialsStatusItem;
};

export type IntegrationApproval = {
  id: string;
  integrationName: "FNS" | "RUSSIAN_POST" | "COURT_ARBITR";
  environment: "SANDBOX" | "PRODUCTION";
  requestedById?: string | null;
  approvedById?: string | null;
  status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPIRED" | "REVOKED";
  reason: string;
  approvedAt?: string | null;
  expiresAt?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type DashboardModel = {
  userRole: string;
  totalCases: number;
};

export type Organization = {
  id: string;
  inn: string;
  kpp: string;
  shortName: string;
  fullName: string;
  ogrn: string;
  legalAddress: string;
  currentDirectorName: string;
  currentDirectorPosition: string;
  reviewStatus: string;
  source: string;
  actualAt: string;
  createdAt: string;
  updatedAt: string;
};

export type OrganizationSnapshot = {
  id: string;
  source: string;
  actualAt: string;
  rawPayload: string;
  createdAt: string;
};

export type FnsLookupLog = {
  id: string;
  organizationId?: string | null;
  inn: string;
  providerMode: string;
  source: string;
  reviewStatus: string;
  requestPayload: string;
  responsePayload: string;
  createdAt: string;
};

export type Employee = {
  id: string;
  organizationId: string;
  userId?: string | null;
  fullName: string;
  position: string;
  email: string;
  isActive: boolean;
  createdAt: string;
};

export type Signatory = {
  id: string;
  organizationId: string;
  employeeId?: string | null;
  signatoryType: string;
  fullName: string;
  authorityBasis: string;
  isActive: boolean;
  createdAt: string;
};

export type PowerOfAttorney = {
  id: string;
  organizationId: string;
  employeeId: string;
  userId?: string | null;
  number: string;
  issuedAt: string;
  expiresAt: string;
  filePath: string;
  status: string;
  authorityScope: string[];
  revokedAt?: string | null;
  createdAt: string;
};

export type SignatoryAuthorityCheck = {
  id: string;
  signatoryId: string;
  caseId?: string | null;
  powerOfAttorneyId?: string | null;
  documentKind: string;
  requiredScopes: string[];
  result: string;
  reason: string;
  checkedAt: string;
};

export type AuthorityMetrics = {
  checksTotal: number;
  validCount: number;
  warningCount: number;
  invalidCount: number;
  blockedActionsCount: number;
};

export type PilotTimelineEvent = {
  id: string;
  caseId: string;
  eventType: string;
  title: string;
  description: string;
  createdAt: string;
  actorUserId?: string | null;
  actorRole?: string | null;
  source: string;
  severity: string;
  relatedEntityType: string;
  relatedEntityId: string;
};

export type PostalDispatch = {
  id: string;
  caseId: string;
  organizationId: string;
  dispatchKind: string;
  providerMode: string;
  recipientName: string;
  recipientAddress: string;
  status: string;
  trackingNumber: string;
  externalDispatchId: string;
  source: string;
  statusPayload: string;
  createdById: string;
  createdAt: string;
};

export type PostalProofCheck = {
  caseId: string;
  hasClaimCopyProof: boolean;
  dispatchIds: string[];
};

export type CourtImportJob = {
  id: string;
  organizationId: string;
  inn: string;
  dateFrom: string;
  dateTo: string;
  participationRole: string;
  providerMode: string;
  status: string;
  source: string;
  resultCount: number;
  createdById: string;
  createdAt: string;
};

export type CourtCaseEvent = {
  id: string;
  eventDate?: string | null;
  eventType: string;
  description: string;
  createdAt: string;
};

export type CourtCaseSnapshot = {
  id: string;
  source: string;
  snapshotPayload: string;
  snapshotHash: string;
  createdAt: string;
};

export type ExternalCourtCase = {
  id: string;
  importJobId: string;
  organizationId: string;
  externalCaseUid: string;
  caseNumber: string;
  courtName: string;
  participantRole: string;
  claimSubject: string;
  caseDate?: string | null;
  linkedCaseId?: string | null;
  source: string;
  payloadHash: string;
  createdAt: string;
  events: CourtCaseEvent[];
  snapshots: CourtCaseSnapshot[];
};

export type CourtSubmissionPackage = {
  id: string;
  caseId: string;
  organizationId: string;
  externalCourtCaseId?: string | null;
  status: string;
  packagePath: string;
  createdById: string;
  note: string;
  createdAt: string;
};

export type PilotFeedback = {
  id: string;
  caseId?: string | null;
  userId: string;
  role: Role;
  module: string;
  severity: string;
  title: string;
  description: string;
  expectedBehavior: string;
  actualBehavior: string;
  screenshotDocumentId?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type PilotCaseMetrics = {
  caseId: string;
  title: string;
  status: string;
  factsReadyMinutes?: number | null;
  pretensionDraftMinutes?: number | null;
  pretensionReviewMinutes?: number | null;
  claimDraftMinutes?: number | null;
  claimReviewMinutes?: number | null;
  pretensionEdits: number;
  claimEdits: number;
  ragWarnings: number;
  authorityWarnings: number;
  authorityInvalids: number;
  authorityChecksTotal: number;
  authority: AuthorityMetrics;
  blockedActions: number;
  feedbackItems: number;
  pretensionDraftDataStatus: string;
};

export type PilotMetricsSummary = {
  totalCases: number;
  completedHappyPathCases: number;
  blockedCases: number;
  totalFeedbackItems: number;
  blockerFeedbackItems: number;
  highFeedbackItems: number;
  feedbackBySeverityTotal: Record<string, number>;
  feedbackBySeverityUnresolved: Record<string, number>;
  averagePretensionDraftMinutes: number;
  averagePretensionDraftDataStatus: string;
  averageClaimDraftMinutes?: number | null;
  totalRagWarnings: number;
  totalAuthorityWarnings: number;
  totalAuthorityInvalids: number;
  totalAuthorityChecks: number;
  totalBlockedActions: number;
  authority: AuthorityMetrics;
  authorityByCase: Array<AuthorityMetrics & { caseId: string; title: string }>;
  cases: PilotCaseMetrics[];
};

export type PilotReport = {
  period: string;
  dateFrom?: string | null;
  dateTo?: string | null;
  totalCases: number;
  caseStatuses: Record<string, number>;
  feedbackTotal: number;
  feedbackBySeverityTotal: Record<string, number>;
  feedbackBySeverityUnresolved: Record<string, number>;
  averagePretensionDraftMinutes: number;
  averagePretensionDraftDataStatus: string;
  averageClaimDraftMinutes?: number | null;
  aiRagWarnings: number;
  authorityWarnings: number;
  authorityInvalids: number;
  authorityChecksTotal: number;
  blockedActions: number;
  exportsGenerated: number;
  exportedCaseIds: string[];
  unresolvedItems: string[];
  timelineSummary: Record<string, number>;
  recommendation: string;
};

export type CaseDetailModel = CaseSummary & {
  description: string;
  documents: CaseDocument[];
  facts: CaseFact[];
  pretension?: DraftDocument | null;
  claim?: DraftDocument | null;
  checklist?: Checklist | null;
  citations?: RagCitation[];
};
