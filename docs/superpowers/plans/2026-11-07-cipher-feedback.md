# Cipher mouse input and feedback plan

Goal: Make each pointer press visible and make code transitions understandable.
Spec: User reports early cipher stage changes and requests click feedback.

Evidence: TrainingSession only increases length after all correct symbols. Wrong input immediately replaces the sequence at the same length and resets preview. TrainingView has no input flash or transition indication. Early length increase is not yet reproduced.

- [x] Regression: partial input cannot advance length, same-tick duplicate is ignored, preview input is ignored, correct/wrong presses yield feedback, final input retains completed progress during a short transition.
- [x] Add portable CipherInteraction presentation state; preserve TrainingSession/server v2 rules and replay inputs. Hold simulation during the 0.6-second success/error presentation, as with an existing local pause; run expiry remains authoritative.
- [x] Integrate in TrainingView/TrainingLeagueView; show cell flash, border pulse, progress dots, and explicit result text. Reset state for every run.
- [x] Compile active runtime, run portable checks and Unity regressions, verify replay parity. Preserve user scene and existing assets.

Review ruling: Deduplicate mouse press edges by InputState.updateCount instead of waiting for a release-only frame; avoids dropping fast legitimate clicks. Regression reproduced the old latch failure before correction.

Visual limitation: active Unity is minimized; direct screenshot inspection and manual PC play remain unverified.

Implementation runs in a staged copy before installing with backups to active Assets. Visual changes are UI rendering only; scoring/sequence generator are unchanged.
