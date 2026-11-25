# ETHICS

## 1. Consent record
Every real person whose story, face, likeness or voice is used is listed here **before** anything of them is generated.

**Design decision (2026-11-26):** no real person's face, likeness or voice appears in the film.
- Characters are **illustrated and generic**, *inspired by* my family's ceremony. No photos of family members are used as references, and no prompt describes a real person's specific features.
- The narrator is a **synthetic Gemini TTS voice** (prebuilt voice), not a clone of any real person.
- The film tells a **shared cultural tradition** (the Ethiopian coffee ceremony) as my family practises it. No individual's private story, name, words or likeness is used.

| Person | What appears | Consent required? | Status |
|---|---|---|---|
| — (no real person) | Illustrated **generic** characters; synthetic prebuilt TTS voice | **No**: no real person's face, likeness or voice is shown or voiced | **Not applicable**, recorded 2026-11-26, before any generation |

**Guardrails that keep this true:**
1. No photo of any real person is used as a reference image or uploaded anywhere.
2. Character prompts describe a generic woman and family, never a real person's features or name.
3. No voice cloning: the narrator is a Gemini prebuilt voice.
4. If any real person's face, likeness or voice is added later, generation stops until their recorded, informed consent is added to this table first.

## 2. Licences
| Component | Model / tool | Licence / terms | Output use |
|---|---|---|---|
| Script, storyboard, translation | Gemini (`gemini-3.8-flash`, fallback `gemini-3.5-flash`) via Google AI Studio | Gemini API Terms of Service (free tier) | Free tier: prompts may be used by Google to improve products, so **no private family details in prompts** |
| Narration | `gemini-3.8-flash-tts` (prebuilt voice) | Gemini API Terms of Service | Synthetic voice, no voice cloning |
| Keyframes | FLUX.1 [schnell] / FLUX.2 [klein] 4B on Cloudflare Workers AI | Apache 2.0 (both). The FLUX.2 klein **9B** is non-commercial and is deliberately **not** used | Usable, including commercially |
| Moving shots | Wan 2.2 TI2V-5B (Kaggle) | Apache 2.0 | Usable |
| Score | ACE-Step 1.5 (Kaggle) | MIT; trained on licensed / royalty-free / synthetic data | Usable, including commercially |
| Assembly | FFmpeg 9.1 (gyan.dev full build) | GPL (build) | Tool only; outputs are mine |
| Placeholder music (radio cut only) | Generated with FFmpeg tone synthesis | n/a (generated) | Not in final film |

## 3. Labelling plan
- A visible **"Made with AI"** end card (2–3 s) in both exports, listing the models used.
- The platform's **AI-disclosure / AI-generated label switched on** when posting.
- Watermarks and provenance metadata (e.g. SynthID on Gemini audio) are **left intact**; no step strips metadata on purpose.
- The public post says plainly that the visuals, voice and music are AI-generated.

## 4. Privacy
- No family names, addresses, locations or photos are sent to any model.
- Prompts describe *a* family and *a* home, never identifiable people.
- Consent evidence (the voice note or message) is kept privately, not in this public repo.
