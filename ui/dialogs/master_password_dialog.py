import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from .base_dialog import BaseDialog


class MasterPasswordDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Tk,
        is_first_time: bool,
        on_success: Callable[[str], None]
    ):
        self.is_first_time = is_first_time
        self.on_success = on_success
        
        if is_first_time:
            super().__init__(parent, "设置主密码", width=420, height=280, resizable=False)
        else:
            super().__init__(parent, "输入主密码", width=420, height=260, resizable=False)

    def _create_content(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        if self.is_first_time:
            self._create_setup_content(main_frame)
        else:
            self._create_unlock_content(main_frame)

    def _create_setup_content(self, parent: ttk.Frame):
        ttk.Label(parent, text="请设置主密码（用于加密保存的连接密码）", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 20))

        ttk.Label(parent, text="主密码:").pack(anchor="w", pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.password_var, show="*").pack(fill="x", pady=5)

        ttk.Label(parent, text="确认密码:").pack(anchor="w", pady=5)
        self.confirm_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.confirm_var, show="*").pack(fill="x", pady=5)

        self._create_button_frame(parent, [
            ("确定", self._do_setup, 15),
            ("取消", self._on_close, 15)
        ])

    def _create_unlock_content(self, parent: ttk.Frame):
        ttk.Label(parent, text="请输入主密码以解锁保存的连接配置", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 10))

        hint_label = ttk.Label(parent, text="提示：默认主密码为 admin", 
                              font=("Segoe UI", 9), foreground="gray")
        hint_label.pack(pady=(0, 15))

        ttk.Label(parent, text="主密码:").pack(anchor="w", pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.password_var, show="*").pack(fill="x", pady=5)

        self._create_button_frame(parent, [
            ("确定", self._do_unlock, 15),
            ("取消", self._on_close, 15)
        ])

    def _do_setup(self):
        pwd = self.password_var.get()
        confirm = self.confirm_var.get()
        
        if not pwd:
            messagebox.showerror("错误", "请输入主密码", parent=self.dialog)
            return
        if len(pwd) < 6:
            messagebox.showerror("错误", "主密码至少需要6个字符", parent=self.dialog)
            return
        if pwd != confirm:
            messagebox.showerror("错误", "两次输入的密码不一致", parent=self.dialog)
            return
        
        self.result = pwd
        self.on_success(pwd)
        self._on_close()

    def _do_unlock(self):
        pwd = self.password_var.get()
        
        if not pwd:
            messagebox.showerror("错误", "请输入主密码", parent=self.dialog)
            return
        
        self.result = pwd
        self.on_success(pwd)
        self._on_close()
