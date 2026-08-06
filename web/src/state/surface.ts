/**
 * Which surface the notebook is read on, and how that choice survives a reload.
 *
 * Three states, not two. "Follow the system" has to be one of them rather than the absence of a
 * choice: a reader on a machine that switches to dark at sunset wants the page to switch with it,
 * and a reader who has explicitly chosen day wants it to stay day at midnight. Storing only
 * `"day" | "night"` cannot tell those apart, so the first click would silently opt out of the
 * system preference forever.
 *
 * The attribute is what the CSS reads. `tokens.css` keys the night palette on
 * `:root:not([data-surface="day"])` inside a dark media query *and* on `:root[data-surface="night"]`
 * outside one, so an explicit choice wins in both directions and `"system"` means "write no
 * attribute and let the media query decide".
 */

export type Surface = "system" | "day" | "night";

export const SURFACES: readonly Surface[] = ["day", "system", "night"] as const;

/** What each option says on the switch. "Auto" would not tell anyone what it follows. */
export const SURFACE_LABEL: Record<Surface, string> = {
  day: "Day",
  system: "System",
  night: "Night",
};

const STORAGE_KEY = "migratlas:surface";

function isSurface(value: string | null): value is Surface {
  return value === "system" || value === "day" || value === "night";
}

/**
 * The stored choice, or "system" if there is none.
 *
 * Wrapped, because `localStorage` throws rather than returning null when a browser is set to block
 * storage entirely -- Safari in private mode historically, and any browser under a strict cookie
 * policy. A reader who has turned storage off should get a working page with an unremembered
 * preference, not a blank one.
 */
export function storedSurface(): Surface {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return isSurface(saved) ? saved : "system";
  } catch {
    return "system";
  }
}

/** Apply a surface to the document, and remember it. Returns what was applied. */
export function applySurface(surface: Surface): Surface {
  const root = document.documentElement;
  if (surface === "system") {
    root.removeAttribute("data-surface");
  } else {
    root.setAttribute("data-surface", surface);
  }
  try {
    localStorage.setItem(STORAGE_KEY, surface);
  } catch {
    // Not remembering a preference is a smaller failure than not honouring it.
  }
  return surface;
}

/**
 * Whether the page is *currently* dark, whichever way it got there.
 *
 * The globe needs this rather than the setting: `"system"` is not a colour, and the basemap has to
 * be repainted with the palette actually in force.
 */
export function isNight(surface: Surface): boolean {
  if (surface === "night") return true;
  if (surface === "day") return false;
  return globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

/**
 * Call `whenever` each time the system preference changes, while the choice is "system".
 *
 * Returns its own teardown. Without this, a reader on "system" whose machine dims at sunset gets
 * the paper turning black under a globe that stays parchment, because MapLibre paint expressions
 * are set once in JavaScript rather than resolved from CSS on every frame.
 */
export function watchSystem(whenever: () => void): () => void {
  const query = globalThis.matchMedia?.("(prefers-color-scheme: dark)");
  if (!query) return () => {};
  query.addEventListener("change", whenever);
  return () => query.removeEventListener("change", whenever);
}
