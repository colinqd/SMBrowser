import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Dict, Optional, Callable


class ConnectDialog:
    def __init__(
        self,
        parent: tk.Tk,
        servers: Dict,
        on_connect: Callable[[str, str, str, str, str, str], None],
        on_save_config: Callable[[str, str, str, str, str, str], None]
    ):
        self.parent = parent
        self.servers = servers
        self.on_connect = on_connect
        self.on_save_config = on_save_config
        self.dialog: Optional[tk.Toplevel] = None
        self.saved_configs_cb: Optional[ttk.Combobox] = None

    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("连接到服务器")
        self.dialog.geometry("500x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="保存的配置:").grid(row=0, column=0, sticky="w", pady=5)
        self.saved_configs_cb = ttk.Combobox(main_frame, values=list(self.servers.keys()), state="readonly")
        self.saved_configs_cb.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)
        self.saved_configs_cb.bind("<<ComboboxSelected>>", self._on_config_select)

        ttk.Label(main_frame, text="服务器地址:").grid(row=1, column=0, sticky="w", pady=5)
        server_ip_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=server_ip_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="端口:").grid(row=2, column=0, sticky="w", pady=5)
        port_var = tk.StringVar(value="445")
        ttk.Entry(main_frame, textvariable=port_var, width=10).grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(main_frame, text="用户名:").grid(row=3, column=0, sticky="w", pady=5)
        username_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=username_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="密码:").grid(row=4, column=0, sticky="w", pady=5)
        password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=password_var, show="*").grid(row=4, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="共享名称:").grid(row=5, column=0, sticky="w", pady=5)
        share_name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=share_name_var).grid(row=5, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="SMB版本:").grid(row=6, column=0, sticky="w", pady=5)
        smb_version_var = tk.StringVar(value="自动协商")
        ttk.Combobox(main_frame, textvariable=smb_version_var,
                    values=["SMBv1", "SMBv2", "SMBv3", "自动协商"],
                    state="readonly").grid(row=6, column=1, sticky="w", pady=5)

        main_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)

        def do_connect():
            self.on_connect(
                server_ip_var.get(),
                port_var.get(),
                username_var.get(),
                password_var.get(),
                share_name_var.get(),
                smb_version_var.get()
            )
            self.dialog.destroy()

        ttk.Button(button_frame, text="连接", command=do_connect, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="保存配置",
                  command=lambda: self._save_config(
                      server_ip_var.get(), port_var.get(), username_var.get(),
                      password_var.get(), share_name_var.get(), smb_version_var.get()
                  ), width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy, width=15).pack(side="left", padx=5)

    def _on_config_select(self, event):
        config_name = self.saved_configs_cb.get()
        if config_name in self.servers:
            config = self.servers[config_name]
            widgets = self.dialog.winfo_children()[0].winfo_children()
            widgets[3].delete(0, "end")
            widgets[3].insert(0, config.get("server_ip", ""))
            widgets[5].delete(0, "end")
            widgets[5].insert(0, config.get("port", "445"))
            widgets[7].delete(0, "end")
            widgets[7].insert(0, config.get("username", ""))
            widgets[9].delete(0, "end")
            widgets[9].insert(0, config.get("password", ""))
            widgets[11].delete(0, "end")
            widgets[11].insert(0, config.get("share_name", ""))
            widgets[13].set(config.get("smb_version", "自动协商"))

    def _save_config(self, server_ip: str, port: str, username: str,
                     password: str, share_name: str, smb_version: str):
        config_name = simpledialog.askstring("保存配置", "输入配置名称:", parent=self.dialog)
        if config_name:
            self.on_save_config(config_name, server_ip, port, username, password, share_name, smb_version)
            if self.saved_configs_cb:
                self.saved_configs_cb["values"] = list(self.servers.keys())
            messagebox.showinfo("成功", f"配置 '{config_name}' 已保存", parent=self.dialog)
