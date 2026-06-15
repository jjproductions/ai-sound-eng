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
        
        # Check for analysis errors
        import json
        features_dict = json.loads(features_json)
        if features_dict.get("status") == "error":
            error_msg = features_dict.get("error_message", "Unknown error")
            self.ui.update_ui("Status: Analysis Failed.", f"Error: {error_msg}", "")
            return
        
        # 2. The Brain (Hermes Agent)
        track_name = file_path.split("/")[-1].replace(".wav", "")
        self.ui.update_ui("Status: Hermes Reasoning (Connecting to Ollama)...")
        
        # Retrieve Procedural Memory
        past_contexts = self.vector_memory.retrieve_similar_contexts(features_json)
        
        decision = self.agent.evaluate_features(features_json, track_name, past_contexts)
        
        self.pending_reasoning = decision.get("reasoning", "")
        self.pending_action = decision.get("action")
        self.pending_features_json = features_json
        
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
        method = getattr(self.daw_adapter, action_type, None)
        if method:
            try:
                if action_type == "bounce_stems":
                    method(**params)
                else:
                    method(track_name=target, **params)
            except TypeError as e:
                print(f"Orchestrator: Parameter mismatch for '{action_type}' - {e}")
        else:
            print(f"Orchestrator: Unknown action type '{action_type}'")
            
        # Log success and update vector memory
        self.vector_memory.store_delta(self.pending_features_json, self.pending_action, self.pending_action)
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
