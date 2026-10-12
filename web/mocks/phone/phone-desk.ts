/**
 * The desktop's table (`web/src/lib/desk/scene.ts`), laid out for a phone held upright.
 *
 * The same models, wood, light, candle and match. What changes is the layout: the page hands over
 * where its paper lies (the pad, the contents card, the settings strip) and where each thing on the
 * table should stand, in screen pixels; the scene casts the paper's shadows and puts the things there.
 * And it can stop drawing altogether, because on a phone the table is only seen between readings.
 */

import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import {
  flameTexture,
  glowTexture,
  match,
  matchbox,
  mug,
  pencil,
  smokeTexture,
} from "desk-props";

export interface Sheet {
  x: number;
  y: number;
  w: number;
  h: number;
  /** Turned on the table, in degrees, about its centre. */
  angle: number;
  /** How thick it is, in metres: a pad casts a shadow, a card hardly does. */
  thick: number;
}

export interface Layout {
  /** The pad, which also sets the scale: it is `padWidth` metres across. */
  pad: Sheet;
  padWidth: number;
  sheets: Sheet[];
  /** Where each thing stands, in screen pixels. */
  at: Record<"candle" | "box" | "glass" | "pen" | "compass" | "cup", [number, number]>;
  /** Which way the pencil lies, in radians about the vertical: 0 points it right. */
  penTurn: number;
}

export interface PhoneDesk {
  place(layout: Layout): void;
  setLit(lit: boolean, animate: boolean): void;
  /** False stops drawing outright: the table is under the pad, and a phone should not pay for it. */
  setRunning(running: boolean): void;
  /** Where a thing stands on the screen now, for the page's tap targets. */
  screenOf(name: "candle" | "box" | "pen"): [number, number];
  /** Roll the pencil a little where it lies: the table saying that it can be picked up. */
  nudge(): void;
  dispose(): void;
}

