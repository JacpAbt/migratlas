/**
 * Entry point for the component preview at `/claims.html`.
 *
 * Separate from `main.ts` on purpose: the globe stays exactly as it is, with its 15 browser tests
 * passing, while the notebook components are built and judged in isolation. The shell replaces
 * `index.html` only once there is something worth putting in it.
 */

import { mount } from "svelte";

import Preview from "./lib/Preview.svelte";

import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const target = document.getElementById("app");
if (!target) throw new Error("no #app to mount into");

mount(Preview, { target, props: { base: import.meta.env.BASE_URL } });
