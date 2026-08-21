/**
 * Entry point.
 *
 * The book is the site. ADR 0013 set the build order -- spike, shell, chapters, world -- and ADR
 * 0015 the shape of a page; the book now carries the introduction, the plates, the evidence, the
 * world and a phone container of its own, so it is the front door rather than a flag behind one.
 *
 * `?shell` still opens the arrival that came before it, and only until its tests have moved. ADR
 * 0007's eight decisions were about that arrival and most of them outlived it -- a claim first, the
 * audit beside the number, nothing behind a control -- which is why the book inherited its claim
 * component, its safeguards and its search rather than replacing them.
 */

import { mount } from "svelte";

import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const target = document.getElementById("app");
if (!target) throw new Error("no #app to mount into");

const base = import.meta.env.BASE_URL;

if (new URLSearchParams(location.search).has("shell")) {
  const { default: Shell } = await import("./lib/shell/Shell.svelte");
  mount(Shell, { target, props: { base } });
} else {
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
}
