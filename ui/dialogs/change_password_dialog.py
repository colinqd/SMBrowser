import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable


class ChangePasswordDialog:
    def __init__(self, parent: tk.Tk, on_success: Callable[[str], None]):
        self.parent = parent
        self.on_success = on_success
        self.dialog: Optional[tk.Toplevel] = None

    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("修改主密码")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="修改主密码", 
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 20))

        ttk.Label(main_frame, text="新主密码:").pack(anchor="w", pady=5)
        new_password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=new_password_var, show="*").pack(fill="x", pady=5)

        ttk.Label(main_frame, text="确认新密码:").pack(anchor="w", pady=5)
        confirm_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=confirm_var, show="*").pack(fill="x", pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        def do_confirm():
            new_pwd = new_password_var.get()
            confirm = confirm_var.get()
            if not new_pwd:
                messagebox.showerror("错误", "请输入新主密码", parent=self.dialog)
                return
            if len(new_pwd) < 6:
                messagebox.showerror("错误", "主密码至少需要6个字符", parent=self.dialog)
                return
            if new_pwd != confirm:
                messagebox.showerror("错误", "两次输入的密码不一致", parent=self.dialog)
                return
            self.on_success(new_pwd)
            self.dialog.destroy()

        ttk.Button(button_frame, text="确定", command=do_confirm, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy, width=15).pack(side="left", padx=5)
