/**
 * Entry point.
 *
 * The book is the site, and it is the only thing here now. ADR 0013 set the build order -- spike,
 * shell, chapters, world -- and ADR 0015 the shape of a page.
 *
 * ADR 0007's eight decisions were about the arrival that came before it, and most of them outlived
 * the component that implemented them: a claim first, the audit beside the number, nothing behind a
 * control. That is why the book inherited the claim, the safeguards, the search, the tools and the
 * drawn furniture rather than replacing any of them -- the measure of a structural rebuild is what
 * did not have to be written twice.
 */

import { mount } from "svelte";

import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const target = document.getElementById("app");
if (!target) throw new Error("no #app to mount into");

const base = import.meta.env.BASE_URL;

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
  loadLedger(base).catch((error: unknown) => error as Error),
  soft(introduction.loadIntroduction(base)),
  soft(sandbox.loadSandbox(base)),
  soft(response.loadResponse(base)),
]);

/*
  The ledger is the one document there is no book without, and saying so is the point.

  The shell it replaced degraded to a globe with a broken panel, because layers were its subject.
  Here the claims are, so there is nothing to carry on with -- and the honest failure is to state
  what happened rather than to reject unhandled and leave a blank page, which is a mode that is
  invisible until it happens in production. `globe.spec.ts` asserts it with a 404 for that reason.

  Written into the DOM rather than mounted as a component: whatever is wrong, this has to work.
*/
if (ledger instanceof Error) {
  const notice = document.createElement("p");
  notice.className = "boot-failure";
  notice.setAttribute("role", "status");
  notice.textContent = "The findings did not load, so there is nothing to set. ";
  const detail = document.createElement("span");
  detail.className = "boot-failure__detail";
  detail.textContent = ledger.message;
  notice.append(detail);
  target.replaceChildren(notice);
} else {
  mount(Reader, {
    target,
    props: { findings: ledger.findings, base, opening, safeguards, dial },
  });
}
