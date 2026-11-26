# DESIGN

Audience and intent are written here **before** anything is generated (first committed 2026-11-26, before any keyframe, clip or music generation).

> **The film is *The King Who Built a Wonder in Stone* (Lalibela, storyboard v8+): see section 6.** Sections 1–5 are the **pipeline-development record** (storyboard v1–v7, an earlier story used to build and user-test the pipeline). They are kept unchanged as evidence of the design process and User Test #1; that earlier film is not part of the submission.

## 1. Brief
- **Working title:** *Three Rounds* (ሶስት ዙር)
- **Story:** my family's traditional Ethiopian coffee ceremony. In my family coffee is more than a drink: when we come together we roast, brew and share coffee, tell stories and laugh. It reminds us of our culture, of love, and of the importance of family.
- **Logline:** *When the smell of fresh-roasted coffee fills the house, a family drops everything and gathers — and over three rounds of coffee, a simple ritual becomes the thread that holds them together.*
- **Audience (who watches):** young Ethiopians, cousins living abroad, families, and people interested in Ethiopian culture.
- **Where they watch:** on a phone, in a social feed (vertical 9:16 first), often with the sound low, so the English subtitles must carry the story on their own.
- **Intent (what they feel at the end):** **pride and warmth.** Pride in a tradition that is ours; warmth like being called home by the smell of coffee.
- **How might we…** help young Ethiopians, especially cousins abroad, feel the warmth and pride of a family coffee ceremony in under 90 seconds, even if they haven't sat at one in years?
- **Constraints:** 60–90 s; illustrated characters inspired by my family (no real faces, no real voices); Amharic narration (Gemini TTS, synthetic voice) with English subtitles; $0 budget; deadline 2026-11-26 23:59 EAT.

## 2. Story beats (one image per beat)
The ceremony's own structure is the story structure: preparation, then the three rounds of coffee — **Abol** (first), **Tona** (second), **Bereka** (third, "the blessing").

1. **The invitation.** Fresh grass is spread on the floor and incense is lit; she sets out the small cups. *(Setting: the ritual begins before anyone arrives.)*
2. **The call.** Green beans roast dark in the pan; the smoke drifts through the house and out the door; one by one the family follows the smell. *(The detail only my family would know: the smell is what brings everyone together.)*
3. **Abol, the first round.** The beans are ground, the clay jebena boils, the first cups are poured; laughter and stories start. *(Togetherness.)*
4. **Tona, the second round.** The cups pass to the youngest; old stories are retold to new ears. *(Tradition handed down.)*
5. **Bereka, the blessing.** The third round, the blessing; the smoke rises one last time. Wherever we are, this is what home smells like. *(Pride and warmth; speaks directly to cousins abroad.)*

**Recurring motif:** the rising smoke of roasting coffee (and incense), seen in beats 1, 2 and 5. It starts as an invitation and ends as a blessing.

**Main character:** one illustrated woman leading the ceremony (inspired by my family, not a likeness of any real person). Other family members appear mainly as hands, silhouettes and backs, to keep character consistency manageable.

## 3. User test #1: radio cut
- **Date:** 2026-11-26
- **Prototype:** `outputs/radio_cut/radio_cut.mp4` (storyboard v2): 80 s, Amharic narration, English subtitles, placeholder drone, black screen.
- **Participants (anonymised, 3):** P1 family member; P2 cousin living abroad; P3 friend.
- **Method:** each watched the radio cut on their own, then answered the same 5 questions in writing (what was it about / what did you feel / anything confusing, slow or fast / which line do you remember / what would you add or remove). Nothing was explained beforehand. Original replies kept privately.

### What they said
| | P1: family member | P2: cousin abroad | P3: friend |
|---|---|---|---|
| **About** | "how the Ethiopian coffee ceremony brings people together and keeps family traditions alive" | "how it connects people to their families and homeland, even when they live far away" | "more than making coffee. It represents hospitality, friendship, and spending time together" |
| **Felt** | "peaceful and proud. It reminded me of sitting with my family during a coffee ceremony" | "emotional and a little homesick" | "interested in the tradition and proud of the cultural meaning behind it" |
| **Confusing / pace** | "The beginning could be slightly shorter so the story reaches its main point sooner." | "the ending could have a little more time to create an emotional impact" | "some sentences could be shorter and more direct" |
| **Line remembered** | "When the roasted smoke rises, no words are needed to call us." (s03) | "Wherever we are in the world, this is what home smells like." (s10) | "Wherever we are in the world, this is what home smells like." (s10) |
| **Add / remove** | "more detail about preparing the coffee, especially washing, roasting, and grinding the beans" | "the familiar sounds of the ceremony, such as coffee beans roasting, coffee being poured, and cups touching" | "make sure the jebena, small coffee cups, and coffee preparation are clearly shown" |

