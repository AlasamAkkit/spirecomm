"""Active CommunicationMod entry point for the C2 research agent.

Run from the usual mod setup or manually with:
    python spirecomm/test_connection.py

Historical controller implementations remain in their versioned files for
reproducibility. The active, explicitly selected policy begins Ascension 10 at
Run 39. Do not start until Run 38 is fully reflected.
"""
from test_connection_c2_a10 import main


if __name__ == "__main__":
    main()
