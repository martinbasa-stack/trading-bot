import tkinter as tk
from tkinter import simpledialog

def prompt_password(title="Unlock Wallet", prompt="Enter wallet password"):
    root = tk.Tk()
    root.withdraw()           # Hide main window
    root.attributes("-topmost", True)

    password = simpledialog.askstring(
        title,
        prompt,
        show="*"               # Password masking
    )

    root.destroy()
    return password
