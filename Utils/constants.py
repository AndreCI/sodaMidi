# PARAMETERS
TIME_BUFFER = 1000  # ms, time used to plan future notes.
BATCH_SIZE = 10
BATCH_NBR_PLANNED = 20
MAX_NOTE_GRAPH = 100
SAMPLE_SIZE = 10

# OPTIONS
TIME_SETTINGS_OPTIONS = ["tempo-basic", "tempo-N", "linear"]
TIME_SETTINGS_OPTIONS_TOOLTIP = \
    ["tempo-basic: Each row is processed at constant interval. The interval is always #rows/song length.",
     "tempo-N: Each row is processed at constant interval. The interval is always #rows/song length.\n"
        "\t\tNotes are then grouped in cluster of N with a silence between each cluster.",
     "Linear: Ratios of temporal distance between rows are preserved. Experimental."]
FUNCTION_OPTIONS = ["linear"]  # isomorphisms
ENCODING_OPTIONS = ["value", "filter", "duration", "velocity"]

# PATHS
FILE_PATH = "data/savefiles"
soundfont_path = "data/soundfonts"
