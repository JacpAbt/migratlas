/**
 * Entry point for the rebuilt shell.
 *
 * A third page while the rebuild runs: `index.html` is the shipped globe with its 15 tests,
 * `claims.html` is the components in isolation, and this is the shell being assembled from them.
 * `index.html` is replaced only when this passes everything that one does.
 */

import { mount } from "svelte";

import Shell from "./lib/shell/Shell.svelte";

import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const target = document.getElementById("app");
if (!target) throw new Error("no #app to mount into");

mount(Shell, { target, props: { base: import.meta.env.BASE_URL } });
