from __future__ import annotations

import pickle

import pandas as pd
from pandas import DataFrame

import Models.data_model as data_model
import Models.music_model
import Models.note_model as note
from Ctrls.track_controller import TrackCtrl
from Models.parameter_encoding_model import ParameterEncoding
from Utils.constants import ENCODING_OPTIONS
from Utils.filter_module import FilterModule
from Utils.soundfont_loader import SoundfontLoader


class Track:
    """
    Model class for a track, regrouping multiples notes and a soundfont. Each track is unique and can be viewed either
    via config view or midi view.
    Notes and soundfont are defined via a parameter encoding model alongside loaded data.
    """

    def __init__(self, id: int):
        # Data
        self.id = id
        sfl = SoundfontLoader.get_instance()
        self.soundfont = sfl.get()  # soundfont selected by user, <=< instrument

        self.name = "Track # {}".format(self.id)
        self.filter = FilterModule()  # Filter module linked to the column, dictating which row in data is used to generate notes
        self.data = data_model.Data.getInstance()
        self.filter.column = self.data.get_variables()[0]
        self.gain = 100  # Volume of the current track, between 0 and 100
        self.muted = False
        self.offset = 0
        self.music = Models.music_model.Music.getInstance()  # Needed to backtrack and remove itself upon deletion, among other things

        # Other models
        self.pencodings = {}
        for pe in ENCODING_OPTIONS:
            self.pencodings[pe] = ParameterEncoding(encoded_var=pe, default_col=self.data.get_best_guess_variable())

        # Ctrls
        self.ctrl = TrackCtrl(self)

        # Views
        self.gTrackView = None
        self.generalView = None
        self.advancedView = None

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["data"]
        del state["music"]
        del state["gTrackView"]
        del state["generalView"]
        del state["advancedView"]
        del state["ctrl"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.data = data_model.Data.getInstance()
        self.music = Models.music_model.Music.getInstance()
        self.ctrl = TrackCtrl(self)

    def serialize(self, path: str) -> None:
        with open(path, 'wb') as f:
            pickle.dump(self, f)
            self.music.sonification_view.set_status_text("Track exported to {}".format(f.name))

    def unserialize(self, path: str) -> None:
        with open(path, 'rb') as f:
            oldid = self.id
            var = pickle.load(f)
            self.__dict__.update(var.__dict__)
            self.id = oldid
            self.ctrl.model = self
            self.music.sonification_view.set_status_text("Track imported to id {}".format(self.id))

    def generate_notes(self, batch: DataFrame) -> [note.TNote]:
        """
        Generate notes for the current track, based on main variable, parameter encoding and filters.
        :param batch: pandas Dataframe,
            a subset of the dataset regardless the considered filter
        :return list of notes
        """
        notes = []  # Container for the next batch of data
        for idx, row in self.filter_batch(batch, False).iterrows():  # iterate over index and row
            notes.append(self.build_note(row))
        return notes

    def build_note(self, row):
        return note.TNote(tfactor=self.music.settings.get_temporal_position(row, self.offset),
                          channel=self.id,
                          value=self.pencodings["value"].get_parameter(row),
                          velocity=int(self.pencodings["velocity"].get_parameter(row) * 1.27),
                          duration=int(self.pencodings["duration"].get_parameter(row)),
                          void=not row['internal_filter'],
                          id=row['internal_id'])

    def build_note2(self, row):
        return pd.Series({'tfactor': self.music.settings.get_temporal_position(row, self.offset),
                          'channel': self.id,
                          'value': self.pencodings["value"].get_parameter(row),
                          'velocity': self.pencodings["velocity"].get_parameter(row),
                          'duration': self.pencodings["duration"].get_parameter(row),
                          'void': not row['internal_filter'],
                          'id': row['internal_id']})

    def filter_batch(self, batch: DataFrame, discard_filtered: bool) -> DataFrame:
        for encoding in self.pencodings.values():
            batch = encoding.filter.eval_batch(batch, discard_filtered)
        return self.filter.eval_batch(batch, discard_filtered)

    def set_main_var(self, variable: str) -> None:
        self.filter.assign_column(variable)

    def set_soundfont(self, soundfont: str) -> None:
        self.soundfont = soundfont

    def duplicate(self) -> None:
        self.music.ctrl.duplicate_track(track=self)

    def remove(self) -> None:
        self.music.ctrl.remove_track(track=self)
        self.gTrackView.frame.hide()
        self.music.sonification_view.trackView.gTrackList.remove(self.gTrackView)
        self.music.sonification_view.set_status_text("Track {} with ID {} deleted".format(self.name, self.id))
