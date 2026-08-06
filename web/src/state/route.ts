/**
 * Which claim is open, in the URL.
 *
 * A finding you cannot link to is a finding nobody cites. Until now the only thing in the address
 * bar was the clock, so every one of these five results lived at the same address and the only way
 * to send someone a specific one was to describe where to click.
 *
 * Shares the hash with `state/time.ts` rather than owning it: both read the existing parameters
 * before writing, so the clock and the claim survive each other. They differ in one deliberate way
 * -- the clock uses `replaceState`, because animating it would otherwise push hundreds of entries
 * and trap the back button, while a claim uses `pushState`, because going back to the last claim
 * you read is exactly what a reader means by back.
 */

const CLAIM = "c";

/** The claim named in the URL, or null for none. Never validated here -- the ledger decides. */
export function readClaim(): string | null {
  return new URLSearchParams(location.hash.slice(1)).get(CLAIM);
}

/**
 * Put a claim in the URL, or take it out.
 *
 * Does nothing when the value is already there, which matters more than it looks: the shell sets
 * the claim from its own state, so without this an effect that re-runs for an unrelated reason
 * would push a duplicate entry and cost one press of the back button each time.
 */
export function writeClaim(key: string | null): void {
  if (readClaim() === key) return;
  const params = new URLSearchParams(location.hash.slice(1));
  if (key) {
    params.set(CLAIM, key);
  } else {
    params.delete(CLAIM);
  }
  const hash = params.toString();
  history.pushState(null, "", hash ? `#${hash}` : location.pathname + location.search);
}

/** Call `whenever` on back and forward. Returns its own teardown. */
export function watchHistory(whenever: () => void): () => void {
  addEventListener("popstate", whenever);
  return () => removeEventListener("popstate", whenever);
}
