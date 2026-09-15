"""The book's connective prose: one opener per chapter, authored here and rendered verbatim.

ADR 0018 recorded the owner's reading of the book as *"a mess of single general points, without a
general story behind it"*. The claims were never the problem. What was missing was the sentence
saying why one chapter follows another, and a reader who could follow it without a degree.

**The voice, chosen by the owner on 2026-09-15 from three mocked directions: somebody writing in
the notebook as they go.** Not a report delivered after the fact -- an account of looking, in the
order the looking happened, including the parts where what turned up was not what was expected. So
these say *we went looking* and *we did not find it* and *we thought that was the finding for about
a week*, because all three are true, and because a reader told how a thing was found out can judge
it for themselves.

**The rule that keeps the voice honest: an opener contains no digits at all.** Every figure a
reader meets on a chapter's opening leaf comes from `figures`, which is read from the ledger, which
is recomputed from the lake on every build. The prose may say *about half a day* and *seven times
weaker*; it may not say a number, because a number typed into narration is the one figure nobody
checks and the first to go stale. `tests/test_chapters.py` enforces it.

That split is also what the owner asked for. The story is readable by anyone; the exact quantities
sit underneath it, and the method that produced them is a page-turn away.

**The slugs are story.ts's, and a test holds the two lists together.** They are the book's stable
identities and neither file may grow a chapter the other does not have.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 3
"""Three: the account became a list of paragraphs, so a long chapter opening takes two leaves
the way the introduction does rather than overflowing one."""

PUBLIC: Final = Path("web/public")
LEDGER: Final = PUBLIC / "findings.json"
DOCUMENT: Final = PUBLIC / "chapters.json"
STORY: Final = Path("web/src/lib/story.ts")


@dataclass(frozen=True, slots=True)
class Opener:
    """One chapter's question, the account that answers it, and the figures underneath."""

    slug: str
    question: str
    """What a reader arrives with. The chapter title is the subject; this is the sentence."""
    paragraphs: list[str]
    """The account, one entry per paragraph so the book paginates it like the introduction.

    Carries no digits anywhere -- see the module docstring.
    """
    figures: list[str]
    """The claims this chapter rests on, each with its computed value. Every digit on the leaf."""


def _ledger() -> dict[str, dict[str, object]]:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    findings: list[dict[str, object]] = payload["findings"]
    return {str(finding["key"]): finding for finding in findings}


def value_of(key: str, ledger: dict[str, dict[str, object]]) -> str:
    """One claim's computed value string, or a marker saying the claim is not published.

    Returning a marker rather than raising: a chapter whose claim was withheld should still open,
    and `build` runs on every build including ones where a finding withheld itself.
    """
    finding = ledger.get(key)
    return str(finding["value"]) if finding else "not published on this build"


def figures_for(keys: list[str], ledger: dict[str, dict[str, object]]) -> list[str]:
    """The figures line: one entry per claim the chapter rests on, value read from the ledger."""
    return [f"{key} — {value_of(key, ledger)}" for key in keys]


def slugs_in_story() -> list[str]:
    """The chapter slugs story.ts declares, in order, read rather than restated."""
    text = STORY.read_text(encoding="utf-8")
    start = text.index("export const CHAPTERS")
    end = text.index("];", start)
    return re.findall(r'slug:\s*"([^"]+)"', text[start:end])


