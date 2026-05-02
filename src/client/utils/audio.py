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

        # Load all sound effects
        self.sfx_click = self._load(os.path.join(AUDIO_DIR, "click.ogg"))
        self.sfx_dead = self._load(os.path.join(AUDIO_DIR, "dead.wav"))
        self.sfx_receive_shot = self._load(os.path.join(AUDIO_DIR, "receive_shot.wav"))
        self.sfx_shoot = self._load(os.path.join(AUDIO_DIR, "shoot.wav"))
        self.sfx_shop = self._load(os.path.join(AUDIO_DIR, "shop.wav"))

        # Volume defaults (0.0 – 1.0)
        if self.sfx_click:
            self.sfx_click.set_volume(0.5)
        if self.sfx_dead:
            self.sfx_dead.set_volume(0.7)
        if self.sfx_receive_shot:
            self.sfx_receive_shot.set_volume(0.4)
        if self.sfx_shoot:
            self.sfx_shoot.set_volume(0.4)
        if self.sfx_shop:
            self.sfx_shop.set_volume(0.6)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _load(path: str):
        """Safely load a sound file; returns None on failure."""
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"[AUDIO] Could not load {path}: {e}")
            return None

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
        """A successful purchase was made in the shop."""
        if self.sfx_shop:
            self.sfx_shop.play()
