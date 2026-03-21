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

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False
    print("警告：tkinterdnd2不可用，拖拽功能禁用")


class SMBClientBrowser(TkinterDnD.Tk if DND_SUPPORT else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMB客户端浏览器")
        self.geometry("1200x800")
        self.conn = None
        self.current_share = ""
        self.current_path = "/"
        self.servers = self.load_servers()
        self.tree_nodes = {}
        self.dragged_item = None
        self.sorted_column = ""
        self.sort_reverse = False
        self.upload_progress = None
        self.upload_progress_label = None
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        connection_frame = ttk.LabelFrame(self, text="服务器连接")
        connection_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(connection_frame, text="服务器地址:").grid(row=0, column=0, padx=5, pady=5)
        self.server_ip = ttk.Entry(connection_frame, width=25)
        self.server_ip.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(connection_frame, text="端口:").grid(row=0, column=2, padx=5, pady=5)
        self.port = ttk.Entry(connection_frame, width=8)
        self.port.insert(0, "445")
        self.port.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(connection_frame, text="用户名:").grid(row=1, column=0, padx=5, pady=5)
        self.username = ttk.Entry(connection_frame, width=25)
        self.username.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(connection_frame, text="密码:").grid(row=1, column=2, padx=5, pady=5)
        self.password = ttk.Entry(connection_frame, width=15, show="*")
        self.password.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(connection_frame, text="共享名称:").grid(row=2, column=0, padx=5, pady=5)
        self.share_name = ttk.Entry(connection_frame, width=25)
        self.share_name.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(connection_frame, text="SMB版本:").grid(row=3, column=0, padx=5, pady=5)
        self.smb_version = ttk.Combobox(connection_frame, values=["SMBv1", "SMBv2", "SMBv3", "自动协商"])
        self.smb_version.current(3)
        self.smb_version.grid(row=3, column=1, padx=5, pady=5)

        ttk.Button(connection_frame, text="连接", command=self.connect_to_server).grid(row=3, column=2, padx=5, pady=5)
        ttk.Button(connection_frame, text="保存配置", command=self.save_config).grid(row=3, column=3, padx=5, pady=5)

        ttk.Label(connection_frame, text="保存的配置:").grid(row=0, column=4, padx=5, pady=5)
        self.saved_servers = ttk.Combobox(connection_frame, values=list(self.servers.keys()), width=20)
        self.saved_servers.grid(row=0, column=5, padx=5, pady=5)
        self.saved_servers.bind("<<ComboboxSelected>>", self.load_selected_config)

        browser_frame = ttk.Frame(self)
        browser_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tree_frame = ttk.LabelFrame(browser_frame, text="目录树")
        tree_frame.pack(side="left", fill="y", padx=(0, 5), pady=5)

        self.tree_dir = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.tree_dir.pack(fill="both", expand=True, padx=5, pady=5)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_dir.yview)
        tree_scroll.pack(side="right", fill="y")
        self.tree_dir.configure(yscrollcommand=tree_scroll.set)

        self.tree_dir.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree_dir.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree_dir.bind("<Button-3>", self.show_tree_context_menu)

        file_frame = ttk.LabelFrame(browser_frame, text="文件列表")
        file_frame.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

        self.file_list = ttk.Treeview(file_frame, columns=("Name", "Size", "Type", "Modified"),
                                     show="headings", selectmode="extended")
        self.file_list.pack(fill="both", expand=True, padx=5, pady=5)

        columns = [
            {"id": "Name", "text": "名称", "width": 300, "anchor": "w"},
            {"id": "Size", "text": "大小", "width": 100, "anchor": "center"},
            {"id": "Type", "text": "类型", "width": 100, "anchor": "center"},
            {"id": "Modified", "text": "修改时间", "width": 150, "anchor": "center"}
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
                anchor=col["anchor"],
                stretch=False
            )

        file_scroll_y = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_list.yview)
        file_scroll_y.pack(side="right", fill="y")
        file_scroll_x = ttk.Scrollbar(file_frame, orient="horizontal", command=self.file_list.xview)
        file_scroll_x.pack(side="bottom", fill="x")
        self.file_list.configure(yscrollcommand=file_scroll_y.set, xscrollcommand=file_scroll_x.set)

        self.file_list.bind("<Button-3>", self.show_file_context_menu)
        self.file_list.bind("<Double-1>", self.on_file_double_click)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(action_frame, text="返回上级", command=self.go_up).pack(side="left", padx=5)
        ttk.Button(action_frame, text="下载文件", command=self.download_selected_files).pack(side="left", padx=5)
        ttk.Button(action_frame, text="上传文件", command=self.upload_file).pack(side="left", padx=5)
        ttk.Button(action_frame, text="上传目录", command=self.upload_directory).pack(side="left", padx=5)
        ttk.Button(action_frame, text="新建文件夹", command=self.create_folder).pack(side="left", padx=5)
        ttk.Button(action_frame, text="刷新", command=self.refresh_files).pack(side="left", padx=5)

        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

        log_frame = ttk.LabelFrame(self, text="操作日志")
        log_frame.pack(fill="both", padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.config(state="disabled")

        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(side="left", padx=5)

        self.upload_progress = ttk.Progressbar(
            self.progress_frame, orient="horizontal", mode="determinate"
        )
        self.upload_progress.pack(fill="x", expand=True, padx=5)
        self.upload_progress.pack_forget()

    def log_message(self, message):
        self.log_area.config(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def connect_to_server(self):
        server_ip = self.server_ip.get().strip()
        port = int(self.port.get()) if self.port.get().isdigit() else 445
        username = self.username.get().strip()
        password = self.password.get()
        share_name = self.share_name.get().strip()
        smb_version_choice = self.smb_version.get()

        use_ntlm_v2 = {
            "SMBv1": False,
            "SMBv2": True,
            "SMBv3": True,
            "自动协商": True
        }[smb_version_choice]

        try:
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

            connected = self.conn.connect(server_ip, port, timeout=30)

            if connected:
                self.available_shares = [s.name for s in self.conn.listShares()]

                if share_name not in self.available_shares:
                    self.log_message(f"警告: 共享 '{share_name}' 不存在")
                    messagebox.showwarning("共享不存在",
                        f"共享 '{share_name}' 不存在！可用共享: {', '.join(self.available_shares)}\n"
                        "目录树已显示所有可用共享")
                    self.current_share = ""
                    self.init_share_tree()
                else:
                    self.current_share = share_name
                    self.init_directory_tree()

            else:
                self.log_message("连接失败，请检查服务器信息")
                self.status_var.set("连接失败")
                messagebox.showerror("错误", "服务器连接失败")
        except (NotConnectedError, OperationFailure) as e:
            self.log_message(f"认证失败: {str(e)}")
            self.status_var.set("认证失败")
            messagebox.showerror("错误", f"认证失败: {str(e)}")
        except socket.error as e:
            if e.errno == 10054:
                self.log_message("连接被远程主机重置 (WinError 10054)")
                self.status_var.set("连接被重置")
                messagebox.showerror("错误", "远程主机强制关闭了连接。请检查防火墙和SMB设置")
            else:
                self.log_message(f"网络错误: {str(e)}")
                self.status_var.set(f"网络错误: {e.errno}")
                messagebox.showerror("错误", f"网络错误: {str(e)}")
        except Exception as e:
            self.log_message(f"未知错误: {str(e)}")
            self.status_var.set("连接错误")
            messagebox.showerror("错误", f"发生异常: {str(e)}")
        finally:
            import socket
            socket.setdefaulttimeout(None)

    def init_share_tree(self):
        for item in self.tree_dir.get_children():
            self.tree_dir.delete(item)

        root_id = self.tree_dir.insert("", "end", text=f"服务器: {self.server_ip.get()}", open=True)
        self.tree_nodes[root_id] = "//SERVER_ROOT//"

        for share in self.available_shares:
            node_id = self.tree_dir.insert(root_id, "end", text=share, tags=("share",))
            self.tree_nodes[node_id] = f"//SHARE//{share}"

        self.status_var.set(f"已连接: {self.server_ip.get()} | 选择共享目录")

    def init_directory_tree(self):
        for item in self.tree_dir.get_children():
            self.tree_dir.delete(item)

        root_id = self.tree_dir.insert("", "end", text=self.current_share, open=True)
        self.tree_nodes[root_id] = "/"

        self.populate_tree_node(root_id, "/")

        self.tree_dir.selection_set(root_id)
        self.tree_dir.focus(root_id)
        self.on_tree_select(None)

    def populate_tree_node(self, parent_id, path):
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

                node_id = self.tree_dir.insert(parent_id, "end", text=d.filename, tags=("dir",))
                self.tree_nodes[node_id] = full_path

                self.tree_dir.insert(node_id, "end", text="Loading...")
        except OperationFailure as e:
            self.log_message(f"目录访问失败: {path} - {str(e)}")
        except Exception as e:
            self.log_message(f"错误加载目录: {path} - {str(e)}")

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
            self.current_share = self.tree_dir.item(node_id, "text")
            self.current_path = "/"
            self.log_message(f"已选择共享: {self.current_share}")
            self.init_directory_tree()
            return

        if node_path and not node_path.startswith("//"):
            self.current_path = node_path
            self.load_file_list()

    def select_in_directory_tree(self, path):
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
            return

        try:
            files = self.conn.listPath(self.current_share, self.current_path)

            for file in files:
                if file.filename in [".", ".."]:
                    continue

                filename = file.filename
                if filename.startswith(".") or " " in filename:
                    filename = f"'{filename}'"

                if file.isDirectory:
                    self.file_list.insert("", "end", text=filename,
                                        values=(filename, "", "目录", datetime.datetime.fromtimestamp(file.last_write_time)),
                                        tags=("dir",))
                else:
                    size = self.format_size(file.file_size)
                    self.file_list.insert("", "end", text=filename,
                                        values=(filename, size, "文件", datetime.datetime.fromtimestamp(file.last_write_time)),
                                        tags=("file",))

            self.file_list.tag_configure("dir", foreground="blue")
            self.file_list.tag_configure("file", foreground="black")

            if self.sorted_column:
                self.sort_file_list(self.sorted_column)

            self.status_var.set(f"当前路径: {self.current_share}:{self.current_path}")
        except OperationFailure as e:
            self.log_message(f"目录访问失败: {self.current_path} - {str(e)}")
            messagebox.showerror("错误", f"操作失败: {str(e)}")

    def format_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024 * 1024):.1f} MB"
        else:
            return f"{size/(1024 * 1024 * 1024):.1f} GB"

    def sort_file_list(self, col):
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
            items.sort(key=lambda x: (0 if x[0] == "目录" else 1, x[0]),
                      reverse=self.sort_reverse)
        else:
            items.sort(key=lambda x: (
                0 if "dir" in self.file_list.item(x[1], "tags") else 1,
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

    def parse_size(self, size_str):
        if not size_str:
            return 0

        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    num = float(size_str.replace(unit, "").strip())
                    return num * multiplier
                except:
                    return 0
        return 0

    def parse_date(self, date_str):
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
        selected = self.tree_dir.selection()
        if not selected:
            return

        current_id = selected[0]
        parent_id = self.tree_dir.parent(current_id)

        if parent_id:
            self.tree_dir.selection_set(parent_id)
            self.tree_dir.focus(parent_id)
            self.on_tree_select(None)

    def on_file_double_click(self, event):
        region = self.file_list.identify("region", event.x, event.y)
        if region == "nothing":
            return

        item = self.file_list.identify_row(event.y)
        if not item:
            return

        item_data = self.file_list.item(item)
        values = item_data["values"]

        if len(values) > 2 and values[2] == "目录":
            dir_name = item_data["text"].strip("'")

            new_path = os.path.join(self.current_path, dir_name).replace("\\", "/")

            if new_path.startswith("//"):
                new_path = new_path[2:]
            if not new_path.startswith("/"):
                new_path = "/" + new_path

            self.current_path = new_path
            self.log_message(f"进入目录: {new_path}")

            self.load_file_list()

            self.select_in_directory_tree(new_path)

    def show_tree_context_menu(self, event):
        item = self.tree_dir.identify_row(event.y)
        if not item:
            return

        menu = Menu(self, tearoff=0)
        menu.add_command(label="刷新目录", command=self.refresh_tree_node)
        menu.add_command(label="删除目录", command=lambda: self.delete_directory(item))
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
            menu.add_command(label=f"删除所选({len(selected_items)}项)",
                            command=self.delete_selected_items)
            menu.add_command(label=f"下载所选({len(selected_items)}项)",
                            command=self.download_selected_files)
        else:
            menu.add_command(label="删除", command=self.delete_selected_files)
            menu.add_command(label="下载", command=self.download_selected_files)

        menu.add_separator()
        menu.add_command(label="下载", command=self.download_selected_files)
        menu.add_command(label="重命名", command=self.rename_file)
        menu.add_command(label="属性", command=lambda: self.show_properties(item, is_dir))
        menu.add_separator()

        menu.add_command(label="删除目录（需空目录）",
                        state="disabled" if self.has_dir_content(item) else "normal",
                        command=lambda: self.delete_directory(item))
        menu.add_command(label="删除目录（含内容）", command=lambda: self.delete_directory_safely(item))

        menu.post(event.x_root, event.y_root)

    def has_dir_content(self, item_id):
        dir_name = self.file_list.item(item_id, "text").strip("'")
        full_path = os.path.join(self.current_path, dir_name).replace("\\", "/")
        try:
            contents = self.conn.listPath(self.current_share, full_path)
            return len([f for f in contents if f.filename not in (".", "..")]) > 0
        except:
            return True

    def refresh_tree_node(self):
        selected = self.tree_dir.selection()
        if selected:
            node_id = selected[0]
            if node_id in self.tree_nodes:
                self.populate_tree_node(node_id, self.tree_nodes[node_id])

    def delete_selected_items(self):
        selected_items = self.file_list.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的文件或目录")
            return

        items_to_delete = []
        for item_id in selected_items:
            item = self.file_list.item(item_id)
            item_name = item["text"].strip("'")
            is_dir = item["values"][2] == "目录"
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
                    self.after(0, lambda: self.log_message(f"已删除: {full_path}"))
                except Exception as e:
                    failed_items.append((item_name, str(e)))
                    self.after(0, lambda: self.log_message(f"删除失败[{item_name}]: {str(e)}"))

            result_msg = f"成功删除 {success_count}/{len(items_to_delete)} 个项目"
            if failed_items:
                result_msg += "\n\n以下项目删除失败:\n"
                result_msg += "\n".join(f"{name}: {error}" for name, error in failed_items)

            self.after(0, lambda: messagebox.showinfo("删除结果", result_msg))
            self.after(0, self.refresh_files_after_upload)

        threading.Thread(target=delete_thread, daemon=True).start()
        self.log_message(f"开始后台删除 {len(items_to_delete)} 个项目...")

    def upload_file(self, local_path=None):
        if not local_path:
            local_paths = filedialog.askopenfilenames(title="选择上传文件")
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
                self.update_progress(progress, f"上传: {filename} ({i+1}/{total_files})")

                try:
                    with open(file_path, "rb") as f:
                        self.conn.storeFile(self.current_share, clean_remote_path, f)
                    success_count += 1
                    self.log_message(f"上传成功: {filename}")
                except Exception as e:
                    self.log_message(f"上传失败[{filename}]: {str(e)}")

            self.update_progress(100, f"上传完成: {success_count}/{total_files} 成功")
            self.log_message(f"文件上传完成: {success_count}/{total_files} 个文件成功")
            messagebox.showinfo("完成", f"成功上传 {success_count} 个文件")
            self.refresh_files()

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
                self.update_progress(0, f"扫描完成, 共 {total_files} 个文件")

                count, success_count, error_list = self._upload_directory_recursive(
                    local_dir_path, remote_base_path, total_files
                    )

                self.update_progress(100, "上传完成")
                self.log_message(f"目录上传完成: {success_count}/{total_files} 个文件成功")
                if error_list:
                    error_msg = "\n".join(error_list[:5])
                    if len(error_list) > 5:
                        error_msg += f"\n...等共 {len(error_list)} 个错误"
                    self.log_message(f"上传错误:\n{error_msg}")

                messagebox.showinfo("完成",
                    f"目录上传完成!\n成功上传 {success_count}/{total_files} 个文件到:\n{remote_base_path}")
                self.refresh_files()
            except Exception as e:
                self.log_message(f"目录上传失败: {str(e)}")
                self.update_progress(0, f"上传失败: {str(e)}")
                messagebox.showerror("错误", f"上传失败: {str(e)}")

        threading.Thread(target=upload_thread, daemon=True).start()
        self.log_message(f"开始上传目录: {local_dir_path} -> {remote_base_path}")

    def _upload_directory_recursive(self, local_path, smb_base_path, total_files, count=0, success_count=0, error_list=None):
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
                self.update_progress(progress, f"上传: {entry} ({count}/{total_files})")

                try:
                    with open(local_entry_path, "rb") as f:
                        self.conn.storeFile(self.current_share, remote_entry_path, f)
                    success_count += 1
                except Exception as e:
                    error_list.append(f"文件上传失败 [{entry}]: {str(e)}")

        return count, success_count, error_list

    def show_progress(self, value, text):
        self.progress_label.config(text=text)
        if not self.upload_progress.winfo_ismapped():
            self.upload_progress.pack(fill="x", expand=True, padx=5)
        self.upload_progress["value"] = value
        self.update()

    def update_progress(self, value, text):
        self.after(0, lambda: self._safe_update_progress(value, text))

    def _safe_update_progress(self, value, text):
        if self.upload_progress:
            self.progress_label.config(text=text)
            self.upload_progress["value"] = value

            if not self.upload_progress.winfo_ismapped():
                self.upload_progress.pack(fill="x", expand=True, padx=5)

            if value >= 100:
                self.after(2000, self.hide_progress)

    def hide_progress(self):
        if self.upload_progress and self.upload_progress.winfo_ismapped():
            self.upload_progress.pack_forget()
            self.progress_label.config(text="")

    def handle_drop(self, event):
        paths = event.data.split()
        for path in paths:
            path = path.strip("{}")

            if os.path.isfile(path):
                self.upload_file(path)
            elif os.path.isdir(path):
                self.upload_directory(path)

    def refresh_files_after_upload(self):
        try:
            selected = self.tree_dir.selection()
            if selected:
                node_id = selected[0]
                if node_id in self.tree_nodes:
                    self.populate_tree_node(node_id, self.tree_nodes[node_id])
                    self.tree_dir.selection_set(node_id)
                    self.tree_dir.focus(node_id)

            self.load_file_list()
        except Exception as e:
            self.log_message(f"刷新界面时出错: {str(e)}")
            self.after(100, self.refresh_files_after_upload)

    def _delete_directory_recursive(self, path):
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

    def create_folder(self):
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

            selected = self.tree_dir.selection()
            if selected:
                self.populate_tree_node(selected[0], self.current_path)

            self.load_file_list()
        except Exception as e:
            self.log_message(f"创建失败: {str(e)}")
            messagebox.showerror("错误", f"目录创建失败: {str(e)}")

    def download_selected_files(self):
        selected_items = self.file_list.selection()
        if not selected_items:
            return

        save_dir = filedialog.askdirectory(title="选择保存位置")
        if not save_dir:
            return

        file_list = []
        for item_id in selected_items:
            item = self.file_list.item(item_id)
            if item["values"][2] != "文件":
                continue
            filename = item["text"].strip("'")
            remote_path = os.path.join(self.current_path, filename)
            clean_remote_path = self.normalize_path(remote_path)
            local_path = os.path.join(save_dir, filename)
            file_list.append((filename, clean_remote_path, local_path))

        if not file_list:
            return

        def download_thread():
            success_count = 0
            for filename, remote_path, local_path in file_list:
                try:
                    with open(local_path, "wb") as f:
                        self.conn.retrieveFile(self.current_share, remote_path, f)
                    self.log_message(f"下载成功: {filename}")
                    success_count += 1
                except Exception as e:
                    self.log_message(f"下载失败[{filename}]: {str(e)}")

            self.log_message(f"下载完成: {success_count}/{len(file_list)}")
            messagebox.showinfo("下载完成",
                              f"成功下载 {success_count} 个文件到:\n{save_dir}")

        threading.Thread(target=download_thread, daemon=True).start()
        self.log_message(f"开始后台下载 {len(file_list)} 个文件...")

    def delete_file(self, item_id):
        item = self.file_list.item(item_id)
        filename = item["text"].strip("'")
        full_path = os.path.join(self.current_path, filename).replace("\\", "/")

        if messagebox.askyesno("确认删除", f"确定删除文件 {filename} 吗？"):
            try:
                self.conn.deleteFiles(self.current_share, full_path)
                self.log_message(f"已删除文件: {full_path}")
                self.refresh_files()
            except OperationFailure as e:
                error_msg = f"删除失败: {str(e)}"
                self.log_message(error_msg)
                messagebox.showerror("错误", f"{error_msg}\n可能原因：文件被占用或权限不足")
            except Exception as e:
                self.log_message(f"未知错误: {str(e)}")
                messagebox.showerror("错误", f"删除失败: {str(e)}")

    def delete_selected_files(self):
        selected_items = self.file_list.selection()
        if not selected_items:
            return

        file_list = []
        for item_id in selected_items:
            item = self.file_list.item(item_id)
            if item["values"][2] != "文件":
                continue
            filename = item["text"].strip("'")
            full_path = os.path.join(self.current_path, filename)
            clean_path = self.normalize_path(full_path)
            file_list.append((filename, clean_path))

        if not file_list:
            return

        confirm = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(file_list)} 个文件吗？"
        )
        if not confirm:
            return

        success_count = 0
        for filename, clean_path in file_list:
            try:
                self.conn.deleteFiles(self.current_share, clean_path)
                self.log_message(f"已删除: {clean_path}")
                success_count += 1
            except Exception as e:
                self.log_message(f"删除失败[{filename}]: {str(e)}")

        self.refresh_files()
        messagebox.showinfo("完成", f"成功删除 {success_count}/{len(file_list)} 个文件")

    def delete_directory(self, item_id):
        dir_name = self.file_list.item(item_id, "text").strip("'")
        full_path = os.path.join(self.current_path, dir_name).replace("\\", "/")

        if self.has_dir_content(item_id):
            messagebox.showerror("错误", "无法删除非空目录！请先清空目录内容")
            return

        if messagebox.askyesno("确认删除", f"确定删除空目录 {dir_name} 吗？"):
            try:
                self.conn.deleteDirectory(self.current_share, full_path)
                self.log_message(f"已删除目录: {full_path}")
                self.refresh_files()
            except OperationFailure as e:
                error_msg = f"目录删除失败: {str(e)}"
                self.log_message(error_msg)
                messagebox.showerror("错误", f"{error_msg}\n错误代码: {e.status}")

    def delete_directory_safely(self, item_id):
        dir_name = self.file_list.item(item_id, "text").strip("'")
        full_path = os.path.join(self.current_path, dir_name).replace("\\", "/")

        if messagebox.askyesno("确认删除", f"确定删除目录 '{dir_name}' 及其所有内容吗？"):
            try:
                self._delete_directory_recursive(full_path)
                self.log_message(f"已删除目录: {full_path}")
                self.refresh_files()
            except Exception as e:
                self.log_message(f"删除失败: {str(e)}")
                messagebox.showerror("错误", f"删除失败: {str(e)}")

    def rename_file(self):
        selected = self.file_list.selection()
        if not selected or len(selected) > 1:
            messagebox.showwarning("警告", "请选择单个文件重命名")
            return

        item_id = selected[0]
        item = self.file_list.item(item_id)
        if item["values"][2] != "文件":
            messagebox.showwarning("警告", "只能重命名文件")
            return

        old_name = item["text"].strip("'")
        new_name = simpledialog.askstring("重命名", "输入新文件名:", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return

        if any(char in new_name for char in '\\/:*?"<>|'):
            messagebox.showerror("错误", "文件名包含非法字符: \\ / : * ? \" < > |")
            return

        old_path = os.path.join(self.current_path, old_name).replace("\\", "/")
        new_path = os.path.join(self.current_path, new_name).replace("\\", "/")

        try:
            self.conn.rename(self.current_share, old_path, new_path)
            self.log_message(f"重命名成功: {old_name} -> {new_name}")
            self.refresh_files()
        except Exception as e:
            self.log_message(f"重命名失败: {str(e)}")
            messagebox.showerror("错误", f"重命名失败: {str(e)}")

    def show_properties(self, item_id, is_dir):
        try:
            if is_dir:
                dir_name = self.tree_dir.item(item_id, "text")
                full_path = self.tree_nodes.get(item_id, "")
                properties = f"名称: {dir_name}\n类型: 文件夹\n位置: {full_path}"

                try:
                    file_count = len(self.conn.listPath(self.current_share, full_path)) - 2
                    properties += f"\n包含项目: {file_count}"
                except:
                    pass
            else:
                file_name = self.file_list.item(item_id, "text").strip("'")
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

    def refresh_files(self):
        selected = self.tree_dir.selection()
        if selected:
            node_id = selected[0]
            if node_id in self.tree_nodes:
                self.populate_tree_node(node_id, self.tree_nodes[node_id])
                self.load_file_list()
                self.log_message("目录已刷新")

    def save_config(self):
        config = {
            "server_ip": self.server_ip.get(),
            "port": self.port.get(),
            "username": self.username.get(),
            "password": self.password.get(),
            "share_name": self.share_name.get(),
            "smb_version": self.smb_version.get()
        }
        config_name = simpledialog.askstring("保存配置", "输入配置名称:")
        if config_name:
            self.servers[config_name] = config
            with open("smb_config.json", "w") as f:
                json.dump(self.servers, f)
            self.saved_servers["values"] = list(self.servers.keys())
            self.log_message(f"配置已保存: {config_name}")

    def load_servers(self):
        try:
            if os.path.exists("smb_config.json"):
                with open("smb_config.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            self.log_message(f"加载配置失败: {str(e)}")
        return {}

    def load_selected_config(self, event):
        config_name = self.saved_servers.get()
        if config_name in self.servers:
            config = self.servers[config_name]
            self.server_ip.delete(0, "end")
            self.server_ip.insert(0, config.get("server_ip", ""))

            self.port.delete(0, "end")
            self.port.insert(0, config.get("port", "445"))

            self.username.delete(0, "end")
            self.username.insert(0, config.get("username", ""))

            self.password.delete(0, "end")
            self.password.insert(0, config.get("password", ""))

            self.share_name.delete(0, "end")
            self.share_name.insert(0, config.get("share_name", ""))

            self.smb_version.set(config.get("smb_version", "自动协商"))

            self.log_message(f"已加载配置: {config_name}")

    def normalize_path(self, path):
        return path.replace("\\", "/").rstrip("/") + "/"

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
