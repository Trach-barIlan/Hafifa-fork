from __future__ import annotations

import logging
from collections.abc import Sequence
from tkinter import END, WORD, Button, Frame, Label, TclError, Text, Tk
from tkinter.filedialog import askopenfilenames
from typing import Protocol

import pygame
from mutagen import MutagenError
from mutagen.easyid3 import EasyID3

BUTTON_WIDTH = 40
BUTTON_BG = "AntiqueWhite1"
POLL_INTERVAL_MS = 100
PLAY_LOOPS = 0
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


    def add_many(self, paths: Sequence[str]) -> None:
        self.items.extend(paths)

    def is_empty(self) -> bool:
        return not self.items

    def current(self) -> str | None:
        if self.is_empty():
            return None
        return self.items[self.index]

    def advance_next(self) -> bool:
        if self.is_empty() or self.index + 1 >= len(self.items):
            return False
        self.index += 1
        return True

    def advance_previous(self) -> bool:
        if self.is_empty() or self.index - 1 < 0:
            return False
        self.index -= 1
        return True


class SongMetadataService:
    @staticmethod
    def read(path: str) -> tuple[str, str]:
        try:
            song = EasyID3(path)
            title = song.get("title")
            title = title[0] if title else "Unknown title"

            artist = song.get("artist")
            artist = artist[0] if artist else "Unknown artist"
            return title, artist
        except (MutagenError, OSError, KeyError):
            return "Unknown title", "Unknown artist"


class AudioPlayer:
    def __init__(self) -> None:
        self.status = "stopped"

    def load(self, path: str) -> None:
        self.status = "loading"
        pygame.mixer.music.load(path)
        self.status = "loaded"

    def play(self) -> None:
        pygame.mixer.music.play(PLAY_LOOPS, PLAY_START_SECONDS)
        self.status = "playing"

    def pause(self) -> None:
        pygame.mixer.music.pause()
        self.status = "paused"

    def unpause(self) -> None:
        pygame.mixer.music.unpause()
        self.status = "playing"

    def stop(self) -> None:
        pygame.mixer.music.stop()
        self.status = "stopped"

    def is_playing(self) -> bool:
        return self.status == "playing" and pygame.mixer.music.get_busy()


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
        self.playback_state = "STOPPED"

    def _set_playback_state(self, state: str) -> None:
        self.playback_state = state

    def on_add(self) -> None:
        try:
            selected_paths = self.view.select_song_paths()
        except TclError:
            logger.exception("Could not open file picker")
            return

        if not selected_paths:
            return

        self.playlist.add_many(selected_paths)
        self._render_playlist()

    def on_play(self) -> None:
        current_song = self.playlist.current()
        if current_song is None:
            return

        self._set_playback_state("STOPPED")

        try:
            self.audio_player.stop()
            self.audio_player.load(current_song)
            self.audio_player.play()
        except (pygame.error, OSError):
            logger.exception("Could not start playback")
            self.audio_player.status = "stopped"
            self._set_playback_state("STOPPED")
            return

        self._set_playback_state("PLAYING")
        self.view.render_now_playing(self._format_now_playing())

    def on_pause_toggle(self) -> None:
        if self.playlist.is_empty() or self.playback_state == "STOPPED":
            self._set_playback_state("STOPPED")
            return

        try:
            if self.playback_state == "PAUSED":
                self.audio_player.unpause()
                self._set_playback_state("PLAYING")
                return

            if self.playback_state == "PLAYING":
                self.audio_player.pause()
                self._set_playback_state("PAUSED")
                return
        except pygame.error:
            logger.exception("Could not toggle pause")
            self._set_playback_state("STOPPED")

    def on_previous(self) -> None:
        if self.playlist.is_empty():
            return

        self.audio_player.stop()
        self._set_playback_state("STOPPED")

        if not self.playlist.advance_previous():
            return
        self.on_play()

    def on_next(self) -> None:
        if self.playlist.is_empty():
            return

        self.audio_player.stop()
        self._set_playback_state("STOPPED")

        if not self.playlist.advance_next():
            self.view.render_now_playing("")
            return
        self.on_play()

    def poll_events(self) -> None:
        if self.playback_state == "PLAYING" and not self.audio_player.is_playing():
            self.audio_player.stop()
            self._set_playback_state("STOPPED")
            self.on_next()
            return

        if self.playback_state == "PAUSED":
            return
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

        self.text1 = Text(self, wrap=WORD, width=60, state="disabled")
        self.text1.grid(row=8, column=0)

        self.after(POLL_INTERVAL_MS, self.poll_music_events)

    def render_playlist(self, lines: list[str]) -> None:
        self.text1.config(state="normal")
        self.text1.delete(1.0, END)
        playlist_content = "\n".join(lines)
        self.text1.insert(END, playlist_content)
        self.text1.config(state="disabled")

    def render_now_playing(self, text: str) -> None:
        self.label1["text"] = text

    def poll_music_events(self) -> None:
        self.controller.poll_events()
        self.after(POLL_INTERVAL_MS, self.poll_music_events)

    def select_song_paths(self) -> tuple[str, ...]:
        return askopenfilenames()


if __name__ == "__main__":
    mixer_enabled = True
    try:
        pygame.mixer.init()
    except pygame.error:
        logger.exception("Could not initialize pygame mixer")
        mixer_enabled = False

    window = Tk()
    window.geometry("500x500")
    window.title("MP3 Music Player")

    app = FrameApp(window)

    def on_closing():
        if mixer_enabled:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass  # Safely ignore cleanup errors if already stopped
        window.destroy()

    # Bind the handler to the window close button (X)
    window.protocol("WM_DELETE_WINDOW", on_closing)

    window.mainloop()
