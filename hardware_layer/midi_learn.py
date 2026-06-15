import mido
import json
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "midi_config.json")

def learn_cc(action_name: str):
    print(f"Waiting for MIDI input to map to action: {action_name}...")
    # List available ports
    ports = mido.get_input_names()
    if not ports:
        print("No MIDI input ports found! Check your hardware connections.")
        return

    # Look for Arturia KeyLab, otherwise use first available
    target_port = ports[0]
    for port in ports:
        if "KeyLab" in port or "Arturia" in port:
            target_port = port
            break
            
    print(f"Listening on port: {target_port}")
    
    try:
        with mido.open_input(target_port) as inport:
            for msg in inport:
                if msg.type == 'control_change':
                    print(f"Received CC {msg.control} on channel {msg.channel}")
                    
                    # Load existing config
                    config = {}
                    if os.path.exists(CONFIG_FILE):
                        with open(CONFIG_FILE, "r") as f:
                            config = json.load(f)
                    
                    config[action_name] = msg.control
                    
                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config, f, indent=4)
                        
                    print(f"Successfully mapped '{action_name}' to CC {msg.control}")
                    break
    except Exception as e:
        print(f"Error opening MIDI port: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python midi_learn.py <action_name>")
        print("Example: python midi_learn.py approve")
    else:
        learn_cc(sys.argv[1])
