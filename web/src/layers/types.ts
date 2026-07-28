/** One entry of the build-layers manifest. */
export interface LayerMeta {
  name: string;
  title: string;
  description: string;
  realm: string;
  evidence_type: string;
  /** Which builder produced it, and so which renderer consumes it. */
  kind: "surface" | "series";
  value_kind: string;
  attribution: string;
  licence: string;
  landing_page: string;
  caveats: string;
}

/** The sidecar the ethics gate writes beside every published layer. */
export interface LayerTerms {
  "dwc:dataGeneralizations": string;
  sensitivity: string;
}

export interface LoadedLayer {
  meta: LayerMeta;
  terms: LayerTerms;
  setVisible: (visible: boolean) => void;
  /** Called when the clock crosses into a new week. Only time-indexed layers implement it. */
  showWeek?: (week: number) => void;
}

export async function fetchLayer<T>(
  baseUrl: string,
  name: string,
): Promise<[T, LayerTerms]> {
  const [data, terms] = await Promise.all([
    fetch(`${baseUrl}layers/${name}.geojson`).then((r) => {
      if (!r.ok) throw new Error(`${name}: ${r.status}`);
      return r.json() as Promise<T>;
    }),
    fetch(`${baseUrl}layers/${name}.meta.json`).then((r) => {
      if (!r.ok) throw new Error(`${name} terms: ${r.status}`);
      return r.json() as Promise<LayerTerms>;
    }),
  ]);
  return [data, terms];
}

export async function loadManifest(baseUrl: string): Promise<LayerMeta[]> {
  const response = await fetch(`${baseUrl}layers/manifest.json`);
  if (!response.ok) return [];
  return (await response.json()) as LayerMeta[];
}

/** Attribution MapLibre shows whenever the layer is visible, terms included. */
export function attributionFor(meta: LayerMeta, terms: LayerTerms): string {
  return (
    `<a href="${meta.landing_page}">${meta.title}</a> (${meta.licence}) — ` +
    terms["dwc:dataGeneralizations"]
  );
}
