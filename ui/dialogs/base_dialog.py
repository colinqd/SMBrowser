import tkinter as tk
from tkinter import ttk
from typing import Optional
import os


class BaseDialog:
    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        width: int = 400,
        height: int = 300,
        resizable: bool = False
    ):
        self.parent = parent
        self.title = title
        self.width = width
        self.height = height
        self.resizable = resizable
        self.dialog: Optional[tk.Toplevel] = None
        self.result = None

    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        
        size = f"{self.width}x{self.height}"
        self.dialog.geometry(size)
        
        if not self.resizable:
            self.dialog.resizable(False, False)
        
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._setup_icon()
        self._center_window()
        self._create_content()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.dialog.wait_window(self.dialog)
        
        return self.result

    def _setup_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app.ico')
            if os.path.exists(icon_path):
                self.dialog.iconbitmap(icon_path)
            elif os.path.exists('app.ico'):
                self.dialog.iconbitmap('app.ico')
        except Exception:
            pass

    def _center_window(self):
        self.dialog.update_idletasks()
        
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        if parent_x < 0 or parent_y < 0 or parent_width <= 1 or parent_height <= 1:
            x = (screen_width - self.width) // 2
            y = (screen_height - self.height) // 2
        else:
            x = parent_x + (parent_width - self.width) // 2
            y = parent_y + (parent_height - self.height) // 2
        
        x = max(0, min(x, screen_width - self.width))
        y = max(0, min(y, screen_height - self.height))
        
        self.dialog.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _create_content(self):
        raise NotImplementedError("子类必须实现 _create_content 方法")

    def _on_close(self):
        self.dialog.destroy()

    def _create_button_frame(self, parent: ttk.Frame, buttons: list) -> ttk.Frame:
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=15)
        
        for text, command, width in buttons:
            ttk.Button(button_frame, text=text, command=command, width=width).pack(side="left", padx=5)
        
        return button_frame
