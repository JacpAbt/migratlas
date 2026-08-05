/**
 * What is known about one animal, fetched when a reader asks about that animal.
 *
 * Sharded 64 ways on the taxon key, the same scheme the surfaces already use, so choosing a species
 * costs one bounded request rather than a 2.2 MB document nobody reads all of. Cached per shard,
 * because searching around a genus hits the same file repeatedly.
 */

export type StudyKind = "shift" | "tracked" | "withheld" | "extent" | "occupancy";

export interface StudyRow {
  label: string;
  value: string;
  detail: string;
}

export interface Study {
  kind: StudyKind;
  headline: string;
  value: string;
  detail: string;
  caveat: string;
  method: string;
  source_id: string;
  taxon: string;
  rows: StudyRow[];
}

export interface SpeciesCard {
  taxon_key: number;
  scientific: string;
  vernacular: string;
  realm: string;
  /** Whether a surface exists on the globe. `false` is a fact about the data, not a gap. */
  drawn: boolean;
  studies: Study[];
}

interface StudyShard {
  schema_version: number;
  species: SpeciesCard[];
}

const SUPPORTED_SCHEMA = 1;
const SHARDS = 64;

/** What each kind is, said once, so no component invents its own wording for it. */
export const KIND_LABEL: Record<StudyKind, string> = {
  shift: "where it has moved",
  tracked: "where it has been followed",
  withheld: "held back",
  extent: "no study here",
  occupancy: "how much of the region it occupies",
};

export class SpeciesStudies {
  readonly #base: string;
  readonly #shards = new Map<number, Promise<Map<number, SpeciesCard>>>();

  constructor(base: string) {
    this.#base = base;
  }

  /**
   * The card for one taxon, or null if the build produced none.
   *
   * Null rather than a thrown error: a species with no card is a state the page has to render
   * anyway, and it is not distinguishable to a reader from a species whose card says there is no
   * study. A failed fetch is the same -- the globe still drew the animal, and losing the page
   * should cost the page rather than the selection.
   */
  async get(taxonKey: number): Promise<SpeciesCard | null> {
    const shard = taxonKey % SHARDS;
    let loading = this.#shards.get(shard);
    if (!loading) {
      loading = this.#load(shard);
      this.#shards.set(shard, loading);
    }
    return (await loading).get(taxonKey) ?? null;
  }

  async #load(shard: number): Promise<Map<number, SpeciesCard>> {
    const name = `species-study-${String(shard).padStart(2, "0")}.json`;
    try {
      const response = await fetch(`${this.#base}${name}`);
      if (!response.ok) throw new Error(`${name}: ${response.status}`);
      const document_ = (await response.json()) as StudyShard;
      if (document_.schema_version !== SUPPORTED_SCHEMA) {
        // Refuse rather than guess, the same rule the ledger keeps: rendering an old shape against
        // new data shows a confidently wrong number.
        throw new Error(`${name} schema ${document_.schema_version}`);
      }
      return new Map(document_.species.map((card) => [card.taxon_key, card]));
    } catch {
      return new Map();
    }
  }
}
