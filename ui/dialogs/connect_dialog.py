import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Dict, Optional, Callable
from .base_dialog import BaseDialog


class ConnectDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Tk,
        servers: Dict,
        on_connect: Callable[[str, str, str, str, str, str], None],
        on_save_config: Callable[[str, str, str, str, str, str], None]
    ):
        super().__init__(parent, "连接到服务器", width=500, height=420, resizable=False)
        self.servers = servers
        self.on_connect = on_connect
        self.on_save_config = on_save_config
        self.saved_configs_cb: Optional[ttk.Combobox] = None
        
        self.server_ip_var = tk.StringVar()
        self.port_var = tk.StringVar(value="445")
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.share_name_var = tk.StringVar()
        self.smb_version_var = tk.StringVar(value="自动协商")

    def _create_content(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="保存的配置:").grid(row=0, column=0, sticky="w", pady=5)
        self.saved_configs_cb = ttk.Combobox(main_frame, values=list(self.servers.keys()), state="readonly")
        self.saved_configs_cb.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)
        self.saved_configs_cb.bind("<<ComboboxSelected>>", self._on_config_select)

        ttk.Label(main_frame, text="服务器地址:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.server_ip_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="端口:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.port_var, width=10).grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(main_frame, text="用户名:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.username_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="密码:").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.password_var, show="*").grid(row=4, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="共享名称:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.share_name_var).grid(row=5, column=1, columnspan=2, sticky="ew", pady=5)

        ttk.Label(main_frame, text="SMB版本:").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Combobox(main_frame, textvariable=self.smb_version_var,
                    values=["SMBv1", "SMBv2", "SMBv3", "自动协商"],
                    state="readonly").grid(row=6, column=1, sticky="w", pady=5)

        main_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="连接", command=self._do_connect, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="保存配置", command=self._save_config, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_close, width=15).pack(side="left", padx=5)

    def _do_connect(self):
        self.on_connect(
            self.server_ip_var.get(),
            self.port_var.get(),
            self.username_var.get(),
            self.password_var.get(),
            self.share_name_var.get(),
            self.smb_version_var.get()
        )
        self._on_close()

    def _on_config_select(self, event):
        config_name = self.saved_configs_cb.get()
        if config_name in self.servers:
            config = self.servers[config_name]
            self.server_ip_var.set(config.get("server_ip", ""))
            self.port_var.set(config.get("port", "445"))
            self.username_var.set(config.get("username", ""))
            self.password_var.set(config.get("password", ""))
            self.share_name_var.set(config.get("share_name", ""))
            self.smb_version_var.set(config.get("smb_version", "自动协商"))

    def _save_config(self):
        config_name = simpledialog.askstring("保存配置", "输入配置名称:", parent=self.dialog)
        if config_name:
            self.on_save_config(
                config_name,
                self.server_ip_var.get(),
                self.port_var.get(),
                self.username_var.get(),
                self.password_var.get(),
                self.share_name_var.get(),
                self.smb_version_var.get()
            )
            if self.saved_configs_cb:
                self.saved_configs_cb["values"] = list(self.servers.keys())
            messagebox.showinfo("成功", f"配置 '{config_name}' 已保存", parent=self.dialog)
