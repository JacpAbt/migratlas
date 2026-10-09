/**
 * The things on the desk that are made here rather than downloaded: a box of matches, a match, a
 * pencil, a cup of coffee, and the sprites a flame and its smoke are drawn with.
 *
 * Built to their real sizes in metres, so they sit beside the scanned models at the right scale and
 * the camera's perspective treats them the same way.
 */

import * as THREE from "three";

/** A canvas as a texture, in sRGB because it is a colour. */
function canvasTexture(width: number, height: number, draw: (c: CanvasRenderingContext2D) => void) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d")!);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

/**
 * Fill `path` blurred by `sigma` pixels, in `color`, whose alpha the path's own fill scales.
 *
 * Through the shadow, not `ctx.filter`: Safari supports the filter only behind a developer setting,
 * and there the flame came out as a hard-edged cut-out. The shape is drawn off the canvas and only
 * its shadow, blurred and offset back, lands in view; a shadow's blur is twice its sigma.
 */
function soft(c: CanvasRenderingContext2D, sigma: number, color: string, fill: string | CanvasGradient, path: () => void) {
  const away = c.canvas.width + 4 * sigma;
  c.save();
  c.shadowColor = color;
  c.shadowBlur = 2 * sigma;
  c.shadowOffsetX = away;
  c.translate(-away, 0);
  c.fillStyle = fill;
  path();
  c.fill();
  c.restore();
}

/** Speckle, for paper and the striker: a little noise so a flat colour reads as a material. */
function speckle(c: CanvasRenderingContext2D, w: number, h: number, light: string, dark: string, n: number) {
  for (let i = 0; i < n; i++) {
    c.fillStyle = Math.random() < 0.5 ? light : dark;
    c.fillRect(Math.random() * w, Math.random() * h, 1 + Math.random() * 1.5, 1 + Math.random() * 1.5);
  }
}

/** A box of matches: a printed lid, kraft ends, and a striking strip down each long side. */
export function matchbox(): THREE.Mesh {
  const kraft = canvasTexture(64, 64, (c) => {
    c.fillStyle = "#cfae78";
    c.fillRect(0, 0, 64, 64);
    speckle(c, 64, 64, "rgba(255,240,210,.35)", "rgba(90,60,30,.25)", 260);
  });
  const lid = canvasTexture(512, 360, (c) => {
    c.fillStyle = "#e3c996";
    c.fillRect(0, 0, 512, 360);
    speckle(c, 512, 360, "rgba(255,245,220,.3)", "rgba(110,70,30,.18)", 3000);
    c.fillStyle = "#f2e5c6";
    c.fillRect(34, 34, 444, 292);
    c.strokeStyle = "#a8302a";
    c.lineWidth = 10;
    c.strokeRect(34, 34, 444, 292);
    c.lineWidth = 3;
    c.strokeRect(54, 54, 404, 252);
    // A sun, the kind of mark a match label carries.
    c.save();
    c.translate(140, 180);
    c.fillStyle = "#c23b2a";
    for (let i = 0; i < 16; i++) {
      c.rotate(Math.PI / 8);
      c.beginPath();
      c.moveTo(0, -30);
      c.lineTo(9, -62);
      c.lineTo(-9, -62);
      c.closePath();
      c.fill();
    }
    c.beginPath();
    c.arc(0, 0, 30, 0, Math.PI * 2);
    c.fill();
    c.restore();
    c.fillStyle = "#6b2318";
    c.font = "bold 50px Georgia, 'Times New Roman', serif";
    c.fillText("SAFETY", 214, 168);
    c.fillText("MATCHES", 214, 226);
    c.font = "italic 24px Georgia, serif";
    c.fillText("strike on box", 216, 270);
  });
  const striker = canvasTexture(256, 64, (c) => {
    c.fillStyle = "#4a2c1d";
    c.fillRect(0, 0, 256, 64);
    speckle(c, 256, 64, "rgba(200,170,140,.5)", "rgba(10,5,2,.6)", 2400);
    // The marks of matches already struck.
    c.strokeStyle = "rgba(20,10,5,.55)";
    c.lineWidth = 2;
    for (let i = 0; i < 9; i++) {
      const x = 20 + Math.random() * 200;
      c.beginPath();
      c.moveTo(x, 18 + Math.random() * 8);
      c.lineTo(x + 30 + Math.random() * 20, 40 + Math.random() * 8);
      c.stroke();
    }
  });
  const paper = (map: THREE.Texture, roughness = 0.85) =>
    new THREE.MeshStandardMaterial({ map, roughness, metalness: 0 });
  // Order: +x, -x, +y (lid), -y, +z, -z.
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(0.056, 0.017, 0.038), [
    paper(kraft),
    paper(kraft),
    paper(lid, 0.7),
    paper(kraft),
    paper(striker, 0.95),
    paper(striker, 0.95),
  ]);
  mesh.position.y = 0.0085;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

