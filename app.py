import os
import flet as ft
import pygame
from mutagen.mp3 import MP3
import threading
import time

class Config:
    SONGS_FOLDER = "songs"
    BACKGROUND_FOLDER = "background"
    MAX_PLAYLIST_SIZE = 10

class Song:
    def __init__(self, songName, filePath):
        self.songName = songName
        self.filePath = filePath
        self.duration = self.GetDuration()
        self.next = None
        self.prev = None

    def GetDuration(self):
        try:
            audio = MP3(self.filePath)
            return int(audio.info.length)
        except Exception as e:
            print(f"Error al obtener duración: {e}")
            return 0

class Playlist:
    def __init__(self):
        self.head = None
        self.tail = None
        self.current = None
        self.length = 0
        self.lock = threading.Lock()

    def Append(self, songName, filePath, position=None):
        with self.lock:
            if self.length >= Config.MAX_PLAYLIST_SIZE:
                return False

            newSong = Song(songName, filePath)

            if position is None or position > self.length + 1:
                position = self.length + 1

            if position == 1:
                newSong.next = self.head
                if self.head:
                    self.head.prev = newSong
                self.head = newSong
                if self.length == 0:
                    self.tail = newSong
                    self.current = newSong
            else:
                temp = self.head
                for _ in range(position - 2):
                    if temp.next is None:
                        break
                    temp = temp.next
                newSong.next = temp.next
                if temp.next:
                    temp.next.prev = newSong
                temp.next = newSong
                newSong.prev = temp
                if newSong.next is None:
                    self.tail = newSong

            self.length += 1
            return True

    def Remove(self, songName):
        with self.lock:
            current = self.head
            while current:
                if current.songName == songName:
                    if current.prev:
                        current.prev.next = current.next
                    else:
                        self.head = current.next

                    if current.next:
                        current.next.prev = current.prev
                    else:
                        self.tail = current.prev

                    if self.current == current:
                        self.current = self.current.next if self.current.next else self.head

                    self.length -= 1
                    return True
                current = current.next
            return False

    def NextSong(self):
        with self.lock:
            if self.current and self.current.next:
                self.current = self.current.next
            else:
                self.current = None

    def PrevSong(self):
        with self.lock:
            if self.current and self.current.prev:
                self.current = self.current.prev

    def Clear(self):
        with self.lock:
            self.head = None
            self.tail = None
            self.current = None
            self.length = 0

