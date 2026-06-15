import tkinter as tk

class FloatingPopup:
    """
    Lightweight, custom tkinter popup that floats over Logic Pro.
    Displays Hermes suggestions, current analysis, and system state.
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JJ AI Sound Eng - Hermes")
        
        # Make the window float on top
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.9)
        
        # Position at the top right
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - 350
        y_pos = 50
        self.root.geometry(f"300x200+{x_pos}+{y_pos}")
        
        # Styling
        self.root.configure(bg="#1E1E1E")
        
        self.title_label = tk.Label(self.root, text="Hermes AI Studio Assistant", 
                                    font=("Helvetica", 14, "bold"), fg="#00FF00", bg="#1E1E1E")
        self.title_label.pack(pady=(10, 5))
        
        self.status_label = tk.Label(self.root, text="Status: Waiting for analysis...", 
                                     font=("Helvetica", 12), fg="white", bg="#1E1E1E", wraplength=280)
        self.status_label.pack(pady=5)
        
        self.reasoning_text = tk.Message(self.root, text="", font=("Helvetica", 10, "italic"), 
                                         fg="#AAAAAA", bg="#1E1E1E", width=280)
        self.reasoning_text.pack(pady=5)
        
        self.action_label = tk.Label(self.root, text="", font=("Helvetica", 12, "bold"), 
                                     fg="#FF00FF", bg="#1E1E1E")
        self.action_label.pack(pady=5)

    def update_ui(self, status: str, reasoning: str = "", action_summary: str = ""):
        def _update():
            self.status_label.config(text=status)
            self.reasoning_text.config(text=reasoning)
            self.action_label.config(text=action_summary)
        self.root.after(0, _update)

    def mainloop(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Test script
    popup = FloatingPopup()
    popup.update_ui("Status: Pending Action", "Vocal bus is too loud compared to the reference.", "Action: Set Volume -> -12dB")
    popup.mainloop()
