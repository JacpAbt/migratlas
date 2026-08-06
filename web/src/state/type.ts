/**
 * Which type the notebook is set in, and how that choice survives a reload.
 *
 * Three presets, and only the first is a preference. Atkinson Hyperlegible was drawn by the
 * Braille Institute for low vision and OpenDyslexic for dyslexic readers, so the other two are
 * accessibility provisions -- which is why this is a control a reader can reach rather than a
 * decision taken for them, and why it sits beside the surface switch rather than behind anything.
 *
 * Deliberately not tied to the surface: someone may want black paper and a legible face, or
 * daylight and a hand. `tokens.css` keys the faces on `data-type` and the palette on
 * `data-surface`, and the two never read each other.
 */

export type TypeChoice = "hand" | "clear" | "dyslexic";

export const TYPES: readonly TypeChoice[] = ["hand", "clear", "dyslexic"] as const;

/** What each option says, and what it is for. The second line is not decoration. */
export const TYPE_LABEL: Record<TypeChoice, { name: string; why: string }> = {
  hand: { name: "Hand", why: "Virgil and Shantell Sans. Nothing on the page is typed." },
  clear: { name: "Clear", why: "Hand headings, Atkinson Hyperlegible for reading." },
  dyslexic: { name: "Dyslexia", why: "OpenDyslexic: weighted bottoms, no mirrored letters." },
};

const STORAGE_KEY = "migratlas:type";

function isChoice(value: string | null): value is TypeChoice {
  return value === "hand" || value === "clear" || value === "dyslexic";
}

/**
 * The stored choice, or the hand.
 *
 * Wrapped, because `localStorage` throws rather than returning null where a browser blocks storage
 * outright. A reader who has turned it off should get a working page with an unremembered
 * preference, not a blank one -- and for this setting in particular, an exception here would take
 * the accessibility options down with it.
 */
export function storedType(): TypeChoice {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return isChoice(saved) ? saved : "hand";
  } catch {
    return "hand";
  }
}

/** Apply a choice to the document, and remember it. Returns what was applied. */
export function applyType(choice: TypeChoice): TypeChoice {
  document.documentElement.setAttribute("data-type", choice);
  try {
    localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Not remembering a preference is a smaller failure than not honouring it.
  }
  return choice;
}
