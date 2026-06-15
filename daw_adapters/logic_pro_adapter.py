import subprocess
from .base_adapter import BaseDAWAdapter

class LogicProAdapter(BaseDAWAdapter):
    """
    Implementation of DAW adapter for Logic Pro 12.2.
    Uses OSC for parameter changes and AppleScript for transport controls/bouncing.
    """
    def __init__(self, osc_client=None):
        self.osc_client = osc_client

    def _run_applescript(self, script: str):
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"AppleScript Error: {result.stderr}")
            return result.stdout.strip()
        except Exception as e:
            print(f"Failed to execute AppleScript: {e}")
            return None

    def bounce_stems(self, track_names: list[str], output_dir: str):
        print(f"LogicProAdapter: Bouncing stems {track_names} to {output_dir}")
        # Applescript logic would go here to automate bounce-in-place or export

    # ==========================================
    # LEVEL & STATE CONTROLS
    # ==========================================
    def set_volume(self, track_name: str, level_db: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/volume", level_db)
            print(f"LogicProAdapter: Sent OSC set_volume for {track_name} to {level_db} dB")
        else:
            print(f"LogicProAdapter (Mock): Setting {track_name} volume to {level_db} dB")

    def set_mute(self, track_name: str, is_muted: bool):
        val = 1 if is_muted else 0
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/mute", val)
            print(f"LogicProAdapter: Sent OSC set_mute for {track_name} to {is_muted}")
        else:
            print(f"LogicProAdapter (Mock): Setting {track_name} mute to {is_muted}")

    def set_solo(self, track_name: str, is_soloed: bool):
        val = 1 if is_soloed else 0
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/solo", val)
            print(f"LogicProAdapter: Sent OSC set_solo for {track_name} to {is_soloed}")
        else:
            print(f"LogicProAdapter (Mock): Setting {track_name} solo to {is_soloed}")

    def set_pan(self, track_name: str, pan_value: int):
        # Pan is -64 to +63
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/pan", pan_value)
            print(f"LogicProAdapter: Sent OSC set_pan for {track_name} to {pan_value}")
        else:
            print(f"LogicProAdapter (Mock): Setting {track_name} pan to {pan_value}")

    # ==========================================
    # EQUALIZATION
    # ==========================================
    def set_eq_band(self, track_name: str, band_index: int, freq: float, gain: float, q: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/eq/{band_index}/freq", freq)
            self.osc_client.send_message(f"/track/{track_name}/eq/{band_index}/gain", gain)
            self.osc_client.send_message(f"/track/{track_name}/eq/{band_index}/q", q)
            print(f"LogicProAdapter: Sent OSC set_eq_band {band_index} for {track_name}")
        else:
            print(f"LogicProAdapter (Mock): Setting EQ band {band_index} on {track_name}: {freq}Hz, {gain}dB, Q={q}")

    def set_high_pass_filter(self, track_name: str, freq: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/eq/hpf/freq", freq)
            print(f"LogicProAdapter: Sent OSC set_high_pass_filter for {track_name} to {freq}Hz")
        else:
            print(f"LogicProAdapter (Mock): Setting high pass filter on {track_name} to {freq}Hz")

    # ==========================================
    # DYNAMICS (COMPRESSION)
    # ==========================================
    def set_compressor_threshold(self, track_name: str, threshold_db: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/compressor/threshold", threshold_db)
            print(f"LogicProAdapter: Sent OSC set_compressor_threshold for {track_name} to {threshold_db}dB")
        else:
            print(f"LogicProAdapter (Mock): Setting compressor threshold on {track_name} to {threshold_db}dB")

    def set_compressor_ratio(self, track_name: str, ratio: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/compressor/ratio", ratio)
            print(f"LogicProAdapter: Sent OSC set_compressor_ratio for {track_name} to {ratio}")
        else:
            print(f"LogicProAdapter (Mock): Setting compressor ratio on {track_name} to {ratio}")

    def set_compressor_attack(self, track_name: str, attack_ms: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/compressor/attack", attack_ms)
        else:
            print(f"LogicProAdapter (Mock): Setting compressor attack on {track_name} to {attack_ms}ms")

    def set_compressor_release(self, track_name: str, release_ms: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/compressor/release", release_ms)
        else:
            print(f"LogicProAdapter (Mock): Setting compressor release on {track_name} to {release_ms}ms")

    # ==========================================
    # AUX SENDS
    # ==========================================
    def set_send_level(self, track_name: str, bus_index: int, level_db: float):
        if self.osc_client:
            self.osc_client.send_message(f"/track/{track_name}/send/{bus_index}/volume", level_db)
            print(f"LogicProAdapter: Sent OSC set_send_level for {track_name} bus {bus_index} to {level_db} dB")
        else:
            print(f"LogicProAdapter (Mock): Setting {track_name} send {bus_index} level to {level_db} dB")

    # ==========================================
    # TRANSPORT
    # ==========================================
    def play(self):
        script = 'tell application "Logic Pro" to play'
        self._run_applescript(script)
        print("LogicProAdapter: Triggered Play")

    def stop(self):
        script = 'tell application "Logic Pro" to stop'
        self._run_applescript(script)
        print("LogicProAdapter: Triggered Stop")