### Insights
1. **The intent landed.** All 3 named pride or warmth/home without being told; the story was understood with no confusion. The brief does not need to change.
2. **The smell lines are the heart of the film.** The only two lines anyone remembered are both about smoke and smell (s03, s10); 2 of 3 remembered the ending line. The smell motif is working, so keep it and give the ending room.
3. **The opening is setup, not story.** Two shots (16 s) of preparation before the "call" felt slow (P1).
4. **People want the process, not just the ritual.** Preparation detail (P1), seeing the objects (P3), hearing them (P2): the audience wants the *craft*.
5. **Shorter, more direct sentences** (P3) suit Amharic TTS too: shorter lines = less robotic delivery risk.

### What changed in `storyboard.json` (v2 → v3)
See the revision log below. In short: merged the two opening shots, added a washing shot and a grinding shot, held the ending 3 s longer, and planned ceremony sound effects for Phase 3.

## 4. User test #2: near-final cut
- **Status: not conducted** (as of 2026-11-26).
- **Why:** deadline-day time pressure. I prioritised finishing the pipeline (score fallback after ACE-Step failed, sound effects, one-command run) over collecting a second round of feedback.
- **What the near-final cut already responds to:** every User Test #1 request is addressed in v3–v7 (shorter opening, washing and grinding shots, longer ending, jebena and cups clearly shown, ceremony sounds).
- **What I would test:** the same 5 questions on `outputs/final/three_rounds_vertical.mp4`, watched on a phone, with two specific checks: (1) do the sound effects help or distract under the Amharic voice, and (2) does the illustrated, pan-and-zoom look still land "pride and warmth" now that there are pictures?
- **Honest cost:** without a second test I can't show that the v3–v7 changes actually worked for the audience; they are supported only by User Test #1 and my own review.

## 5. Storyboard revision log
| Date | Shot | Change | Because |
|---|---|---|---|
| 2026-11-26 | all | v1 drafted by `pipeline/script.py` (Gemini 3.8 Flash) from section 2: 10 shots, 76 s + 3 s end card, 63 Amharic narration words, s05 left silent for the music | First draft for the radio cut. Reviewed and approved by me (native Amharic speaker) |
| 2026-11-26 | s02 | v2: duration 7 s → 8 s (film 79 s → 80 s) | Measured narration (`outputs/narration/timings.json`): s02's line is 6.65 s; with 0.8 s breathing room it needs 7.45 s. Narration timing sets shot length |
| 2026-11-26 | s01 + old s02 | v3: merged into one opening shot (grass, incense **and** cup tray); old s02 ("cups set on the tray") removed. Preparation before the "call" drops from 16 s to 14 s and is now active steps, not setup | User Test #1, P1: "The beginning could be slightly shorter" |
| 2026-11-26 | new s02 | v3: **new shot**: hands washing green beans; new short line "በመጀመሪያ ጥሬው ቡና በንጹህ ውሃ ይታጠባል።" / "First, the green beans are washed in clean water." | P1: "more detail about preparing the coffee, especially washing, roasting, and grinding" |
| 2026-11-26 | s05 | v3: silent jebena insert → **grinding in the wooden mortar, jebena steaming behind**, with a short line "…ይወቀጣል፤ ጀበናውም ይፈላል።" / "The roasted beans are pounded, and the jebena comes to a boil." | P1 (grinding) + P3: "make sure the jebena… and coffee preparation are clearly shown" |
| 2026-11-26 | s10 | v3: 9 s → **12 s** | P2: "the ending could have a little more time"; P2 and P3 both remembered this line |
| 2026-11-26 | (Phase 3) | Planned: quiet ceremony sound effects (roasting crackle, pouring, cups touching) under the narration | P2: "the familiar sounds of the ceremony". Needs a licensed or generated sound source; tracked for assembly |
| 2026-11-26 | s02, s03, s05, s06, s07, s10 | v7: **ceremony sound effects added**, declared per shot in the new `sfx` field: wash (s02), roast crackle (s03), pestle thuds (s05), pour (s06), cup clinks (s07, s10). Synthesised in code (`pipeline/sfx.py`, no recordings or licences), mixed into the music bed so they duck under the narration | User Test #1, P2: "add the familiar sounds of the ceremony, such as coffee beans roasting, coffee being poured, and cups touching" |
| 2026-11-26 | s02, s05 | v3 timing fix: s02 6 → 7 s, s05 7 → 8 s | Measured new narration: s02 5.40 s and s05 6.38 s, which need 6.20 s and 7.18 s with breathing room |
| 2026-11-26 | all | v3 total: 10 shots, 80 s + 3 s end card = **83 s**; 68 narration words (60.9 s spoken, 76% of the film); radio cut rebuilt | |

