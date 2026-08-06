/** Mock wiring: rough.js for every drawn mark, and a live migration globe for direction C. */

import rough from "roughjs";

const ink = () => getComputedStyle(document.body).getPropertyValue("--a-ink").trim() || "#26302a";
const rust = () => getComputedStyle(document.body).getPropertyValue("--a-rust").trim() || "#a3441f";
const moss = () => getComputedStyle(document.body).getPropertyValue("--a-moss").trim() || "#4a6b4e";
const pencil = () =>
  getComputedStyle(document.body).getPropertyValue("--a-pencil").trim() || "#6d6a5c";

/** Everything drawn, redrawn on resize and on a palette change. */
function draw(): void {
  for (const node of document.querySelectorAll<SVGSVGElement>("svg[data-rough]")) {
    const box = node.getBoundingClientRect();
    const w = Math.max(box.width, 8);
    const h = Math.max(box.height, 8);
    node.setAttribute("viewBox", `0 0 ${w} ${h}`);
    node.replaceChildren();
    const rc = rough.svg(node);
    // A stable seed per element, so a redraw is the same hand rather than a new one.
    const seed = [...(node.dataset.rough ?? "")].reduce((a, c) => a + c.charCodeAt(0), 7);

    switch (node.dataset.rough) {
      case "underline":
        node.append(
          rc.line(2, 7, w - 6, 5, { stroke: rust(), strokeWidth: 2.4, roughness: 1.6, bowing: 2, seed }),
        );
        break;

      case "btn": {
        const accent = node.parentElement?.classList.contains("a-btn--go") ||
          node.parentElement?.classList.contains("c-btn");
        node.append(
          rc.rectangle(3, 3, w - 6, h - 6, {
            stroke: accent ? rust() : pencil(),
            strokeWidth: accent ? 1.9 : 1.4,
            roughness: 2.1,
            bowing: 1.6,
            seed,
          }),
        );
        break;
      }

      case "bracket":
        node.append(
          rc.linearPath(
            [[7, 1], [2, 8], [2, h - 8], [7, h - 1]],
            { stroke: pencil(), strokeWidth: 1.3, roughness: 2.2, seed },
          ),
        );
        break;

      case "tick":
        node.append(
          rc.linearPath([[2, 7], [5.5, 11], [11.5, 2]], {
            stroke: moss(),
            strokeWidth: 2,
            roughness: 1.5,
            seed,
          }),
        );
        break;

      case "aster":
        for (const angle of [0, 60, 120]) {
          const r = 5.5;
          const dx = Math.cos((angle * Math.PI) / 180) * r;
          const dy = Math.sin((angle * Math.PI) / 180) * r;
          node.append(
            rc.line(6.5 - dx, 6.5 - dy, 6.5 + dx, 6.5 + dy, {
              stroke: rust(),
              strokeWidth: 1.2,
              roughness: 1.4,
              seed: seed + angle,
            }),
          );
        }
        break;

      case "tape":
        node.append(
          rc.rectangle(2, 4, w - 4, h - 10, {
            stroke: "rgba(120,140,110,0.55)",
            strokeWidth: 1,
            roughness: 2.4,
            fill: "rgba(190,205,175,0.35)",
            fillStyle: "solid",
            seed,
          }),
        );
        break;

      case "radar":
        node.append(
          rc.arc(11, 22, 26, 26, Math.PI * 1.15, Math.PI * 1.95, false, {
            stroke: moss(), strokeWidth: 1.6, roughness: 1.8, seed,
          }),
          rc.line(11, 22, 11, 32, { stroke: moss(), strokeWidth: 1.6, roughness: 1.6, seed }),
          rc.line(5, 32, 17, 32, { stroke: moss(), strokeWidth: 1.6, roughness: 1.6, seed }),
          rc.arc(24, 12, 18, 18, Math.PI * 0.6, Math.PI * 1.1, false, {
            stroke: pencil(), strokeWidth: 1, roughness: 2.4, seed,
          }),
        );
        break;

      case "chart": {
        // Direction B's figure: an engraved-looking scatter with a fitted line.
        const pts: [number, number][] = [];
        for (let i = 0; i < 31; i += 1) {
          const x = 24 + (i / 30) * (w - 48);
          const y = h - 34 - (i / 30) * 42 + Math.sin(i * 2.3) * 16;
          pts.push([x, y]);
        }
        node.append(
          rc.line(24, h - 22, w - 24, h - 22, { stroke: "#2a2724", strokeWidth: 1, roughness: 0.6 }),
          rc.line(24, 8, 24, h - 22, { stroke: "#2a2724", strokeWidth: 1, roughness: 0.6 }),
        );
        for (const [x, y] of pts) {
          node.append(
            rc.circle(x, y, 4, { stroke: "#55504a", strokeWidth: 0.8, roughness: 1.1, seed }),
          );
        }
        node.append(
          rc.line(24, pts[0]![1] + 12, w - 24, pts[30]![1] - 6, {
            stroke: "#3d5c40", strokeWidth: 2.2, roughness: 0.8, seed,
          }),
        );
        break;
      }
    }
  }
}

/* ---------------------------------------------------------------- direction C
   A globe with migration actually moving on it.

   Canvas rather than MapLibre, because this is a mock and the question is whether motion earns
   the screen -- not whether MapLibre can do it. In the real thing this is a MapLibre layer fed by
   the track data, or a deck.gl TripsLayer.
*/
interface Bird {
  from: [number, number];
  to: [number, number];
  t: number;
  speed: number;
}

