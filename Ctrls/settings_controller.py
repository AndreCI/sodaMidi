from __future__ import annotations
import math
import threading

import Models.settings_model as ts
from Utils.utils import is_int
import ViewsPyQT5.settings_view as sv


class SettingsCtrl():
    """
    Ctrl for the time settings model
    """

    def __init__(self, model:ts.GeneralSettings):
        self.model = model  # TimeSettings Model

    def change_batch_size(self, batch_size:int, batch_planned:int)->None:
        if self.model.music.ctrl.playing:
            self.model.music.ctrl.stoppedEvent.wait()
        self.model.batchSize = batch_size
        self.model.batchPlanned = batch_planned
        self.model.data.batch_size = batch_size
        self.model.music.ctrl.change_queue_size(batch_size * batch_planned)

    def validate(self, batch_size:int, batch_planned:int, song_length:int, note_timing:int, sample_size:int, tempo_idx:int,
                 autoload:bool, graphical_length:int, graphical_precentage:int)->None:
        """
        Validate time settings entered by user and update models accordingly
        """

        if not (is_int(batch_size) and
                is_int(batch_planned) and
                is_int(song_length) and
                is_int(note_timing) and
                is_int(sample_size) and
                is_int(graphical_length) and
                is_int(graphical_precentage)):
            return
        threading.Thread(target=self.change_batch_size, args=[int(batch_size), int(batch_planned)], daemon=True, name="change_batch_size").start()
        self.model.musicDuration = int(song_length)
        self.model.timeBuffer = int(note_timing)
        self.model.sampleSize = int(sample_size)
        self.model.set_type(self.model.possible_types[tempo_idx])
        self.model.autoload = autoload
        self.model.autoloadDataPath = self.model.data.path
        self.model.graphicalLength = int(graphical_length) * 1000
        self.model.graphicalBarPercentage = float(graphical_precentage) / 100

        self.write_to_ini()

    def write_to_ini(self)->None:
        with open("settings.ini", "w") as settingsFile:
            line = "autoload=" + str(self.model.autoload) + "\n"
            settingsFile.write(line)
            line = "datapath=\"" + str(self.model.autoloadDataPath) + "\"\n"
            settingsFile.write(line)
            line = "timestampcol=\"" + str(self.model.data.date_column) + "\"\n"
            settingsFile.write(line)
            line = "debugverbose=" + str(self.model.debugVerbose) + "\n"
            settingsFile.write(line)
            line = "graphicalLength=" + str(self.model.graphicalLength) + "\n"
            settingsFile.write(line)
            line = "graphicalBarPercentage=" + str(self.model.graphicalBarPercentage) + "\n"
            settingsFile.write(line)
            line = "batchSize=" + str(self.model.batchSize) + "\n"
            settingsFile.write(line)
            line = "batchPlanned=" + str(self.model.batchPlanned) + "\n"
            settingsFile.write(line)
            line = "timeBuffer=" + str(self.model.timeBuffer) + "\n"
            settingsFile.write(line)
            line = "sampleSize=" + str(self.model.sampleSize) + "\n"
            settingsFile.write(line)

    def open_settings(self, view:sv.SettingsView):
        self.model.tsView = view
        view.model = self.model
        view.update_ui()
        view.show()