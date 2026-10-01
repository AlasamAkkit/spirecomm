# INVALIDATED FOR FINAL COMPARISON

This directory contains the completed B2 v1.1.0 batch.

It is retained for debugging and provenance, but it must **not** be used as the final B2 control dataset.

Reason: the v1.1.0 controller reopened permanent card rewards after the LLM selected Skip because CommunicationMod continued exposing the skipped card reward on the parent COMBAT_REWARD list.

Retrospective audit found:

- 92 Skip decisions across 19 affected permanent card-reward instances;
- 9 of 15 completed runs affected;
- maximum 29 repeated skips at one reward;
- every affected reward eventually resolved by taking a card or Singing Bowl.

The final matched experiment restarts B2 from empty memory using test_connection_b2_v1_1_1.py, followed by C2 using test_connection_c2_v1_1_1.py.
