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

const base = import.meta.env.BASE_URL;

/*
 * `?book` opens the book instead of the arrival, while it is being built.
 *
 * ADR 0013's build order is spike, then shell, then chapters, then the world, and the shell is not
 * finished until it carries the introduction, the plates and the world -- so the default stays the
 * arrival until it does. A flag rather than a branch inside `Shell.svelte`: the book is not a mode
 * of the old shell, it replaces it, and threading it through 750 lines of a component due for
 * retirement would make both harder to read and the switch harder to make.
 *
 * The flag and this comment go when the book becomes the default.
 */
if (new URLSearchParams(location.search).has("book")) {
  const [{ default: Reader }, { loadLedger }, introduction, sandbox, response] = await Promise.all([
    import("./lib/book/Reader.svelte"),
    import("./lib/ledger"),
    import("./lib/book/introduction"),
    import("./lib/sandbox/sandbox"),
    import("./lib/sandbox/response"),
  ]);
  /*
    All four documents before the first frame, because the book's page count is computed from them.

    How many passages the introduction has, and which claims carry an audit or a dial, decide how
    many spreads there are -- so a folio printed before they land is a folio that renumbers itself
    under the reader, and a link to a page opens a different page. A book cannot count its own pages
    later. Together they are 56 KB; the 460 KB assessment behind one figure is still fetched lazily
    by `Figure.svelte`, because that one changes nothing about where the pages fall.

    Each is allowed to fail on its own. A missing document costs the pages it would have filled and
    says so on the leaf, which is the treatment `Plate` already gives a basemap that will not load --
    not a blank book.
  */
  const soft = <T,>(work: Promise<T>): Promise<T | null> => work.catch(() => null);
  const [ledger, opening, safeguards, dial] = await Promise.all([
    loadLedger(base),
    soft(introduction.loadIntroduction(base)),
    soft(sandbox.loadSandbox(base)),
    soft(response.loadResponse(base)),
  ]);
  mount(Reader, {
    target,
    props: { findings: ledger.findings, base, opening, safeguards, dial },
  });
} else {
  mount(Shell, { target, props: { base } });
}