## 6. Story change: *The King Who Built a Wonder in Stone* (v8)

**Decided:** 2026-11-26, by me, late in the project. **Written and committed before any v8 narration, image, score or edit was generated.**

### Why I changed the story
I chose to tell Lalibela's story, Ethiopia's rock-hewn churches, as the heritage I most want young Ethiopians and the diaspora to feel proud of. It is national rather than family heritage.

### Brief (v8)
- **Logline:** *A twelfth-century Ethiopian king dreams of a new Jerusalem, and generations of craftsmen carve it, church by church, out of the living rock of Lalibela.*
- **Audience:** young Ethiopians, Ethiopians abroad, and people curious about Ethiopian history and faith.
- **Where they watch:** on a phone, in a social feed (9:16 first), often with the sound low, so subtitles carry the story.
- **Intent (what they feel at the end):** **pride and awe.** Pride that this was made in Ethiopia; awe at what people carved by hand.
- **How might we…** help young Ethiopians and the diaspora feel the scale and devotion behind Lalibela in 80 seconds, so they leave proud of a wonder that is theirs?
- **Structure (5 beats, 8 shots):** 1 vision (s01–s02) → 2 the impossible challenge and the carving (s03–s04) → 3 the reveal: eleven churches, Bete Giyorgis (s05–s06) → 4 a living faith (s07) → 5 the legacy (s08). Closing card: "ETHIOPIA – A WONDER CARVED IN STONE".
- **Source script:** my 8-scene script (narration in English). Adapted for the pipeline:
  1. every scene is 10 s (80 s + 3 s end card = 83 s);
  2. narration translated into **Amharic** and **shortened to ~9–10 words per line**, because Amharic TTS speaks at ≈1.13 words/s (E-03); the original English lines would not fit 10-second scenes;
  3. English subtitles are translations of the Amharic lines, so the voice and the text match.

### What carries over, and what doesn't
- **Carries over:** the whole pipeline, style approach, caching, logging, every experiment and failure (E-01 to E-10, F-01 to F-08) and their lessons: object glossary for culturally specific things (E-06, now Bete Giyorgis), shot-level specificity (E-07), per-aspect crops and subtitles (E-08), measured narration timing (E-03), effects beside the voice (E-10).
- **Does not carry over (honest cost):** User Test #1 tested the *coffee-ceremony* radio cut. Its findings (shorter opening, show the process, give the ending room, use real sounds, show the objects) informed how I structured v8, but **the new story itself has not been tested with its audience**. Section 4's note on User Test #2 applies doubly.

### Risks I'm watching
- **Accuracy:** Bete Giyorgis is a specific, famous building. Image models draw generic churches, so its physical form is fixed in the storyboard's `object_glossary`, and each keyframe is checked against it. Images are artistic impressions, not documentation.
- **Respect:** a sacred, living place. Priests and pilgrims appear as generic, unidentifiable figures in prayer, never posed for spectacle.
- **King Lalibela** is a historical figure with no surviving likeness; he is drawn as an imagined, generic king (see ETHICS.md).

### Revision log (v8 onwards)
| Date | Shot | Change | Because |
|---|---|---|---|
| 2026-11-26 | all | v8: new story, 8 shots × 10 s, 74 Amharic words, new style block, `object_glossary` for Bete Giyorgis and rock-hewn churches, sounds `wind` (s01, s08) and `chisel` (s03, s04), closing title card | Story change (above) |
| 2026-11-26 | s08 | duration 10 → 11.5 s (film 83 → 84.5 s) | Measured narration: the closing line is 10.16 s, needing 10.96 s with breathing room. The other 7 shortened Amharic lines fit (7.2–8.6 s) |
| 2026-11-26 | s04, s05, s06, s08 | v9/v10: image prompts rewritten with explicit geometry and camera angle | 4/8 first keyframes were architecturally wrong (European domes, a box instead of the cross-shaped Bete Giyorgis): E-11 |
| 2026-11-26 | all | Amharic narration text and audio for all 8 lines reviewed and approved by me (native speaker) | Lines were translated and shortened by the pipeline author, so they needed a native check before release |
| 2026-11-26 | s08 | v11: English subtitle shortened to "Lalibela shows the world Ethiopia's history, faith and heritage." (same meaning as the Amharic) | It could not fit 2 lines on the 9:16 frame (E-14) |
| 2026-11-26 | end card | "Illustrated characters, not real people" → "Illustrations are artistic impressions; figures are imagined" | King Lalibela is a real historical person; the old line (true for the coffee film) was no longer accurate |
