/**
 * The table the journal lies on, as a real scene: a camera above a walnut table, models with real
 * materials, daylight from the upper left, and at night a candle whose flame is the only light.
 *
 * The book itself stays HTML on top of this canvas, so the camera looks straight down -- the one
 * view in which a flat page and a table can share a picture -- and is placed so that the book's
 * rectangle on the screen covers exactly a book-sized rectangle of the table. Everything else is
 * then where perspective puts it: things near the window's edges show their sides, tall things lean
 * away from the centre, and the book casts its shadow on the wood.
 *
 * Models: Poly Haven (CC0), shrunk for the web -- see `web/public/desk/README.md`.
 */

import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { flameTexture, glowTexture, match, matchbox, mug, pencil, smokeTexture } from "./props";

export interface Desk {
  /** Fit the camera and the things on the table to the window and the book again. */
  place(): void;
  /** Light the candle or put it out; `animate` plays the match, or the smoke. */
  setLit(lit: boolean, animate: boolean): void;
  dispose(): void;
}

/**
 * The open journal's width on the table, in metres: a large sketchbook, two leaves a little over A4.
 * Everything else is at its real size against it -- a mug is 8.6 cm across -- so this sets how much
 * of the margin the things on the desk take.
 */
const BOOK_W = 0.56;
/**
 * How high the camera is above the table, which is how strongly tall things lean away from the
 * centre. From 1.7 m a 26 cm candle at the window's edge leaned 15 cm and read as lying down; this
 * is the long lens of a flat-lay photograph, where it leans by about its own width.
 */
