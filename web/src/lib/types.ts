export type Verdict =
  | "PASS"
  | "CORRECTED"
  | "CORRECTED_PARTIAL"
  | "UNSAFE"
  | "INSUFFICIENT_DATA"
  | "STALE_DATA"
  | "MIRRORING_REQUIRED"
  | "UNREACHABLE"

export interface Thresholds {
  recent_window_days: number
  min_window_observations: number
  numeric_lower_percentile: number
  numeric_upper_percentile: number
  categorical_min_count: number
  categorical_min_share?: number
  joint_expected_min: number
  joint_under_ratio?: number
  correction_budget: number
  stale_window_max_days?: number
}

export interface AttributeResult {
  name: string
  kind: "numeric" | "categorical"
  decoy_value: number | string
  in_tolerance: boolean | null
  band?: [number, number]
  count?: number
  window_size?: number
  unit?: string
  no_window?: boolean
}

export interface PairFinding {
  attr_a: string
  attr_b: string
  value_a: number | string
  value_b: number | string
  observed: number
  expected: number
  fingerprint: boolean
}

export interface Fix {
  attribute: string
  before: number | string
  after: number | string
  action: string
  re_verified?: boolean
  applied?: boolean
  reason?: string
}

export interface AnalysisSummary {
  window_size: number
  attributes: AttributeResult[]
  pairs: PairFinding[]
}

export interface ScenarioReport {
  scenario_id: string
  note: string
  seed: number
  schema_version: string
  verdict: Verdict
  expected_verdict?: Verdict
  thresholds: Thresholds
  history_size: number
  window_size: number
  attributes: AttributeResult[]
  pairs: PairFinding[]
  corrections: Fix[]
  blocked_attributes: string[]
  final?: AnalysisSummary
}

export interface LoopEvent {
  id: number
  cycle: number
  timestamp: string
  verdict: Verdict
  recheck: Verdict
  fixes: Fix[]
  real_obs: Record<string, unknown>
  decoy_obs: Record<string, unknown>
}

export interface ScenarioSummary {
  id: string
  verdict: Verdict
  expected?: Verdict
}

export interface Status {
  scenarios: ScenarioSummary[]
  loop: { running: boolean; latest_event: LoopEvent | null }
}

export interface ObservationRow {
  days_ago: number
  service_banner: string
  patch_cadence_days: number
  timing_band: string
  account_age_days: number
  monitoring_behavior: string
}

export interface ObservationsResponse {
  target: string
  days: number
  count: number
  observations: ObservationRow[]
}

export interface ReconCandidate {
  name: string
  banner_visible: boolean
  patch_age_days: number | null
  reachable: boolean
  has_auth: boolean
  subdomain_style: string
  is_decoy: boolean
}

export interface RankedCandidate {
  candidate: ReconCandidate
  score: number
  reasons: string[]
}

export interface ReconResult {
  phases: string[]
  exit_code: number
  verdict?: Verdict
  result_text?: string
  selected: ReconCandidate | null
  ranked: RankedCandidate[]
  observation: Record<string, unknown> | null
  corrections: Fix[]
  analysis: {
    window_size: number
    insufficient?: boolean
    attributes: AttributeResult[]
    pairs: PairFinding[]
  } | null
}

export const ATTRIBUTE_LABELS: Record<string, string> = {
  service_banner: "Service banner",
  patch_cadence_days: "Patch cadence",
  timing_band: "Timing band",
  account_age_days: "Account age",
  monitoring_behavior: "Monitoring behavior",
}

export const ATTRIBUTE_DESCRIPTIONS: Record<string, string> = {
  service_banner: "server header/banner",
  patch_cadence_days: "days between security patches",
  timing_band: "response latency band",
  account_age_days: "cert / account-age metadata",
  monitoring_behavior: "scan-response profile",
}

export const OBSERVABLE_KEYS = [
  "service_banner",
  "patch_cadence_days",
  "timing_band",
  "account_age_days",
  "monitoring_behavior",
] as const