## Changelog ##

> **FYP note:** this file is the legacy `spirecomm` package changelog. The Slay the Spire LLM FYP research/controller history is maintained in `docs/CHANGELOG.md`, with final B2/C2 results in `docs/FINAL_B2_C2_ANALYSIS.md`.

### FYP integration status — October 2026

The repository now also contains the completed LLM-agent research stack: constrained gameplay control, structured experimental logging, post-run reflection, persistent memory, human-feedback workflows, and frozen A/B/C1/B2/C2 experiment archives. The final matched B2/C2 experiment is complete; The frozen C2 v1.2.1 controller remains the matched-comparison treatment. Subsequent continual Runs 16–36 explored explicit controller interventions; from Run 37 the locally activated v1.4.0 stable controller is intended to remain fixed while human teaching accumulates. See `docs/CONTINUAL_CHANGELOG.md`, `docs/CONTINUAL_C2_STATUS.md`, and `docs/SYSTEM_ARCHITECTURE_AND_RETROSPECTIVE.md`. This package changelog otherwise remains historical.

#### Development ####
* Added card_in_play, turn, and cards_discarded_this_turn from the Communication Mod combat state
* Added monster move history from the Communication Mod combat state

#### v0.6.0 ####
* Fixed "for_transform" field in card select screens
* Added act boss information from Communication Mod 0.6.0
* Added new power fields from Communication Mod 0.7.0
* Added "limbo" cards from Communication Mod 0.7.0

#### v0.5.0 ####
* Added "any_number" to the grid select screen, to maintain compatibility with Communication Mod 0.5.0

#### v0.4.1

* Added setup.py and installation instructions

#### v0.4.0 ####
* Initial public release