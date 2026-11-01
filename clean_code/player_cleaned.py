from __future__ import annotations

import logging
from tkinter import END, WORD, Button, Frame, Label, TclError, Text, Tk
from tkinter.filedialog import askopenfilenames
from typing import Protocol

import pygame
from mutagen import MutagenError
from mutagen.easyid3 import EasyID3

BUTTON_WIDTH = 40
BUTTON_BG = "AntiqueWhite1"
POLL_INTERVAL_MS = 100
PLAY_LOOPS = 1
PLAY_START_SECONDS = 0.0

logger = logging.getLogger(__name__)


class PlayerView(Protocol):
    def render_playlist(self, lines: list[str]) -> None:
        ...

    def render_now_playing(self, text: str) -> None:
        ...

    def select_song_paths(self) -> tuple[str, ...]:
        ...

class Playlist:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.index = 0

    def add_many(self, paths: tuple[str, ...]) -> None:
        for path in paths:
            self.items.append(path)

    def is_empty(self) -> bool:
        return len(self.items) == 0

    def current(self) -> str | None:
        if self.is_empty():
            return None
        return self.items[self.index]

    def advance_next(self) -> None:
        if self.is_empty():
            return
        self.index = (self.index + 1) % len(self.items)

    def advance_previous(self) -> None:
        if self.is_empty():
            return
        self.index = (self.index - 1) % len(self.items)


class SongMetadataService:
    @staticmethod
    def read(path: str) -> tuple[str, str]:
        try:
            song = EasyID3(path)
            title = song.get("title", ["Unknown title"])[0]
            artist = song.get("artist", ["Unknown artist"])[0]
            return title, artist
        except (MutagenError, OSError, KeyError):
            return "Unknown title", "Unknown artist"


class AudioPlayer:
    def __init__(self) -> None:
        self.track_started = False

    def load(self, path: str) -> None:
        pygame.mixer.music.load(path)

    def play(self) -> None:
        pygame.mixer.music.play(PLAY_LOOPS, PLAY_START_SECONDS)
        self.track_started = True

    def pause(self) -> None:
        pygame.mixer.music.pause()

    def unpause(self) -> None:
        pygame.mixer.music.unpause()

    def is_playing(self) -> bool:
        return pygame.mixer.music.get_busy()


class PlayerController:
    def __init__(
        self,
        view: PlayerView,
        playlist: Playlist,
        audio_player: AudioPlayer,
        metadata_service: SongMetadataService,
    ) -> None:
        self.view = view
        self.playlist = playlist
        self.audio_player = audio_player
        self.metadata_service = metadata_service
        self.paused = False
        self._was_playing = False

    def on_add(self) -> None:
        try:
            selected_paths = self.view.select_song_paths()
        except TclError as error:
            logger.exception("Could not open file picker", exc_info=error)
            return

        if not selected_paths:
            return

        self.playlist.add_many(selected_paths)
        self._render_playlist()

    def on_play(self) -> None:
        current_song = self.playlist.current()
        if current_song is None:
            return

        try:
            self.audio_player.load(current_song)
            self.audio_player.play()
            self.paused = False
        except (pygame.error, OSError) as error:
            logger.exception("Could not start playback", exc_info=error)
            return

        self.view.render_now_playing(self._format_now_playing())
        self._was_playing = True

    def on_pause_toggle(self) -> None:
        try:
            if self.paused:
                self.audio_player.unpause()
                self.paused = False
            else:
                self.audio_player.pause()
                self.paused = True
        except pygame.error as error:
            logger.exception("Could not toggle pause", exc_info=error)

    def on_previous(self) -> None:
        if self.playlist.is_empty():
            return
        self.playlist.advance_previous()
        self.on_play()

    def on_next(self) -> None:
        if self.playlist.is_empty():
            return
        self.playlist.advance_next()
        self.on_play()

    def poll_events(self) -> None:
        try:
            is_playing_now = self.audio_player.is_playing()
        except pygame.error as error:
            logger.exception("Could not poll playback state", exc_info=error)
            return

        if self.audio_player.track_started and self._was_playing and not is_playing_now and not self.paused:
            self.on_next()
            return

        self._was_playing = is_playing_now

    def _render_playlist(self) -> None:
        lines: list[str] = []
        for index, path in enumerate(self.playlist.items, start=1):
            title, artist = self.metadata_service.read(path)
            lines.append(f"{index} : {title} - {artist}")
        self.view.render_playlist(lines)

    def _format_now_playing(self) -> str:
        current_song = self.playlist.current()
        if current_song is None:
            return ""

        title, artist = self.metadata_service.read(current_song)
        return f"Now playing: Nr:{self.playlist.index + 1} {title} - {artist}"


class FrameApp(Frame):
    def __init__(self, master: Tk):
        super().__init__(master)
        self.grid()

        playlist = Playlist()
        audio_player = AudioPlayer()
        metadata_service = SongMetadataService()
        self.controller = PlayerController(self, playlist, audio_player, metadata_service)

        button_specs = [
            ("ADD TO LIST", self.controller.on_add),
            ("PLAY SONG", self.controller.on_play),
            ("PAUSE/UNPAUSE", self.controller.on_pause_toggle),
            ("PREVIOUS SONG", self.controller.on_previous),
            ("NEXT SONG", self.controller.on_next),
        ]
        for row, (text, command) in enumerate(button_specs, start=1):
            Button(self, text=text, command=command, bg=BUTTON_BG, width=BUTTON_WIDTH).grid(
                row=row, column=0
            )

        self.label1 = Label(self, fg="Black", font=("Helvetica 12 bold italic", 10), bg="ivory2")
        self.label1.grid(row=6, column=0)

        self.text1 = Text(self, wrap=WORD, width=60)
        self.text1.grid(row=8, column=0)

        self.after(POLL_INTERVAL_MS, self.poll_music_events)

    def render_playlist(self, lines: list[str]) -> None:
        self.text1.delete(0.0, END)
        for line in lines:
            self.text1.insert(END, f"{line}\n")

    def render_now_playing(self, text: str) -> None:
        self.label1["text"] = text

    def poll_music_events(self) -> None:
        self.controller.poll_events()
        self.after(POLL_INTERVAL_MS, self.poll_music_events)

    def select_song_paths(self) -> tuple[str, ...]:
        return askopenfilenames()


if __name__ == "__main__":
    pygame.mixer.init()
    window = Tk()
    window.geometry("500x500")
    window.title("MP3 Music Player")

    app = FrameApp(window)
    window.mainloop()