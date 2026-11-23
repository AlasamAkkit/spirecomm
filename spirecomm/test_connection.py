"""Active CommunicationMod entry point for Run 57 restart and later (v1.7.2).

The original Run-57 v1.7.1 attempt was paused due to malformed card-reward
JSON and closed by the operator after a local evidence backup. This launcher
starts a NEW recorded attempt in the still-uncompleted run slot. It does NOT
reattach to an already-running game, rewrite old logs, or replay old actions.
All historical v1.7.1/v1.7.0 implementations remain unchanged.
"""
from test_connection_c2_v172 import main


if __name__ == "__main__":
    main()