const CAMERA_HEIGHT = 4.5;
const STRIKE = 3.4;
const BOX_TURN = 0.12;

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const span = (t: number, a: number, b: number) => ease(clamp01((t - a) / (b - a)));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export async function createPhoneDesk(
  canvas: HTMLCanvasElement,
  /** Where a file of the table lives: a URL, or a blob the page made from what it carries. */
  url: (name: string) => string,
  initiallyLit: boolean,
  onState: (state: "lit" | "out" | "lighting") => void,
): Promise<PhoneDesk> {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  // Unlike the desktop, the table is what the reader is looking at here, so it is drawn sharp.
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#120c08");
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(12, 1, 0.1, 10);
  camera.position.set(0, CAMERA_HEIGHT, 0);
  camera.up.set(0, 0, -1);
  camera.lookAt(0, 0, 0);

  const sky = new THREE.HemisphereLight("#fff3e2", "#3b2416", 1);
  const sun = new THREE.DirectionalLight("#fff0dc", 1);
  sun.position.set(-0.35, 2.2, -2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.002;
  sun.shadow.radius = 6;
  scene.add(sky, sun, sun.target);

  const candleLight = new THREE.PointLight("#ff9a45", 0, 1.6, 2);
  candleLight.castShadow = true;
  candleLight.shadow.mapSize.set(512, 512);
  candleLight.shadow.bias = -0.002;
  candleLight.shadow.radius = 4;
  scene.add(candleLight);

  const textures = new THREE.TextureLoader();
  const load = (name: string, color: boolean) =>
    new Promise<THREE.Texture>((resolve, reject) =>
      textures.load(
        url(name),
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
  const [woodColor, woodNormal] = await Promise.all([load("wood_diff.webp", true), load("wood_nor.webp", false)]);
  const table = new THREE.Mesh(
    new THREE.PlaneGeometry(4, 3),
    new THREE.MeshPhysicalMaterial({
      map: woodColor,
      normalMap: woodNormal,
      roughness: 0.62,
      specularIntensity: 0.35,
      envMapIntensity: 0.25,
    }),
  );
  table.rotation.x = -Math.PI / 2;
  table.receiveShadow = true;
  scene.add(table);

  // The paper: never drawn, it is HTML above the canvas, but it lies on the table and casts shadows.
  const ghost = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false });
  const slabs: THREE.Mesh[] = [];

  const gltf = new GLTFLoader();
  const model = async (name: string) => {
    const loaded = await gltf.loadAsync(url(`${name}.glb`));
    loaded.scene.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      const material = mesh.material as THREE.MeshPhysicalMaterial;
      if (material.transmission > 0) {
        material.transmission = 0;
        material.transparent = true;
        material.opacity = 0.22;
        material.roughness = 0.04;
        material.metalness = 0;
        mesh.castShadow = false;
      }
    });
    return loaded.scene;
  };
  const [holder, compass, magnifier] = await Promise.all([
    model("brass_candleholders"),
    model("seadogs_compass"),
    model("magnifying_glass_01"),
  ]);

  const candle = new THREE.Group();
  const holderBox = new THREE.Box3().setFromObject(holder);
  holder.position.x -= (holderBox.min.x + holderBox.max.x) / 2;
  holder.position.z -= (holderBox.min.z + holderBox.max.z) / 2;
  candle.add(holder);
  const candleHeight = holderBox.max.y;
  const candleScale = 0.26 / candleHeight;
  candle.scale.setScalar(candleScale);
  const wickTop = new THREE.Vector3(0, candleHeight + 0.004 / candleScale, 0);

  compass.scale.setScalar(1.15);
  const compassGroup = new THREE.Group().add(compass);

  const glassScale = 0.8;
  const glassBox = new THREE.Box3().setFromObject(magnifier);
  const lensRadius = ((glassBox.max.x - glassBox.min.x) / 2) * glassScale;
  magnifier.rotation.x = Math.PI / 2;
  magnifier.scale.setScalar(glassScale);
  magnifier.position.set(0, glassBox.max.z * glassScale, -(glassBox.max.y * glassScale - lensRadius));
  const glassGroup = new THREE.Group().add(magnifier);

  const box = matchbox();
  const boxGroup = new THREE.Group().add(box);
  const pen = pencil();
  const penGroup = new THREE.Group().add(pen);
  const cup = mug();
  const cupGroup = new THREE.Group().add(cup);
  scene.add(candle, compassGroup, glassGroup, boxGroup, penGroup, cupGroup);

  const flameMap = flameTexture();
  const glowMap = glowTexture();
  const smokeMap = smokeTexture();
  const additive = (map: THREE.Texture) =>
    new THREE.SpriteMaterial({ map, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true });
  const flame = new THREE.Sprite(additive(flameMap));
  flame.center.set(0.5, 0.06);
  const halo = new THREE.Sprite(additive(glowMap));
  const smoke = new THREE.Sprite(new THREE.SpriteMaterial({ map: smokeMap, depthWrite: false, transparent: true, opacity: 0 }));
  smoke.center.set(0.5, 0.02);
  scene.add(flame, halo, smoke);

  const theMatch = match();
  const matchFlame = new THREE.Sprite(additive(flameMap));
  matchFlame.center.set(0.5, 0.06);
  const matchHalo = new THREE.Sprite(additive(glowMap));
  const matchLight = new THREE.PointLight("#ffab55", 0, 1.2, 2);
  const matchSmoke = new THREE.Sprite(new THREE.SpriteMaterial({ map: smokeMap, depthWrite: false, transparent: true, opacity: 0 }));
  matchSmoke.center.set(0.5, 0.02);
  theMatch.group.visible = false;
  matchFlame.visible = matchHalo.visible = matchSmoke.visible = smoke.visible = false;
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
    new THREE.PointsMaterial({ color: "#ffcf7a", size: 0.0022, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }),
  );
  sparks.visible = false;
  scene.add(sparks);

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

  // --- Where everything is ------------------------------------------------------------------------
  let k = 1;
  let width = 1;
  let height = 1;
  const toTable = (sx: number, sy: number) => new THREE.Vector3((sx - width / 2) / k, 0, (sy - height / 2) / k);
  const anchors = { candle: new THREE.Vector3(), box: new THREE.Vector3() };
  const penHome = new THREE.Vector3();
  /** When the pencil last began to roll, on the scene's clock; null when it lies still. */
  let rolling: number | null = null;

  function place(layout: Layout): void {
    const rect = canvas.getBoundingClientRect();
    width = Math.max(1, canvas.clientWidth || rect.width);
    height = Math.max(1, canvas.clientHeight || rect.height);
    renderer.setSize(width, height, false);
    k = layout.pad.w / layout.padWidth;
    camera.aspect = width / height;
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(height / 2 / (k * CAMERA_HEIGHT)));
    camera.updateProjectionMatrix();

    for (const slab of slabs) scene.remove(slab);
    slabs.length = 0;
    for (const sheet of [layout.pad, ...layout.sheets]) {
      const slab = new THREE.Mesh(new THREE.BoxGeometry(sheet.w / k, sheet.thick, sheet.h / k), ghost);
      slab.position.copy(toTable(sheet.x + sheet.w / 2, sheet.y + sheet.h / 2)).setY(sheet.thick / 2);
      slab.rotation.y = (-sheet.angle * Math.PI) / 180;
      slab.castShadow = true;
      scene.add(slab);
      slabs.push(slab);
    }

    const at = (name: keyof Layout["at"]) => toTable(...layout.at[name]);
    anchors.candle.copy(at("candle"));
    candle.position.copy(anchors.candle);
    anchors.box.copy(at("box"));
    boxGroup.position.copy(anchors.box);
    boxGroup.rotation.y = BOX_TURN;
    cupGroup.position.copy(at("cup"));
    cupGroup.rotation.y = -0.5;
    glassGroup.position.copy(at("glass"));
    glassGroup.rotation.y = 2.3;
    penGroup.position.copy(at("pen"));
    penGroup.rotation.y = layout.penTurn;
    penHome.copy(penGroup.position);
    compassGroup.position.copy(at("compass"));
    compassGroup.rotation.y = 0.25;

    const extent = Math.max(width, height) / k / 2 + 0.2;
    const shadowCamera = sun.shadow.camera;
    shadowCamera.left = -extent;
    shadowCamera.right = extent;
    shadowCamera.top = extent;
    shadowCamera.bottom = -extent;
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

  const probe = new THREE.Vector3();
  function orient(sprite: THREE.Sprite, at: THREE.Vector3, size: number): void {
    sprite.position.copy(at);
    const a = probe.copy(at).project(camera);
    const ax = a.x;
    const ay = a.y;
    const b = probe.copy(at).add(new THREE.Vector3(0, size, 0)).project(camera);
    const dx = (b.x - ax) * camera.aspect;
    const dy = b.y - ay;
    const c = probe.copy(at).add(new THREE.Vector3(size, 0, 0)).project(camera);
    const across = Math.hypot((c.x - ax) * camera.aspect, c.y - ay) || 1;
    const along = Math.hypot(dx, dy);
    const foreshorten = Math.max(0.5, Math.min(1, along / across));
    (sprite.material as THREE.SpriteMaterial).rotation = Math.atan2(-dx, dy);
    sprite.scale.set(size * 0.55, size * foreshorten, 1);
  }

  function screenOf(name: "candle" | "box" | "pen"): [number, number] {
    const at = name === "candle" ? candleLight.position.clone().setY(0.1) : name === "box" ? anchors.box.clone() : penHome.clone();
    const p = at.project(camera);
    return [((p.x + 1) / 2) * width, ((1 - p.y) / 2) * height];
  }

  let lit = initiallyLit;
  let night = initiallyLit ? 1 : 0;
  let strength = initiallyLit ? 1 : 0;
  let strike: number | null = null;
  let snuff: number | null = null;
  let fromNight = night;

  function light(nightAmount: number, candleStrength: number, time: number): void {
    const flicker = candleStrength > 0
      ? 1 + 0.07 * Math.sin(time * 11.3) + 0.05 * Math.sin(time * 23.7 + 1.3) + 0.04 * Math.sin(time * 5.1)
      : 1;
    sky.intensity = lerp(0.3, 0.015, nightAmount);
    sun.intensity = lerp(3.4, 0, nightAmount);
    const roomLight = lerp(0.2, 0.02, nightAmount);
    for (const [material, level] of reflective) material.envMapIntensity = level * roomLight;
    renderer.toneMappingExposure = lerp(1, 1.1, nightAmount);
    candleLight.intensity = 0.32 * candleStrength * flicker;
    flame.visible = halo.visible = candleStrength > 0.001;
    flame.material.opacity = Math.min(1, candleStrength * 1.2);
    const s = 0.026 * candleStrength * (0.96 + 0.06 * Math.sin(time * 9.7));
    orient(flame, candleLight.position.clone().add(new THREE.Vector3(0, -0.012, 0)), Math.max(s, 0.0001));
    halo.scale.setScalar(0.11 * candleStrength * flicker);
    halo.material.opacity = 0.55 * candleStrength;
  }

  // The match, as the desktop strikes it: in from beyond the top edge, along the box, to the wick.
  function matchAt(t: number, wick: THREE.Vector3): void {
    const p = t / STRIKE;
    const group = theMatch.group;
    group.visible = p < 0.97;
    const boxPos = anchors.box;
    const along = new THREE.Vector3(Math.cos(BOX_TURN), 0, -Math.sin(BOX_TURN));
    const side = new THREE.Vector3(Math.sin(BOX_TURN), 0, Math.cos(BOX_TURN));
    const start = boxPos.clone().addScaledVector(along, -0.026).addScaledVector(side, 0.021).setY(0.014);
    const end = boxPos.clone().addScaledVector(along, 0.03).addScaledVector(side, 0.021).setY(0.014);
    const offstage = boxPos.clone().add(new THREE.Vector3(0.03, 0.08, -0.22));
    const lifted = end.clone().add(new THREE.Vector3(0.01, 0.06, -0.03));
    const atWick = wick.clone().add(new THREE.Vector3(-0.005, -0.003, -0.005));
    const away = wick.clone().add(new THREE.Vector3(-0.03, -0.07, -0.08));
    const rest = away.clone().add(new THREE.Vector3(-0.02, -0.03, -0.04));
    let pos: THREE.Vector3;
    if (p < 0.16) pos = offstage.clone().lerp(start, span(p, 0, 0.16));
    else if (p < 0.23) pos = start.clone().lerp(end, clamp01((p - 0.16) / 0.07));
    else if (p < 0.3) pos = end.clone().lerp(lifted, span(p, 0.23, 0.3));
    else if (p < 0.46) pos = lifted.clone().lerp(atWick, span(p, 0.3, 0.46));
    else if (p < 0.6) pos = atWick.clone();
    else if (p < 0.7) pos = atWick.clone().lerp(away, span(p, 0.6, 0.7));
    else pos = away.clone().lerp(rest, span(p, 0.7, 0.92));
    group.position.copy(pos);
    const shake = p > 0.7 && p < 0.84 ? Math.sin((p - 0.7) * 120) * 0.35 * (1 - (p - 0.7) / 0.14) : 0;
    group.rotation.set(0, 1.9 + shake, 0.42);

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
    const smokeT = (p - 0.78) / 0.2;
    matchSmoke.visible = smokeT > 0 && smokeT < 1;
    if (matchSmoke.visible) {
      orient(matchSmoke, head, 0.03 + 0.03 * smokeT);
      matchSmoke.material.opacity = 0.5 * Math.sin(Math.PI * smokeT);
    }
  }

  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clock = new THREE.Clock();
  let dirty = true;
  let lastFrame = 0;
  let running = true;

  function frame(): void {
    const time = clock.getElapsedTime();
    const wick = candleLight.position.clone().add(new THREE.Vector3(0, -0.012, 0));
    if (strike !== null) {
      const p = (time - strike) / STRIKE;
      night = lerp(fromNight, 1, span(p, 0, 0.26));
      strength = p < 0.56 ? 0 : p < 0.66 ? lerp(0.1, 1.15, span(p, 0.56, 0.66)) : lerp(1.15, 1, span(p, 0.66, 0.8));
      matchAt(time - strike, wick);
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
    if (rolling !== null) {
      // A hexagonal pencil rolled a sixth of a turn away and back, travelling as far as it rolls.
      const t = clamp01((time - rolling) / 1.1);
      const turn = 1.05 * Math.sin(Math.PI * t);
      pen.rotation.x = turn;
      const across = new THREE.Vector3(Math.sin(penGroup.rotation.y), 0, Math.cos(penGroup.rotation.y));
      penGroup.position.copy(penHome).addScaledVector(across, turn * 0.0036);
      renderer.shadowMap.needsUpdate = true;
      if (t >= 1) {
        rolling = null;
        pen.rotation.x = 0;
        penGroup.position.copy(penHome);
      }
    }
    light(night, strength, time);
    renderer.render(scene, camera);
    dirty = false;
  }

  function tick(now: number): void {
    if (!running) {
      renderer.setAnimationLoop(null);
      return;
    }
    const animating = strike !== null || snuff !== null || rolling !== null;
    const flickering = !still && strength > 0;
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
    if (running) renderer.setAnimationLoop(tick);
  }

  function setLit(next: boolean, animate: boolean): void {
    if (next === lit) return;
    lit = next;
    fromNight = night;
    const time = clock.getElapsedTime();
    if (next) {
      snuff = null;
      smoke.visible = false;
      if (animate && !still && running) {
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
      if (animate && !still && running) snuff = time;
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

  return {
    place(layout) {
      place(layout);
      frame();
      onState(lit ? "lit" : "out");
    },
    setLit,
    setRunning(next) {
      running = next;
      if (next) requestRender();
      else renderer.setAnimationLoop(null);
    },
    screenOf,
    nudge() {
      if (still) return;
      rolling = clock.getElapsedTime();
      requestRender();
    },
    dispose() {
      document.removeEventListener("visibilitychange", onVisibility);
      renderer.setAnimationLoop(null);
      renderer.dispose();
    },
  };
}
