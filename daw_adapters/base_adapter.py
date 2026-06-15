from abc import ABC, abstractmethod

class BaseDAWAdapter(ABC):
    """
    Abstract interface defining the core actions Hermes can execute in a DAW.
    """
    
    @abstractmethod
    def bounce_stems(self, track_names: list[str], output_dir: str):
        """
        Triggers the DAW to render the specified tracks to .wav files 
        for offline librosa analysis.
        """
        pass

    # ==========================================
    # LEVEL & STATE CONTROLS
    # ==========================================
    @abstractmethod
    def set_volume(self, track_name: str, level_db: float):
        """Sets the primary fader level."""
        pass
        
    @abstractmethod
    def set_mute(self, track_name: str, is_muted: bool):
        """Toggles track mute state."""
        pass

    @abstractmethod
    def set_solo(self, track_name: str, is_soloed: bool):
        """Toggles track solo state."""
        pass
        
    @abstractmethod
    def set_pan(self, track_name: str, pan_value: int):
        """Sets track panning (e.g., -64 for Hard Left, +63 for Hard Right)."""
        pass

    # ==========================================
    # EQUALIZATION
    # ==========================================
    @abstractmethod
    def set_eq_band(self, track_name: str, band_index: int, freq: float, gain: float, q: float):
        """
        Adjusts a specific band on the track's EQ plugin.
        Replaces the generic 'add_eq' to allow multi-band control.
        """
        pass

    @abstractmethod
    def set_high_pass_filter(self, track_name: str, freq: float):
        """Sets the cutoff frequency for the track's high-pass filter."""
        pass

    # ==========================================
    # DYNAMICS (COMPRESSION)
    # ==========================================
    @abstractmethod
    def set_compressor_threshold(self, track_name: str, threshold_db: float):
        """Adjusts the point at which compression begins."""
        pass

    @abstractmethod
    def set_compressor_ratio(self, track_name: str, ratio: float):
        """Adjusts the severity of the compression (e.g., 4.0 for 4:1)."""
        pass

    @abstractmethod
    def set_compressor_attack(self, track_name: str, attack_ms: float):
        """Adjusts the attack time of the compression."""
        pass

    @abstractmethod
    def set_compressor_release(self, track_name: str, release_ms: float):
        """Adjusts the release time of the compression."""
        pass

    # ==========================================
    # AUX SENDS
    # ==========================================
    @abstractmethod
    def set_send_level(self, track_name: str, bus_index: int, level_db: float):
        """Sets the send level to a specific bus."""
        pass

    # ==========================================
    # TRANSPORT
    # ==========================================
    @abstractmethod
    def play(self):
        """Plays the DAW."""
        pass

    @abstractmethod
    def stop(self):
        """Stops the DAW."""
        pass
