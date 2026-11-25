# DESIGN

Audience and intent are written here **before** anything is generated (first committed 2026-11-26, before any keyframe, clip or music generation).

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
- Date:
- Participants (anonymised, ≥3):
- Method:
- What they said:
- Insights:
- What changed:

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
| 2026-11-26 | s02, s05 | v3 timing fix: s02 6 → 7 s, s05 7 → 8 s | Measured new narration: s02 5.40 s and s05 6.38 s, which need 6.20 s and 7.18 s with breathing room |
| 2026-11-26 | all | v3 total: 10 shots, 80 s + 3 s end card = **83 s**; 68 narration words (60.9 s spoken, 76% of the film); radio cut rebuilt | |
