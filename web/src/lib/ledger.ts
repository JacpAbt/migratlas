/**
 * The claim ledger as it arrives on the wire, plus the few decisions about how to read it.
 *
 * Deliberately in `.ts` rather than inside a component: this project has no `svelte-check`, because
 * that tool pins TypeScript at 6 and the repo is on 7. So `tsc --noEmit` is the only type gate, it
 * does not see `.svelte` markup, and anything worth type-checking has to live out here. Components
 * stay thin on purpose.
 *
 * Every number here was computed from the lake by `reports/findings.py`. Nothing in the frontend
 * recomputes or reformats a value -- a second copy of a number is a second thing that drifts, and
 * this one would drift in front of a reader.
 */

export type FindingDirection = "change" | "null" | "limit" | "neutral";

/** What the work did about one risk of bias. "considered" is deliberately not an option. */
export type BiasStatus = "addressed" | "bounded" | "open" | "not applicable";

/** One ROBITT domain (Boyd et al. 2022, Methods in Ecology and Evolution 13:1497). */
export interface BiasDomain {
  domain: string;
  status: BiasStatus;
  finding: string;
}

export interface Finding {
  key: string;
  claim: string;
  value: string;
  scope: string;
  caveat: string;
  method: string;
  realm: string;
  taxon_scope: string;
  evidence_type: string;
  bias: BiasDomain[];
  direction: FindingDirection;
  supporting: string[];
}

export interface Ledger {
  schema_version: number;
  findings: Finding[];
}

export const SUPPORTED_SCHEMA = 2;

export const REPOSITORY = "https://github.com/JacpAbt/migratlas/blob/main/";

/** The banner above a claim. Says in words what the left rule says in colour. */
export const DIRECTION_LABEL: Record<FindingDirection, string> = {
  change: "change detected",
  null: "no change detected",
  limit: "limit of this work",
  neutral: "finding",
};

/**
 * The instrument that stands where an illustration would.
 *
 * ADR 0007 decision 5: a creature appears only beside a claim that genuinely identifies a taxon.
 * The radar cannot separate birds from bats from insects, so drawing a swallow next to it would
 * contradict, in the most legible register the page has, what the words underneath say. What goes
 * there instead is the apparatus -- and the absence of an animal becomes the caveat made visible.
 *
 * Keyed by evidence type and realm together, because SURVEY_INDEX is a trawl at sea and a walked
 * route on land, and drawing a net over South Africa would be worse than drawing nothing.
 */
export type Instrument = "radar" | "trawl" | "route" | "grid";

export function instrumentFor(finding: Finding): Instrument {
  if (finding.evidence_type === "flux") return "radar";
  if (finding.evidence_type === "survey_index") {
    return finding.realm === "marine" ? "trawl" : "route";
  }
  return "grid";
}

/**
 * Whether this claim's taxa are identified well enough to draw one.
 *
 * Not used yet -- there are no plates in the repo. It is here because the rule belongs with the
 * data rather than in whichever component eventually renders a plate, and because writing it down
 * now is what stops a later "let's add some illustrations" pass from quietly ignoring it.
 */
export function taxonIsIdentified(finding: Finding): boolean {
  const scope = finding.taxon_scope.toLowerCase();
  return !(
    scope.includes("unattributed") ||
    scope.includes("biomass") ||
    scope === "all" ||
    scope === ""
  );
}

export async function loadLedger(base: string): Promise<Ledger> {
  const response = await fetch(`${base}findings.json`);
  if (!response.ok) throw new Error(`findings.json: ${response.status}`);
  const ledger = (await response.json()) as Ledger;
  if (ledger.schema_version !== SUPPORTED_SCHEMA) {
    // Refuse rather than guess. A schema change means a field moved, and rendering the old shape
    // against new data shows a confidently wrong number, which is the one failure this whole
    // project is arranged to prevent.
    throw new Error(
      `findings.json schema ${ledger.schema_version}, expected ${SUPPORTED_SCHEMA}`,
    );
  }
  return ledger;
}