function globe(canvas: HTMLCanvasElement): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Rough flyway endpoints: breeding grounds to wintering grounds, lon/lat.
  const routes: [[number, number], [number, number]][] = [
    [[-95, 55], [-90, 20]], [[-110, 50], [-103, 18]], [[-80, 48], [-72, 12]],
    [[-120, 58], [-108, 24]], [[-70, 52], [-60, 5]], [[-100, 60], [-95, 15]],
    [[-88, 45], [-84, 10]], [[-115, 52], [-105, 22]], [[-75, 44], [-66, 8]],
  ];
  const birds: Bird[] = [];
  for (let i = 0; i < 320; i += 1) {
    const route = routes[i % routes.length]!;
    const jitter = (v: number) => v + (Math.random() - 0.5) * 9;
    birds.push({
      from: [jitter(route[0][0]), jitter(route[0][1])],
      to: [jitter(route[1][0]), jitter(route[1][1])],
      t: Math.random(),
      speed: 0.0012 + Math.random() * 0.0022,
    });
  }

  let spin = -95;
  const size = () => {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * devicePixelRatio;
    canvas.height = rect.height * devicePixelRatio;
  };
  size();
  addEventListener("resize", size);

  // Orthographic projection: only the facing hemisphere, which is what makes it read as a globe.
  const project = (lon: number, lat: number, cx: number, cy: number, r: number) => {
    const p = ((lon - spin) * Math.PI) / 180;
    const l = (lat * Math.PI) / 180;
    const l0 = (28 * Math.PI) / 180;
    const cosc = Math.sin(l0) * Math.sin(l) + Math.cos(l0) * Math.cos(l) * Math.cos(p);
    if (cosc < 0) return null;
    return [
      cx + r * Math.cos(l) * Math.sin(p),
      cy - r * (Math.cos(l0) * Math.sin(l) - Math.sin(l0) * Math.cos(l) * Math.cos(p)),
    ] as [number, number];
  };

  function frame(): void {
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w * 0.58;
    const cy = h * 0.52;
    const r = Math.min(w, h) * 0.42;

    ctx.clearRect(0, 0, w, h);

    // The sphere.
    const sea = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.35, r * 0.1, cx, cy, r);
    sea.addColorStop(0, "#1d4a5e");
    sea.addColorStop(1, "#0a1c26");
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = sea;
    ctx.fill();

    // Graticule, so the rotation is legible.
    ctx.strokeStyle = "rgba(140,180,200,0.13)";
    ctx.lineWidth = devicePixelRatio;
    for (let lat = -60; lat <= 60; lat += 30) {
      ctx.beginPath();
      let started = false;
      for (let lon = -180; lon <= 180; lon += 3) {
        const p = project(lon, lat, cx, cy, r);
        if (!p) { started = false; continue; }
        if (started) ctx.lineTo(p[0], p[1]); else { ctx.moveTo(p[0], p[1]); started = true; }
      }
      ctx.stroke();
    }
    for (let lon = -180; lon < 180; lon += 30) {
      ctx.beginPath();
      let started = false;
      for (let lat = -85; lat <= 85; lat += 3) {
        const p = project(lon, lat, cx, cy, r);
        if (!p) { started = false; continue; }
        if (started) ctx.lineTo(p[0], p[1]); else { ctx.moveTo(p[0], p[1]); started = true; }
      }
      ctx.stroke();
    }

    // The birds. A comet: a bright head with a fading tail behind it along its own route.
    for (const bird of birds) {
      bird.t += bird.speed;
      if (bird.t > 1.15) bird.t = -0.15;
      for (let tail = 0; tail < 6; tail += 1) {
        const t = bird.t - tail * 0.018;
        if (t < 0 || t > 1) continue;
        const lon = bird.from[0] + (bird.to[0] - bird.from[0]) * t;
        // Curved, because a flyway is not a straight line on a sphere.
        const lat = bird.from[1] + (bird.to[1] - bird.from[1]) * t + Math.sin(t * Math.PI) * 3;
        const p = project(lon, lat, cx, cy, r);
        if (!p) continue;
        const fade = (1 - tail / 6) * (1 - Math.abs(t - 0.5) * 0.5);
        ctx.beginPath();
        ctx.arc(p[0], p[1], (tail === 0 ? 2.1 : 1.5) * devicePixelRatio, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 205, 120, ${fade * 0.85})`;
        ctx.fill();
      }
    }

    // Limb light, so the sphere has an edge.
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(150,200,225,0.25)";
    ctx.lineWidth = 1.5 * devicePixelRatio;
    ctx.stroke();

    spin += 0.035;
    requestAnimationFrame(frame);
  }
  frame();
}

draw();
addEventListener("resize", draw);
document.getElementById("dark")?.addEventListener("change", (event) => {
  document.body.classList.toggle("dark", (event.target as HTMLInputElement).checked);
  draw();
});
for (const button of document.querySelectorAll<HTMLButtonElement>(".picker button")) {
  button.addEventListener("click", () =>
    document.getElementById(button.dataset.go ?? "")?.scrollIntoView({ behavior: "smooth" }),
  );
}

const canvas = document.getElementById("c-globe");
if (canvas instanceof HTMLCanvasElement) globe(canvas);