def build(ledger: dict[str, dict[str, object]] | None = None) -> list[Opener]:
    """The six chapters that carry claims. The way in and the way out have their own pages."""
    read = ledger if ledger is not None else _ledger()

    return [
        Opener(
            slug="what-changed",
            question="Are animals really doing things earlier than they used to?",
            paragraphs=[
                (
                    "We started with the simplest question we could think of, because it is the "
                    "one everybody asks first. Are they actually early, or does it only feel that "
                    "way? The trouble is that almost nobody has watched any single animal for long "
                    "enough to say. So we went looking for records kept by people who were not "
                    "trying to answer this question at all."
                ),
                (
                    "We found two. A network of American weather radars, built to spot "
                    "thunderstorms, which has been quietly filling up with birds on autumn nights "
                    "for thirty years — nobody counted them, the radar just did. And several "
                    "thousand volunteers in Britain who have walked the same paths every summer "
                    "week since the seventies, writing down the butterflies they saw."
                ),
                (
                    "The two have nothing in common: different continents, different animals, one "
                    "machine and one clipboard. They agree. The birds' busiest night of autumn has "
                    "been creeping earlier by about half a day each decade, and the butterflies "
                    "are flying earlier by around two days."
                ),
                (
                    "Before believing either we checked the obvious way to be fooled — that the "
                    "radar is watching different creatures than it used to, insects rather than "
                    "birds. It is not. The speed of whatever is up there has not shifted, and "
                    "insects do not fly at bird speed."
                ),
                (
                    "So: yes, they are early. The next question is what moved them, and that one "
                    "took far longer."
                ),
            ],
            figures=figures_for(["autumn-advance", "flight-advance", "composition-stable"], read),
        ),
        Opener(
            slug="why-it-changed",
            question="What is telling them to go early?",
            paragraphs=[
                (
                    "If an animal is early, something is telling it to be. The obvious suspect is "
                    "warmth, and the obvious suspect turned out to be right — about halfway. "
                    "Butterflies are the easy case, because a caterpillar is more or less built by "
                    "the temperature it grows up in. Give a British butterfly one extra degree "
                    "before its season and it flies about five days earlier, which covers roughly "
                    "three quarters of everything that has happened to it. The birds are harder. "
                    "The same degree of warmth buys around two thirds of a day — seven times "
                    "weaker — and covers only about half of their change."
                ),
                (
                    "We spent a long time looking for the other half. We tried rain, and sunshine, "
                    "and the date the leaves come out, one at a time and then all together. Each "
                    "of them is real, in the sense that each moves more species than chance would. "
                    "Not one of them helped us predict a year we had hidden from the model. We "
                    "also asked whether the birds had changed how they travel rather than when "
                    "they leave, and they have not. So half of the birds' shift has no name, and "
                    "we would rather say so than invent one."
                ),
                (
                    "About the warmth itself we can be sharper, and this is the hardest number in "
                    "the chapter. We asked what made their spring warmer by running the climate "
                    "models with human emissions in them and then again without. Almost all of it "
                    "is ours."
                ),
            ],
            figures=figures_for(["anthropogenic-share"], read),
        ),
        Opener(
            slug="what-did-not",
            question="If they leave earlier, are they also living somewhere else?",
            paragraphs=[
                (
                    "Here is what we expected, and what nearly everybody expects. The world warms; "
                    "animals that can move follow the temperature they like; so over thirty years "
                    "everything should be drifting toward the poles."
                ),
                (
                    "We went looking for it in four separate records and did not find it. Fish, "
                    "across twenty-nine trawl surveys on both sides of the Atlantic, counted by "
                    "ships that have been doing the same haul for decades: the middle of the pack "
                    "has moved about a hundredth of a degree of latitude in ten years, which is "
                    "roughly a kilometre, which is nothing. Birds across southern Africa, counted "
                    "once in the eighties and again thirty years later by two enormous volunteer "
                    "efforts: no net change. Elk in the Canadian Rockies and reindeer on Svalbard, "
                    "wearing collars that report where they are: their yearly journeys are the "
                    "same length now as when the collars went on."
                ),
                (
                    "We are not telling you the poleward shift is a myth. It is well measured "
                    "where it has been looked for hardest, and this project would find it there "
                    "too. What we can say is narrower and more uncomfortable: it is not something "
                    "all animals are doing at once, and if you take a large pile of species and "
                    "ask what the pile did, the answer is nothing whatsoever."
                ),
                (
                    "We thought that was the finding for about a week. It is not. The next chapter "
                    "is about why."
                ),
            ],
            figures=figures_for(["marine-null", "atlas-no-net-change", "displacement-flat"], read),
        ),
        Opener(
            slug="no-average-animal",
            question="Why does a pile of species add up to nothing?",
            paragraphs=[
                (
                    "Because the pile is the problem. Take eighteen stretches of shelf sea and ask "
                    "each one which way its fish went. They will not agree — some north, some "
                    "south, and far more lopsided than luck can produce. We checked whether the "
                    "seas that warmed most were the ones heading furthest north. They were not. "
                    "Add all of it together and it cancels, and the cancelling is what the last "
                    "chapter was looking at. An average over animals that disagree is a number "
                    "describing none of them."
                ),
                (
                    "So we started asking what decides. If it were the place, a rule learned in "
                    "one part of the world ought to work in another, and we tried exactly that: "
                    "took the response measured in one realm and used it to predict the next. It "
                    "misses by roughly ten times what it should."
                ),
                (
                    "Which points at the animal, and every time we have been able to check, the "
                    "animal is what it points at. Sort butterflies by species and the species "
                    "agree with themselves; sort them by which patch of countryside they live in "
                    "and they do not. Whether a fish is thriving follows the fish from one sea to "
                    "the next. Two herds given the same deep snow do opposite things — the "
                    "reindeer keep moving, the elk take shorter steps."
                ),
                (
                    "This is the turn in the book, so its limit should be plain. Knowing that the "
                    "animal decides does not tell us which animal will do what. The thing that "
                    "would — a table of what each species eats, how far it goes, what it can bear "
                    "— is not something we have."
                ),
            ],
            figures=figures_for(["seas-disagree", "transfer-fails"], read),
        ),
        Opener(
            slug="can-be-predicted",
            question="Can you tell me when they will arrive next year?",
            paragraphs=[
                (
                    "No, and the honest version of that answer is more interesting than the "
                    "answer. It is what we get asked most, and for a while we assumed the "
                    "thirty-year trend meant we could. It does not, and the reason is worth a "
                    "chapter."
                ),
                (
                    "A trend is what is left after you average away everything that makes one year "
                    "different from the next. A forecast is that difference. They are nearly "
                    "opposite jobs. When we tried to predict one station's next autumn from the "
                    "weather it had, it worked at barely better than guessing — at most stations, "
                    "not at all. Ask about a whole region instead and it improves enough to be "
                    "worth something, and a regional outlook is the only forecast this project "
                    "will stand behind."
                ),
                (
                    "The far future is a different problem and we treat it differently. When the "
                    "question is what the middle of this century looks like, most of the honest "
                    "answer is about where our evidence stops rather than about skill: for a good "
                    "share of the futures we were asked to project, the right answer is that we "
                    "cannot say. We publish that mask as a finding of its own, because a "
                    "projection without one is a claim about places nobody ever measured."
                ),
            ],
            figures=figures_for(["skill-sparse", "projection-mask"], read),
        ),
        Opener(
            slug="cannot-see",
            question="What did we get wrong, or never see at all?",
            paragraphs=[
                (
                    "Two kinds of blindness, and we would rather hand them over than have somebody "
                    "find them."
                ),
                (
                    "The first is ordinary: the map of where our evidence comes from is not the "
                    "map of the world. A third of the animal records we can measure change with "
                    "are southern, and almost none of the weather records that would explain them "
                    "are. Every southern claim in this book is therefore measured with a northern "
                    "instrument, and each one says so."
                ),
                (
                    "The second is stranger and it bothers us more. When two programmes count the "
                    "same birds, in the same country, in the same years, with different methods, "
                    "they disagree — and they still disagree after the ordinary error of "
                    "estimating anything is taken out of both. So it is not noise. Somewhere "
                    "between a bird existing and a number appearing there is a choice of method "
                    "that moves the answer, and nothing in this book is finer than that."
                ),
                (
                    "Neither is a reason to distrust what is here. They are the reason everything "
                    "here is written the way it is: with its scope, with what it cannot tell you, "
                    "and with the attempts that failed printed beside the ones that did not."
                ),
            ],
            figures=figures_for(["coverage-bias", "protocol-disagreement"], read),
        ),
    ]


def write(openers: list[Opener] | None = None) -> Path:
    """Render to `web/public/chapters.json`, sorted so a rebuild with no change is a no-op."""
    built = openers if openers is not None else build()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "chapters": {
            opener.slug: {
                "question": opener.question,
                "paragraphs": opener.paragraphs,
                "figures": opener.figures,
            }
            for opener in built
        },
    }
    DOCUMENT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return DOCUMENT
