# Continual C2 memory audit (shadow-only, no controller changes)

This introduces a **read-only** diagnostic for the existing human-teaching
system. It does not restart the original autonomous-baseline experiment, modify
the v1.6.1 gameplay controller, or change the current playbook.

## Current evidence

Runs 49–53 (all v1.6.1, A10) reached floors 33, 30, 13, 16 and 7,
respectively. These were different game seeds, so the declining floors are not
a causal learning test. Logged combat memory exposure rose from 42 to 48 rules;
average acting-combat input tokens rose from about 20,650 to 26,950.

The actual live implementation in followup_reflection.py attaches authoritative
human teaching verbatim, rather than merging that text. The v1.3 memory
implementation retrieves *every* decision-applicable rule; additionally, a
matched card/enemy/relic can pin and repeat the same human text. This can
produce broad, repetitive prompts, but the full current local playbook is not
versioned on GitHub and its exact duplicate rules have not been examined here.

Run 53 generated a false reflection diagnosis: it stated that the player
entered Lagavulin with too little HP. The compact state shows 74/74 HP upon
entering the elite. Losses occurred during combat, not before it.

## Run the audit locally

From the project root (in the same environment where you run the controller):

    python reflection/offline_learning_audit.py --first-run 48 --last-run 53 --preview-run 53 --preview-floor 7 --output reflection/learning_audits/run53_audit.json

The inputs default to the private, local condition_c2_playbook.json,
condition_c2_raw_memory.jsonl, and run_XX_raw.json / run_XX_states.json /
run_XX_initial_reflection.json under reflection/condition_c2_outputs.

Omit --output to print JSON instead. The output path must be a **new** file,
and may not overwrite the live playbook, memory, or any review file.

The tool reports:
- Complete raw-memory source-ID coverage in the current playbook;
- Authoritative verbatim count and length, rule count and decision scopes;
- Lexically similar rules for *human review*, never automatic consolidation;
- A10 run outcomes and measured acting-agent prompt/token sizes;
- A bounded flag for inaccurate Lagavulin entry-HP reflection claims;
- A **shadow-only** ordering of memory attention candidates for a recorded
  decision. Unselected IDs are still explicitly listed as preserved.

No controller code, retrieval policy, official human feedback, or stored
memory is edited. Entity relevance scoring is a heuristic, **not** proven
decision improvement. No rule is omitted from the live agent.

Offline tests:

    python -m unittest discover -s reflection/tests -p "test_offline_learning_audit.py" -v

Next step: inspect the generated local report, manually adjudicate candidate
repeat/conflict pairs, and design a separate versioned learning experiment
only if the evidence supports it. Keep the v1.6.1 baseline frozen.
