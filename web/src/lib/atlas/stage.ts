/**
 * The atlas's stage: the canvases, the camera and the clock, and every move between places.
 *
 * Four sheets, back to front: `A` the map the camera is looking at, `B` a settled map faded over it
 * when a move ends, `trails` where the radar's strokes dry, and `live` for everything else that
 * moves. The component owns the page around them -- the words, the controls, the callouts -- and
 * hears from here through `onState`.
 *
 * A move is a list of steps run by the frame clock. Every move between places is made in one
 * projection, the plates' Lambert with its centre travelling the great circle (ADR 0021 decision 4),
 * and the flat world appears only at the ends: going in, it closes to a spot round the place; inside
 * that spot, where Equal Earth and the plate's Lambert differ by a pixel or two, the camera changes
 * projection; and the spot opens as the camera dives. The owner saw the globe swell and shrink at
 * both ends of the earlier versions and called it jarring.
 */

import {
  between,
  dipFor,
  ease,
  equalEarth,
  lambert,
  View,
  viewOf,
  type Box,
  type Camera,
  type Sheet,
} from "./geo";
import {
  frameOf,
  loadPlateMap,
  WEEKS,
  type Place,
  type PlateMap,
  type PlateWords,
  type Words,
  type WorldMap,
} from "./data";
import { drawMap, type Graticule, type Label, type Palette, type Part } from "./ink";
import { NightSky } from "./night";
import { JOURNEY_DAYS, Journeys } from "./journeys";
import type { Herd } from "./herd";
import type { Ice } from "./ice";
import type { StillDrawn, StillMap } from "./still";

const WORLD_BOX: Box = { west: -180, east: 180, south: -90, north: 90 };
const FOCUS = 0.4;
const DIVE = 1.4;
const SETTLE = 0.35;
/** Pixels: the spot left round a place when the camera changes projection. */
const SPOT = 130;
/** How strongly what moves is drawn over a still map on the world view: there, but not the subject. */
const UNDER_STILL = 0.3;

/** What the stage draws, loaded before it is made. */
export interface Cast {
  world: WorldMap;
  night: NightSky;
  journeys: Journeys;
  herds: Record<string, Herd>;
  ice: Ice;
}

/** What the page around the stage needs to know, sent whenever it changes. */
export interface StageState {
  /** The plate looked at or being moved to; `world` for the whole world. */
  showing: string;
  moving: boolean;
  callouts: number;
  clock: "year" | "journey";
  week: number;
  day: number;
  readout: string;
  /** The still map shown, or empty. */
  still: string;
}

/** What one frame drew, for the suite to ask -- the map's answer, not the DOM's. */
export interface Drawn {
  showing: string;
  strokes: number;
  journeys: number;
  herd: number;
  ice: boolean;
  frames: number;
  /** The still map on the settled sheet, or empty; its cells decoded, and what of them was drawn. */
  still: string;
  cells: number;
  dots: number;
  rings: number;
  squares: number;
}

interface Sheets {
  A: HTMLCanvasElement;
  B: HTMLCanvasElement;
  trails: HTMLCanvasElement;
  live: HTMLCanvasElement;
}

interface Step {
  dur: number;
  enter?: () => void;
  run: (f: number) => Frame;
}

interface Frame {
  view: View;
  shown: string[];
  comet: boolean;
  callouts?: number;
}

interface Move {
  target: string;
  steps: Step[];
  t0: number;
  at: number;
}

export class Stage {
  private ctx: Record<keyof Sheets, CanvasRenderingContext2D>;
  private W = 1;
  private H = 1;
  private dpr = 1;
  private box: Sheet = { x: 0, y: 0, w: 1, h: 1 };
  private worldView = View.fit(equalEarth(), WORLD_BOX, this.box);
  private plates = new Map<string, View>();
  private maps = new Map<string, PlateMap>();
  private cache = new Map<string, HTMLCanvasElement>();
  private mode = "world";
  private move: Move | null = null;
  private queued: string | null = null;
  private queuedStill: StillMap | null = null;
  /** The still map shown, and during a move the one on the place being left. */
  private stillOn: StillMap | null = null;
  private leaving: StillMap | null = null;
  private stillDrawn = new Map<string, StillDrawn>();
  private raf = 0;
  private last = 0;
  private told = "";
  private still: boolean;
  week: number;
  day = 0;
  playing = true;
  speed = 1;
  /** While a reader drags the clock, the stage does not advance it under their hand. */
  holding = false;
  readonly drawn: Drawn = {
    showing: "world",
    strokes: 0,
    journeys: 0,
    herd: 0,
    ice: false,
    frames: 0,
    still: "",
    cells: 0,
    dots: 0,
    rings: 0,
    squares: 0,
  };