/** A wooden match, its head at the group's origin and its stick running back along +x. */
export function match(): { group: THREE.Group; head: THREE.Mesh; char: THREE.Mesh } {
  const group = new THREE.Group();
  const stick = new THREE.Mesh(
    new THREE.BoxGeometry(0.046, 0.0021, 0.0021),
    new THREE.MeshStandardMaterial({ color: "#e2c48f", roughness: 0.8 }),
  );
  stick.position.x = 0.023;
  stick.castShadow = true;
  const shape = new THREE.SphereGeometry(0.0024, 16, 12);
  shape.scale(1.35, 1, 1);
  const head = new THREE.Mesh(
    shape,
    new THREE.MeshStandardMaterial({ color: "#9e2a19", roughness: 0.55 }),
  );
  head.castShadow = true;
  const char = new THREE.Mesh(
    shape,
    new THREE.MeshStandardMaterial({ color: "#1d1511", roughness: 0.95 }),
  );
  char.visible = false;
  group.add(stick, head, char);
  return { group, head, char };
}

/** A yellow pencil, sharpened, lying along +x with its point at -x. */
export function pencil(): THREE.Group {
  const group = new THREE.Group();
  const r = 0.0036;
  const length = 0.15;
  const paint = new THREE.MeshStandardMaterial({ color: "#f0b51f", roughness: 0.42 });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, length, 6), paint);
  body.rotation.z = Math.PI / 2;
  body.position.x = length / 2;
  const wood = new THREE.Mesh(
    new THREE.ConeGeometry(r, 0.02, 6, 1, true),
    new THREE.MeshStandardMaterial({ color: "#e6cb98", roughness: 0.85 }),
  );
  wood.rotation.z = Math.PI / 2;
  wood.position.x = -0.01;
  const lead = new THREE.Mesh(
    new THREE.ConeGeometry(r * 0.32, 0.0065, 8),
    new THREE.MeshStandardMaterial({ color: "#2a2826", roughness: 0.5, metalness: 0.3 }),
  );
  lead.rotation.z = Math.PI / 2;
  lead.position.x = -0.0168;
  const ferrule = new THREE.Mesh(
    new THREE.CylinderGeometry(r * 1.05, r * 1.05, 0.011, 16),
    new THREE.MeshStandardMaterial({ color: "#c9c8c2", roughness: 0.3, metalness: 0.9 }),
  );
  ferrule.rotation.z = Math.PI / 2;
  ferrule.position.x = length + 0.0055;
  const eraser = new THREE.Mesh(
    new THREE.CylinderGeometry(r, r, 0.009, 16),
    new THREE.MeshStandardMaterial({ color: "#e58a7a", roughness: 0.9 }),
  );
  eraser.rotation.z = Math.PI / 2;
  eraser.position.x = length + 0.0155;
  for (const part of [body, wood, lead, ferrule, eraser]) {
    part.castShadow = true;
    part.receiveShadow = true;
    group.add(part);
  }
  group.position.y = r;
  return group;
}

