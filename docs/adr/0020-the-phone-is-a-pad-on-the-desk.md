# ADR 0020 — The phone is a pad on the desk

**Status:** accepted · 2026-10-12, when the owner answered the five questions it was proposed with on
2026-10-11 (the last section). Replaces the phone container of [ADR 0015](0015-the-book-on-the-desk.md)
decision 8 (leaves you swipe, chapters on the fore-edge) and the phone half of decision 9 (the
phone's own seams and its overflow rule). The spread, its fit and its guard are untouched.

## Context

On 2026-10-10 the owner said the desktop book is very good and the phone loses most of it. Asked
what was missing, they named **the object** (a book on a lit table) and **the turn** — the phone is
flat paper in a horizontal scroll-snap rail. After the first mock gave it an object, they named a
second loss: *"the journal part ... it's not an object missing, it's the experience"*. Asked which
part, they took all four offered: the glance (a page seen whole before it is read), the second voice
(notes, arrows, rings and marks reacting to the text), writing in progress, and pages that vary.

The cause of the second loss is in the code, not only in the feel. Under 62rem `Claim.svelte` drops
the margin note under its paragraph and hides its arrow (`display: none`), and `pages.ts` gives the
phone one panel per leaf — so every composed page of the spread arrives on the phone as a column of
text.

Four mocks were built on the book's own text, fonts, paper and models, each judged by the owner on a
phone. What each settled:

| Mock | What it tried | Owner's verdict |
| --- | --- | --- |
| 1 | A top-bound pocket pad: pages flip up over a spiral, following the finger; chapter flags on the right edge | Kept — but the journal was still missing |
| 2 | The same finding pages two ways: a lens zooming over big composed pages, and phone pages the hand writes on as you arrive | No zoom: *"the zoom feels like the page was not done for phone"*. The writing kept; the lens's page compositions looked better |
| 3 | Writing only, every page composed at the phone's own size with a narrow margin for notes and marks | Kept |
| 4a–c | The desktop's 3D table as cover and menu, the pad on it | Kept, after two corrections: settings are the things on the table, not a strip or a pop-up; labels on open wood, not always on; chapters live in the notebook |

The mock sources are in `web/mocks/phone/`, as `web/mocks/book.html` was kept for ADR 0015 until the
build retired it.

## Decisions

1. **The phone's object is a top-bound pad.** A page lifts toward the reader and over a drawn wire
   at the top, the point under the finger staying under the finger, as one rigid sheet — the desktop's
   turn went back to one rigid sheet in `1897684`, and the pad keeps that. The stack shows at the foot and
   the card back under it. A dog-eared corner turns forward, the wire turns back, the keyboard does
   both. It answers the reason `Leaves.svelte` gives for scroll-snap — a turn needs somewhere for
   the page to go — because a top-bound page has somewhere: over the top.

2. **Every page is made at the phone's own size, and nothing on it zooms or pans.** Where a page
   has something to say beside its text, it has a margin: a column of about 78px at 375 wide that
   holds the notes, the verdict marks, the ticks, a plate's key and the apparatus sketches, each
   level with what it is about. A note beside its passage is joined to it by a bracket in the
   gutter; a note about words further up the page reaches them with an arrow drawn round the margin,
   never through a line of writing. Pages that only carry prose use the full width.

3. **The hand writes on a page the first time it is read.** Underlines, rings, notes word by word,
   arrows, brackets, verdict marks, a chart's dots year by year and its trend, a plate's tape and
   the circle on it — in the order they were put down. A tap finishes the writing at once. A page
   already read stays written. Under reduced motion every page arrives written.

4. **The desk is the cover and the menu, and it is drawn only while it is seen.** A cold open lands
   on the table with the pad shut on it; touching the pad brings the camera down until the page
   fills the screen; the table button or a pinch puts it down. A link to a page opens the page and
   never the table. While a page is being read the scene renders nothing.

5. **On the table, things are the settings.** The candle (and the matches) is the light, with the
   desktop's match and smoke. The pencil is the hand: each touch rolls it and the pad on the table
   is written again in the next of Hand, Clear and Dyslexia, its name chalked by the pencil for a
   moment in its own letters. The chapters are the pad's own flags, which work on the table too.
   No strip, no card, no pop-up menu. A thing is labelled in chalk on open wood when the table comes
   into view, the label fades after six seconds, and once the thing has been used its label does not
   come back. *System* is the light's default until the candle is first touched.

6. **The phone's pages are measured, not authored.** The core of this ADR, below: the page breaks
   follow the type setting, the screen and the realm, because no fixed set of seams can be right for
   three faces at a dozen phone sizes.

7. **The phone grows type to fill a page and never shrinks it.** The owner refused smaller type as
   the answer to an overflowing leaf when the phone first got its own pages, and the dyslexia setting
   got more paper rather than a lower floor. The mocks broke that rule — their fit shrank pages to
   0.88 at 375×667, and ten pages at 375×812 in the dyslexia setting — and the build must not copy
   it: where the mocks shrank, the book adds a leaf.

   The other things the mocks did only because they were mocks: the models embedded as base64 and
   stored without meshopt (an artifact would not take them as files, and might not run the decoder's
   WebAssembly), a second copy of the desk scene, chapters cut to their opening page, and flows
   checked by state while the browser pane was hidden. None of it carries over.

8. **The guard walks every type at every phone size, and allows no overflow.** It replaces today's
   phone guard, which walks the hand alone at 375×812 and admits a leaf that holds one indivisible
   thing.

## Pagination that follows the type

### What is there now, and why it cannot stay

`pages.ts` arranges the same panels twice: the spread pads each section to an even page count, the
phone concatenates and splits a few panel kinds at authored seams (`said`/`matters`, `value`/
`caveat`, `first`/`rest`). The seams were measured in the hand at 375×812. The dyslexia setting gets
its own *spread* arrangement (`ROOMY_TYPES`), but the phone has one arrangement for all three faces,
and its guard (`book.spec.ts`, *no leaf overflows unless it holds one indivisible thing*) walks only
the hand. Recorded on 2026-09-24 and not re-measured since: in the dyslexia setting 6 of 165 phone
leaves overflow with mixed content, by 13 to 178px.

The pad makes this worse in three ways at once: the spiral, the stack and the flags take height and
width from every leaf; the margin narrows the text column on composed pages; and a leaf can no longer
scroll, because a vertical drag on a page now turns it. Authoring a fourth set of seams for that
geometry would fit one phone in one face.

### The design

**Blocks.** Every phone panel becomes an ordered list of blocks with stable ids
(`autumn-advance.record.caveat`), each carrying one rule:

| Rule | Meaning | Examples |
| --- | --- | --- |
| `start` | Begins a new leaf | a section (intro, opener, claim, world); the finding; the record's register; the audit; a figure |
| `keep` | Stays whole on one leaf | the stamped statement; a row of text with its margin note; a chart with its title; a plate; a knob; a refusal's scrap |
| `glue` | Stays with the block after it | a kicker, a heading, a question before its first paragraph |
| `flow` | May end a leaf and the next block begins the next one; a paragraph taller than a whole leaf continues on the next at the end of a sentence | a paragraph, a passage, a plain caption |

A `keep` block may declare an ordered fallback — the row whose note no longer fits beside its text
sets the note under it — so a composition degrades the way its designer chose, not where it happens
to break. The authored seams in `pages.ts` become the default `start` points, so the hand at a large
phone should paginate close to today; A4 measures whether it does.

**Measurement.** A hidden galley at the leaf's real content width, in the current type setting,
renders a section's blocks and reads their heights. Ink is drawn over the layout and never sizes it,
so the galley renders no ink — a plate's hachure is 1.4 MB of path data on the desktop, and the
measurement does not need a stroke of it. Leaf capacity is read from a real leaf element, not from
constants, so a change to the spiral or the flags paginates itself.

**Packing.** Greedy, in reading order, honouring the rules: predictable, the way a compositor works,
and cheap enough to rerun. A paragraph taller than a whole leaf is cut at the last sentence end that
fits and continues on the next leaf, as a printed book carries a paragraph overleaf — never in the
middle of a sentence (owner, 2026-10-12). Whether a shorter paragraph may also be cut to fill the
rest of a leaf is a separate question: A4 measures what it would save in half-empty leaves, and it is
the owner's then. Any other block taller than a whole leaf with no fallback is *overfull*: the
paginator marks the leaf, and the guard fails on it by name.

**When it reruns.** On the faces of the chosen setting landing (`document.fonts` *loadingdone* and
the `data-type` observer `fit.ts` already uses — measuring against the fallback face is measuring the
wrong book), on a type change, on resize and rotation (debounced), and on a realm change. Cached by
type, content size and realm.

**Keeping the reader's place.** The leaf is found by the id of the block at its top, the way
`placeOf` finds a panel today, so a type change or a rotation lands on the same passage.

**Addresses.** `ch` and `p` keep meaning a chapter and an offset in the arrangement the reader has,
as they already differ between a spread and a phone. A phone link also carries the block (`b=`), so
a passage shared from one phone opens on the same passage on another phone, in another face, or on
a desktop through `placeOf`.

**Filling.** After packing, a leaf below the target runs the *growing* half of `fit.ts` — air first,
then type, to the same ceilings as the spread (1.22 and 1.16) — which is the owner's first lever for
a half-empty page. Never the shrinking half.

## Which container a device gets

Today `Reader` chooses by the window's width (`width < 62rem`), so a tablet turned from landscape to
upright drops its spread and becomes leaves under the reader's hands. The owner's worry about the pad
was exactly that: *"someone goes from landscape to vertical and everything changes, which is
jarring. We could just decide based on screen size."*

So on a device that rotates the container is chosen once, from the screen, and turning it never
changes the container: a phone gets the pad held either way, and a tablet gets one container held
either way. Which one a tablet gets is measured rather than guessed (A0): the spread is rendered on
an upright tablet, and if its body type comes out below the spread's own floor, tablets get the pad.
A desktop window still chooses by its width, because resizing a window is a deliberate act — and
narrowing one to a phone's width is how the phone gets looked at on a desk.

What a phone turned on its side still changes is where its pages break, because the leaf is a
different shape and the pagination follows it; the passage being read stays in view. Keeping the
breaks too would need the page held at its upright shape, which landscape can only show at about
half size, and a page cannot lock the orientation outside fullscreen.

## The guard

- **No overflow, in every type, at every phone size, walked by turning.** 360×740, 375×667, 390×844,
  414×896 and 430×932, in Hand, Clear and Dyslexia. Measured on the rendered leaf by the lowest mark
  that paints (the method that found the 79%-that-was-61% fill error), against a content box that
  clears the spiral, the stack, the flags and the folio. Independent of the paginator's own numbers,
  which a guard must not trust.
- **Nothing lost to paper.** Every block id appears on exactly one leaf, in reading order, in every
  arrangement — the phone's form of *the dyslexia setting gets more paper, and loses nothing to it*.
- **The reader stays on the passage** across a type change and a rotation.
- **Overfull blocks are listed**, not admitted: a block that cannot fit any phone leaf is a defect in
  the composition, fixed by its fallback.
- **Tests arrive the way a reader does**, by turning from a page of the same kind: a turn reuses a
  slot's component and hands it new props, and a measurement keyed on an element goes stale on that
  path while a cold `goto` passes.

How long fifteen walks take is not known yet and is the first thing A4 measures; if the suite grows
past what CI can carry, the two extreme sizes stay in CI for all three types and the middle three move
to a hand-run walk, recorded as such.

## Build order

One change at a time; each lands with `make web-test` green and is looked at before the next.

| Step | What lands | Kill condition |
| --- | --- | --- |
| A0 | The container chosen once from the screen on devices that rotate, by the window on a desktop; the spread measured on an upright tablet (768×1024, 820×1180) and shown to the owner, which settles the tablet's container | — |
| A1 | Block lists for every panel kind, rendered through block ranges (as `intro` and `opener` already render `from`/`to`). No visible change: still one panel per leaf | A component cannot render a block range without changing what the spread shows |
| A2 | The packer as a pure function, with unit tests on synthetic heights | — |
| A3 | The galley and its invalidation | A full pagination takes over 300 ms on a mid phone (CPU throttled ×4 as the proxy, then the owner's phone): paginate per chapter on demand instead |
| A4 | The phone's leaves from measured packing, in today's scroll-snap container; the new guard in all three types | Measured packing leaves more pages under half full than today's seams do |
| B1 | The pad: wire, stack, flags, corner, the flip under the finger, the mounted window kept at the leaf and its neighbours; the realm tabs on the foot of the stack, or on the left edge if the owner finds the foot odd on the phone | The flip cannot hold a steady frame rate with a chart on the leaf on the owner's phone: fall back to a turn animated on release only |
| B2 | The world leaf in the pad: drags belong to the globe, turns come from the corner and the wire | — |
| C1 | Margin rows and phone compositions for the panel kinds the mocks designed (finding, how, headline figure, plate, record, survived, bias); the rest wait for C2 | — |
| C2 | A fifth mock for the kinds not yet designed (knobs, refusals, ribbon, strip and coverage figures, the absent leaf), judged by the owner before they are built | — |
| C3 | Writing on arrival: a per-leaf order, tap to finish, written stays written, reduced motion arrives written | — |
| D1 | `desk/scene.ts` takes a layout instead of computing the desktop's: the desktop's layout is today's placement, the phone's the mock's portrait one | The desktop table changes in any way a screenshot at 1280×800 can see |
| D2 | The desk on the phone: the cover, the camera move, the scene paused while reading, the table button and the pinch | — |
| D3 | The candle, the matches and the pencil as the settings, through `state/surface.ts` and `state/type.ts`; the flags on the table; the chalk labels and their lifecycle | — |
| D4 | No WebGL: the table photographed from the scene itself — wood, things, shadows and their lean, by day and by candle — rendered once at the phone layout and composited where the scene would draw each thing, so it looks as the live table does, flat; the candle, the matches and the pencil still work; every object a labelled button in the tab order | The composite differs from the live scene in a screenshot at the same size by more than a reader would see: render whole tables per screen shape instead of composited things |
| E1 | [ADR 0015](0015-the-book-on-the-desk.md) gets a dated amendment pointing here; the mock is deleted | — |

**For the whole direction:** if the table costs noticeable heat or battery on the owner's phone, or
its first frame takes long enough on a phone network that the cover is a wait, the desk becomes a
prerendered image with the same objects as sprites — the cover and the menu survive without 3D.

## What does not change

The content: both containers show the same authored pages, and the phone only arranges them. The
prose stays authored in `src/migratlas/reports/`; the two chalk words (*light*, *writing*) are
interface labels and live in the frontend, as the setting names do now. The drawings stay the
apparatus — ADR 0007 decision 5. The spread, its fit and its fifteen walks are untouched, except that
D1 moves where the desk's layout is computed.

## Settled with the owner, 2026-10-12

Proposed on 2026-10-11 with five questions open. The answers, in the owner's words where they gave
them, and where each now lives above:

1. **A paragraph longer than a leaf** — today it scrolls, and on the pad a vertical drag turns the
   page, so it cannot. Proposed that it continue on the next leaf at a sentence end; the owner: *"I
   agree that it can continue on the next page."* In *Packing*.
2. **The realm filter**, in no mock — proposed as four small tabs on the foot of the pad's stack,
   where the desktop has them under the book; the owner: *"Agree, or on the left is ok too if we see
   it looks odd."* In B1.
3. **Tablets held upright**, which get the phone container today — proposed as the pad, centred on a
   larger table. The owner's answer changed the question: rotating should not change the
   container, so it is chosen from the screen. In *Which container a device gets* and A0.
4. **No WebGL** — proposed as sprites rendered from the scene; the owner: *"make them look identical
   to how it looks now, just in 2D, so still remember about the depth and everything."* In D4, with
   a screenshot comparison as its kill condition.
5. **The mocks' sources** are committed in `web/mocks/phone/` and deleted at E1.