  constructor(
    private readonly sheets: Sheets,
    private readonly cast: Cast,
    private readonly words: Words,
    private readonly base: string,
    private pal: Palette,
    week: number,
    private readonly onState: (state: StageState) => void,
  ) {
    const get = (c: HTMLCanvasElement): CanvasRenderingContext2D => {
      const context = c.getContext("2d");
      if (!context) throw new Error("no 2D canvas");
      return context;
    };
    this.ctx = { A: get(sheets.A), B: get(sheets.B), trails: get(sheets.trails), live: get(sheets.live) };
    this.week = week;
    // Reduced motion lands on the final state on the first frame: nothing plays, a move is a cut.
    this.still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.playing = !this.still;
  }

  // --- Size and paper --------------------------------------------------------------------------

  /** Fit to a new size: `map` is the part of the sheet the map is framed in. */
  layout(width: number, height: number, map: Sheet): void {
    this.W = Math.max(1, width);
    this.H = Math.max(1, height);
    this.dpr = Math.min(2, devicePixelRatio || 1);
    for (const c of Object.values(this.sheets)) {
      c.width = Math.round(this.W * this.dpr);
      c.height = Math.round(this.H * this.dpr);
    }
    this.box = map;
    this.worldView = View.fit(equalEarth(), WORLD_BOX, map);
    this.plates.clear();
    for (const place of this.places()) {
      this.plates.set(place.name, View.fit(lambert(place.centre[0], place.centre[1]), frameOf(place), map));
    }
    this.cache.clear();
    this.stillDrawn.clear();
    this.move = null;
    this.settle();
  }

  /** The paper changed, so the ink did: every settled map is drawn again. */
  repaint(pal: Palette): void {
    this.pal = pal;
    this.cache.clear();
    this.stillDrawn.clear();
    if (!this.move) this.settle();
  }

  /** Where a plate's place is on the world view, for its callout's leader. */
  anchor(plate: PlateWords): [number, number] {
    return this.worldView.project(plate.centre[0], plate.centre[1]);
  }

  // --- Running ---------------------------------------------------------------------------------

