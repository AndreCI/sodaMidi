from __future__ import annotations

import logging
import platform
import threading
import time
from queue import Empty

import Ctrls.music_controller as mctrl
import Models.music_model as music
# import fluidsynth as m_fluidsynth
from Models.note_model import int_to_note, ANote
from Utils import m_fluidsynth


class MusicView:
    """
    Wrapper for fluidsynth and its sequencer, so that music can be "viewed" i.e. listen to.
    """

    def __init__(self, model: music.Music, ctrl: mctrl.MusicCtrl):
        self.model = model
        self.ctrl = ctrl
        self.synth = m_fluidsynth.Synth()
        self.sequencer = m_fluidsynth.Sequencer(time_scale=self.model.timescale)
        self.registeredSynth = self.sequencer.register_fluidsynth(self.synth)

        self.starting_time = None
        self.pause_start_time = None
        self.consumer_thread = threading.Thread(target=self.consume, daemon=True, name="Note_consumer_thread")
        self.consumer_thread.start()

        logging.log(logging.INFO, "platform {} detected ".format(platform.system()))

        # Start the synth so its ready to play notes
        if platform.system() == "Windows":
            # Use the line below if for MS Windows driver
            self.synth.start()
        elif platform.system() == "Linux":
            self.synth.start(driver="alsa")
            # you might have to use other drivers:
            # fs.start(driver="alsa", midi_driver="alsa_seq")
        else:
            self.synth.start(driver="coreaudio")
            # you might have to use other drivers:
            # fs.start(driver="alsa", midi_driver="alsa_seq")

    def save_play_time(self) -> None:
        if (not self.ctrl.playing):  # If we are starting a new music, register the starting time
            self.starting_time = self.sequencer.get_tick()
            logging.log(logging.INFO, "started playing from origin: {}".format(self.starting_time))
        elif (self.ctrl.paused):  # If the model was paused, increment starting time by pause time
            paused_time = self.sequencer.get_tick() - self.pause_start_time
            self.starting_time += paused_time
            logging.log(logging.INFO, "started playing from unpaused: {}".format(self.starting_time))
        else:
            raise RuntimeError("Issue with play/pause/stop logic.")

    def save_pause_time(self) -> None:
        self.pause_start_time = self.sequencer.get_tick()  # Register when the pause button was pressed
        logging.log(logging.INFO, "pausing at : {}".format(self.pause_start_time))

    def TNote_to_ANote(self, n):
        print(n)
        abs = self.model.get_absolute_note_timing(n.tfactor)
        return ANote(timing=self.get_relative_note_timing(abs), tfactor=n.tfactor, channel=n.channel, value=n.value,
                     velocity=n.velocity, duration=n.duration, void=n.void, id=n.id)

    def dummy(self, row):
        return 0

    def play_dataframe(self):
        for notes in self.model.tracks_note.values():
            print(notes)
            timed_notes = notes.apply(lambda x: self.TNote_to_ANote(x), axis=1)
            print(timed_notes)
            for idx, note in timed_notes.iteritems():
                self.sequencer.note(absolute=False, time=int(note.timing), channel=note.channel, key=note.value,
                                    duration=note.duration, velocity=note.velocity, dest=self.registeredSynth)

    def play_note(self, note):
        self.sequencer.note(absolute=True, time=0, channel=note.channel, key=note.value,
                            duration=note.duration, velocity=note.velocity, dest=self.registeredSynth)

    def consume(self) -> None:  # TODO test if 3.11 is faster.
        """
        Threaded.
        Consume notes generated by music_model and feed them to the sequencer at regular interval.
        """
        prev_note_idx = 0
        while True:  # This thread never stops.
            if (self.ctrl.finished and self.model.notes.empty()):
                self.model.sonification_view.topBarView.press_stop_button()
                logging.log(logging.INFO,
                            "Music ended after {} secs".format(self.model.settings.get_music_duration()), )
                self.model.sonification_view.set_status_text(
                    "Music ended after {} secs".format(self.model.settings.get_music_duration()), 10000)
                time.sleep(0.1)
            self.ctrl.playingEvent.wait()  # Wait for the playing event
            self.ctrl.pausedEvent.wait()  # Wait for the playing event
            self.ctrl.fullSemaphore.acquire()  # Wait for the queue to have at least 1 note
            self.ctrl.queueSemaphore.acquire()  # Check if the queue is free
            try:
                note = self.model.notes.get_nowait()
                self.ctrl.queueSemaphore.release()  # Release queue
                self.ctrl.emptySemaphore.release()  # Inform producer that there is room in the queue
                # relative timing: how many ms a note has to wait before it can be played.
                # i.e. in how many ms should this note be played
                note_timing_abs = self.model.get_absolute_note_timing(note.tfactor)
                note_timing = self.get_relative_note_timing(note_timing_abs)  # update timing
                if (not note.void):
                    while (note_timing > self.model.settings.timeBuffer and  # check if next note is ripe
                           not self.ctrl.skipNextNote and  # check if next note should be skipped
                           note_timing > -100 and self.ctrl.playing):  # Check if the note is not stale
                        time.sleep(self.model.settings.timeBuffer / 2000)  # wait half the buffer time
                        self.ctrl.pausedEvent.wait()  # If paused was pressed during this waiting time, wait for PLAY event
                        note_timing = self.get_relative_note_timing(note_timing_abs)  # update timing

                    if (self.ctrl.playing and note_timing > -100 and not self.ctrl.skipNextNote):
                        # log_line = self.write_log_line(note, track_log_str, note_timing, note_timing_abs, prev_note_idx)
                        self.sequencer.note(absolute=False, time=int(note_timing), channel=note.channel, key=note.value,
                                            duration=note.duration, velocity=note.velocity, dest=self.registeredSynth)
                    else:
                        self.ctrl.skipNextNote = False  # Once the note is skipped, don't skip the next ones
                        log_line = "SKIPPED Note [track={}, value={}, vel={}, dur={}, timing abs={}] at t={}, data row #{} planned scheduled in {}ms. {} notes remaining".format(
                            note.channel, int_to_note(note.value), note.velocity, note.duration, note_timing_abs,
                            self.sequencer.get_tick(), note.id, note_timing, self.model.notes.qsize())
                        logging.log(logging.INFO, log_line)
                if (prev_note_idx != note.id):
                    threading.Thread(
                        target=self.model.sonification_view.tableView.currentDataModel.push_row_to_data_frame,
                        args=[note_timing],
                        daemon=True).start()
                prev_note_idx = note.id

            except Empty:
                logging.log(logging.ERROR, "Empty notes queue")
                self.ctrl.queueSemaphore.release()  # Release semaphores
                self.ctrl.emptySemaphore.release()

    def get_relative_note_timing(self, note_timing_absolute: float) -> int:
        """
        :param note_timing_absolute: int:
            a value between 0 and model.musicDuration
        :return:
            the temporal distance (ms) between get_tick() and the input
        """
        return int(note_timing_absolute - (self.sequencer.get_tick() - self.starting_time))

    def convert(self, temporal_pos: int, to_absolute: bool = True) -> float:
        if to_absolute:
            return float(temporal_pos - self.starting_time) / (self.model.settings.get_music_duration() * 1000)
        else:
            return (temporal_pos) * self.model.settings.get_music_duration() * 1000 + self.starting_time

    def get_absolute_tick(self) -> float:
        return self.convert(self.sequencer.get_tick(), to_absolute=True)

    def set_relative_tick(self, absolute_tick: float) -> float:
        self.starting_time = self.sequencer.get_tick() - absolute_tick * self.model.settings.get_music_duration() * 1000

    def get_temporal_distance(self, temporal_pos: float, absolute: bool = True) -> float:
        if absolute:
            return temporal_pos - self.get_absolute_tick()
        else:
            return temporal_pos - self.sequencer.get_tick()

    """
    Absolute: between 0 and 1
    Relative: between N and music.duration + N
    Distance: between -music.duration and music.duration, temporal distance with ctp
    Current temporal position! Can be moved, stopped, etc. in absolute space but is the slow and steady arrow of time
    in relative, get by .get_tick()
    -> Need conversion tools between absolute and relative temporal position
    Modify relative bounds to change behavior
    pause simply pauses ctp in absolute, but in relative it prevents production and consumtion of notes, and then increments N by pause_time at the end of pause.
    stop simply pauses and set ctp to 0 in absolute, but in relative it pauses, reset data idx to 0, empty queue and then unpause at the start of new music/
    fbw simply moves ctp by -10 in absolute, but in relative it pauses, moves idx by -10, empty queue, and then unpause
    """
