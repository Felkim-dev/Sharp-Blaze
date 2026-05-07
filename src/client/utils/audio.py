import pygame
import os

class AudioManager:
    """Centralized audio manager for all game sound effects.
    
    Loads audio files once and provides simple play methods
    that can be called from any screen or module.
    """

    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        pygame.mixer.init()

        # Resolve the audio assets directory
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        AUDIO_DIR = os.path.join(CURRENT_DIR, "..", "assets", "audio")

        # Background music path
        self._music_path = os.path.join(AUDIO_DIR, "game_music.mp3")
        self._music_loaded = False  # True once the file has been loaded into mixer.music
        self._music_playing = False  # True while the music is actively playing (not paused)

        # Load all sound effects
        self.sfx_click = self._load(os.path.join(AUDIO_DIR, "click.ogg"))
        self.sfx_dead = self._load(os.path.join(AUDIO_DIR, "dead.wav"))
        self.sfx_receive_shot = self._load(os.path.join(AUDIO_DIR, "receive_shot.wav"))
        self.sfx_shoot = self._load(os.path.join(AUDIO_DIR, "shoot.wav"))
        self.sfx_shop = self._load(os.path.join(AUDIO_DIR, "shop.wav"))
        self.sfx_explosion = self._load(os.path.join(AUDIO_DIR, "explosion.wav"))

        # Volume defaults (0.0 – 1.0)
        self.sfx_volume = 1.0      # Master SFX volume (0.0 – 1.0)
        self.music_volume = 1.0    # Master Music volume (0.0 – 1.0)

        # Base volume ratios for each SFX (relative to master)
        self._sfx_base = {
            'click': 0.5,
            'dead': 0.7,
            'receive_shot': 0.4,
            'shoot': 0.4,
            'shop': 0.6,
            'explosion': 0.8,
        }

        self._apply_sfx_volume()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _load(path: str):
        """Safely load a sound file; returns None on failure."""
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"[AUDIO] Could not load {path}: {e}")
            return None

    def _apply_sfx_volume(self):
        """Apply the master SFX volume to all loaded sound effects."""
        sfx_map = {
            'click': self.sfx_click,
            'dead': self.sfx_dead,
            'receive_shot': self.sfx_receive_shot,
            'shoot': self.sfx_shoot,
            'shop': self.sfx_shop,
            'explosion': self.sfx_explosion,
        }
        for key, sound in sfx_map.items():
            if sound:
                sound.set_volume(self._sfx_base[key] * self.sfx_volume)

    # --------------------------------------------------------- volume controls
    def set_sfx_volume(self, volume_percent: int):
        """Set master SFX volume from a 0-100 slider value."""
        self.sfx_volume = max(0.0, min(1.0, volume_percent / 100))
        self._apply_sfx_volume()

    def set_music_volume(self, volume_percent: int):
        """Set music volume from a 0-100 slider value."""
        self.music_volume = max(0.0, min(1.0, volume_percent / 100))
        pygame.mixer.music.set_volume(self.music_volume)

    # -------------------------------------------------------- music playback
    def start_music(self):
        """Load and play the background music in an infinite loop.
        Safe to call multiple times — will not restart if already playing."""
        if self._music_playing:
            return
        try:
            if not self._music_loaded:
                pygame.mixer.music.load(self._music_path)
                self._music_loaded = True
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1)  # -1 = infinite loop
            self._music_playing = True
        except Exception as e:
            print(f"[AUDIO] Could not start music: {e}")

    def stop_music(self):
        """Pause the background music (keeps position so it can resume)."""
        if self._music_playing:
            pygame.mixer.music.pause()
            self._music_playing = False

    def resume_music(self):
        """Resume the background music from where it was paused."""
        if not self._music_playing and self._music_loaded:
            pygame.mixer.music.unpause()
            self._music_playing = True

    # ------------------------------------------------------------ public API
    def play_click(self):
        """Button click in menus (not in-game)."""
        if self.sfx_click:
            self.sfx_click.play()

    def play_dead(self):
        """An entity (unit or structure) was destroyed."""
        if self.sfx_dead:
            self.sfx_dead.play()

    def play_receive_shot(self):
        """An entity received a shot from the enemy."""
        if self.sfx_receive_shot:
            self.sfx_receive_shot.play()

    def play_shoot(self):
        """A unit fires at an enemy."""
        if self.sfx_shoot:
            self.sfx_shoot.play()

    def play_shop(self):
        if self.sfx_shop:
            self.sfx_shop.play()

    def play_explosion(self):
        if self.sfx_explosion:
            self.sfx_explosion.play()

