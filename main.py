import sys
import threading
from interface_layer.ears import analyze_stem_features
from cognitive_layer.hermes_agent import HermesAgent
from hardware_layer.midi_listener import MidiListener
from daw_adapters.logic_pro_adapter import LogicProAdapter
from memory_db.state_manager import StateManager
from memory_db.vector_memory import VectorMemory
from ui_layer.floating_popup import FloatingPopup

class Orchestrator:
    """
    Core orchestrator linking the Brain, Ears, UI, Hardware, and DAW adapter.
    """
    def __init__(self):
        self.state_manager = StateManager()
        self.vector_memory = VectorMemory()
        self.daw_adapter = LogicProAdapter()
        self.agent = HermesAgent()
        
        # UI must run on the main thread
        self.ui = FloatingPopup()
        
        # Pending action state
        self.pending_action = None
        self.pending_reasoning = ""
        self.current_context_hash = ""
        
        # Initialize MIDI Listener callbacks
        self.midi_listener = MidiListener({
            "approve": self.on_approve,
            "reject": self.on_reject,
            "modify": self.on_modify
        })

    def run(self, file_path: str):
        # Start background MIDI listener
        self.midi_listener.start()
        
        # Run analysis asynchronously so UI can start immediately
        threading.Thread(target=self._run_analysis_pipeline, args=(file_path,), daemon=True).start()
        
        # Start UI event loop (blocks main thread until closed)
        self.ui.mainloop()
        
        # Cleanup when UI closes
        self.midi_listener.stop()

    def _run_analysis_pipeline(self, file_path: str):
        # 1. The Ears (Audio Analysis)
        self.ui.update_ui("Status: Analyzing Audio Stems...")
        features_json = analyze_stem_features(file_path)
        
        # 2. The Brain (Hermes Agent)
        track_name = file_path.split("/")[-1].replace(".wav", "")
        self.ui.update_ui("Status: Hermes Reasoning (Connecting to Ollama)...")
        
        decision = self.agent.evaluate_features(features_json, track_name)
        
        self.pending_reasoning = decision.get("reasoning", "")
        self.pending_action = decision.get("action")
        self.current_context_hash = f"{track_name}_hash"
        
        if self.pending_action:
            action_type = self.pending_action.get("type")
            target = self.pending_action.get("target_track")
            action_summary = f"{action_type} on {target}"
            
            # Display pending action waiting for HITL MIDI
            self.ui.update_ui("Status: Pending HITL Approval", self.pending_reasoning, action_summary)
            
            # Log pending state to SQLite
            self.state_manager.log_action(action_type, target, self.pending_action.get("parameters", {}), "pending")
        else:
            self.ui.update_ui("Status: No action recommended.", self.pending_reasoning, "")

    def on_approve(self):
        if not self.pending_action:
            return
            
        print("Orchestrator: MIDI Approve Received!")
        action_type = self.pending_action.get("type")
        target = self.pending_action.get("target_track")
        params = self.pending_action.get("parameters", {})
        
        self.ui.update_ui("Status: Executing Action in Logic Pro...", self.pending_reasoning, "Approved")
        
        # Execute via Logic Pro Adapter
        if action_type == "bounce_stems":
            self.daw_adapter.bounce_stems(params.get("track_names", []), params.get("output_dir", ""))
        elif action_type == "set_volume":
            self.daw_adapter.set_volume(target, params.get("level_db", 0.0))
        elif action_type == "set_mute":
            self.daw_adapter.set_mute(target, params.get("is_muted", True))
        elif action_type == "set_solo":
            self.daw_adapter.set_solo(target, params.get("is_soloed", True))
        elif action_type == "set_pan":
            self.daw_adapter.set_pan(target, params.get("pan_value", 0))
        elif action_type == "set_eq_band":
            self.daw_adapter.set_eq_band(target, params.get("band_index", 1), params.get("freq", 1000.0), params.get("gain", 0.0), params.get("q", 1.0))
        elif action_type == "set_high_pass_filter":
            self.daw_adapter.set_high_pass_filter(target, params.get("freq", 80.0))
        elif action_type == "set_compressor_threshold":
            self.daw_adapter.set_compressor_threshold(target, params.get("threshold_db", -20.0))
        elif action_type == "set_compressor_ratio":
            self.daw_adapter.set_compressor_ratio(target, params.get("ratio", 4.0))
        elif action_type == "set_compressor_attack":
            self.daw_adapter.set_compressor_attack(target, params.get("attack_ms", 10.0))
        elif action_type == "set_compressor_release":
            self.daw_adapter.set_compressor_release(target, params.get("release_ms", 100.0))
        elif action_type == "set_send_level":
            self.daw_adapter.set_send_level(target, params.get("bus_index", 1), params.get("level_db", -6.0))
            
        # Log success and update vector memory
        self.vector_memory.store_delta(self.current_context_hash, self.pending_action, self.pending_action)
        self.ui.update_ui("Status: Done.", "Action executed successfully.", "")
        self.pending_action = None

    def on_reject(self):
        if not self.pending_action:
            return
        print("Orchestrator: MIDI Reject Received!")
        self.ui.update_ui("Status: Action Rejected.", "Awaiting new analysis or input.", "Rejected")
        self.pending_action = None

    def on_modify(self):
        if not self.pending_action:
            return
        print("Orchestrator: MIDI Modify Received!")
        self.ui.update_ui("Status: Modify Action.", "User is manually modifying the parameters via CC.", "Modifying...")

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_wav_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    orchestrator = Orchestrator()
    orchestrator.run(file_path)

if __name__ == "__main__":
    main()
