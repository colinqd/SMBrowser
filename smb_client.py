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
import base64
from io import BytesIO
from typing import Optional, Dict, List, Tuple, Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD, COPY, ASK
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False
    COPY = None
    ASK = None


class SMBClientBrowser(TkinterDnD.Tk if DND_SUPPORT else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMB文件管理器")
        self.geometry("1400x800")
        self.minsize(1000, 600)
        
        self.conn: Optional[SMBConnection] = None
        self.current_share: str = ""
        self.remote_path: str = "/"
        self.local_path: str = os.path.expanduser("~")
        self.current_server_ip: str = ""
        self.servers: Dict = self.load_servers()
        self.remote_tree_nodes: Dict[str, str] = {}
        self.local_tree_nodes: Dict[str, str] = {}
        self.local_sorted_column: str = "Name"
        self.local_sort_reverse: bool = False
        self.remote_sorted_column: str = "Name"
        self.remote_sort_reverse: bool = False
        self.task_queue: queue.Queue = queue.Queue()
        self.is_connected: bool = False
        self.available_shares: List[str] = []
        
        self.setup_style()
        self.create_icons()
        self.create_widgets()
        self.init_local_browser()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.process_tasks()
        
        if DND_SUPPORT:
            self.setup_drag_drop()
        
        self.update_local_sort_indicator()
        self.update_remote_sort_indicator()

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
        
        style.configure("Treeview", 
                       font=('Segoe UI', 9), 
                       rowheight=24,
                       background="#ffffff",
                       foreground="#000000",
                       fieldbackground="#ffffff")
        style.configure("Treeview.Heading", 
                       font=('Segoe UI', 9, 'bold'),
                       background="#f0f0f0",
                       foreground="#000000")
        style.map("Treeview",
                  background=[('selected', '#0078d4')],
                  foreground=[('selected', '#ffffff')])
        style.configure("TLabelframe", font=('Segoe UI', 9))
        style.configure("TButton", font=('Segoe UI', 9))
        style.configure("TLabel", font=('Segoe UI', 9))
        style.configure("TEntry", font=('Segoe UI', 9))
        style.configure("TCombobox", font=('Segoe UI', 9))
        style.configure("Status.TLabel", padding=2, font=('Segoe UI', 8))
        
        self.configure(bg="#f0f0f0")

    def create_icons(self):
        from PIL import Image, ImageDraw, ImageColor
        
        def create_folder_icon(size=16):
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            folder_color = '#FFD700'
            darker_color = '#DAA520'
            
            draw.rectangle([2, 5, size-2, size-2], fill=folder_color, outline=darker_color)
            draw.rectangle([2, 3, size-6, 6], fill=darker_color, outline=darker_color)
            
            return img
        
        def create_file_icon(size=16):
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            paper_color = '#FFFFFF'
            line_color = '#808080'
            corner_color = '#E0E0E0'
            
            draw.rectangle([3, 1, size-4, size-2], fill=paper_color, outline=line_color)
            draw.polygon([size-7, 1, size-4, 1, size-4, 5, size-7, 5], fill=corner_color, outline=line_color)
            draw.line([size-7, 1, size-4, 4], fill=line_color)
            
            draw.line([6, 7, size-7, 7], fill=line_color)
            draw.line([6, 10, size-7, 10], fill=line_color)
            draw.line([6, 13, size-10, 13], fill=line_color)
            
            return img
        
        def create_drive_icon(size=16):
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            drive_color = '#A0A0A0'
            outline_color = '#606060'
            
            draw.rectangle([2, 4, size-2, size-3], fill=drive_color, outline=outline_color)
            draw.rectangle([4, 2, size-4, 5], fill=drive_color, outline=outline_color)
            draw.rectangle([6, size-5, size-8, size-3], fill='#303030')
            
            return img
        
        def create_server_icon(size=16):
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            box_color = '#4A90D9'
            outline_color = '#2E5B8A'
            
            draw.rectangle([2, 3, size-2, size-3], fill=box_color, outline=outline_color)
            draw.rectangle([4, 5, size-4, 8], fill='#FFFFFF')
            draw.rectangle([4, 10, size-4, 13], fill='#FFFFFF')
            
            return img
        
        def img_to_photo(img):
            with BytesIO() as output:
                img.save(output, format='PNG')
                data = output.getvalue()
            return tk.PhotoImage(data=base64.b64encode(data))
        
        self.icons = {
            'folder': img_to_photo(create_folder_icon(16)),
            'file': img_to_photo(create_file_icon(16)),
            'drive': img_to_photo(create_drive_icon(16)),
            'server': img_to_photo(create_server_icon(16)),
            'share': img_to_photo(create_folder_icon(16))
        }

    def create_widgets(self):
        self.create_menubar()
        self.create_toolbar()
        self.create_path_bars()
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
        view_menu.add_command(label="刷新", command=self.refresh_all, accelerator="F5")
        menubar.add_cascade(label="查看", menu=view_menu)
        
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.config(menu=menubar)
        
        self.bind("<F5>", lambda e: self.refresh_all())
        self.bind("<Control-n>", lambda e: self.show_connect_dialog())

    def create_toolbar(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=2)
        
        ttk.Button(toolbar, text="新建", command=self.create_folder).pack(side="left", padx=2)
        ttk.Button(toolbar, text="上传", command=self.upload_from_local).pack(side="left", padx=2)
        ttk.Button(toolbar, text="下载", command=self.download_to_local).pack(side="left", padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_remote_items).pack(side="left", padx=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5, pady=3)
        
        ttk.Button(toolbar, text="刷新", command=self.refresh_all).pack(side="left", padx=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5, pady=3)
        
        self.conn_status_label = ttk.Label(toolbar, text="未连接", foreground="red")
        self.conn_status_label.pack(side="right", padx=10)

    def create_path_bars(self):
        path_frame = ttk.Frame(self)
        path_frame.pack(fill="x", padx=5, pady=2)
        
        left_path_frame = ttk.Frame(path_frame)
        left_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ttk.Label(left_path_frame, text="本地:").pack(side="left")
        ttk.Button(left_path_frame, text="↑", width=4, command=self.go_local_up).pack(side="left", padx=(2, 0))
        self.local_path_entry = ttk.Entry(left_path_frame)
        self.local_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.local_path_entry.bind("<Return>", self.on_local_path_enter)
        
        right_path_frame = ttk.Frame(path_frame)
        right_path_frame.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        ttk.Label(right_path_frame, text="远程:").pack(side="left")
        ttk.Button(right_path_frame, text="↑", width=4, command=self.go_remote_up).pack(side="left", padx=(2, 0))
        self.remote_path_entry = ttk.Entry(right_path_frame)
        self.remote_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.remote_path_entry.bind("<Return>", self.on_remote_path_enter)
        
        self.btn_connect = ttk.Button(right_path_frame, text="连接服务器", command=self.show_connect_dialog)
        self.btn_connect.pack(side="left", padx=5)

    def create_main_panes(self):
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        left_frame = ttk.LabelFrame(main_paned, text="本地文件")
        main_paned.add(left_frame, weight=1)
        
        self.create_local_panel(left_frame)
        
        right_frame = ttk.LabelFrame(main_paned, text="远程文件 (SMB)")
        main_paned.add(right_frame, weight=1)
        
        self.create_remote_panel(right_frame)

    def create_local_panel(self, parent):
        local_paned = ttk.PanedWindow(parent, orient="horizontal")
        local_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        local_tree_frame = ttk.Frame(local_paned)
        local_paned.add(local_tree_frame, weight=1)
        
        self.local_tree = ttk.Treeview(local_tree_frame, show="tree", selectmode="browse")
        self.local_tree.pack(side="left", fill="both", expand=True)
        
        local_tree_scroll = ttk.Scrollbar(local_tree_frame, orient="vertical", command=self.local_tree.yview)
        local_tree_scroll.pack(side="right", fill="y")
        self.local_tree.configure(yscrollcommand=local_tree_scroll.set)
        
        self.local_tree.bind("<<TreeviewOpen>>", self.on_local_tree_expand)
        self.local_tree.bind("<<TreeviewSelect>>", self.on_local_tree_select)
        
        local_list_frame = ttk.Frame(local_paned)
        local_paned.add(local_list_frame, weight=2)
        
        self.local_file_list = ttk.Treeview(local_list_frame, 
                                             columns=("Name", "Size", "Type", "Modified"),
                                             show="headings", selectmode="extended")
        self.local_file_list.pack(side="left", fill="both", expand=True)
        
        local_columns = [
            {"id": "Name", "text": "名称", "width": 200, "anchor": "w"},
            {"id": "Size", "text": "大小", "width": 80, "anchor": "e"},
            {"id": "Type", "text": "类型", "width": 80, "anchor": "center"},
            {"id": "Modified", "text": "修改日期", "width": 140, "anchor": "center"}
        ]
        
        for col in local_columns:
            self.local_file_list.heading(
                col["id"], 
                text=col["text"], 
                anchor=col["anchor"],
                command=lambda c=col["id"]: self.sort_local_file_list(c)
            )
            self.local_file_list.column(col["id"], width=col["width"], anchor=col["anchor"])
        
        local_scroll_y = ttk.Scrollbar(local_list_frame, orient="vertical", command=self.local_file_list.yview)
        local_scroll_y.pack(side="right", fill="y")
        local_scroll_x = ttk.Scrollbar(local_list_frame, orient="horizontal", command=self.local_file_list.xview)
        local_scroll_x.pack(side="bottom", fill="x")
        self.local_file_list.configure(yscrollcommand=local_scroll_y.set, xscrollcommand=local_scroll_x.set)
        
        self.local_file_list.bind("<Double-1>", self.on_local_file_double_click)
        self.local_file_list.bind("<Return>", lambda e: self.on_local_file_double_click(e))
        self.local_file_list.bind("<Button-3>", self.show_local_context_menu)

    def create_remote_panel(self, parent):
        remote_paned = ttk.PanedWindow(parent, orient="horizontal")
        remote_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        remote_tree_frame = ttk.Frame(remote_paned)
        remote_paned.add(remote_tree_frame, weight=1)
        
        self.remote_tree = ttk.Treeview(remote_tree_frame, show="tree", selectmode="browse")
        self.remote_tree.pack(side="left", fill="both", expand=True)
        
        remote_tree_scroll = ttk.Scrollbar(remote_tree_frame, orient="vertical", command=self.remote_tree.yview)
        remote_tree_scroll.pack(side="right", fill="y")
        self.remote_tree.configure(yscrollcommand=remote_tree_scroll.set)
        
        self.remote_tree.bind("<<TreeviewOpen>>", self.on_remote_tree_expand)
        self.remote_tree.bind("<<TreeviewSelect>>", self.on_remote_tree_select)
        
        remote_list_frame = ttk.Frame(remote_paned)
        remote_paned.add(remote_list_frame, weight=2)
        
        self.remote_file_list = ttk.Treeview(remote_list_frame, 
                                              columns=("Name", "Size", "Type", "Modified"),
                                              show="headings", selectmode="extended")
        self.remote_file_list.pack(side="left", fill="both", expand=True)
        
        remote_columns = [
            {"id": "Name", "text": "名称", "width": 200, "anchor": "w"},
            {"id": "Size", "text": "大小", "width": 80, "anchor": "e"},
            {"id": "Type", "text": "类型", "width": 80, "anchor": "center"},
            {"id": "Modified", "text": "修改日期", "width": 140, "anchor": "center"}
        ]
        
        for col in remote_columns:
            self.remote_file_list.heading(
                col["id"], 
                text=col["text"], 
                anchor=col["anchor"],
                command=lambda c=col["id"]: self.sort_remote_file_list(c)
            )
            self.remote_file_list.column(col["id"], width=col["width"], anchor=col["anchor"])
        
        remote_scroll_y = ttk.Scrollbar(remote_list_frame, orient="vertical", command=self.remote_file_list.yview)
        remote_scroll_y.pack(side="right", fill="y")
        remote_scroll_x = ttk.Scrollbar(remote_list_frame, orient="horizontal", command=self.remote_file_list.xview)
        remote_scroll_x.pack(side="bottom", fill="x")
        self.remote_file_list.configure(yscrollcommand=remote_scroll_y.set, xscrollcommand=remote_scroll_x.set)
        
        self.remote_file_list.bind("<Double-1>", self.on_remote_file_double_click)
        self.remote_file_list.bind("<Return>", lambda e: self.on_remote_file_double_click(e))
        self.remote_file_list.bind("<Delete>", lambda e: self.delete_remote_items())
        self.remote_file_list.bind("<Button-3>", self.show_remote_context_menu)

    def setup_drag_drop(self):
        if not DND_SUPPORT:
            return
        
        self._local_dragging = False
        self._remote_dragging = False
        
        self.remote_file_list.drop_target_register(DND_FILES)
        self.remote_file_list.dnd_bind('<<Drop>>', self.on_drop_to_remote)
        self.remote_file_list.dnd_bind('<<DropEnter>>', self.on_drop_enter)
        self.remote_file_list.dnd_bind('<<DropPosition>>', self.on_drop_position)
        self.remote_file_list.dnd_bind('<<DropLeave>>', self.on_drop_leave)
        
        self.local_file_list.drop_target_register(DND_FILES)
        self.local_file_list.dnd_bind('<<Drop>>', self.on_drop_to_local)
        self.local_file_list.dnd_bind('<<DropEnter>>', self.on_drop_enter)
        self.local_file_list.dnd_bind('<<DropPosition>>', self.on_drop_position)
        self.local_file_list.dnd_bind('<<DropLeave>>', self.on_drop_leave)
        
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_external_drop)
        
        self.local_file_list.drag_source_register(1, DND_FILES)
        self.local_file_list.dnd_bind('<<DragInitCmd>>', self.on_local_drag_init)
        self.local_file_list.dnd_bind('<<DragEndCmd>>', self.on_local_drag_end)
        
        self.remote_file_list.drag_source_register(1, DND_FILES)
        self.remote_file_list.dnd_bind('<<DragInitCmd>>', self.on_remote_drag_init)
        self.remote_file_list.dnd_bind('<<DragEndCmd>>', self.on_remote_drag_end)

    def create_status_bar(self):
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", side="bottom")
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                      relief="sunken", anchor="w", style="Status.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True, padx=2)
        
        self.local_count_var = tk.StringVar(value="本地: 0 个项目")
        ttk.Label(status_frame, textvariable=self.local_count_var, 
                 relief="sunken", anchor="e").pack(side="left", padx=5)
        
        self.remote_count_var = tk.StringVar(value="远程: 0 个项目")
        ttk.Label(status_frame, textvariable=self.remote_count_var, 
                 relief="sunken", anchor="e").pack(side="right", padx=2)

    def create_log_area(self):
        self.log_toggle = ttk.Button(self, text="▼ 显示日志", command=self.toggle_log)
        self.log_toggle.pack(fill="x", padx=5, pady=(0, 5))
        
        self.log_frame = ttk.LabelFrame(self, text="操作日志")
        self.log_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.log_frame.pack_forget()
        
        self.log_area = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_visible = False

    def toggle_log(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_toggle.config(text="▲ 隐藏日志")
            self.log_frame.pack(after=self.log_toggle, fill="both", expand=True, padx=5, pady=(0, 5))
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
            self.conn_status_label.config(text="已连接", foreground="green")
            self.btn_connect.config(text="断开连接", command=self.disconnect)
        else:
            self.conn_status_label.config(text="未连接", foreground="red")
            self.btn_connect.config(text="连接服务器", command=self.show_connect_dialog)

    def init_local_browser(self):
        for item in self.local_tree.get_children():
            self.local_tree.delete(item)
        
        drives = self.get_local_drives()
        for drive in drives:
            node_id = self.local_tree.insert("", "end", text=f" {drive}", image=self.icons['drive'], open=False)
            self.local_tree_nodes[node_id] = drive
            self.local_tree.insert(node_id, "end", text="Loading...")
        
        self.load_local_files(self.local_path)

    def get_local_drives(self):
        drives = []
        if sys.platform == 'win32':
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive = chr(65 + i) + ":\\"
                    drives.append(drive)
        else:
            drives = ["/"]
        return drives

    def populate_local_tree_node(self, parent_id: str, path: str):
        try:
            for child in self.local_tree.get_children(parent_id):
                self.local_tree.delete(child)
            
            if os.path.exists(path):
                dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                for d in dirs:
                    full_path = os.path.join(path, d)
                    node_id = self.local_tree.insert(parent_id, "end", text=f" {d}", image=self.icons['folder'], tags=("dir",))
                    self.local_tree_nodes[node_id] = full_path
                    
                    try:
                        os.listdir(full_path)
                        self.local_tree.insert(node_id, "end", text="Loading...")
                    except:
                        pass
        except Exception as e:
            self.log_message(f"本地目录访问失败: {path} - {str(e)}")

    def on_local_tree_expand(self, event):
        node_id = self.local_tree.focus()
        if node_id and node_id in self.local_tree_nodes:
            self.populate_local_tree_node(node_id, self.local_tree_nodes[node_id])

    def on_local_tree_select(self, event):
        selected = self.local_tree.selection()
        if not selected:
            return
        
        node_id = selected[0]
        if node_id in self.local_tree_nodes:
            self.local_path = self.local_tree_nodes[node_id]
            self.local_path_entry.delete(0, "end")
            self.local_path_entry.insert(0, self.local_path)
            self.load_local_files(self.local_path)

    def load_local_files(self, path: str):
        for item in self.local_file_list.get_children():
            self.local_file_list.delete(item)
        
        file_count = 0
        try:
            if os.path.exists(path):
                items = os.listdir(path)
                
                for item in items:
                    item_path = os.path.join(path, item)
                    
                    try:
                        if os.path.isdir(item_path):
                            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M")
                            self.local_file_list.insert("", "end", text=item,
                                                         values=(item, "", "文件夹", mod_time),
                                                         tags=("dir",),
                                                         image=self.icons['folder'])
                            file_count += 1
                    except:
                        pass
                
                for item in items:
                    item_path = os.path.join(path, item)
                    
                    try:
                        if os.path.isfile(item_path):
                            size = self.format_size(os.path.getsize(item_path))
                            ext = os.path.splitext(item)[1].upper()[1:] if "." in item else ""
                            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M")
                            self.local_file_list.insert("", "end", text=item,
                                                         values=(item, size, ext or "文件", mod_time),
                                                         tags=("file",),
                                                         image=self.icons['file'])
                            file_count += 1
                    except:
                        pass
                
                self.local_file_list.tag_configure("dir", foreground="#0078d4")
                self.local_file_list.tag_configure("file", foreground="black")
                
                if self.local_sorted_column:
                    self.sort_local_file_list(self.local_sorted_column)
            
            self.local_count_var.set(f"本地: {file_count} 个项目")
        except Exception as e:
            self.log_message(f"加载本地文件失败: {path} - {str(e)}")
            self.local_count_var.set(f"本地: 0 个项目")

    def on_local_file_double_click(self, event):
        item = self.local_file_list.identify_row(event.y) if event else self.local_file_list.selection()
        if not item:
            return
        
        if isinstance(item, tuple):
            if not item:
                return
            item = item[0]
        
        item_data = self.local_file_list.item(item)
        tags = item_data.get("tags", [])
        
        if "dir" in tags:
            dir_name = item_data["text"].strip()
            new_path = os.path.join(self.local_path, dir_name)
            
            self.local_path = new_path
            self.local_path_entry.delete(0, "end")
            self.local_path_entry.insert(0, self.local_path)
            self.expand_local_tree_to_path(new_path)
            self.load_local_files(new_path)

    def expand_local_tree_to_path(self, target_path: str):
        for node_id, node_path in self.local_tree_nodes.items():
            if node_path == target_path:
                self.local_tree.selection_set(node_id)
                self.local_tree.focus(node_id)
                self.local_tree.see(node_id)
                
                parent = self.local_tree.parent(node_id)
                while parent:
                    self.local_tree.item(parent, open=True)
                    parent = self.local_tree.parent(parent)
                return

    def go_local_up(self):
        parent_path = os.path.dirname(self.local_path)
        if parent_path and os.path.exists(parent_path) and parent_path != self.local_path:
            self.local_path = parent_path
            self.local_path_entry.delete(0, "end")
            self.local_path_entry.insert(0, self.local_path)
            self.expand_local_tree_to_path(self.local_path)
            self.load_local_files(self.local_path)

    def go_remote_up(self):
        if not self.remote_path or self.remote_path == "/":
            return
        parent_path = os.path.dirname(self.remote_path)
        if parent_path == "":
            parent_path = "/"
        self.remote_path = parent_path
        self.remote_path_entry.delete(0, "end")
        self.remote_path_entry.insert(0, f"{self.current_share}:{self.remote_path}")
        self.expand_remote_tree_to_path(self.remote_path)
        self.load_remote_files()

    def on_local_path_enter(self, event):
        path = self.local_path_entry.get()
        if os.path.exists(path) and os.path.isdir(path):
            self.local_path = path
            self.expand_local_tree_to_path(path)
            self.load_local_files(path)

    def init_remote_browser(self):
        for item in self.remote_tree.get_children():
            self.remote_tree.delete(item)
        self.remote_tree_nodes.clear()
        
        root_id = self.remote_tree.insert("", "end", text=f" {self.current_server_ip}", image=self.icons['server'], open=True)
        self.remote_tree_nodes[root_id] = "//SERVER_ROOT//"
        
        for share in self.available_shares:
            node_id = self.remote_tree.insert(root_id, "end", text=f" {share}", image=self.icons['share'], tags=("share",))
            self.remote_tree_nodes[node_id] = f"//SHARE//{share}"

    def init_remote_directory_tree(self):
        for item in self.remote_tree.get_children():
            self.remote_tree.delete(item)
        self.remote_tree_nodes.clear()
        
        root_id = self.remote_tree.insert("", "end", text=f" {self.current_share}", image=self.icons['share'], open=True)
        self.remote_tree_nodes[root_id] = "/"
        
        self.populate_remote_tree_node(root_id, "/")
        
        self.remote_tree.selection_set(root_id)
        self.remote_tree.focus(root_id)
        self.on_remote_tree_select(None)

    def populate_remote_tree_node(self, parent_id: str, path: str):
        if not self.conn or not self.current_share:
            return
        
        try:
            for child in self.remote_tree.get_children(parent_id):
                self.remote_tree.delete(child)
            
            dirs = [f for f in self.conn.listPath(self.current_share, path)
                    if f.isDirectory and f.filename not in (".", "..")]
            
            for d in dirs:
                full_path = os.path.join(path, d.filename).replace("\\", "/")
                
                if full_path.startswith("//"):
                    full_path = full_path[2:]
                if not full_path.startswith("/"):
                    full_path = "/" + full_path
                
                node_id = self.remote_tree.insert(parent_id, "end", text=f" {d.filename}", image=self.icons['folder'], tags=("dir",))
                self.remote_tree_nodes[node_id] = full_path
                
                self.remote_tree.insert(node_id, "end", text="Loading...")
        except NotConnectedError:
            self.log_message(f"连接已断开，无法访问目录: {path}")
            self.update_connection_status(False)
        except Exception as e:
            self.log_message(f"远程目录访问失败: {path} - {str(e)}")

    def on_remote_tree_expand(self, event):
        node_id = self.remote_tree.focus()
        if node_id and self.remote_tree.tag_has("dir", node_id):
            self.populate_remote_tree_node(node_id, self.remote_tree_nodes[node_id])

    def on_remote_tree_select(self, event):
        selected = self.remote_tree.selection()
        if not selected:
            return
        
        node_id = selected[0]
        node_path = self.remote_tree_nodes.get(node_id, "")
        
        if node_path.startswith("//SHARE//"):
            self.current_share = self.remote_tree.item(node_id, "text").strip()
            self.remote_path = "/"
            self.log_message(f"已选择共享: {self.current_share}")
            self.init_remote_directory_tree()
            return
        
        if node_path and not node_path.startswith("//"):
            self.remote_path = node_path
            self.remote_path_entry.delete(0, "end")
            self.remote_path_entry.insert(0, f"{self.current_share}:{self.remote_path}")
            self.load_remote_files()

    def load_remote_files(self):
        for item in self.remote_file_list.get_children():
            self.remote_file_list.delete(item)
        
        if not self.conn or not self.current_share:
            self.remote_count_var.set("远程: 0 个项目")
            return
        
        try:
            files = self.conn.listPath(self.current_share, self.remote_path)
            file_count = 0
            
            for file in files:
                if file.filename in [".", ".."]:
                    continue
                
                file_count += 1
                filename = file.filename
                
                try:
                    mod_time = datetime.datetime.fromtimestamp(file.last_write_time).strftime("%Y-%m-%d %H:%M")
                except:
                    mod_time = "未知"
                
                if file.isDirectory:
                    self.remote_file_list.insert("", "end", text=filename,
                                                  values=(filename, "", "文件夹", mod_time),
                                                  tags=("dir",),
                                                  image=self.icons['folder'])
                else:
                    size = self.format_size(file.file_size)
                    ext = os.path.splitext(filename)[1].upper()[1:] if "." in filename else ""
                    self.remote_file_list.insert("", "end", text=filename,
                                                  values=(filename, size, ext or "文件", mod_time),
                                                  tags=("file",),
                                                  image=self.icons['file'])
            
            self.remote_file_list.tag_configure("dir", foreground="#0078d4")
            self.remote_file_list.tag_configure("file", foreground="black")
            
            if self.remote_sorted_column:
                self.sort_remote_file_list(self.remote_sorted_column)
            
            self.remote_count_var.set(f"远程: {file_count} 个项目")
            self.update_status(f"{self.current_share}:{self.remote_path}")
            
        except NotConnectedError:
            self.log_message(f"连接已断开，无法访问目录: {self.remote_path}")
            self.update_connection_status(False)
            self.remote_count_var.set("远程: 0 个项目")
        except Exception as e:
            self.log_message(f"目录访问失败: {self.remote_path} - {str(e)}")
            self.remote_count_var.set("远程: 0 个项目")

    def on_remote_file_double_click(self, event):
        item = self.remote_file_list.identify_row(event.y) if event else self.remote_file_list.selection()
        if not item:
            return
        
        if isinstance(item, tuple):
            if not item:
                return
            item = item[0]
        
        item_data = self.remote_file_list.item(item)
        tags = item_data.get("tags", [])
        
        if "dir" in tags:
            dir_name = item_data["text"].strip()
            new_path = os.path.join(self.remote_path, dir_name).replace("\\", "/")
            
            if new_path.startswith("//"):
                new_path = new_path[2:]
            if not new_path.startswith("/"):
                new_path = "/" + new_path
            
            self.remote_path = new_path
            self.remote_path_entry.delete(0, "end")
            self.remote_path_entry.insert(0, f"{self.current_share}:{self.remote_path}")
            self.log_message(f"进入目录: {new_path}")
            
            self.load_remote_files()
            self.expand_remote_tree_to_path(new_path)

    def expand_remote_tree_to_path(self, target_path: str):
        for node_id, node_path in self.remote_tree_nodes.items():
            if node_path == target_path:
                self.remote_tree.selection_set(node_id)
                self.remote_tree.focus(node_id)
                self.remote_tree.see(node_id)
                
                parent = self.remote_tree.parent(node_id)
                while parent:
                    self.remote_tree.item(parent, open=True)
                    if parent in self.remote_tree_nodes:
                        self.populate_remote_tree_node(parent, self.remote_tree_nodes[parent])
                    parent = self.remote_tree.parent(parent)
                return

    def show_local_context_menu(self, event):
        menu = Menu(self, tearoff=0)
        selected_items = self.local_file_list.selection()
        
        if selected_items:
            menu.add_command(label="上传到远程", command=self.upload_from_local)
            menu.add_separator()
            menu.add_command(label="删除", command=self.delete_local_items)
            menu.add_separator()
        menu.add_command(label="刷新", command=lambda: self.load_local_files(self.local_path))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def show_remote_context_menu(self, event):
        menu = Menu(self, tearoff=0)
        selected_items = self.remote_file_list.selection()
        
        if selected_items:
            menu.add_command(label="下载到本地", command=self.download_to_local)
            menu.add_separator()
            menu.add_command(label="删除", command=self.delete_remote_items)
            menu.add_separator()
        menu.add_command(label="刷新", command=self.load_remote_files)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def on_drop_enter(self, event):
        event.widget.focus_force()
        return event.action

    def on_drop_position(self, event):
        return event.action

    def on_drop_leave(self, event):
        return event.action

    def on_local_drag_init(self, event):
        if self._local_dragging:
            return 'break'
        
        selection = self.local_file_list.selection()
        if not selection:
            return 'break'
        
        data = []
        for item_id in selection:
            item = self.local_file_list.item(item_id)
            filename = item["text"].strip()
            full_path = os.path.join(self.local_path, filename)
            if os.path.exists(full_path):
                data.append(full_path)
        
        if data:
            self._local_dragging = True
            return ((ASK, COPY), (DND_FILES,), tuple(data))
        return 'break'

    def on_local_drag_end(self, event):
        self._local_dragging = False

    def on_remote_drag_init(self, event):
        if self._remote_dragging:
            return 'break'
        
        if not self.conn or not self.current_share:
            return 'break'
        
        selection = self.remote_file_list.selection()
        if not selection:
            return 'break'
        
        data = []
        for item_id in selection:
            item = self.remote_file_list.item(item_id)
            filename = item["text"].strip()
            full_path = os.path.join(self.remote_path, filename).replace("\\", "/")
            data.append(f"{self.current_share}:{full_path}")
        
        if data:
            self._remote_dragging = True
            return ((ASK, COPY), (DND_FILES,), tuple(data))
        return 'break'

    def on_remote_drag_end(self, event):
        self._remote_dragging = False

    def on_remote_path_enter(self, event):
        path_text = self.remote_path_entry.get()
        if ":" in path_text:
            share, path = path_text.split(":", 1)
            if share == self.current_share:
                self.remote_path = path
                self.expand_remote_tree_to_path(path)
                self.load_remote_files()

    def format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024 * 1024):.1f} MB"
        else:
            return f"{size/(1024 * 1024 * 1024):.1f} GB"

    def sort_local_file_list(self, col: str):
        if self.local_sorted_column == col:
            self.local_sort_reverse = not self.local_sort_reverse
        else:
            self.local_sorted_column = col
            self.local_sort_reverse = False
        
        items = [(self.local_file_list.set(child, col), child)
                 for child in self.local_file_list.get_children('')]
        
        self.sort_items(self.local_file_list, items, col, self.local_sort_reverse)
        self.update_local_sort_indicator()

    def sort_remote_file_list(self, col: str):
        if self.remote_sorted_column == col:
            self.remote_sort_reverse = not self.remote_sort_reverse
        else:
            self.remote_sorted_column = col
            self.remote_sort_reverse = False
        
        items = [(self.remote_file_list.set(child, col), child)
                 for child in self.remote_file_list.get_children('')]
        
        self.sort_items(self.remote_file_list, items, col, self.remote_sort_reverse)
        self.update_remote_sort_indicator()

    def sort_items(self, treeview, items, col: str, reverse: bool):
        def get_sort_key(item):
            val, item_id = item
            tags = treeview.item(item_id, "tags")
            is_dir = tags and "dir" in tags
            dir_priority = 0 if is_dir else 1
            
            if col == "Size":
                return (dir_priority, self.parse_size(val))
            elif col == "Modified":
                return (dir_priority, self.parse_date(val))
            elif col == "Type":
                return (dir_priority, val)
            else:
                natural_key = [int(s) if s.isdigit() else s.lower()
                              for s in re.split(r'(\d+)', val)]
                return (dir_priority, natural_key)
        
        items.sort(key=get_sort_key, reverse=reverse)
        
        for index, (val, item) in enumerate(items):
            treeview.move(item, '', index)

    def update_local_sort_indicator(self):
        for col in self.local_file_list["columns"]:
            text = self.local_file_list.heading(col)["text"]
            text = text.replace(" ↑", "").replace(" ↓", "")
            
            if col == self.local_sorted_column:
                arrow = " ↓" if self.local_sort_reverse else " ↑"
                self.local_file_list.heading(col, text=text + arrow)
            else:
                self.local_file_list.heading(col, text=text)

    def update_remote_sort_indicator(self):
        for col in self.remote_file_list["columns"]:
            text = self.remote_file_list.heading(col)["text"]
            text = text.replace(" ↑", "").replace(" ↓", "")
            
            if col == self.remote_sorted_column:
                arrow = " ↓" if self.remote_sort_reverse else " ↑"
                self.remote_file_list.heading(col, text=text + arrow)
            else:
                self.remote_file_list.heading(col, text=text)

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
            self.init_remote_directory_tree()
        else:
            self.init_remote_browser()
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
        
        for item in self.remote_tree.get_children():
            self.remote_tree.delete(item)
        for item in self.remote_file_list.get_children():
            self.remote_file_list.delete(item)
        
        self.remote_tree_nodes.clear()
        self.remote_path_entry.delete(0, "end")
        self.remote_count_var.set("远程: 0 个项目")

    def refresh_all(self):
        self.load_local_files(self.local_path)
        self.load_remote_files()
        self.log_message("已刷新")
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
        
        new_path = os.path.join(self.remote_path, folder_name).replace("\\", "/")
        
        try:
            self.conn.createDirectory(self.current_share, new_path)
            self.log_message(f"文件夹已创建: {new_path}")
            self.load_remote_files()
            self.expand_remote_tree_to_path(self.remote_path)
        except Exception as e:
            self.log_message(f"创建失败: {str(e)}")
            messagebox.showerror("错误", f"目录创建失败: {str(e)}")

    def upload_from_local(self):
        selected_items = self.local_file_list.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先在本地选择要上传的文件")
            return
        
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        files_to_upload = []
        for item_id in selected_items:
            item = self.local_file_list.item(item_id)
            filename = item["text"].strip()
            local_path = os.path.join(self.local_path, filename)
            
            if os.path.exists(local_path):
                files_to_upload.append((filename, local_path))
        
        if not files_to_upload:
            return
        
        def upload_thread():
            success_count = 0
            total_files = len(files_to_upload)
            
            for i, (filename, local_path) in enumerate(files_to_upload):
                self.after(0, lambda f=filename, c=i+1, t=total_files: 
                          self.update_status(f"上传: {f} ({c}/{t})"))
                
                try:
                    if os.path.isfile(local_path):
                        remote_path = os.path.join(self.remote_path, filename).replace("\\", "/")
                        with open(local_path, "rb") as f:
                            self.conn.storeFile(self.current_share, remote_path, f)
                        success_count += 1
                        self.after(0, lambda f=filename: self.log_message(f"上传成功: {f}"))
                    elif os.path.isdir(local_path):
                        self.upload_directory_recursive(local_path, self.remote_path)
                        success_count += 1
                except Exception as e:
                    self.after(0, lambda f=filename, e=str(e): self.log_message(f"上传失败[{f}]: {e}"))
            
            self.after(0, lambda: self.update_status("上传完成"))
            self.after(0, lambda: self.log_message(f"上传完成: {success_count}/{total_files}"))
            self.after(0, lambda: messagebox.showinfo("完成", f"成功上传 {success_count} 个文件"))
            self.after(0, self.load_remote_files)
        
        threading.Thread(target=upload_thread, daemon=True).start()

    def upload_directory_recursive(self, local_dir: str, remote_base: str):
        dir_name = os.path.basename(local_dir)
        remote_dir = os.path.join(remote_base, dir_name).replace("\\", "/")
        
        try:
            self.conn.createDirectory(self.current_share, remote_dir)
        except:
            pass
        
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = os.path.join(remote_dir, item).replace("\\", "/")
            
            if os.path.isdir(local_path):
                self.upload_directory_recursive(local_path, remote_dir)
            else:
                with open(local_path, "rb") as f:
                    self.conn.storeFile(self.current_share, remote_path, f)

    def download_to_local(self):
        selected_items = self.remote_file_list.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先在远程选择要下载的文件")
            return
        
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        files_to_download = []
        for item_id in selected_items:
            item = self.remote_file_list.item(item_id)
            filename = item["text"].strip()
            tags = item.get("tags", [])
            is_dir = "dir" in tags
            
            remote_path = os.path.join(self.remote_path, filename).replace("\\", "/")
            local_path = os.path.join(self.local_path, filename)
            files_to_download.append((filename, remote_path, local_path, is_dir))
        
        if not files_to_download:
            return
        
        def download_thread():
            success_count = 0
            total_files = len(files_to_download)
            
            for i, (filename, remote_path, local_path, is_dir) in enumerate(files_to_download):
                self.after(0, lambda f=filename, c=i+1, t=total_files: 
                          self.update_status(f"下载: {f} ({c}/{t})"))
                
                try:
                    if not is_dir:
                        with open(local_path, "wb") as f:
                            self.conn.retrieveFile(self.current_share, remote_path, f)
                        success_count += 1
                        self.after(0, lambda f=filename: self.log_message(f"下载成功: {f}"))
                    else:
                        self.download_directory_recursive(remote_path, local_path)
                        success_count += 1
                except Exception as e:
                    self.after(0, lambda f=filename, e=str(e): self.log_message(f"下载失败[{f}]: {e}"))
            
            self.after(0, lambda: self.update_status("下载完成"))
            self.after(0, lambda: self.log_message(f"下载完成: {success_count}/{total_files}"))
            self.after(0, lambda: messagebox.showinfo("完成", f"成功下载 {success_count} 个文件"))
            self.after(0, lambda: self.load_local_files(self.local_path))
        
        threading.Thread(target=download_thread, daemon=True).start()

    def download_directory_recursive(self, remote_dir: str, local_base: str):
        if not os.path.exists(local_base):
            os.makedirs(local_base)
        
        try:
            items = self.conn.listPath(self.current_share, remote_dir)
            for item in items:
                if item.filename in [".", ".."]:
                    continue
                
                remote_path = os.path.join(remote_dir, item.filename).replace("\\", "/")
                local_path = os.path.join(local_base, item.filename)
                
                if item.isDirectory:
                    self.download_directory_recursive(remote_path, local_path)
                else:
                    with open(local_path, "wb") as f:
                        self.conn.retrieveFile(self.current_share, remote_path, f)
        except Exception as e:
            self.log_message(f"下载目录失败: {remote_dir} - {str(e)}")

    def delete_local_items(self):
        selected_items = self.local_file_list.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的文件或目录")
            return
        
        items_to_delete = []
        for item_id in selected_items:
            item = self.local_file_list.item(item_id)
            item_name = item["text"].strip()
            tags = item.get("tags", [])
            is_dir = "dir" in tags
            full_path = os.path.join(self.local_path, item_name)
            items_to_delete.append((item_name, full_path, is_dir))
        
        if not items_to_delete:
            return
        
        confirm_msg = f"确定要删除选中的 {len(items_to_delete)} 个项目吗？\n此操作不可恢复！"
        if not messagebox.askyesno("确认删除", confirm_msg):
            return
        
        success_count = 0
        
        def delete_thread():
            nonlocal success_count
            import shutil
            for item_name, full_path, is_dir in items_to_delete:
                try:
                    if os.path.exists(full_path):
                        if is_dir:
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
                        success_count += 1
                        self.after(0, lambda p=full_path: self.log_message(f"已删除: {p}"))
                except Exception as e:
                    self.after(0, lambda n=item_name, e=str(e): self.log_message(f"删除失败[{n}]: {e}"))
            
            self.after(0, lambda: self.update_status("删除完成"))
            self.after(0, lambda: messagebox.showinfo("完成", f"成功删除 {success_count} 个项目"))
            self.after(0, lambda: self.load_local_files(self.local_path))
        
        threading.Thread(target=delete_thread, daemon=True).start()

    def delete_remote_items(self):
        selected_items = self.remote_file_list.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的文件或目录")
            return
        
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        items_to_delete = []
        for item_id in selected_items:
            item = self.remote_file_list.item(item_id)
            item_name = item["text"].strip()
            tags = item.get("tags", [])
            is_dir = "dir" in tags
            full_path = os.path.join(self.remote_path, item_name).replace("\\", "/")
            items_to_delete.append((item_name, full_path, is_dir))
        
        if not items_to_delete:
            return
        
        confirm_msg = f"确定要删除选中的 {len(items_to_delete)} 个项目吗？"
        if not messagebox.askyesno("确认删除", confirm_msg):
            return
        
        success_count = 0
        
        def delete_thread():
            nonlocal success_count
            for item_name, full_path, is_dir in items_to_delete:
                try:
                    if is_dir:
                        self.delete_remote_directory_recursive(full_path)
                    else:
                        self.conn.deleteFiles(self.current_share, full_path)
                    success_count += 1
                    self.after(0, lambda p=full_path: self.log_message(f"已删除: {p}"))
                except Exception as e:
                    self.after(0, lambda n=item_name, e=str(e): self.log_message(f"删除失败[{n}]: {e}"))
            
            self.after(0, lambda: self.update_status("删除完成"))
            self.after(0, lambda: messagebox.showinfo("完成", f"成功删除 {success_count} 个项目"))
            self.after(0, self.load_remote_files)
        
        threading.Thread(target=delete_thread, daemon=True).start()

    def delete_remote_directory_recursive(self, path: str):
        try:
            contents = self.conn.listPath(self.current_share, path)
            for file in contents:
                if file.filename in ['.', '..']:
                    continue
                
                item_path = os.path.join(path, file.filename).replace("\\", "/")
                if file.isDirectory:
                    self.delete_remote_directory_recursive(item_path)
                else:
                    self.conn.deleteFiles(self.current_share, item_path)
            
            self.conn.deleteDirectory(self.current_share, path)
        except Exception as e:
            self.log_message(f"删除目录失败: {path} - {str(e)}")
            raise

    def on_external_drop(self, event):
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        files = self.parse_dnd_files(event.data)
        if files:
            self.upload_files_by_path(files)

    def on_drop_to_remote(self, event):
        if not self.conn or not self.current_share:
            messagebox.showwarning("提示", "请先连接到服务器")
            return
        
        if self._local_dragging:
            self.upload_from_local()
            return event.action
        
        files = self.parse_dnd_files(event.data)
        if files:
            self.upload_files_by_path(files)
        
        return event.action

    def on_drop_to_local(self, event):
        if self._remote_dragging:
            if not self.conn or not self.current_share:
                messagebox.showwarning("提示", "请先连接到服务器")
                return event.action
            self.download_to_local()
            return event.action
        
        files = self.parse_dnd_files(event.data)
        if files:
            for src_path in files:
                filename = os.path.basename(src_path)
                dest_path = os.path.join(self.local_path, filename)
                try:
                    import shutil
                    if os.path.isdir(src_path):
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(src_path, dest_path)
                    else:
                        shutil.copy2(src_path, dest_path)
                    self.log_message(f"已复制: {filename}")
                except Exception as e:
                    self.log_message(f"复制失败[{filename}]: {str(e)}")
            self.load_local_files(self.local_path)
        
        return event.action

    def parse_dnd_files(self, data):
        files = []
        if data:
            try:
                paths = self.tk.splitlist(data)
                for path in paths:
                    path = path.strip()
                    if path and os.path.exists(path):
                        files.append(path)
            except:
                data = data.strip()
                if data.startswith('{') and data.endswith('}'):
                    data = data[1:-1]
                paths = data.split('} {')
                for path in paths:
                    path = path.strip('{}').strip()
                    if path and os.path.exists(path):
                        files.append(path)
        return files

    def upload_files_by_path(self, file_paths):
        if not self.conn or not self.current_share:
            return
        
        def upload_thread():
            success_count = 0
            total_files = len(file_paths)
            
            for i, local_path in enumerate(file_paths):
                self.after(0, lambda f=os.path.basename(local_path), c=i+1, t=total_files: 
                          self.update_status(f"上传: {f} ({c}/{t})"))
                
                try:
                    if os.path.isfile(local_path):
                        filename = os.path.basename(local_path)
                        remote_path = os.path.join(self.remote_path, filename).replace("\\", "/")
                        with open(local_path, "rb") as f:
                            self.conn.storeFile(self.current_share, remote_path, f)
                        success_count += 1
                        self.after(0, lambda f=filename: self.log_message(f"上传成功: {f}"))
                    elif os.path.isdir(local_path):
                        self.upload_directory_recursive(local_path, self.remote_path)
                        success_count += 1
                except Exception as e:
                    self.after(0, lambda f=os.path.basename(local_path), e=str(e): self.log_message(f"上传失败[{f}]: {e}"))
            
            self.after(0, lambda: self.update_status("上传完成"))
            self.after(0, lambda: self.log_message(f"上传完成: {success_count}/{total_files}"))
            self.after(0, self.load_remote_files)
        
        threading.Thread(target=upload_thread, daemon=True).start()

    def show_about(self):
        about_text = """SMB文件管理器 v3.0

双栏本地-远程文件管理器，支持拖拽操作。

功能特性:
• 双栏文件浏览（本地+远程）
• 服务器连接管理
• 文件上传/下载（支持拖拽）
• 目录自动展开
• 文件列表排序
• 批量操作
• 操作日志
"""
        messagebox.showinfo("关于", about_text)

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