"""Explicit opt-in CommunicationMod launcher for the v1.7.3 trial.

The normal test_connection.py remains bound to v1.7.2.
Only point CommunicationMod here after the offline preflight and
the Run-57+ finalized/reflected boundary have both passed.
"""
from test_connection_c2_v173 import main


if __name__ == "__main__":
    main()