class TrackListLC:
    def __init__(self, page: ft.Page):
        self.page = page
        self.playlist = Playlist()
        self.backgroundImages = self.LoadBackgroundImages()
        self.currentBgIndex = 0
        self.SetupUI()
        self.InitializeAudio()
        self.StartEventListener()

    def SetupUI(self):
        self.page.title = "Taller Listas dobles"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.title = ft.Text("TrackListLC", size=40, weight=ft.FontWeight.BOLD)
        self.songLabel = ft.Text("Selecciona una canción", size=18)

        self.playButton = ft.IconButton(
            ft.icons.PLAY_CIRCLE_FILL, 
            icon_size=40,
            on_click=self.TogglePlayPause
        )
        self.prevButton = ft.IconButton(
            ft.icons.SKIP_PREVIOUS, 
            icon_size=40,
            on_click=self.PrevSong
        )
        self.nextButton = ft.IconButton(
            ft.icons.SKIP_NEXT, 
            icon_size=40,
            on_click=self.NextSong
        )

        self.progressBar = ft.Slider(min=0, max=100, value=0, expand=True)
        self.progressLabel = ft.Text("00:00 / 00:00")

        self.playlistView = ft.ListView(expand=True, spacing=5)
        self.salsaView = ft.ListView(expand=True, spacing=5)

        self.filePicker = ft.FilePicker(on_result=self.HandleFilePick)
        self.page.overlay.append(self.filePicker)

        self.volumeSlider = ft.Slider(
            min=0, max=100, value=70,
            on_change=self.AdjustVolume
        )
        
        self.addButton = ft.ElevatedButton(
            "Agregar Canción", 
            icon=ft.icons.ADD,
            on_click=lambda _: self.filePicker.pick_files(
                allow_multiple=False,
                allowed_extensions=["mp3"]
            )
        )
        self.removeButton = ft.ElevatedButton(
            "Eliminar Actual", 
            icon=ft.icons.DELETE,
            on_click=self.RemoveCurrentSong
        )
        self.clearButton = ft.ElevatedButton(
            "Limpiar Lista", 
            icon=ft.icons.CLEAR,
            on_click=self.ClearPlaylist
        )
        self.positionInput = ft.TextField(
            label=f"Posición (1-{Config.MAX_PLAYLIST_SIZE})", 
            width=150, 
            keyboard_type=ft.KeyboardType.NUMBER
        )

        self.bgImage = ft.Image(
            src=self.backgroundImages[0] if self.backgroundImages else "",
            fit=ft.ImageFit.COVER, 
            opacity=0.3
        )

        self.page.add(
            ft.Stack([
                self.bgImage,
                ft.Column([
                    ft.Row([self.title], alignment=ft.MainAxisAlignment.CENTER),
                    
                    ft.Row([
                        self.prevButton,
                        self.playButton,
                        self.nextButton
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    
                    ft.Row([self.songLabel], alignment=ft.MainAxisAlignment.CENTER),
                    
                    ft.Column([
                        ft.Row([self.progressBar], width=600),
                        ft.Row([self.progressLabel], alignment=ft.MainAxisAlignment.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    
                    ft.Row([
                        ft.Icon(ft.icons.VOLUME_UP),
                        self.volumeSlider
                    ], width=600),
                    
                    ft.Row([
                        self.addButton,
                        self.removeButton,
                        self.clearButton,
                        self.positionInput
                    ], wrap=True),
                    
                    ft.Tabs(
                        selected_index=0,
                        tabs=[
                            ft.Tab(text="Tu Lista", content=self.playlistView),
                            ft.Tab(text="Salsa", content=self.salsaView)
                        ],
                        expand=True
                    )
                ], expand=True)
            ], expand=True)
        )

    def InitializeAudio(self):
        pygame.mixer.init()
        pygame.mixer.music.set_endevent(pygame.USEREVENT)
        self.LoadSalsaSongs()

    def StartEventListener(self):
        def EventListener():
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.USEREVENT:
                        self.NextSong(None)
                time.sleep(0.1)
        
        threading.Thread(target=EventListener, daemon=True).start()

    def LoadBackgroundImages(self):
        os.makedirs(Config.BACKGROUND_FOLDER, exist_ok=True)
        return [
            os.path.join(Config.BACKGROUND_FOLDER, f) 
            for f in os.listdir(Config.BACKGROUND_FOLDER) 
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ]

    def LoadSalsaSongs(self):
        os.makedirs(Config.SONGS_FOLDER, exist_ok=True)
        salsaSongs = [
            f for f in os.listdir(Config.SONGS_FOLDER) 
            if f.lower().endswith(".mp3")
        ]
        
        self.salsaView.controls.clear()
        for song in salsaSongs:
            self.salsaView.controls.append(
                ft.ListTile(
                    title=ft.Text(song),
                    leading=ft.Icon(ft.icons.MUSIC_NOTE),
                    on_click=lambda e, s=song: self.PlaySalsaSong(s)
                )
            )
        self.salsaView.update()

    def PlaySalsaSong(self, songName):
        filePath = os.path.join(Config.SONGS_FOLDER, songName)
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(filePath)
            pygame.mixer.music.play()
            self.UpdateSongLabel(f"Reproduciendo: {songName}")
            self.ChangeBackground()
            
            duration = MP3(filePath).info.length
            self.progressBar.max = duration
            self.progressBar.value = 0
            self.progressLabel.value = f"00:00 / {self.FormatTime(duration)}"
            self.page.update()
        except Exception as e:
            print(f"Error al reproducir canción: {e}")
            self.UpdateSongLabel(f"Error al reproducir {songName}")

    def HandleFilePick(self, e):
        if e.files:
            filePath = e.files[0].path
            songName = os.path.basename(filePath)
            position = (
                int(self.positionInput.value) 
                if self.positionInput.value.isdigit() 
                else None
            )
            
            if self.playlist.Append(songName, filePath, position):
                self.UpdatePlaylistView()
            else:
                self.ShowSnackbar("¡La lista está llena (máx 10 canciones)!")

    def UpdatePlaylistView(self):
        self.playlistView.controls.clear()
        current = self.playlist.head
        while current:
            self.playlistView.controls.append(
                ft.ListTile(
                    title=ft.Text(current.songName),
                    leading=ft.Icon(ft.icons.MUSIC_NOTE),
                    trailing=ft.IconButton(
                        ft.icons.DELETE, 
                        on_click=lambda e, s=current.songName: self.RemoveSong(s)
                    ),
                    on_click=lambda e, s=current: self.SetCurrentSong(s)
                )
            )
            current = current.next
        self.playlistView.update()

    def RemoveSong(self, songName):
        if self.playlist.Remove(songName):
            self.UpdatePlaylistView()
            if self.playlist.current is None:
                self.UpdateSongLabel("Selecciona una canción")

    def SetCurrentSong(self, song):
        self.playlist.current = song
        self.PlaySong()

    def ClearPlaylist(self, _=None):
        self.playlist.Clear()
        self.UpdatePlaylistView()
        self.UpdateSongLabel("Lista vacía")
        pygame.mixer.music.stop()

    def PlaySong(self):
        if self.playlist.current:
            try:
                pygame.mixer.music.load(self.playlist.current.filePath)
                pygame.mixer.music.play()
                self.UpdateProgressBar()
                self.UpdateSongLabel(f"Reproduciendo: {self.playlist.current.songName}")
                self.ChangeBackground()
            except Exception as e:
                print(f"Error al reproducir: {e}")
                self.UpdateSongLabel(f"Error al reproducir {self.playlist.current.songName}")

    def TogglePlayPause(self, _):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.UpdateSongLabel(f"Pausado: {self.playlist.current.songName}")
        else:
            pygame.mixer.music.unpause()
            self.UpdateSongLabel(f"Reproduciendo: {self.playlist.current.songName}")
            self.UpdateProgressBar()

    def NextSong(self, _):
        pygame.mixer.music.stop()
        self.playlist.NextSong()
        if self.playlist.current:
            self.PlaySong()
        else:
            self.UpdateSongLabel("Fin de la lista de reproducción")
            self.progressBar.value = 0
            self.progressLabel.value = "00:00 / 00:00"
            self.page.update()

    def PrevSong(self, _):
        pygame.mixer.music.stop()
        self.playlist.PrevSong()
        if self.playlist.current:
            self.PlaySong()

    def UpdateProgressBar(self):
        def Run():
            while pygame.mixer.music.get_busy() and self.playlist.current:
                currentTime = pygame.mixer.music.get_pos() // 1000
                self.progressBar.value = currentTime
                self.progressLabel.value = (
                    f"{self.FormatTime(currentTime)} / "
                    f"{self.FormatTime(self.playlist.current.duration)}"
                )
                self.page.update()
                time.sleep(1)
        
        threading.Thread(target=Run, daemon=True).start()

    def RemoveCurrentSong(self, _):
        if self.playlist.current:
            songName = self.playlist.current.songName
            self.playlist.Remove(songName)
            pygame.mixer.music.stop()
            self.UpdatePlaylistView()

            if self.playlist.current:
                self.PlaySong()
            else:
                self.UpdateSongLabel("Selecciona una canción")

    def AdjustVolume(self, e):
        pygame.mixer.music.set_volume(e.control.value / 100)

    def ChangeBackground(self):
        if self.backgroundImages:
            self.currentBgIndex = (self.currentBgIndex + 1) % len(self.backgroundImages)
            self.bgImage.src = self.backgroundImages[self.currentBgIndex]
            self.page.update()

    def UpdateSongLabel(self, text):
        self.songLabel.value = text
        self.page.update()

    def ShowSnackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()

    @staticmethod
    def FormatTime(seconds):
        minutes = seconds // 60
        sec = seconds % 60
        return f"{minutes:02}:{sec:02}"

def main(page: ft.Page):
    TrackListLC(page)

ft.app(target=main, view=ft.WEB_BROWSER)