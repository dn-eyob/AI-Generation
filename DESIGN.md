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
- Date:
- Participants (anonymised, ≥3):
- Method:
- What they said (verbatim where possible):
- Insights:
- What changed in `storyboard.json`:

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
