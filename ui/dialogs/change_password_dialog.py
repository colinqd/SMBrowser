import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable
from .base_dialog import BaseDialog


class ChangePasswordDialog(BaseDialog):
    def __init__(self, parent: tk.Tk, on_success: Callable[[str], None]):
        super().__init__(parent, "修改主密码", width=420, height=280, resizable=False)
        self.on_success = on_success

    def _create_content(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="修改主密码", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 20))

        ttk.Label(main_frame, text="新主密码:").pack(anchor="w", pady=5)
        self.new_password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.new_password_var, show="*").pack(fill="x", pady=5)

        ttk.Label(main_frame, text="确认新密码:").pack(anchor="w", pady=5)
        self.confirm_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.confirm_var, show="*").pack(fill="x", pady=5)

        self._create_button_frame(main_frame, [
            ("确定", self._do_confirm, 15),
            ("取消", self._on_close, 15)
        ])

    def _do_confirm(self):
        new_pwd = self.new_password_var.get()
        confirm = self.confirm_var.get()
        
        if not new_pwd:
            messagebox.showerror("错误", "请输入新主密码", parent=self.dialog)
            return
        if len(new_pwd) < 6:
            messagebox.showerror("错误", "主密码至少需要6个字符", parent=self.dialog)
            return
        if new_pwd != confirm:
            messagebox.showerror("错误", "两次输入的密码不一致", parent=self.dialog)
            return
        
        self.result = new_pwd
        self.on_success(new_pwd)
        self._on_close()