/** A cup of coffee: a turned ceramic mug, the coffee in it, and a handle. */
export function mug(): THREE.Group {
  const group = new THREE.Group();
  const profile = [
    [0, 0],
    [0.036, 0],
    [0.04, 0.003],
    [0.042, 0.012],
    [0.043, 0.088],
    [0.0425, 0.093],
    [0.0405, 0.094],
    [0.0385, 0.09],
    [0.0375, 0.012],
    [0.03, 0.009],
    [0, 0.008],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const ceramic = new THREE.MeshPhysicalMaterial({
    color: "#efeae1",
    roughness: 0.28,
    clearcoat: 0.7,
    clearcoatRoughness: 0.15,
  });
  const body = new THREE.Mesh(new THREE.LatheGeometry(profile, 64), ceramic);
  const coffee = new THREE.Mesh(
    new THREE.CircleGeometry(0.0378, 48),
    // Glossy, but dark enough that it shows coffee rather than a grey reflection of the room.
    new THREE.MeshPhysicalMaterial({ color: "#2a1508", roughness: 0.12, clearcoat: 0.5, envMapIntensity: 0.35 }),
  );
  coffee.rotation.x = -Math.PI / 2;
  coffee.position.y = 0.074;
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.0065, 14, 32, Math.PI), ceramic);
  handle.rotation.z = -Math.PI / 2;
  handle.position.set(0.042, 0.05, 0);
  for (const part of [body, handle]) {
    part.castShadow = true;
    part.receiveShadow = true;
  }
  group.add(body, coffee, handle);
  return group;
}

/** A flame, drawn once: an orange body, a yellow heart, a white core and a blue root, soft-edged. */
export function flameTexture(): THREE.Texture {
  return canvasTexture(128, 256, (c) => {
    const tear = (w: number, h: number, base: number) => {
      c.beginPath();
      c.moveTo(64, base);
      c.bezierCurveTo(64 - w, base - h * 0.25, 64 - w * 0.6, base - h * 0.75, 64, base - h);
      c.bezierCurveTo(64 + w * 0.6, base - h * 0.75, 64 + w, base - h * 0.25, 64, base);
      c.closePath();
    };
    soft(c, 7, "rgba(255,120,30,0.85)", "#000", () => tear(44, 210, 236));
    soft(c, 5, "rgba(255,196,90,0.95)", "#000", () => tear(32, 170, 232));
    soft(c, 3, "rgba(255,248,226,1)", "#000", () => tear(18, 110, 226));
    soft(c, 4, "rgba(90,130,255,0.55)", "#000", () => {
      c.beginPath();
      c.ellipse(64, 228, 14, 9, 0, 0, Math.PI * 2);
    });
  });
}

/** A soft round glow, white at the centre, for the light around a flame. */
export function glowTexture(): THREE.Texture {
  return canvasTexture(128, 128, (c) => {
    const g = c.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, "rgba(255,200,120,0.9)");
    g.addColorStop(0.25, "rgba(255,160,70,0.35)");
    g.addColorStop(1, "rgba(255,140,50,0)");
    c.fillStyle = g;
    c.fillRect(0, 0, 128, 128);
  });
}

/** A wisp of smoke: soft grey, fading upward. */
export function smokeTexture(): THREE.Texture {
  return canvasTexture(64, 128, (c) => {
    // The gradient fades the wisp upward: in the shadow it is the alpha, and `color` the grey.
    const g = c.createLinearGradient(0, 128, 0, 0);
    g.addColorStop(0, "rgba(0,0,0,0.7)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    soft(c, 6, "rgb(220,220,220)", g, () => {
      c.beginPath();
      c.moveTo(32, 124);
      c.bezierCurveTo(10, 90, 50, 60, 28, 30);
      c.bezierCurveTo(20, 18, 40, 8, 32, 0);
      c.lineTo(40, 0);
      c.bezierCurveTo(50, 12, 32, 22, 40, 34);
      c.bezierCurveTo(62, 62, 22, 92, 40, 124);
      c.closePath();
    });
  });
}
