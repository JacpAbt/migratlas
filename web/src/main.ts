/**
 * Entry point.
 *
 * One page: a claim first, with the globe live behind it. See ADR 0007 for the eight decisions this
 * shell implements and for what it replaced -- a layer switcher that made a *layer* the first-class
 * thing, where the project's asset is that every number carries its own audit.
 */

import { mount } from "svelte";

import Shell from "./lib/shell/Shell.svelte";

import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const target = document.getElementById("app");
if (!target) throw new Error("no #app to mount into");

mount(Shell, { target, props: { base: import.meta.env.BASE_URL } });