  start(): void {
    if (this.raf) return;
    this.last = performance.now();
    const tick = (now: number): void => {
      this.frame(now);
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  dispose(): void {
    this.stop();
    this.cache.clear();
    this.stillDrawn.clear();
  }

  /** The sheets as one picture: what a turning page shows of the atlas while it turns. */
  picture(): string {
    const out = document.createElement("canvas");
    out.width = this.sheets.A.width;
    out.height = this.sheets.A.height;
    const c = out.getContext("2d");
    if (!c) return "";
    for (const sheet of [this.sheets.A, this.sheets.B, this.sheets.trails, this.sheets.live]) {
      c.globalAlpha = Number(sheet.style.opacity || 1);
      c.drawImage(sheet, 0, 0);
    }
    return out.toDataURL("image/png");
  }

  // --- Choosing a place ------------------------------------------------------------------------

  /**
   * Go to a plate, or to `world`, showing `still` there or no still map. A choice made during a move
   * waits for it to end.
   */
  async show(key: string, still: StillMap | null = null): Promise<void> {
    if (key !== "world" && !this.maps.has(key)) {
      this.maps.set(key, await loadPlateMap(this.base, this.place(key).map));
    }
    if (this.move) {
      this.queued = key;
      this.queuedStill = still;
      return;
    }
    if (key === this.mode) {
      // The same place with another still map, or none: only its settled sheet changes.
      const changed = still !== this.stillOn;
      this.stillOn = still;
      if (changed) this.settle();
      this.tell(true);
      return;
    }
    this.leaving = this.stillOn;
    this.stillOn = still;
    const steps =
      this.mode === "world"
        ? this.stepsIn(key, this.leaving ? UNDER_STILL : 1)
        : key === "world"
          ? this.stepsOut(this.mode, still && !still.words.plate ? UNDER_STILL : 1)
          : this.stepsBetween(this.mode, key);
    if (key === "bylot") this.day = 0;
    if (this.still) {
      // Reduced motion: no move to watch, only where it ends.
      this.mode = key;
      this.leaving = null;
      this.settle();
      this.tell(true);
      return;
    }
    this.move = { target: key, steps, t0: performance.now(), at: -1 };
    this.clearTrails();
    this.tell(true);
  }

  get showing(): string {
    return this.move?.target ?? this.mode;
  }

  /** The still map shown, or empty. */
  get stillShown(): string {
    return this.stillOn?.words.name ?? "";
  }

  private plate(name: string): PlateWords {
    const plate = this.words.plates.find((p) => p.name === name);
    if (!plate) throw new Error(`no plate ${name}`);
    return plate;
  }

  /** Every place the camera can go: the systems' plates, then the still maps' of one region. */
  private places(): Place[] {
    return [...this.words.plates, ...this.words.stills.flatMap((s) => (s.plate ? [s.plate] : []))];
  }

  private place(name: string): Place {
    const place = this.places().find((p) => p.name === name);
    if (!place) throw new Error(`no place ${name}`);
    return place;
  }

  /** The still map on a place's sheet: during a move, the arriving one where the camera is going. */
  private stillOnSheet(key: string): StillMap | null {
    const pick = this.move && key !== this.move.target ? this.leaving : this.stillOn;
    return pick && (pick.words.plate?.name ?? "world") === key ? pick : null;
  }

  /** How strongly what moves is drawn at a place: dimmed under the world's still map. */
  private dim(key: string): number {
    return key === "world" && this.stillOnSheet(key) ? UNDER_STILL : 1;
  }

  // --- The maps --------------------------------------------------------------------------------

  private size(): { w: number; h: number; dpr: number } {
    return { w: this.W, h: this.H, dpr: this.dpr };
  }

  private worldPart(alpha: number, hatch: boolean): Part {
    return { land: this.cast.world.land, borders: this.cast.world.borders, alpha, hatch };
  }

  /**
   * A plate's own map. Its rivers are the map where the plate is all land, so the Ya Ha Tinda's are
   * drawn heavier and named; under the radar's strokes only the great rivers, faint.
   */
  private platePart(name: string, alpha: number, hatch: boolean): Part {
    const map = this.maps.get(name);
    if (!map) return { land: [], alpha: 0, hatch: false };
    const inland = map.lakes.length > 0;
    const herdPlate = name === "svalbard" || name === "ya-ha-tinda";
    const part: Part = {
      land: map.land,
      box: map.box,
      alpha,
      hatch,
      rivers: map.rivers,
      creeks: map.creeks,
      lakes: map.lakes,
      hatchAlpha: herdPlate ? 0.5 : 1,
      riverAlpha: inland ? 0.75 : 0.35,
      riverWidth: inland ? 1.1 : 0.6,
    };
    if (!herdPlate) part.borders = this.cast.world.borders;
    if (inland && hatch) part.labels = this.labels(name, map);
    return part;
  }

  /** Each named river once, on its longest stretch, along the line and inside the map's box. */
  private labels(name: string, map: PlateMap): Label[] {
    const view = this.plates.get(name);
    if (!view) return [];
    const out: Label[] = [];
    for (const { name: text, line } of map.named) {
      if (line.length < 4) continue;
      const m = Math.floor(line.length / 2);
      const [mx, my] = view.project(line[m]![0], line[m]![1]);
      const box = this.box;
      if (mx < box.x || mx > box.x + box.w || my < box.y || my > box.y + box.h * 0.95) continue;
      const [ax, ay] = view.project(line[m - 1]![0], line[m - 1]![1]);
      const [bx, by] = view.project(line[Math.min(line.length - 1, m + 1)]![0], line[Math.min(line.length - 1, m + 1)]![1]);
      let angle = Math.atan2(by - ay, bx - ax);
      if (angle > Math.PI / 2) angle -= Math.PI;
      else if (angle < -Math.PI / 2) angle += Math.PI;
      out.push({ text, lon: line[m]![0], lat: line[m]![1], angle });
    }
    return out;
  }

  private graticule(key: string): Graticule {
    if (key === "world") return { lon: 30, lat: 20 };
    if (key === "north-america") return { lon: 10, lat: 10 };
    if (key === "bylot") return { lon: 15, lat: 5 };
    if (key === "southern-africa") return { lon: 5, lat: 5 };
    return { lon: 0.5, lat: 0.25 };
  }

  /**
   * A settled map -- the world, or a plate hatched or in outline, with its still map if it has one
   * -- drawn once and kept.
   */
  private sheet(key: string, hatch: boolean): HTMLCanvasElement {
    const still = hatch ? this.stillOnSheet(key) : null;
    const id = `${key}:${hatch}:${still?.words.name ?? ""}`;
    const cached = this.cache.get(id);
    if (cached) return cached;
    const canvas = document.createElement("canvas");
    canvas.width = this.sheets.A.width;
    canvas.height = this.sheets.A.height;
    const c = canvas.getContext("2d")!;
    if (key === "world") {
      drawMap(c, this.worldView, this.size(), this.pal, [this.worldPart(1, hatch)], { graticule: this.graticule("world") });
    } else {
      // The plate's file covers what the spread shows; a taller sheet sees the world's outline past it.
      const view = this.plates.get(key)!;
      const map = this.maps.get(key);
      const beyond: Part = { ...this.worldPart(1, hatch), ...(map ? { outside: map.box } : {}) };
      drawMap(c, view, this.size(), this.pal, [beyond, this.platePart(key, 1, hatch)], {
        graticule: hatch ? this.graticule(key) : null,
      });
    }
    if (still) {
      c.save();
      c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      const view = key === "world" ? this.worldView : this.plates.get(key)!;
      this.stillDrawn.set(id, still.draw(c, view, this.pal, this.W, this.H));
      c.restore();
    }
    this.cache.set(id, canvas);
    return canvas;
  }

  private lay(target: CanvasRenderingContext2D, key: string, hatch: boolean): void {
    target.clearRect(0, 0, target.canvas.width, target.canvas.height);
    target.drawImage(this.sheet(key, hatch), 0, 0);
  }

  private settle(): void {
    this.lay(this.ctx.A, this.mode, true);
    this.ctx.B.clearRect(0, 0, this.sheets.B.width, this.sheets.B.height);
    this.sheets.B.style.opacity = "0";
    this.opacity(1, this.dim(this.mode));
    const still = this.stillOnSheet(this.mode);
    const drew = this.stillDrawn.get(`${this.mode}:true:${still?.words.name ?? ""}`);
    Object.assign(this.drawn, {
      still: still?.words.name ?? "",
      cells: still?.cells.v.length ?? 0,
      dots: drew?.dots ?? 0,
      rings: drew?.rings ?? 0,
      squares: drew?.squares ?? 0,
    });
    this.mask(0, 0, this.full());
    this.clearTrails();
    this.cast.night.reset();
  }

  private clearTrails(): void {
    this.ctx.trails.clearRect(0, 0, this.sheets.trails.width, this.sheets.trails.height);
  }

  private opacity(map: number, moving: number): void {
    this.sheets.A.style.opacity = String(map);
    this.sheets.trails.style.opacity = this.sheets.live.style.opacity = String(moving);
  }

  private full(): number {
    return Math.hypot(this.W, this.H) * 1.1;
  }

  /** Everything outside a circle round (x, y) faded away, its edge feathered. */
  private mask(x: number, y: number, r: number, feather = 0.35): void {
    const css =
      r >= this.full()
        ? "none"
        : `radial-gradient(circle at ${x}px ${y}px, #000 ${Math.max(0, r * (1 - feather))}px, transparent ${r}px)`;
    for (const c of [this.sheets.A, this.sheets.trails, this.sheets.live]) {
      c.style.maskImage = css;
      c.style.setProperty("-webkit-mask-image", css);
    }
  }

  // --- The moves -------------------------------------------------------------------------------

  private centre(): [number, number] {
    return [this.W / 2, this.box.y + this.box.h / 2];
  }

  private camera(name: string): Camera {
    const plate = this.place(name);
    const view = this.plates.get(name)!;
    return { lon: plate.centre[0], lat: plate.centre[1], s: view.scale, tx: view.tx, ty: view.ty };
  }

  /**
   * The plate's camera at the world's scale, over where the world map puts the place. Both
   * projections are equal-area on the unit sphere, so the place is drawn the size the world shows it.
   */
  private spot(name: string): Camera {
    const plate = this.place(name);
    const [x, y] = this.worldView.project(plate.centre[0], plate.centre[1]);
    return { lon: plate.centre[0], lat: plate.centre[1], s: this.worldView.scale, tx: x, ty: y };
  }

  /**
   * How open the spot is at a camera: by how far it has zoomed from the world, not by time, so it is
   * wide for nearly all of a dive -- shrunk by the clock, the deep dive to a herd spent most of its
   * length on an empty page.
   */
  private openness(c: Camera, name: string): number {
    const depth = Math.log(c.s / this.worldView.scale) / Math.log(this.plates.get(name)!.scale / this.worldView.scale);
    return Math.min(1, Math.sqrt(Math.max(0, depth) * 2.2));
  }

  /** Never past 60 degrees of arc: the horizon is at 90, the land folded along it. */
  private within(c: Camera, r: number): number {
    return Math.min(r, Math.max(SPOT, c.s));
  }

  /** A fine coast weighs in as the camera's scale nears the plate's. */
  private fineness(c: Camera, name: string): number {
    return Math.max(0, Math.min(1, 1 - Math.log(this.plates.get(name)!.scale / c.s) / 1.2));
  }

  private mapAt(view: View, fine: Part[]): void {
    const weight = fine.reduce((m, p) => Math.max(m, p.alpha), 0);
    drawMap(this.ctx.A, view, this.size(), this.pal, [this.worldPart(1 - weight, false), ...fine]);
  }

  private everything(): string[] {
    return ["world", ...this.words.plates.map((p) => p.name)];
  }

  /** In from the world; `moving` is how strongly the world's moving layers were drawn. */
  private stepsIn(name: string, moving: number): Step[] {
    const spot = this.spot(name);
    const cam = this.camera(name);
    const full = this.full();
    return [
      {
        dur: FOCUS,
        run: (f) => {
          this.mask(spot.tx, spot.ty, full + (SPOT - full) * ease(f));
          this.opacity(1, moving);
          return { view: this.worldView, shown: f < 0.5 ? this.everything() : [name], comet: false, callouts: 1 - Math.min(1, f * 3) };
        },
      },
      {
        dur: DIVE,
        run: (f) => {
          const c = between(spot, cam, f);
          const view = viewOf(c);
          this.mapAt(view, [this.platePart(name, this.fineness(c, name), false)]);
          this.mask(c.tx, c.ty, this.within(c, SPOT + (full - SPOT) * this.openness(c, name)));
          this.opacity(1, Math.max(0, (f - 0.55) / 0.45));
          return { view, shown: [name], comet: true };
        },
      },
      {
        dur: SETTLE,
        enter: () => {
          this.mask(0, 0, full);
          this.lay(this.ctx.B, name, true);
        },
        run: (f) => {
          this.sheets.B.style.opacity = String(f);
          return { view: this.plates.get(name)!, shown: [name], comet: false };
        },
      },
    ];
  }

  /** Out to the world; `moving` is how strongly the world's moving layers will be drawn there. */
  private stepsOut(name: string, moving: number): Step[] {
    const spot = this.spot(name);
    const cam = this.camera(name);
    const full = this.full();
    return [
      {
        dur: SETTLE,
        enter: () => {
          this.lay(this.ctx.B, name, true);
          this.sheets.B.style.opacity = "1";
          this.lay(this.ctx.A, name, false);
        },
        run: (f) => {
          this.sheets.B.style.opacity = String(1 - f);
          return { view: this.plates.get(name)!, shown: [name], comet: false };
        },
      },
      {
        dur: DIVE,
        run: (f) => {
          const c = between(cam, spot, f);
          const view = viewOf(c);
          this.mapAt(view, [this.platePart(name, this.fineness(c, name), false)]);
          this.mask(c.tx, c.ty, this.within(c, SPOT + (full - SPOT) * this.openness(c, name)));
          this.opacity(1, Math.max(0, 1 - f / 0.45));
          return { view, shown: [name], comet: true };
        },
      },
      {
        dur: FOCUS,
        enter: () => this.lay(this.ctx.A, "world", true),
        run: (f) => {
          this.mask(spot.tx, spot.ty, SPOT + (full - SPOT) * ease(f));
          this.opacity(1, f * moving);
          return { view: this.worldView, shown: this.everything(), comet: false, callouts: Math.max(0, (f - 0.6) / 0.4) };
        },
      },
    ];
  }

  /** From one plate straight to another, easing out only as far as a frame holding both. */
  private stepsBetween(from: string, to: string): Step[] {
    const a = this.camera(from);
    const b = this.camera(to);
    const dip = dipFor(a, b, this.box);
    // Farther apart, a little longer: the eye needs time to follow a long move.
    const dur = DIVE * (0.85 + 0.45 * Math.min(1, dip / 3));
    const full = this.full();
    return [
      {
        dur: SETTLE,
        enter: () => {
          this.lay(this.ctx.B, from, true);
          this.sheets.B.style.opacity = "1";
          this.lay(this.ctx.A, from, false);
        },
        run: (f) => {
          this.sheets.B.style.opacity = String(1 - f);
          return { view: this.plates.get(from)!, shown: [from], comet: false };
        },
      },
      {
        dur,
        run: (f) => {
          const c = between(a, b, f, dip);
          const view = viewOf(c);
          const leaving = f < 0.5;
          this.mapAt(view, [
            this.platePart(from, leaving ? this.fineness(c, from) : 0, false),
            this.platePart(to, leaving ? 0 : this.fineness(c, to), false),
          ]);
          // The higher the camera, the more of the sheet's edge is faded: no globe's curve shows.
          const lift = 4 * f * (1 - f);
          this.mask(c.tx, c.ty, this.within(c, full + (Math.min(this.W, this.H) * 0.75 - full) * Math.min(1, lift * 1.6)), 0.55);
          this.opacity(1, leaving ? Math.max(0, 1 - f / 0.25) : Math.max(0, (f - 0.75) / 0.25));
          return { view, shown: [leaving ? from : to], comet: true };
        },
      },
      {
        dur: SETTLE,
        enter: () => {
          this.mask(0, 0, full);
          this.lay(this.ctx.B, to, true);
        },
        run: (f) => {
          this.sheets.B.style.opacity = String(f);
          return { view: this.plates.get(to)!, shown: [to], comet: false };
        },
      },
    ];
  }

  /** Where the camera is this frame, running whichever step the clock is in. */
  private animate(now: number): Frame & { done: boolean } {
    const move = this.move!;
    let e = (now - move.t0) / 1000;
    for (let i = 0; i < move.steps.length; i++) {
      const s = move.steps[i]!;
      const last = i === move.steps.length - 1;
      if (e <= s.dur || last) {
        if (move.at !== i) {
          move.at = i;
          s.enter?.();
        }
        return { ...s.run(Math.min(1, e / s.dur)), done: last && e >= s.dur };
      }
      e -= s.dur;
    }
    throw new Error("a move with no steps");
  }

  private finish(): void {
    const move = this.move!;
    this.move = null;
    this.mode = move.target;
    this.leaving = null;
    this.settle();
    const queued = this.queued;
    const queuedStill = this.queuedStill;
    this.queued = null;
    this.queuedStill = null;
    if (queued && (queued !== this.mode || queuedStill !== this.stillOn)) void this.show(queued, queuedStill);
    this.tell(true);
  }

  // --- A frame ---------------------------------------------------------------------------------

  private frame(now: number): void {
    const dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    if (this.playing && !this.holding) {
      this.week = (this.week + dt * this.speed) % WEEKS;
      if (this.mode === "bylot" && !this.move) {
        this.day += dt * this.speed * 7;
        if (this.day > JOURNEY_DAYS + 25) this.day = 0;
      }
    }

    let view: View;
    let shown: string[];
    let comet = false;
    let callouts = this.mode === "world" ? 1 : 0;
    if (this.move) {
      const out = this.animate(now);
      ({ view, shown, comet } = out);
      callouts = out.callouts ?? 0;
      if (out.done) {
        this.finish();
        return;
      }
    } else {
      view = this.mode === "world" ? this.worldView : this.plates.get(this.mode)!;
      shown = this.mode === "world" ? this.everything() : [this.mode];
    }
    this.draw(view, shown, comet, dt);
    this.drawn.showing = this.showing;
    this.drawn.frames += 1;
    if (Math.abs(callouts - this.calloutsShown) > 0.02 || now - this.toldAt > 250) {
      this.calloutsShown = callouts;
      this.toldAt = now;
      this.tell(false);
    }
  }

  private calloutsShown = 1;
  private toldAt = 0;

  private draw(view: View, shown: string[], comet: boolean, dt: number): void {
    const { trails, live } = this.ctx;
    const world = shown.includes("world");
    trails.save();
    trails.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (comet) trails.clearRect(0, 0, this.W, this.H);
    else {
      // Dry what is there: a trail lasts about a second, long enough to read as a line drawn.
      trails.globalCompositeOperation = "destination-out";
      trails.fillStyle = `rgba(0,0,0,${1 - Math.exp(-dt * 1.5)})`;
      trails.fillRect(0, 0, this.W, this.H);
      trails.globalCompositeOperation = "source-over";
    }
    this.drawn.strokes = 0;
    if (shown.includes("north-america")) {
      this.cast.night.frame(trails, dt, this.week, view, this.pal, comet);
      this.drawn.strokes = this.cast.night.count;
    }
    trails.restore();

    live.save();
    live.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    live.clearRect(0, 0, this.W, this.H);
    this.drawn.ice = world;
    if (world) this.cast.ice.frame(live, this.week, view, this.pal);
    this.drawn.herd = 0;
    for (const name of ["svalbard", "ya-ha-tinda"]) {
      const herd = this.cast.herds[name];
      if (!herd || !shown.includes(name)) continue;
      // From afar a blot as big as the herd; close enough to see cells, its range and its shifts.
      if (view.pxPerKm(herd.centre[0], herd.centre[1]) * 1.112 < 1.5) herd.blot(live, this.week, view, this.pal);
      else {
        herd.range(live, this.week, view, this.pal);
        this.drawn.herd += 1;
      }
    }
    this.drawn.journeys = 0;
    if (shown.includes("bylot")) {
      const far = view.pxPerKm(-79, 73) < 0.08;
      const day = this.mode === "bylot" && !this.move ? this.day : (performance.now() / 1000) * 7 % (JOURNEY_DAYS + 25);
      this.drawn.journeys = this.cast.journeys.frame(live, day, view, this.pal, far);
    }
    if (!this.move && this.mode !== "world") this.scaleBar(live, view, this.place(this.mode));
    live.restore();
  }

  /** A pencil scale bar, a round distance long, at the plate's lower left. */
  private scaleBar(c: CanvasRenderingContext2D, view: View, plate: Place): void {
    const ppk = view.pxPerKm(plate.centre[0], plate.centre[1]);
    const target = (this.W * 0.12) / ppk;
    const nice = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000].reduce((p, n) => (n <= target ? n : p), 1);
    const px = nice * ppk;
    const x = this.box.x + this.W * 0.3;
    const y = this.box.y + this.box.h - 6;
    c.save();
    c.strokeStyle = this.pal.pencil;
    c.fillStyle = this.pal.pencil;
    c.lineWidth = 1.2;
    c.beginPath();
    c.moveTo(x, y - 4);
    c.lineTo(x, y);
    c.lineTo(x + px, y + 0.6);
    c.lineTo(x + px, y - 4);
    c.stroke();
    c.font = `12px ${this.pal.font}`;
    c.fillText(`${nice} km`, x + px + 6, y + 3);
    c.restore();
  }

  // --- Telling the page ------------------------------------------------------------------------

  private readout(showing: string): string {
    const r = this.words.readout;
    if (showing === "north-america") return this.cast.night.readout(this.week, r.air);
    if (showing === "bylot") {
      return `${r.journey.day} ${Math.min(JOURNEY_DAYS, Math.floor(this.day) + 1)} ${r.journey.each} · ${this.drawn.journeys} ${r.journey.of} ${this.cast.journeys.count} ${r.journey.going}`;
    }
    const herd = this.cast.herds[showing];
    if (herd) {
      const { cells, reached } = herd.counts(this.week);
      return `${r.herd.in} ${cells} ${r.herd.cells} · ${reached} ${r.herd.reached}`;
    }
    // A still map has no week to read out; what is on the sheet is named instead.
    if (this.stillOn) return this.stillOn.words.button;
    return this.words.world.readout;
  }

  private tell(force: boolean): void {
    const showing = this.showing;
    const state: StageState = {
      showing,
      moving: this.move !== null,
      callouts: this.calloutsShown,
      clock: showing === "bylot" ? "journey" : "year",
      week: this.week,
      day: this.day,
      readout: this.readout(showing),
      still: this.stillShown,
    };
    const key = JSON.stringify(state);
    if (!force && key === this.told) return;
    this.told = key;
    this.onState(state);
  }
}
