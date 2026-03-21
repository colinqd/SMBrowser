import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, Menu, simpledialog
from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError, OperationFailure
import json
import os
import threading
import datetime
import re
import sys
import queue
import time
from typing import Optional, Dict, List, Tuple, Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False


class SMBClientBrowser(TkinterDnD.Tk if DND_SUPPORT else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMB文件管理器")
        self.geometry("1280x720")
        self.minsize(800, 600)
        
        self.conn: Optional[SMBConnection] = None
        self.current_share: str = ""
        self.current_path: str = "/"
        self.current_server_ip: str = ""
        self.servers: Dict = self.load_servers()
        self.tree_nodes: Dict[str, str] = {}
        self.dragged_item: Optional[str] = None
        self.sorted_column: str = ""
        self.sort_reverse: bool = False
        self.task_queue: queue.Queue = queue.Queue()
        self.is_connected: bool = False
        self.available_shares: List[str] = []
        
        self.setup_style()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.process_tasks()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except:
            try:
                style.theme_use('winnative')
            except:
                try:
                    style.theme_use('clam')
                except:
                    pass
        
        style.configure("Toolbar.TButton", padding=(8, 4), relief="raised", font=('Segoe UI', 9))
        style.map("Toolbar.TButton", 
                 relief=[('pressed', 'sunken'), ('active', 'raised')])
        style.configure("Path.TEntry", padding=4, font=('Segoe UI', 9))
        style.configure("Status.TLabel", padding=2, font=('Segoe UI', 8))
        style.configure("Treeview", font=('Segoe UI', 9), rowheight=22)
        style.configure("Treeview.Heading", font=('Segoe UI', 9, 'bold'))
        style.configure("TLabelframe", font=('Segoe UI', 9))
        style.configure("TButton", font=('Segoe UI', 9))
        style.configure("TLabel", font=('Segoe UI', 9))
        style.configure("TEntry", font=('Segoe UI', 9))
        style.configure("TCombobox", font=('Segoe UI', 9))
        
        self.configure(bg="#ffffff")

    def create_widgets(self):
        self.create_menubar()
        self.create_toolbar()
        self.create_path_bar()
        self.create_main_panes()
        self.create_status_bar()
        self.create_log_area()

    def create_menubar(self):
        menubar = Menu(self)
        
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="连接服务器", command=self.show_connect_dialog, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_close, accelerator="Alt+F4")
        menubar.add_cascade(label="文件", menu=file_menu)
        
        view_menu = Menu(menubar, tearoff=0)
        view_menu.add_command(label="刷新", command=self.refresh_files, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="大图标", command=lambda: self.set_view_mode("large"))
        view_menu.add_command(label="详细信息", command=lambda: self.set_view_mode("details"))
        menubar.add_cascade(label="查看", menu=view_menu)
        
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.config(menu=menubar)
        
        self.bind("<F5>", lambda e: self.refresh_files())
        self.bind("<Control-n>", lambda e: self.show_connect_dialog())

    def create_toolbar(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=2)
        
        self.btn_back = ttk.Button(toolbar, text="← 后退", command=self.go_up)
        self.btn_back.pack(side="left", padx=2)
        self.btn_back.state(["disabled"])
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5, pady=3)
        
        ttk.Button(toolbar, text="📁 新建文件夹", command=self.create_folder).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📤 上传文件", command=self.upload_file).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📥 下载选中", command=self.download_selected_files).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑️ 删除", command=self.delete_selected_items).pack(side="left", padx=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5, pady=3)
        
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_files).pack(side="left", padx=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5, pady=3)
        
        self.conn_status_label = ttk.Label(toolbar, text="🔴 未连接", foreground="red")
        self.conn_status_label.pack(side="right", padx=10)

    def create_path_bar(self):
        path_frame = ttk.Frame(self)
        path_frame.pack(fill="x", padx=10, pady=2)
        
        ttk.Label(path_frame, text="路径:").pack(side="left")
        
        self.path_entry = ttk.Entry(path_frame, style="Path.TEntry")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.path_entry.bind("<Return>", self.on_path_enter)
        
        self.btn_connect = ttk.Button(path_frame, text="连接服务器", command=self.show_connect_dialog)
        self.btn_connect.pack(side="left", padx=5)

    def create_main_panes(self):
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        left_frame = ttk.LabelFrame(main_paned, text="📁 文件夹")
        main_paned.add(left_frame, weight=1)
        
        self.tree_dir = ttk.Treeview(left_frame, show="tree", selectmode="browse")
        self.tree_dir.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_dir.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree_dir.configure(yscrollcommand=tree_scroll.set)
        
        self.tree_dir.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree_dir.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree_dir.bind("<Button-3>", self.show_tree_context_menu)
        
        right_frame = ttk.LabelFrame(main_paned, text="📄 文件列表")
        main_paned.add(right_frame, weight=4)
        
        self.file_list = ttk.Treeview(right_frame, 
                                     columns=("Name", "Size", "Type", "Modified"),
                                     show="headings", selectmode="extended")
        self.file_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        columns = [
            {"id": "Name", "text": "名称", "width": 350, "anchor": "w"},
            {"id": "Size", "text": "大小", "width": 100, "anchor": "e"},
            {"id": "Type", "text": "类型", "width": 100, "anchor": "center"},
            {"id": "Modified", "text": "修改日期", "width": 160, "anchor": "center"}
        ]
        
        for col in columns:
            self.file_list.heading(
                col["id"],
                text=col["text"],
                anchor=col["anchor"],
                command=lambda c=col["id"]: self.sort_file_list(c)
            )
            self.file_list.column(
                col["id"],
                width=col["width"],
                anchor=col["anchor"]
            )
        
        file_scroll_y = ttk.Scrollbar(right_frame, orient="vertical", command=self.file_list.yview)
        file_scroll_y.pack(side="right", fill="y")
        file_scroll_x = ttk.Scrollbar(right_frame, orient="horizontal", command=self.file_list.xview)
        file_scroll_x.pack(side="bottom", fill="x")
        self.file_list.configure(yscrollcommand=file_scroll_y.set, xscrollcommand=file_scroll_x.set)
        
        self.file_list.bind("<Button-3>", self.show_file_context_menu)
        self.file_list.bind("<Double-1>", self.on_file_double_click)
        self.file_list.bind("<Return>", lambda e: self.on_file_double_click(e))
        self.file_list.bind("<Delete>", lambda e: self.delete_selected_items())

    def create_status_bar(self):
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", side="bottom")
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                      relief="sunken", anchor="w", style="Status.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True, padx=2)
        
        self.item_count_var = tk.StringVar(value="0 个项目")
        ttk.Label(status_frame, textvariable=self.item_count_var, 
                 relief="sunken", anchor="e").pack(side="right", padx=2)

    def create_log_area(self):
        self.log_toggle = ttk.Button(self, text="▼ 显示日志", command=self.toggle_log)
        self.log_toggle.pack(fill="x", padx=10, pady=(0, 5))
        
        self.log_frame = ttk.LabelFrame(self, text="操作日志")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.log_frame.pack_forget()
        
        self.log_area = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_visible = False

    def toggle_log(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_toggle.config(text="▲ 隐藏日志")
            self.log_frame.pack(after=self.log_toggle, fill="both", expand=True, padx=10, pady=(0, 5))
        else:
            self.log_toggle.config(text="▼ 显示日志")
            self.log_frame.pack_forget()

    def log_message(self, message: str):
        self.log_area.config(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def update_status(self, text: str):
        self.status_var.set(text)

    def update_connection_status(self, connected: bool):
        self.is_connected = connected
        if connected:
            self.conn_status_label.config(text="🟢 已连接", foreground="green")
            self.btn_connect.config(text="断开连接", command=self.disconnect)
        else:
            self.conn_status_label.config(text="🔴 未连接", foreground="red")
            self.btn_connect.config(text="连接服务器", command=self.show_connect_dialog)

    def show_connect_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("连接到服务器")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="保存的配置:").grid(row=0, column=0, sticky="w", pady=5)
        saved_configs = ttk.Combobox(main_frame, values=list(self.servers.keys()), state="readonly")
        saved_configs.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)
        
        def on_config_select(event):
            config_name = saved_configs.get()
            if config_name in self.servers:
                config = self.servers[config_name]
                server_ip_var.set(config.get("server_ip", ""))
                port_var.set(config.get("port", "445"))
                username_var.set(config.get("username", ""))
                password_var.set(config.get("password", ""))
                share_name_var.set(config.get("share_name", ""))
                smb_version_var.set(config.get("smb_version", "自动协商"))
        
        saved_configs.bind("<<ComboboxSelected>>", on_config_select)
        
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
            self.connect_to_server(
                server_ip_var.get(),
                port_var.get(),
                username_var.get(),
                password_var.get(),
                share_name_var.get(),
                smb_version_var.get()
            )
            dialog.destroy()
        
        ttk.Button(button_frame, text="连接", command=do_connect, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="保存配置", 
                  command=lambda: self.save_connection_config(
                      server_ip_var.get(), port_var.get(), username_var.get(),
                      password_var.get(), share_name_var.get(), smb_version_var.get(),
                      saved_configs
                  ), width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side="left", padx=5)

    def save_connection_config(self, server_ip: str, port: str, username: str, 
                                password: str, share_name: str, smb_version: str, 
                                combobox: ttk.Combobox):
        config_name = simpledialog.askstring("保存配置", "输入配置名称:")
        if config_name:
            self.servers[config_name] = {
                "server_ip": server_ip,
                "port": port,
                "username": username,
                "password": password,
                "share_name": share_name,
                "smb_version": smb_version
            }
            with open("smb_config.json", "w", encoding="utf-8") as f:
                json.dump(self.servers, f, ensure_ascii=False, indent=2)
            combobox["values"] = list(self.servers.keys())
            self.log_message(f"配置已保存: {config_name}")
            messagebox.showinfo("成功", f"配置 '{config_name}' 已保存")

    def connect_to_server(self, server_ip: str, port: str, username: str, 
                       password: str, share_name: str, smb_version_choice: str):
        if not server_ip:
            messagebox.showerror("错误", "请输入服务器地址")
            return

        self.current_server_ip = server_ip

        def connect_thread():
            try:
                self.after(0, lambda: self.update_status("正在连接..."))
                
                port_num = int(port) if port and port.isdigit() else 445
                
                use_ntlm_v2 = {
                    "SMBv1": False,
                    "SMBv2": True,
                    "SMBv3": True,
                    "自动协商": True
                }.get(smb_version_choice, True)

                import socket
                socket.setdefaulttimeout(30)

                self.conn = SMBConnection(
                    username,
                    password,
                    "SMBClient",
                    server_ip,
                    use_ntlm_v2=use_ntlm_v2,
                    is_direct_tcp=True
                )

                connected = self.conn.connect(server_ip, port_num, timeout=30)

                if connected:
                    self.after(0, lambda: self.on_connected(share_name))
                else:
                    self.after(0, lambda: self.on_connect_failed("连接失败"))

            except (NotConnectedError, OperationFailure) as e:
                self.after(0, lambda: self.on_connect_failed(f"认证失败: {str(e)}"))
            except socket.error as e:
                if hasattr(e, 'errno') and e.errno == 10054:
                    self.after(0, lambda: self.on_connect_failed("连接被远程主机重置"))
                else:
                    self.after(0, lambda: self.on_connect_failed(f"网络错误: {str(e)}"))
            except Exception as e:
                self.after(0, lambda: self.on_connect_failed(f"发生异常: {str(e)}"))
            finally:
                import socket
                socket.setdefaulttimeout(None)

        threading.Thread(target=connect_thread, daemon=True).start()

    def on_connected(self, share_name: str):
        self.update_connection_status(True)
        self.update_status("连接成功")
        self.log_message("服务器连接成功")
        
        self.available_shares = [s.name for s in self.conn.listShares()]
        
        if share_name and share_name in self.available_shares:
            self.current_share = share_name
            self.init_directory_tree()
        else:
            self.init_share_tree()
            if share_name:
                messagebox.showwarning("提示", 
                    f"共享 '{share_name}' 不存在！可用共享: {', '.join(self.available_shares)}")

    def on_connect_failed(self, message: str):
        self.update_connection_status(False)
        self.update_status(message)
        self.log_message(message)
        messagebox.showerror("连接失败", message)

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
        
        self.update_connection_status(False)
        self.update_status("已断开连接")
        self.log_message("已断开连接")
        
        for item in self.tree_dir.get_children():
            self.tree_dir.delete(item)
        for item in self.file_list.get_children():
            self.file_list.delete(item)
        
        self.tree_nodes.clear()
        self.path_entry.delete(0, "end")
        self.item_count_var.set("0 个项目")

    def init_share_tree(self):
        for item in self.tree_dir.get_children():
            self.tree_dir.delete(item)
        
        root_id = self.tree_dir.insert("", "end", text=f"🖥️ {self.current_server_ip}", open=True)
        self.tree_nodes[root_id] = "//SERVER_ROOT//"
        
        for share in self.available_shares:
            node_id = self.tree_dir.insert(root_id, "end", text=f"📁 {share}", tags=("share",))
            self.tree_nodes[node_id] = f"//SHARE//{share}"
        
        self.update_status("请选择共享目录")

    def init_directory_tree(self):
        for item in self.tree_dir.get_children():
            self.tree_dir.delete(item)
        
        root_id = self.tree_dir.insert("", "end", text=f"📁 {self.current_share}", open=True)
        self.tree_nodes[root_id] = "/"
        
        self.populate_tree_node(root_id, "/")
        
        self.tree_dir.selection_set(root_id)
        self.tree_dir.focus(root_id)
        self.on_tree_select(None)

    def populate_tree_node(self, parent_id: str, path: str):
        if not self.conn or not self.current_share:
            return
        
        try:
            for child in self.tree_dir.get_children(parent_id):
                self.tree_dir.delete(child)
            
            dirs = [f for f in self.conn.listPath(self.current_share, path)
                    if f.isDirectory and f.filename not in (".", "..")]
            
            for d in dirs:
                full_path = os.path.join(path, d.filename).replace("\\", "/")
                
                if full_path.startswith("//"):
                    full_path = full_path[2:]
                if not full_path.startswith("/"):
                    full_path = "/" + full_path
                
                node_id = self.tree_dir.insert(parent_id, "end", text=f"📁 {d.filename}", tags=("dir",))
                self.tree_nodes[node_id] = full_path
                
                self.tree_dir.insert(node_id, "end", text="Loading...")
        except NotConnectedError:
            self.log_message(f"连接已断开，无法访问目录: {path}")
            self.update_connection_status(False)
        except OperationFailure as e:
            self.log_message(f"操作失败: {path} - {str(e)}")
        except Exception as e:
            self.log_message(f"目录访问失败: {path} - {str(e)}")

    def on_tree_expand(self, event):
        node_id = self.tree_dir.focus()
        if node_id and self.tree_dir.tag_has("dir", node_id):
            self.populate_tree_node(node_id, self.tree_nodes[node_id])

    def on_tree_select(self, event):
        selected = self.tree_dir.selection()
        if not selected:
            return
        
        node_id = selected[0]
        node_path = self.tree_nodes.get(node_id, "")
        
        if node_path.startswith("//SHARE//"):
            self.current_share = self.tree_dir.item(node_id, "text").replace("📁 ", "")
            self.current_path = "/"
            self.log_message(f"已选择共享: {self.current_share}")
            self.init_directory_tree()
            self.update_back_button_state()
            return
        
        if node_path and not node_path.startswith("//"):
            self.current_path = node_path
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, f"{self.current_share}:{self.current_path}")
            self.load_file_list()
            self.update_back_button_state()

    def on_path_enter(self, event):
        path_text = self.path_entry.get()
        if ":" in path_text:
            share, path = path_text.split(":", 1)
            if share == self.current_share:
                self.current_path = path
                self.select_in_directory_tree(path)
                self.load_file_list()

    def select_in_directory_tree(self, path: str):
        for node_id, node_path in self.tree_nodes.items():
            if node_path == path:
                self.tree_dir.selection_set(node_id)
                self.tree_dir.focus(node_id)
                self.tree_dir.see(node_id)
                return True
        
        parent_path = os.path.dirname(path.rstrip("/"))
        if not parent_path or parent_path == "/":
            return False
        
        parent_id = None
        for node_id, node_path in self.tree_nodes.items():
            if node_path == parent_path:
                parent_id = node_id
                break
        
        if parent_id:
            self.tree_dir.item(parent_id, open=True)
            self.populate_tree_node(parent_id, parent_path)
            
            for node_id, node_path in self.tree_nodes.items():
                if node_path == path:
                    self.tree_dir.selection_set(node_id)
                    self.tree_dir.focus(node_id)
                    self.tree_dir.see(node_id)
                    return True
        
        return False

    def load_file_list(self):
        for item in self.file_list.get_children():
            self.file_list.delete(item)
        
        if not self.conn or not self.current_share:
            self.item_count_var.set("0 个项目")
            return
        
        try:
            files = self.conn.listPath(self.current_share, self.current_path)
            file_count = 0
            
            for file in files:
                if file.filename in [".", ".."]:
                    continue
                
                file_count += 1
                filename = file.filename
                
                try:
                    mod_time = datetime.datetime.fromtimestamp(file.last_write_time).strftime("%Y-%m-%d %H:%M")
                except (ValueError, OSError):
                    mod_time = "未知"
                
                if file.isDirectory:
                    self.file_list.insert("", "end", text=filename,
                                        values=(f"📁 {filename}", "", "文件夹", mod_time),
                                        tags=("dir",))
                else:
                    size = self.format_size(file.file_size)
                    ext = os.path.splitext(filename)[1].upper()[1:] if "." in filename else ""
                    self.file_list.insert("", "end", text=filename,
                                        values=(f"📄 {filename}", size, ext or "文件", mod_time),
                                        tags=("file",))
            
            self.file_list.tag_configure("dir", foreground="#0078d4")
            self.file_list.tag_configure("file", foreground="black")
            
            if self.sorted_column:
                self.sort_file_list(self.sorted_column)
            
            self.item_count_var.set(f"{file_count} 个项目")
            self.update_status(f"{self.current_share}:{self.current_path}")
            
        except NotConnectedError:
            self.log_message(f"连接已断开，无法访问目录: {self.current_path}")
            self.update_connection_status(False)
            self.update_status("连接已断开")
        except OperationFailure as e:
            self.log_message(f"操作失败: {self.current_path} - {str(e)}")
            self.update_status("操作失败")
        except Exception as e:
            self.log_message(f"目录访问失败: {self.current_path} - {str(e)}")
            self.update_status("目录访问失败")

    def format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024 * 1024):.1f} MB"
        else:
            return f"{size/(1024 * 1024 * 1024):.1f} GB"

    def sort_file_list(self, col: str):
        if self.sorted_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sorted_column = col
            self.sort_reverse = False
        
        items = [(self.file_list.set(child, col), child)
                 for child in self.file_list.get_children('')]
        
        if col == "Size":
            items.sort(key=lambda x: self.parse_size(x[0]), reverse=self.sort_reverse)
        elif col == "Modified":
            items.sort(key=lambda x: self.parse_date(x[0]), reverse=self.sort_reverse)
        elif col == "Type":
            items.sort(key=lambda x: (0 if self.file_list.item(x[1], "tags")[0] == "dir" else 1, x[0]),
                      reverse=self.sort_reverse)
        else:
            items.sort(key=lambda x: (
                0 if self.file_list.item(x[1], "tags")[0] == "dir" else 1,
                [int(s) if s.isdigit() else s.lower()
                for s in re.split(r'(\d+)', x[0])]
                ), reverse=self.sort_reverse)
        
        for index, (val, item) in enumerate(items):
            self.file_list.move(item, '', index)
        
        self.update_sort_indicator()

    def update_sort_indicator(self):
        for col in self.file_list["columns"]:
            text = self.file_list.heading(col)["text"]
            text = text.replace(" ↑", "").replace(" ↓", "")
            
            if col == self.sorted_column:
                arrow = " ↓" if self.sort_reverse else " ↑"
                self.file_list.heading(col, text=text + arrow)
            else:
                self.file_list.heading(col, text=text)

    def parse_size(self, size_str: str) -> int:
        if not size_str:
            return 0
        
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    num = float(size_str.replace(unit, "").strip())
                    return int(num * multiplier)
                except:
                    return 0
        return 0

    def parse_date(self, date_str: str) -> float:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M",
            "%d-%b-%y %H:%M"
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).timestamp()
            except:
                continue
        return 0

    def go_up(self):
        if self.current_path == "/":
            return
        
        parent_path = os.path.dirname(self.current_path.rstrip("/"))
        if not parent_path:
            parent_path = "/"
        
        self.current_path = parent_path
        self.select_in_directory_tree(parent_path)
        self.load_file_list()
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, f"{self.current_share}:{self.current_path}")
        self.update_back_button_state()
    
    def update_back_button_state(self):
        if self.current_path == "/":
            self.btn_back.state(["disabled"])
        else:
            self.btn_back.state(["!disabled"])

    def on_file_double_click(self, event):
        item = self.file_list.identify_row(event.y) if event else self.file_list.selection()
        if not item:
            return
        
        if isinstance(item, tuple):
            if not item:
                return
            item = item[0]
        
        item_data = self.file_list.item(item)
        values = item_data["values"]
        
        if len(values) > 2 and values[2] in ["文件夹", "目录"]:
            dir_name = item_data["text"].strip()
            if dir_name.startswith("📁 "):
                dir_name = dir_name[2:]
            
            new_path = os.path.join(self.current_path, dir_name).replace("\\", "/")
            
            if new_path.startswith("//"):
                new_path = new_path[2:]
            if not new_path.startswith("/"):
                new_path = "/" + new_path
            
            self.current_path = new_path
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, f"{self.current_share}:{self.current_path}")
            self.log_message(f"进入目录: {new_path}")
            
            self.load_file_list()
            self.select_in_directory_tree(new_path)
            self.update_back_button_state()

    def show_tree_context_menu(self, event):
        item = self.tree_dir.identify_row(event.y)
        if not item:
            return
        
        menu = Menu(self, tearoff=0)
        menu.add_command(label="刷新", command=self.refresh_tree_node)
        menu.add_separator()
        menu.add_command(label="属性", command=lambda: self.show_properties(item, is_dir=True))
        
        menu.post(event.x_root, event.y_root)

    def show_file_context_menu(self, event):
        item = self.file_list.identify_row(event.y)
        if not item:
            return
        
        item_tags = self.file_list.item(item, "tags")
        is_dir = "dir" in item_tags
        
        selected_items = self.file_list.selection()
        if item not in selected_items:
            self.file_list.selection_set(item)
            selected_items = [item]
        
        menu = Menu(self, tearoff=0)
        
        if len(selected_items) > 1:
            menu.add_command(label=f"下载所选({len(selected_items)}项)",
                            command=self.download_selected_files)
            menu.add_command(label=f"删除所选({len(selected_items)}项)",
                            command=self.delete_selected_items)
        else:
            if is_dir:
                menu.add_command(label="打开", command=lambda: self.on_file_double_click(event))
            menu.add_command(label="下载", command=self.download_selected_files)
            menu.add_command(label="删除", command=self.delete_selected_items)
        
        menu.add_separator()
        menu.add_command(label="刷新", command=self.refresh_files)
        
        menu.post(event.x_root, event.y_root)

    def refresh_tree_node(self):
        selected = self.tree_dir.selection()
        if selected:
            node_id = selected[0]
            if node_id in self.tree_nodes:
                self.populate_tree_node(node_id, self.tree_nodes[node_id])

    def refresh_files(self):
        selected = self.tree_dir.selection()
        if selected:
            node_id = selected[0]
            if node_id in self.tree_nodes:
                self.populate_tree_node(node_id, self.tree_nodes[node_id])
                self.load_file_list()
                self.log_message("目录已刷新")
                self.update_status("已刷新")

    def create_folder(self):
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        folder_name = simpledialog.askstring("新建文件夹", "输入文件夹名称:")
        if not folder_name:
            return
        
        if any(char in folder_name for char in '\\/:*?"<>|'):
            messagebox.showerror("错误", "文件夹名称包含非法字符: \\ / : * ? \" < > |")
            return
        
        new_path = os.path.join(self.current_path, folder_name).replace("\\", "/")
        
        try:
            self.conn.createDirectory(self.current_share, new_path)
            self.log_message(f"文件夹已创建: {new_path}")
            self.refresh_files()
        except Exception as e:
            self.log_message(f"创建失败: {str(e)}")
            messagebox.showerror("错误", f"目录创建失败: {str(e)}")

    def upload_file(self, local_path=None):
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        if not local_path:
            local_paths = filedialog.askopenfilenames(title="选择要上传的文件")
            if not local_paths:
                return
        else:
            local_paths = [local_path]
        
        total_files = len(local_paths)
        
        def upload_thread():
            success_count = 0
            for i, file_path in enumerate(local_paths):
                filename = os.path.basename(file_path)
                remote_path = os.path.join(self.current_path, filename)
                clean_remote_path = self.normalize_path(remote_path)
                
                progress = int((i + 1) * 100 / total_files)
                self.after(0, lambda p=progress, f=filename, t=i+1, tt=total_files: 
                          self.update_status(f"上传: {f} ({t}/{tt})"))
                
                try:
                    with open(file_path, "rb") as f:
                        self.conn.storeFile(self.current_share, clean_remote_path, f)
                    success_count += 1
                    self.after(0, lambda f=filename: self.log_message(f"上传成功: {f}"))
                except Exception as e:
                    self.after(0, lambda f=filename, e=str(e): self.log_message(f"上传失败[{f}]: {e}"))
            
            self.after(0, lambda: self.update_status("上传完成"))
            self.after(0, lambda: self.log_message(f"文件上传完成: {success_count}/{total_files} 个文件成功"))
            self.after(0, lambda: messagebox.showinfo("完成", f"成功上传 {success_count} 个文件"))
            self.after(0, self.refresh_files)
        
        threading.Thread(target=upload_thread, daemon=True).start()

    def upload_directory(self, local_dir_path=None):
        if not self.conn or not self.current_share:
            messagebox.showerror("错误", "请先连接到SMB服务器")
            return
        
        if not local_dir_path:
            local_dir_path = filedialog.askdirectory(title="选择要上传的目录")
        if not local_dir_path:
            return
        
        dir_name = os.path.basename(local_dir_path)
        remote_base_path = os.path.join(self.current_path, dir_name).replace("\\", "/")
        
        remote_exists = False
        try:
            self.conn.listPath(self.current_share, remote_base_path)
            remote_exists = True
            self.log_message(f"检测到目标目录已存在: {remote_base_path}")
        except Exception as e:
            self.log_message(f"检查目录存在性时出错: {str(e)}")
        
        if remote_exists:
            if not messagebox.askyesno("覆盖确认",
                                    f"目标目录 '{remote_base_path}' 已存在。是否覆盖？\n"
                                    "(覆盖将删除目标目录及其所有内容)"):
                self.log_message("用户取消上传：目标目录已存在且用户选择不覆盖")
                return
        
        def upload_thread():
            try:
                total_files = sum(len(files) for _, _, files in os.walk(local_dir_path))
                self.after(0, lambda: self.update_status(f"扫描完成, 共 {total_files} 个文件"))

                count, success_count, error_list = self._upload_directory_recursive(
                    local_dir_path, remote_base_path, total_files
                    )
                
                self.after(0, lambda: self.update_status("上传完成"))
                self.after(0, lambda: self.log_message(f"目录上传完成: {success_count}/{total_files} 个文件成功"))
                if error_list:
                    error_msg = "\n".join(error_list[:5])
                    if len(error_list) > 5:
                        error_msg += f"\n...等共 {len(error_list)} 个错误"
                    self.after(0, lambda: self.log_message(f"上传错误:\n{error_msg}"))
                
                self.after(0, lambda: messagebox.showinfo("完成",
                    f"目录上传完成!\n成功上传 {success_count}/{total_files} 个文件到:\n{remote_base_path}"))
                self.after(0, self.refresh_files)
            except Exception as e:
                self.after(0, lambda: self.log_message(f"目录上传失败: {str(e)}"))
                self.after(0, lambda: self.update_status(f"上传失败: {str(e)}"))
                self.after(0, lambda: messagebox.showerror("错误", f"上传失败: {str(e)}"))
        
        threading.Thread(target=upload_thread, daemon=True).start()
        self.log_message(f"开始上传目录: {local_dir_path} -> {remote_base_path}")

    def _upload_directory_recursive(self, local_path: str, smb_base_path: str, total_files: int, 
                                    count: int = 0, success_count: int = 0, error_list: List = None):
        if error_list is None:
            error_list = []
        
        for entry in os.listdir(local_path):
            local_entry_path = os.path.join(local_path, entry)
            remote_entry_path = os.path.join(smb_base_path, entry).replace("\\", "/")
            
            if os.path.isdir(local_entry_path):
                try:
                    self.conn.createDirectory(self.current_share, remote_entry_path)
                except OperationFailure as e:
                    if "STATUS_OBJECT_NAME_COLLISION" not in str(e):
                        error_list.append(f"目录创建失败: {remote_entry_path} - {str(e)}")
                
                count, success_count, error_list = self._upload_directory_recursive(
                    local_entry_path, remote_entry_path, total_files, count, success_count, error_list
                    )
            
            else:
                count += 1
                progress = min(100, int(count * 100 / total_files)) if total_files > 0 else 0
                self.after(0, lambda p=progress, e=entry, c=count, tt=total_files: 
                          self.update_status(f"上传: {e} ({c}/{tt})"))
                
                try:
                    with open(local_entry_path, "rb") as f:
                        self.conn.storeFile(self.current_share, remote_entry_path, f)
                    success_count += 1
                except Exception as e:
                    error_list.append(f"文件上传失败 [{entry}]: {str(e)}")
        
        return count, success_count, error_list

    def download_selected_files(self):
        selected_items = self.file_list.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要下载的文件")
            return
        
        save_dir = filedialog.askdirectory(title="选择保存位置")
        if not save_dir:
            return
        
        file_list = []
        for item_id in selected_items:
            item = self.file_list.item(item_id)
            filename = item["text"].strip()
            if filename.startswith("📁 ") or filename.startswith("📄 "):
                filename = filename[2:]
            
            if item["values"][2] in ["文件夹", "目录"]:
                continue
            
            remote_path = os.path.join(self.current_path, filename)
            clean_remote_path = self.normalize_path(remote_path)
            local_path = os.path.join(save_dir, filename)
            file_list.append((filename, clean_remote_path, local_path))
        
        if not file_list:
            return
        
        def download_thread():
            success_count = 0
            total_files = len(file_list)
            for i, (filename, remote_path, local_path) in enumerate(file_list):
                self.after(0, lambda f=filename, c=i+1, t=total_files: 
                          self.update_status(f"下载: {f} ({c}/{t})"))
                try:
                    with open(local_path, "wb") as f:
                        self.conn.retrieveFile(self.current_share, remote_path, f)
                    self.after(0, lambda f=filename: self.log_message(f"下载成功: {f}"))
                    success_count += 1
                except Exception as e:
                    self.after(0, lambda f=filename, e=str(e): self.log_message(f"下载失败[{f}]: {e}"))
            
            self.after(0, lambda: self.update_status("下载完成"))
            self.after(0, lambda: self.log_message(f"下载完成: {success_count}/{len(file_list)}"))
            self.after(0, lambda: messagebox.showinfo("下载完成",
                              f"成功下载 {success_count} 个文件到:\n{save_dir}"))
        
        threading.Thread(target=download_thread, daemon=True).start()
        self.log_message(f"开始后台下载 {len(file_list)} 个文件...")

    def delete_selected_items(self):
        selected_items = self.file_list.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的文件或目录")
            return
        
        items_to_delete = []
        for item_id in selected_items:
            item = self.file_list.item(item_id)
            item_name = item["text"].strip()
            if item_name.startswith("📁 ") or item_name.startswith("📄 "):
                item_name = item_name[2:]
            
            is_dir = item["values"][2] in ["文件夹", "目录"]
            full_path = os.path.join(self.current_path, item_name).replace("\\", "/")
            items_to_delete.append((item_name, full_path, is_dir, item_id))
        
        if not items_to_delete:
            messagebox.showwarning("警告", "没有有效的项目可删除")
            return
        
        file_count = sum(1 for item in items_to_delete if not item[2])
        dir_count = len(items_to_delete) - file_count
        
        non_empty_dirs = []
        for item in items_to_delete:
            if item[2]:
                try:
                    contents = self.conn.listPath(self.current_share, item[1])
                    if len([f for f in contents if f.filename not in ('.', '..')]) > 0:
                        non_empty_dirs.append(item[0])
                except:
                    non_empty_dirs.append(item[0])
        
        if file_count and dir_count:
            confirm_msg = f"确定要删除选中的 {file_count} 个文件和 {dir_count} 个目录吗？"
        elif file_count:
            confirm_msg = f"确定要删除选中的 {file_count} 个文件吗？"
        else:
            confirm_msg = f"确定要删除选中的 {dir_count} 个目录吗？"
        
        if non_empty_dirs:
            confirm_msg += f"\n\n警告: 以下目录非空: {', '.join(non_empty_dirs)}\n删除非空目录将同时删除其所有内容！"
        
        if not messagebox.askyesno("确认删除", confirm_msg):
            return
        
        success_count = 0
        failed_items = []
        
        def delete_thread():
            nonlocal success_count
            for item_name, full_path, is_dir, item_id in items_to_delete:
                try:
                    if is_dir:
                        self._delete_directory_recursive(full_path)
                    else:
                        self.conn.deleteFiles(self.current_share, full_path)
                    success_count += 1
                    self.after(0, lambda p=full_path: self.log_message(f"已删除: {p}"))
                except Exception as e:
                    failed_items.append((item_name, str(e)))
                    self.after(0, lambda n=item_name, e=str(e): self.log_message(f"删除失败[{n}]: {e}"))
            
            result_msg = f"成功删除 {success_count}/{len(items_to_delete)} 个项目"
            if failed_items:
                result_msg += "\n\n以下项目删除失败:\n"
                result_msg += "\n".join(f"{name}: {error}" for name, error in failed_items)
            
            self.after(0, lambda: messagebox.showinfo("删除结果", result_msg))
            self.after(0, self.refresh_files)
            self.after(0, lambda: self.update_status("删除完成"))
        
        threading.Thread(target=delete_thread, daemon=True).start()
        self.log_message(f"开始后台删除 {len(items_to_delete)} 个项目...")

    def _delete_directory_recursive(self, path: str):
        try:
            contents = self.conn.listPath(self.current_share, path)
            for file in contents:
                if file.filename in ['.', '..']:
                    continue
                
                item_path = os.path.join(path, file.filename).replace("\\", "/")
                if file.isDirectory:
                    self._delete_directory_recursive(item_path)
                else:
                    self.conn.deleteFiles(self.current_share, item_path)
            
            self.conn.deleteDirectory(self.current_share, path)
        except Exception as e:
            self.log_message(f"删除目录失败: {path} - {str(e)}")
            raise

    def show_properties(self, item_id: str, is_dir: bool):
        try:
            if is_dir:
                dir_name = self.tree_dir.item(item_id, "text").replace("📁 ", "").replace("🖥️ ", "")
                full_path = self.tree_nodes.get(item_id, "")
                properties = f"名称: {dir_name}\n类型: 文件夹\n位置: {full_path}"
                
                try:
                    file_count = len(self.conn.listPath(self.current_share, full_path)) - 2
                    properties += f"\n包含项目: {file_count}"
                except:
                    pass
            else:
                file_name = self.file_list.item(item_id, "text").replace("📄 ", "").replace("📁 ", "")
                full_path = os.path.join(self.current_path, file_name).replace("\\", "/")
                properties = f"名称: {file_name}\n类型: 文件\n位置: {full_path}"
                
                file_attr = self.conn.getAttributes(self.current_share, full_path)
                
                size = self.format_size(file_attr.file_size)
                modified = datetime.datetime.fromtimestamp(file_attr.last_write_time)
                
                properties += f"\n大小: {size}\n修改时间: {modified}"
            
            messagebox.showinfo("属性", properties)
        except Exception as e:
            self.log_message(f"获取属性失败: {str(e)}")
            messagebox.showerror("错误", f"无法获取属性: {str(e)}")

    def show_about(self):
        about_text = """SMB文件管理器 v2.0

一个功能完善的SMB协议文件管理器，
仿照Windows资源管理器风格设计。

功能特性:
• 服务器连接管理
• 双栏文件浏览
• 文件上传/下载
• 目录操作
• 批量操作
• 操作日志
"""
        messagebox.showinfo("关于", about_text)

    def normalize_path(self, path: str) -> str:
        return path.replace("\\", "/").rstrip("/")

    def set_view_mode(self, mode: str):
        pass

    def process_tasks(self):
        try:
            while True:
                task = self.task_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(100, self.process_tasks)

    def load_servers(self) -> Dict:
        try:
            if os.path.exists("smb_config.json"):
                with open("smb_config.json", "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
        return {}

    def on_close(self):
        if self.conn:
            try:
                self.conn.close()
                self.log_message("连接已关闭")
            except:
                pass
        self.destroy()


if __name__ == "__main__":
    app = SMBClientBrowser()
    app.mainloop()
