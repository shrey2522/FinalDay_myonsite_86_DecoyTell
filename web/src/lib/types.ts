export type Verdict = "PASS" | "CORRECTED" | "UNSAFE" | "INSUFFICIENT_DATA" | "UNREACHABLE"

export interface AttributeResult {
  name: string
  kind: "numeric" | "categorical"
  decoy_value: number | string
  in_tolerance: boolean | null
  band?: [number, number]
  count?: number
  window_size?: number
  unit?: string
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

export interface ScenarioReport {
  scenario_id: string
  note: string
  verdict: Verdict
  expected_verdict?: Verdict
  window_size: number
  attributes: AttributeResult[]
  pairs: PairFinding[]
  corrections: Fix[]
  blocked_attributes: string[]
  final?: { attributes: AttributeResult[]; pairs: PairFinding[] }
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

export interface Status {
  scenarios: { id: string; verdict: Verdict; expected?: Verdict }[]
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