/**
 * The dart that points where the mass moved.
 *
 * Drawn once into a canvas and registered with `map.addImage`, the same route the land hatch
 * takes, because a symbol layer cannot be handed to rough.js. The glyph points north and MapLibre
 * rotates it by the week's measured bearing with `icon-rotation-alignment: "map"`, so the drawing
 * is presentation and the angle is data -- the shaft's centre line is dead straight for the same
 * reason the data circles are not wobbled: the direction *is* the measurement, and only the pen's
 * pressure may waver around it.
 */

import type { Pattern } from "../globe/hatch";

/** Canvas side in CSS pixels. The glyph is drawn with margin so rotation never clips it. */
const SIDE = 26;

/** Generated at 2x and declared as such, so the strokes stay strokes on a dense display. */
const SCALE = 2;

/** Lateral pressure wander of the shaft, in CSS pixels. Deterministic: the same dart every time. */
const WOBBLE = 0.5;

export const DART = "flow-dart";

export function dartIcon(colour: string): Pattern {
  const side = SIDE * SCALE;
  const canvas = document.createElement("canvas");
  canvas.width = side;
  canvas.height = side;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("no 2d context for the dart");

  context.strokeStyle = colour;
  context.lineCap = "round";
  context.lineJoin = "round";

  const cx = side / 2;
  const tip = 4 * SCALE;
  const tail = (SIDE - 4) * SCALE;

  // The shaft: straight in the mean, drawn in short segments whose width breathes a little, which
  // is how a hand keeps a line straight -- pressure varies, position does not.
  const segments = 6;
  for (let index = 0; index < segments; index += 1) {
    const from = tip + ((tail - tip) * index) / segments;
    const to = tip + ((tail - tip) * (index + 1)) / segments;
    // Deterministic per segment; symmetric about zero so the mean line stays the axis.
    const sway = WOBBLE * SCALE * Math.sin(index * 2.399963);
    context.lineWidth = 1.6 * SCALE * (0.85 + 0.3 * Math.abs(Math.sin(index * 1.7)));
    context.beginPath();
    context.moveTo(cx + sway * 0.4, from);
    context.lineTo(cx - sway * 0.4, to);
    context.stroke();
  }

  // The head: two strokes back from the tip, slightly unequal the way a quick mark is.
  context.lineWidth = 1.7 * SCALE;
  const barb = 5.5 * SCALE;
  context.beginPath();
  context.moveTo(cx - barb * 0.95, tip + barb);
  context.lineTo(cx, tip);
  context.lineTo(cx + barb * 1.05, tip + barb * 1.08);
  context.stroke();

  return { data: context.getImageData(0, 0, side, side), pixelRatio: SCALE };
}
