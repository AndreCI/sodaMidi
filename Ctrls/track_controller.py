from Utils.soundfont_loader import SoundfontLoader
from Views.track_config_view import TrackConfigView
from Views.track_midi_view import TrackMidiView
from ViewsPyQT5.ViewsUtils.views_utils import selectedTrackStyle, selectTrackButtonStyle


class TrackCtrl:
    """
    Controller for a track. each track have its own ctrl and its own views.
    """

    def __init__(self, model):
        # Model
        self.model = model  # Track Model
        self.soundfontUtils = SoundfontLoader.get_instance()

    def update_filter(self, filter: str):
        self.model.filter.assign(filter)

    def set_soundfont(self, soundfont: str):
        self.model.soundfont = self.soundfontUtils.get(soundfont)
        self.model.music.ctrl.load_soundfonts()

    def set_main_var(self, column: str):
        self.model.set_main_var(column)

    def change_offset(self, offset:float):
        self.model.offset = float(offset)

    def change_gain(self, gain: int):
        self.model.gain = int(gain)
        self.model.music.ctrl.change_local_gain(self.model.id, self.model.gain)

    def mute_track(self):
        self.model.muted = not self.model.muted
        self.model.music.ctrl.change_local_gain(self.model.id, 0 if self.model.muted else self.model.gain)

    def select(self):
        if(self.model.generalView.selectedTrack is not None):
            self.model.generalView.selectedTrack.gTrackView.selectButton.setStyleSheet(selectTrackButtonStyle)
        self.model.generalView.selectedTrack = self.model
        self.model.generalView.display_track(self.model)
        self.model.advancedView.display_track(self.model)
        self.model.gTrackView.selectButton.setStyleSheet(selectedTrackStyle)

    def remove(self):
        # for pencoding_model in self.model.pencodings.values():
        #     pencoding_model.ctrl.destroy()
        self.model.remove()

    def open_encoding(self, encoded_var: str):
        self.model.pencodings[encoded_var].ctrl.show_window()

    def change_name(self, name):
        self.model.name = name
        self.model.gTrackView.selectButton.setText(name)