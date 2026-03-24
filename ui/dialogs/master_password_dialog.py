import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable


class MasterPasswordDialog:
    def __init__(
        self,
        parent: tk.Tk,
        is_first_time: bool,
        on_success: Callable[[str], None]
    ):
        self.parent = parent
        self.is_first_time = is_first_time
        self.on_success = on_success
        self.dialog: Optional[tk.Toplevel] = None
        self.result: Optional[str] = None

    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        if self.is_first_time:
            self.dialog.title("设置主密码")
            self._show_setup_dialog()
        else:
            self.dialog.title("输入主密码")
            self._show_unlock_dialog()

    def _show_setup_dialog(self):
        self.dialog.geometry("400x280")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="请设置主密码（用于加密保存的连接密码）", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 20))

        ttk.Label(main_frame, text="主密码:").pack(anchor="w", pady=5)
        password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=password_var, show="*").pack(fill="x", pady=5)

        ttk.Label(main_frame, text="确认密码:").pack(anchor="w", pady=5)
        confirm_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=confirm_var, show="*").pack(fill="x", pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        def do_confirm():
            pwd = password_var.get()
            confirm = confirm_var.get()
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
            self.dialog.destroy()

        ttk.Button(button_frame, text="确定", command=do_confirm, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy, width=15).pack(side="left", padx=5)

    def _show_unlock_dialog(self):
        self.dialog.geometry("400x260")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="请输入主密码以解锁保存的连接配置", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 10))

        hint_label = ttk.Label(main_frame, text="提示：默认主密码为 admin", 
                              font=("Segoe UI", 9), foreground="gray")
        hint_label.pack(pady=(0, 15))

        ttk.Label(main_frame, text="主密码:").pack(anchor="w", pady=5)
        password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=password_var, show="*").pack(fill="x", pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        def do_confirm():
            pwd = password_var.get()
            if not pwd:
                messagebox.showerror("错误", "请输入主密码", parent=self.dialog)
                return
            self.result = pwd
            self.on_success(pwd)
            self.dialog.destroy()

        ttk.Button(button_frame, text="确定", command=do_confirm, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy, width=15).pack(side="left", padx=5)
