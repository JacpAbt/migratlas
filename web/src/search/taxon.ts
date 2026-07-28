/**
 * Species search against a prebuilt static index.
 *
 * No backend and no request per keystroke: the index is generated from the GBIF
 * Backbone at build time and searched in memory. Keys are GBIF usage keys, so the
 * frontend and the pipeline agree on what a species is.
 */

export interface TaxonEntry {
  key: number;
  scientific: string;
  vernacular: string;
  group: string;
  realm: string;
}

export interface TaxonHit extends TaxonEntry {
  score: number;
}

export class TaxonIndex {
  #entries: TaxonEntry[] = [];
  #haystack: string[] = [];

  static async load(url: string): Promise<TaxonIndex> {
    const index = new TaxonIndex();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`taxon index ${response.status}`);
    index.#entries = (await response.json()) as TaxonEntry[];
    index.#haystack = index.#entries.map((e) =>
      `${e.scientific} ${e.vernacular} ${e.group}`.toLowerCase(),
    );
    return index;
  }

  get size(): number {
    return this.#entries.length;
  }

  search(query: string, limit = 8): TaxonHit[] {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2) return [];

    const hits: TaxonHit[] = [];
    for (const [i, hay] of this.#haystack.entries()) {
      const entry = this.#entries[i];
      if (!entry) continue;
      const score = rank(hay, needle);
      if (score > 0) hits.push({ ...entry, score });
    }
    // Ties broken by vernacular name so results do not reshuffle between keystrokes.
    hits.sort((a, b) => b.score - a.score || a.vernacular.localeCompare(b.vernacular));
    return hits.slice(0, limit);
  }
}

function rank(haystack: string, needle: string): number {
  const at = haystack.indexOf(needle);
  if (at < 0) return 0;
  if (at === 0) return 3;
  // A match at a word boundary is what someone typing "grey whale" means; a match
  // mid-word usually is not.
  return haystack[at - 1] === " " ? 2 : 1;
}