const CAMERA_HEIGHT = 4.5;
/** How long the match takes, from the box to the wick and away. */
const STRIKE = 3.4;

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
/** Where `t` is between `a` and `b`, eased, clamped. */
const span = (t: number, a: number, b: number) => ease(clamp01((t - a) / (b - a)));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export async function createDesk(
  canvas: HTMLCanvasElement,
  book: HTMLElement,
  base: string,
  initiallyLit: boolean,
  onState: (state: "lit" | "out" | "lighting") => void,
): Promise<Desk> {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  // A background, under a page: drawn at one pixel per CSS pixel, which no one reading the page sees.
  renderer.setPixelRatio(1);
  // AgX rather than ACES: ACES pushed the wood's oranges toward neon under the sun and the candle.
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  /* Nothing that casts a shadow moves except when the table is laid out again, so the shadows are
     drawn then and not on every frame: a flickering candle changes how bright its light is, not
     where its shadows fall. A point light's shadow is six renders, and per frame that was enough to
     stall a software renderer outright. */
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#120c08");
  const pmrem = new THREE.PMREMGenerator(renderer);
  /** The room the varnish and the brass reflect; handed to each material below, not to the scene. */
  const room = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(12, 1, 0.1, 10);
  camera.position.set(0, CAMERA_HEIGHT, 0);
  camera.up.set(0, 0, -1);
  camera.lookAt(0, 0, 0);

  // --- The light: daylight, and the night that replaces it ---------------------------------------
  const sky = new THREE.HemisphereLight("#fff3e2", "#3b2416", 1);
  const sun = new THREE.DirectionalLight("#fff0dc", 1);
  /* From a window on the far side of the table, a little to the right, so every shadow falls toward
     the reader the way the book's own CSS shadow does. From the upper left, the candle's shadow ran
     under the book -- which is HTML and cannot receive it -- and was cut off at the page's edge. */
  sun.position.set(0.35, 2.2, -2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.bias = -0.0004;
  // A texel or two. At 1 cm it lifted the table out of the book's shadow, which is 2 cm tall.
  sun.shadow.normalBias = 0.002;
  sun.shadow.radius = 6;
  scene.add(sky, sun, sun.target);

  const candleLight = new THREE.PointLight("#ff9a45", 0, 1.6, 2);
  candleLight.castShadow = true;
  candleLight.shadow.mapSize.set(512, 512);
  candleLight.shadow.bias = -0.002;
  candleLight.shadow.radius = 4;
  scene.add(candleLight);

  // --- The table ------------------------------------------------------------------------------------
  const textures = new THREE.TextureLoader();
  const load = (name: string, color: boolean) =>
    new Promise<THREE.Texture>((resolve, reject) =>
      textures.load(
        `${base}desk/${name}`,
        (texture) => {
          texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
          texture.repeat.set(5, 4);
          texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
          if (color) texture.colorSpace = THREE.SRGBColorSpace;
          resolve(texture);
        },
        undefined,
        reject,
      ),
    );
  const [woodColor, woodNormal] = await Promise.all([
    load("wood_diff.webp", true),
    load("wood_nor.webp", false),
  ]);
  const table = new THREE.Mesh(
    new THREE.PlaneGeometry(4, 3),
    new THREE.MeshPhysicalMaterial({
      map: woodColor,
      normalMap: woodNormal,
      // Waxed, not lacquered: the scanned roughness made the varnish a mirror for the sun.
      roughness: 0.62,
      specularIntensity: 0.35,
      envMapIntensity: 0.25,
    }),
  );
  table.rotation.x = -Math.PI / 2;
  table.receiveShadow = true;
  scene.add(table);

  /* The book: never drawn -- the page is HTML above this canvas -- but it is on the table, so it
     casts its shadow there and keeps the candle's light off what lies under it. */
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(BOOK_W, 0.022, BOOK_W / 1.58),
    new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false }),
  );
  slab.position.y = 0.011;
  slab.castShadow = true;
  scene.add(slab);

  // --- The things on it -------------------------------------------------------------------------------
  const gltf = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const model = async (name: string) => {
    const loaded = await gltf.loadAsync(`${base}desk/${name}.glb`);
    loaded.scene.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    });
    return loaded.scene;
  };
  const [holder, compass] = await Promise.all([model("brass_candleholders"), model("seadogs_compass")]);

  // The candle in its brass holder, centred on its own base and scaled to a desk candle's height.
  const candle = new THREE.Group();
  holder.position.set(0, 0, 0);
  const holderBox = new THREE.Box3().setFromObject(holder);
  holder.position.x -= (holderBox.min.x + holderBox.max.x) / 2;
  holder.position.z -= (holderBox.min.z + holderBox.max.z) / 2;
  candle.add(holder);
  const candleHeight = holderBox.max.y;
  const candleScale = 0.26 / candleHeight;
  candle.scale.setScalar(candleScale);
  // In the candle's own, unscaled coordinates: the top of the wax, and a few millimetres above it.
  const wickTop = new THREE.Vector3(0, candleHeight + 0.004 / candleScale, 0);

  compass.scale.setScalar(1.15);
  const compassGroup = new THREE.Group().add(compass);

  const box = matchbox();
  const boxGroup = new THREE.Group().add(box);
  const pen = pencil();
  const penGroup = new THREE.Group().add(pen);
  const cup = mug();
  const cupGroup = new THREE.Group().add(cup);
  scene.add(candle, compassGroup, boxGroup, penGroup, cupGroup);

  // --- The flame, its light, its smoke ----------------------------------------------------------------
  const flameMap = flameTexture();
  const glowMap = glowTexture();
  const smokeMap = smokeTexture();
  const additive = (map: THREE.Texture) =>
    new THREE.SpriteMaterial({ map, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true });
  const flame = new THREE.Sprite(additive(flameMap));
  flame.center.set(0.5, 0.06);
  const halo = new THREE.Sprite(additive(glowMap));
  const smoke = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: smokeMap, depthWrite: false, transparent: true, opacity: 0 }),
  );
  smoke.center.set(0.5, 0.02);
  scene.add(flame, halo, smoke);

  // The match, with its own flame and a little light of its own while it burns.
  const theMatch = match();
  const matchFlame = new THREE.Sprite(additive(flameMap));
  matchFlame.center.set(0.5, 0.06);
  const matchHalo = new THREE.Sprite(additive(glowMap));
  const matchLight = new THREE.PointLight("#ffab55", 0, 1.2, 2);
  const matchSmoke = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: smokeMap, depthWrite: false, transparent: true, opacity: 0 }),
  );
  matchSmoke.center.set(0.5, 0.02);
  /* Hidden until a strike shows them. A sprite starts visible and a metre across: left so, the
     match's flame stood a metre tall at the table's centre, a white glare above the book by day. */
  theMatch.group.visible = false;
  matchFlame.visible = matchHalo.visible = matchSmoke.visible = smoke.visible = false;
  // It moves, and a moving shadow would mean redrawing the shadows every frame.
  theMatch.group.traverse((node) => (node.castShadow = false));
  scene.add(theMatch.group, matchFlame, matchHalo, matchLight, matchSmoke);

  const sparkGeometry = new THREE.BufferGeometry();
  const sparkCount = 14;
  sparkGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(sparkCount * 3), 3));
  const sparkSpeeds = Array.from({ length: sparkCount }, () =>
    new THREE.Vector3((Math.random() - 0.2) * 0.25, Math.random() * 0.2, (Math.random() - 0.5) * 0.2),
  );
  const sparks = new THREE.Points(
    sparkGeometry,
    new THREE.PointsMaterial({
      color: "#ffcf7a",
      size: 0.0022,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
    }),
  );
  sparks.visible = false;
  scene.add(sparks);

  /* Each material gets the room as its own map. Given through `scene.environment`, three.js
     overwrites every material's `envMapIntensity` with the scene's one number, so the waxed table
     and the coffee reflected the room as brightly as the brass. Night dims each from its own level. */
  const reflective = new Map<THREE.MeshStandardMaterial, number>();
  scene.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    for (const material of [mesh.material].flat()) {
      if (!(material instanceof THREE.MeshStandardMaterial) || reflective.has(material)) continue;
      material.envMap = room;
      reflective.set(material, material.envMapIntensity);
    }
  });

  // --- Where everything is, from the book's place on the screen ---------------------------------------
  let k = 1;
  let width = 1;
  let height = 1;
  const toTable = (sx: number, sy: number) => new THREE.Vector3((sx - width / 2) / k, 0, (sy - height / 2) / k);

  const anchors = {
    candle: new THREE.Vector3(),
    box: new THREE.Vector3(),
  };

  function place(): void {
    const rect = canvas.getBoundingClientRect();
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    const bookRect = book.getBoundingClientRect();
    const left = bookRect.left - rect.left;
    const top = bookRect.top - rect.top;
    const bw = bookRect.width;
    const bh = bookRect.height;
    // Pixels per metre on the table, from the book's own width; the camera's field of view follows.
    k = bw / BOOK_W;
    camera.aspect = width / height;
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(height / 2 / (k * CAMERA_HEIGHT)));
    camera.updateProjectionMatrix();

    const H = bh;
    const at = (sx: number, sy: number) => toTable(left + sx, top + sy);
    slab.position.copy(at(bw / 2, bh / 2)).setY(0.011);

    anchors.candle.copy(at(-0.075 * H, bh - 0.3 * H));
    candle.position.copy(anchors.candle);
    anchors.box.copy(at(-0.085 * H, bh - 0.05 * H));
    boxGroup.position.copy(anchors.box);
    boxGroup.rotation.y = 0.18;
    penGroup.position.copy(at(-0.13 * H, 0.38 * H));
    penGroup.rotation.y = 0.42;
    // Clear of the book and its thumb tabs, which stand out 0.045H: nothing here may pass under them.
    cupGroup.position.copy(at(bw + 0.18 * H, 0.16 * H));
    cupGroup.rotation.y = 0.9;
    compassGroup.position.copy(at(bw + 0.14 * H, bh + 0.02 * H));
    compassGroup.rotation.y = -0.5;

    // The daylight's shadows cover what the camera sees.
    const reach = Math.max(width, height) / k / 2 + 0.2;
    const shadowCamera = sun.shadow.camera;
    shadowCamera.left = -reach;
    shadowCamera.right = reach;
    shadowCamera.top = reach;
    shadowCamera.bottom = -reach;
    shadowCamera.near = 0.1;
    shadowCamera.far = 6;
    shadowCamera.updateProjectionMatrix();

    const wick = candle.localToWorld(wickTop.clone());
    candleLight.position.copy(wick).add(new THREE.Vector3(0, 0.012, 0));
    orient(flame, wick, 0.026);
    halo.position.copy(wick).add(new THREE.Vector3(0, 0.01, 0));
    smoke.position.copy(wick);
    renderer.shadowMap.needsUpdate = true;
    requestRender();
  }

  /*
    A flame stands up from its wick, so on the screen it points the way "up" projects at that place
    -- outward from the window's centre, foreshortened by how steeply the camera sees it. Drawn as a
    camera-facing sprite turned and shortened to match, with a floor on the shortening so a flame
    seen from almost straight above still reads as a flame.
  */
  const probe = new THREE.Vector3();
  function orient(sprite: THREE.Sprite, base: THREE.Vector3, size: number): void {
    sprite.position.copy(base);
    const a = probe.copy(base).project(camera);
    const ax = a.x;
    const ay = a.y;
    const b = probe.copy(base).add(new THREE.Vector3(0, size, 0)).project(camera);
    const dx = (b.x - ax) * camera.aspect;
    const dy = b.y - ay;
    const c = probe.copy(base).add(new THREE.Vector3(size, 0, 0)).project(camera);
    const across = Math.hypot((c.x - ax) * camera.aspect, c.y - ay) || 1;
    const along = Math.hypot(dx, dy);
    const foreshorten = Math.max(0.5, Math.min(1, along / across));
    (sprite.material as THREE.SpriteMaterial).rotation = Math.atan2(-dx, dy);
    sprite.scale.set(size * 0.55, size * foreshorten, 1);
  }

  // --- The states between day and night ----------------------------------------------------------------
  let lit = initiallyLit;
  /** How much of the night has come in, 0..1, and the candle's strength, 0..1. */
  let night = initiallyLit ? 1 : 0;
  let strength = initiallyLit ? 1 : 0;
  let strike: number | null = null;
  let snuff: number | null = null;
  let fromNight = night;

  function light(nightAmount: number, candleStrength: number, time: number): void {
    const flicker = candleStrength > 0
      ? 1 + 0.07 * Math.sin(time * 11.3) + 0.05 * Math.sin(time * 23.7 + 1.3) + 0.04 * Math.sin(time * 5.1)
      : 1;
    /* By day the sun is most of the light. With the sky and the room nearly its equal, a shadow was
       19% darker than the wood beside it and the things on the table looked pasted on; at these, it
       is about half as bright, measured on the bare table. */
    sky.intensity = lerp(0.3, 0.015, nightAmount);
    sun.intensity = lerp(3.4, 0, nightAmount);
    const roomLight = lerp(0.2, 0.02, nightAmount);
    for (const [material, level] of reflective) material.envMapIntensity = level * roomLight;
    renderer.toneMappingExposure = lerp(1, 1.1, nightAmount);
    // A candle is about one candela; the room is dark enough that it is the light.
    candleLight.intensity = 0.32 * candleStrength * flicker;
    flame.visible = halo.visible = candleStrength > 0.001;
    flame.material.opacity = Math.min(1, candleStrength * 1.2);
    const s = 0.026 * candleStrength * (0.96 + 0.06 * Math.sin(time * 9.7));
    orient(flame, candleLight.position.clone().add(new THREE.Vector3(0, -0.012, 0)), Math.max(s, 0.0001));
    halo.scale.setScalar(0.11 * candleStrength * flicker);
    halo.material.opacity = 0.55 * candleStrength;
  }

  function matchAt(t: number, wick: THREE.Vector3): void {
    const p = t / STRIKE;
    const group = theMatch.group;
    group.visible = p < 0.97;
    const boxPos = anchors.box;
    const along = new THREE.Vector3(Math.cos(0.18), 0, -Math.sin(0.18));
    const side = new THREE.Vector3(Math.sin(0.18), 0, Math.cos(0.18));
    const start = boxPos.clone().addScaledVector(along, -0.026).addScaledVector(side, 0.021).setY(0.01);
    const end = boxPos.clone().addScaledVector(along, 0.03).addScaledVector(side, 0.021).setY(0.01);
    const offstage = boxPos.clone().add(new THREE.Vector3(-0.18, 0.06, 0.14));
    const lifted = end.clone().add(new THREE.Vector3(0.01, 0.06, -0.02));
    const atWick = wick.clone().add(new THREE.Vector3(0.006, -0.004, 0.004));
    const away = wick.clone().add(new THREE.Vector3(-0.07, -0.08, 0.06));
    const rest = away.clone().add(new THREE.Vector3(-0.02, -0.03, 0.03));
    let pos: THREE.Vector3;
    if (p < 0.16) pos = offstage.clone().lerp(start, span(p, 0, 0.16));
    else if (p < 0.23) pos = start.clone().lerp(end, clamp01((p - 0.16) / 0.07));
    else if (p < 0.3) pos = end.clone().lerp(lifted, span(p, 0.23, 0.3));
    else if (p < 0.46) pos = lifted.clone().lerp(atWick, span(p, 0.3, 0.46));
    else if (p < 0.6) pos = atWick.clone();
    else if (p < 0.7) pos = atWick.clone().lerp(away, span(p, 0.6, 0.7));
    else pos = away.clone().lerp(rest, span(p, 0.7, 0.92));
    group.position.copy(pos);
    // Held from below-left, tilted up toward the hand, and shaken out after.
    const shake = p > 0.7 && p < 0.84 ? Math.sin((p - 0.7) * 120) * 0.35 * (1 - (p - 0.7) / 0.14) : 0;
    group.rotation.set(0, 2.4 + shake, 0.42);

    const burning = p >= 0.215 && p < 0.78;
    const flare = p < 0.3 ? 1 + 0.9 * Math.max(0, 1 - Math.abs(p - 0.24) / 0.05) : 1;
    const dying = p > 0.66 ? clamp01(1 - (p - 0.66) / 0.12) : 1;
    const size = burning ? 0.014 * flare * dying : 0;
    const head = group.localToWorld(new THREE.Vector3(0, 0, 0));
    matchFlame.visible = matchHalo.visible = burning;
    if (burning) {
      orient(matchFlame, head, Math.max(size, 0.0001));
      matchHalo.position.copy(head);
      matchHalo.scale.setScalar(0.07 * flare * dying);
      matchHalo.material.opacity = 0.6 * dying;
    }
    matchLight.position.copy(head).add(new THREE.Vector3(0, 0.01, 0));
    matchLight.intensity = burning ? 0.35 * flare * dying : 0;
    theMatch.head.visible = p < 0.28;
    theMatch.char.visible = p >= 0.28;

    // Sparks off the striker as the head catches.
    const sparkT = (p - 0.21) / 0.09;
    sparks.visible = sparkT > 0 && sparkT < 1;
    if (sparks.visible) {
      const positions = sparkGeometry.getAttribute("position") as THREE.BufferAttribute;
      for (let i = 0; i < sparkCount; i++) {
        const v = sparkSpeeds[i]!;
        positions.setXYZ(i, end.x + v.x * sparkT * 0.25, end.y + v.y * sparkT * 0.25, end.z + v.z * sparkT * 0.25);
      }
      positions.needsUpdate = true;
      (sparks.material as THREE.PointsMaterial).opacity = 1 - sparkT;
    }
    // And the smoke when it is shaken out.
    const smokeT = (p - 0.78) / 0.2;
    matchSmoke.visible = smokeT > 0 && smokeT < 1;
    if (matchSmoke.visible) {
      orient(matchSmoke, head, 0.03 + 0.03 * smokeT);
      matchSmoke.material.opacity = 0.5 * Math.sin(Math.PI * smokeT);
    }
  }

  // --- The loop: running only while something moves ---------------------------------------------------
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clock = new THREE.Clock();
  let dirty = true;
  let lastFrame = 0;

  function frame(): void {
    const time = clock.getElapsedTime();
    const wick = candleLight.position.clone().add(new THREE.Vector3(0, -0.012, 0));
    if (strike !== null) {
      const t = time - strike;
      const p = t / STRIKE;
      night = lerp(fromNight, 1, span(p, 0, 0.26));
      strength = p < 0.56 ? 0 : p < 0.66 ? lerp(0.1, 1.15, span(p, 0.56, 0.66)) : lerp(1.15, 1, span(p, 0.66, 0.8));
      matchAt(t, wick);
      if (p >= 1) {
        strike = null;
        theMatch.group.visible = false;
        matchFlame.visible = matchHalo.visible = matchSmoke.visible = sparks.visible = false;
        matchLight.intensity = 0;
        night = 1;
        strength = 1;
        onState("lit");
      }
    } else if (snuff !== null) {
      const t = time - snuff;
      strength = 1 - span(t, 0, 0.45);
      night = lerp(fromNight, 0, span(t, 0.1, 1.1));
      const smokeT = t / 2.4;
      smoke.visible = smokeT < 1;
      orient(smoke, wick, 0.04 + 0.05 * smokeT);
      smoke.material.opacity = 0.55 * Math.sin(Math.PI * clamp01(smokeT));
      if (t > 2.4) {
        snuff = null;
        smoke.visible = false;
        night = 0;
        strength = 0;
      }
    }
    light(night, strength, time);
    renderer.render(scene, camera);
    dirty = false;
  }

  function tick(now: number): void {
    const animating = strike !== null || snuff !== null;
    const flickering = !still && strength > 0;
    // A flame flickering on its own is drawn at about 20 frames a second; a match, at every frame.
    if (!animating && flickering && now - lastFrame < 50) return;
    if (!animating && !flickering && !dirty) {
      renderer.setAnimationLoop(null);
      return;
    }
    lastFrame = now;
    frame();
  }

  function requestRender(): void {
    dirty = true;
    renderer.setAnimationLoop(tick);
  }

  function setLit(next: boolean, animate: boolean): void {
    if (next === lit) return;
    lit = next;
    fromNight = night;
    const time = clock.getElapsedTime();
    if (next) {
      snuff = null;
      smoke.visible = false;
      if (animate && !still) {
        strike = time;
        onState("lighting");
      } else {
        night = 1;
        strength = 1;
        onState("lit");
      }
    } else {
      strike = null;
      theMatch.group.visible = false;
      matchFlame.visible = matchHalo.visible = matchSmoke.visible = sparks.visible = false;
      matchLight.intensity = 0;
      if (animate && !still) snuff = time;
      else {
        night = 0;
        strength = 0;
      }
      onState("out");
    }
    requestRender();
  }

  const onVisibility = () => {
    if (document.hidden) renderer.setAnimationLoop(null);
    else requestRender();
  };
  document.addEventListener("visibilitychange", onVisibility);

  place();
  onState(lit ? "lit" : "out");

  return {
    place,
    setLit,
    dispose() {
      document.removeEventListener("visibilitychange", onVisibility);
      renderer.setAnimationLoop(null);
      scene.traverse((node) => {
        const mesh = node as THREE.Mesh;
        mesh.geometry?.dispose();
        const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
        for (const m of Array.isArray(material) ? material : material ? [material] : []) m.dispose();
      });
      room.dispose();
      pmrem.dispose();
      renderer.dispose();
    },
  };
}
