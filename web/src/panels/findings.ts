/**
 * The findings panel: what the research established, rather than what data went in.
 *
 * Rendered from `findings.json`, which the pipeline computes from the lake — so the numbers here
 * are the ones the analysis produced and cannot drift from it by being edited in place.
 *
 * Every finding shows its scope and its caveat, not behind a toggle. A number on a globe reads as
 * settled fact, and these are not: they hold for a stated region over a stated period, and one of
 * them is the project's own coverage bias.
 */

export type FindingDirection = "change" | "null" | "limit" | "neutral";

export interface Finding {
  key: string;
  claim: string;
  value: string;
  scope: string;
  caveat: string;
  method: string;
  direction: FindingDirection;
  supporting: string[];
}

interface FindingsDocument {
  schema_version: number;
  findings: Finding[];
}

const SUPPORTED_SCHEMA = 1;

const LABEL: Record<FindingDirection, string> = {
  change: "change detected",
  null: "no change detected",
  limit: "limit of this work",
  neutral: "finding",
};

const REPOSITORY = "https://github.com/JacpAbt/migratlas/blob/main/";

function element(tag: string, className?: string, text?: string): HTMLElement {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function card(finding: Finding): HTMLElement {
  const item = element("li", `finding finding--${finding.direction}`);
  item.append(element("p", "finding__label", LABEL[finding.direction] ?? LABEL.neutral));
  item.append(element("h3", "finding__claim", finding.claim));
  item.append(element("p", "finding__value", finding.value));

  const detail = element("dl", "finding__detail");
  for (const [term, description] of [
    ["Where and when", finding.scope],
    ["Caveat", finding.caveat],
  ]) {
    detail.append(element("dt", undefined, term));
    detail.append(element("dd", undefined, description));
  }
  item.append(detail);

  if (finding.supporting.length > 0) {
    const survived = element("ul", "finding__supporting");
    for (const line of finding.supporting) survived.append(element("li", undefined, line));
    item.append(element("p", "finding__supporting-label", "Survived"));
    item.append(survived);
  }

  // The method note is the pre-registration: it states what was predicted before the analysis
  // ran, which is the only thing that makes these readable as tests rather than as stories.
  const method = element("a", "finding__method", "Method and pre-registration") as HTMLAnchorElement;
  method.href = `${REPOSITORY}${finding.method}`;
  method.rel = "noopener";
  method.target = "_blank";
  item.append(method);
  return item;
}

/**
 * Load and render the findings. Resolves to the number rendered, so a caller can tell the
 * difference between "no findings" and "the fetch failed".
 */
export async function mountFindings(container: HTMLElement, base: string): Promise<number> {
  let document_: FindingsDocument;
  try {
    const response = await fetch(`${base}findings.json`);
    if (!response.ok) throw new Error(`findings.json: ${response.status}`);
    document_ = (await response.json()) as FindingsDocument;
  } catch (error) {
    // A missing findings file must not take the globe down with it: the layers are still worth
    // showing, so the panel says it is unavailable and the map carries on.
    container.append(element("p", "finding__error", "Findings are unavailable."));
    console.warn("could not load findings", error);
    return 0;
  }

  if (document_.schema_version !== SUPPORTED_SCHEMA) {
    // Refuse rather than guess: a schema change means a field moved, and rendering the old shape
    // against new data would show a confidently wrong number.
    container.append(
      element("p", "finding__error", "Findings were built by an incompatible pipeline version."),
    );
    console.warn(
      `findings.json schema ${document_.schema_version}, expected ${SUPPORTED_SCHEMA}`,
    );
    return 0;
  }

  const list = element("ul", "finding-list");
  for (const finding of document_.findings) list.append(card(finding));
  container.append(list);
  collapseOnNarrowScreens(container);
  return document_.findings.length;
}

/**
 * Start collapsed on a phone, where an open panel covers the globe entirely.
 *
 * Done here rather than in the markup because the markup has no way to ask how wide the viewport
 * is, and shipping it collapsed for everyone would hide the results on the desktop view where
 * they are the point.
 */
function collapseOnNarrowScreens(container: HTMLElement): void {
  const panel = container.closest("details");
  if (!panel) return;
  const narrow = window.matchMedia("(max-width: 48rem)");
  if (narrow.matches) panel.open = false;
}
