import mido
import json
import os
import threading

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "midi_config.json")

class MidiListener:
    def __init__(self, callbacks=None):
        """
        callbacks: dict mapping action names (e.g. 'approve') to callable functions.
        """
        self.callbacks = callbacks or {}
        self.config = {}
        self.running = False
        self.thread = None
        self._load_config()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
        else:
            print(f"Warning: MIDI config {CONFIG_FILE} not found. Run midi_learn.py first.")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _listen_loop(self):
        ports = mido.get_input_names()
        if not ports:
            print("MidiListener: No MIDI input ports found!")
            return

        target_port = ports[0]
        for port in ports:
            if "KeyLab" in port or "Arturia" in port:
                target_port = port
                break
                
        try:
            # open_input blocks waiting for messages in iteration
            with mido.open_input(target_port) as inport:
                print(f"MidiListener: Started listening on {target_port}")
                for msg in inport:
                    if not self.running:
                        break
                    
                    # We only care about CC messages based on requirements
                    if msg.type == 'control_change':
                        # Check against mapped actions
                        for action_name, cc_num in self.config.items():
                            if msg.control == cc_num:
                                if action_name in self.callbacks:
                                    print(f"MidiListener: Triggering callback for '{action_name}'")
                                    self.callbacks[action_name]()
        except Exception as e:
            print(f"MidiListener Error: {e}")

if __name__ == "__main__":
    # Simple test mode
    def on_approve():
        print("APPROVE Triggered!")
    def on_reject():
        print("REJECT Triggered!")
        
    listener = MidiListener({"approve": on_approve, "reject": on_reject})
    listener.start()
    print("Press Ctrl+C to stop testing.")
    import time
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        listener.stop()
