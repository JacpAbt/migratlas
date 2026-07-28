/** The single clock every layer reads, kept in the URL so views are shareable. */

export interface TimeState {
  /** Day of year, 0-365. */
  day: number;
  /** Minutes past midnight UTC, 0-1439. */
  minute: number;
  year: number;
}

type Listener = (state: TimeState, instant: Date) => void;

const MINUTES_PER_DAY = 1440;

export class Clock {
  #state: TimeState;
  #listeners = new Set<Listener>();
  #timer: number | null = null;

  constructor(initial?: Partial<TimeState>) {
    const now = new Date();
    const fromUrl = readUrl();
    this.#state = {
      year: now.getUTCFullYear(),
      day: dayOfYear(now),
      minute: now.getUTCHours() * 60 + now.getUTCMinutes(),
      ...fromUrl,
      ...initial,
    };
    // Publish the initial state too, or a freshly loaded view is unshareable until the
    // user happens to move a slider.
    writeUrl(this.#state);
  }

  get state(): TimeState {
    return this.#state;
  }

  /** UTC instant the current state denotes. */
  get instant(): Date {
    const { year, day, minute } = this.#state;
    return new Date(Date.UTC(year, 0, 1 + day, 0, minute));
  }

  /**
   * Week index 0-51, the granularity weekly abundance surfaces are published at.
   * Data layers filter on this rather than being rebuilt.
   */
  get week(): number {
    return Math.min(51, Math.floor(this.#state.day / 7));
  }

  set(patch: Partial<TimeState>): void {
    this.#state = { ...this.#state, ...patch };
    writeUrl(this.#state);
    for (const listener of this.#listeners) listener(this.#state, this.instant);
  }

  subscribe(listener: Listener): () => void {
    this.#listeners.add(listener);
    listener(this.#state, this.instant);
    return () => this.#listeners.delete(listener);
  }

  get playing(): boolean {
    return this.#timer !== null;
  }

  /** Advance `minutesPerTick` of simulated time on each animation frame. */
  play(minutesPerTick = 8): void {
    if (this.#timer !== null) return;
    const tick = (): void => {
      const total = this.#state.minute + minutesPerTick;
      this.set({
        minute: total % MINUTES_PER_DAY,
        day: (this.#state.day + Math.floor(total / MINUTES_PER_DAY)) % 366,
      });
      this.#timer = requestAnimationFrame(tick);
    };
    this.#timer = requestAnimationFrame(tick);
  }

  pause(): void {
    if (this.#timer === null) return;
    cancelAnimationFrame(this.#timer);
    this.#timer = null;
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }
}

export function dayOfYear(date: Date): number {
  const start = Date.UTC(date.getUTCFullYear(), 0, 1);
  return Math.floor((date.getTime() - start) / 86_400_000);
}

export function formatInstant(instant: Date): string {
  return instant.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

function readUrl(): Partial<TimeState> {
  const params = new URLSearchParams(location.hash.slice(1));
  const patch: Partial<TimeState> = {};
  const day = Number(params.get("d"));
  const minute = Number(params.get("t"));
  if (Number.isFinite(day) && params.has("d")) patch.day = clamp(day, 0, 365);
  if (Number.isFinite(minute) && params.has("t")) patch.minute = clamp(minute, 0, 1439);
  return patch;
}

function writeUrl(state: TimeState): void {
  const params = new URLSearchParams(location.hash.slice(1));
  params.set("d", String(state.day));
  params.set("t", String(state.minute));
  // replaceState, not a hash assignment: animating would otherwise push hundreds of
  // history entries and trap the back button.
  history.replaceState(null, "", `#${params}`);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
