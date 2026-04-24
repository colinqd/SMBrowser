import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
import threading
import queue
import time
import os


def _format_size(size_bytes):
    if size_bytes <= 0:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_speed(bytes_per_sec):
    if bytes_per_sec <= 0:
        return ""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"


def _format_time(seconds):
    if seconds <= 0:
        return "-"
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        return f"{int(seconds / 60)}分{int(seconds % 60)}秒"
    else:
        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        return f"{h}时{m}分"


class TransferItem:
    def __init__(self, filename: str, src_path: str, dst_path: str, is_upload: bool, is_dir: bool = False):
        self.id = id(self)
        self.filename = filename
        self.src_path = src_path
        self.dst_path = dst_path
        self.is_upload = is_upload
        self.is_dir = is_dir
        self.status = "pending"
        self.progress = 0.0
        self.size = 0
        self.transferred = 0
        self.speed = 0.0
        self.speed_str = ""
        self.error = ""
        self.start_time = 0.0
        self.end_time = 0.0


class TransferTask:
    def __init__(self, task_id: int, items: List[TransferItem]):
        self.task_id = task_id
        self.items = items
        self.start_time = time.time()
        self.end_time = 0.0
        self.is_upload = len(items) > 0 and items[0].is_upload


class TransferManager:
    def __init__(self):
        self.tasks: Dict[int, TransferTask] = {}
        self.next_task_id = 1
        self.window: Optional['TransferProgressWindow'] = None
        self.queue = queue.Queue()

    def create_task(self, items: List[TransferItem]) -> TransferTask:
        task = TransferTask(self.next_task_id, items)
        self.tasks[task.task_id] = task
        self.next_task_id += 1
        if self.window and self.window.winfo_exists():
            self.queue.put(('task_add', task))
        return task

    def get_task(self, task_id: int) -> Optional[TransferTask]:
        return self.tasks.get(task_id)

    def update_task_progress(self, task_id: int, item: TransferItem, progress: float,
                             speed_str: str = "", transferred: int = 0, speed_bps: float = 0.0):
        item.progress = progress
        if speed_str:
            item.speed_str = speed_str
        if transferred > 0:
            item.transferred = transferred
        if speed_bps > 0:
            item.speed = speed_bps
        if self.window and self.window.winfo_exists():
            self.queue.put(('progress', task_id, item.id, progress, speed_str, transferred, speed_bps))

    def update_task_status(self, task_id: int, item: TransferItem, status: str, error: str = ""):
        item.status = status
        if error:
            item.error = error
        if status == "running" and item.start_time == 0:
            item.start_time = time.time()
        if status == "completed" and item.end_time == 0:
            item.end_time = time.time()
            item.progress = 1.0
            item.transferred = item.size
        if self.window and self.window.winfo_exists():
            self.queue.put(('status', task_id, item.id, status, error))

    def update_item_size(self, task_id: int, item: TransferItem, size: int):
        item.size = size
        if self.window and self.window.winfo_exists():
            self.queue.put(('size', task_id, item.id, size))

    def complete_task(self, task_id: int):
        if task_id in self.tasks:
            self.tasks[task_id].end_time = time.time()
            if self.window and self.window.winfo_exists():
                self.queue.put(('task_complete', task_id))

    def show_window(self, parent: tk.Tk):
        if self.window is None or not self.window.winfo_exists():
            self.window = TransferProgressWindow(parent, self)
            self._rebuild_existing_tasks()
        self.window.show()

    def _rebuild_existing_tasks(self):
        if not self.window or not self.window.winfo_exists():
            return
        for task in self.tasks.values():
            self.queue.put(('task_add', task))
            for item in task.items:
                if item.size > 0:
                    self.queue.put(('size', task.task_id, item.id, item.size))
                self.queue.put(('status', task.task_id, item.id, item.status, item.error))
                if item.progress > 0:
                    self.queue.put(('progress', task.task_id, item.id, item.progress,
                                    item.speed_str, item.transferred, item.speed))

    def hide_window(self):
        if self.window and self.window.winfo_exists():
            self.window.hide()

    def get_statistics(self) -> Dict[str, int]:
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }
        for task in self.tasks.values():
            for item in task.items:
                if item.is_dir:
                    stats['total_dirs'] += 1
                else:
                    stats['total_files'] += 1
                if item.status == 'pending':
                    stats['pending'] += 1
                elif item.status == 'running':
                    stats['running'] += 1
                elif item.status == 'completed':
                    stats['completed'] += 1
                elif item.status == 'failed':
                    stats['failed'] += 1
        return stats


class TransferProgressWindow(tk.Toplevel):
    COLUMNS = ("filename", "size", "progress", "speed", "eta", "status")
    COL_HEADERS = {
        "filename": "文件名",
        "size": "大小",
        "progress": "进度",
        "speed": "速度",
        "eta": "剩余时间",
        "status": "状态",
    }
    COL_WIDTHS = {
        "filename": 260,
        "size": 90,
        "progress": 180,
        "speed": 100,
        "eta": 80,
        "status": 90,
    }

    def __init__(self, parent: tk.Tk, manager: TransferManager):
        super().__init__(parent)
        self.title("文件传输")
        self.geometry("950x550")
        self.minsize(750, 400)
        self.resizable(True, True)
        self.manager = manager
        self.queue = manager.queue
        self.item_iids: Dict[int, str] = {}
        self.dir_item_map: Dict[int, List[int]] = {}  # 目录ID -> 子项ID列表
        self.task_tags: Dict[int, str] = {}
        self.running = True
        self._next_tag = 0

        self._setup_ui()
        self._process_queue()
        self.protocol("WM_DELETE_WINDOW", self.hide)

    def _setup_ui(self):
        header_frame = ttk.Frame(self, padding=(10, 8, 10, 4))
        header_frame.pack(fill="x")

        self.stats_label = ttk.Label(header_frame, text="准备就绪", font=('Segoe UI', 9))
        self.stats_label.pack(side="left")

        total_frame = ttk.Frame(header_frame)
        total_frame.pack(side="right", fill="x", expand=True, padx=20)
        ttk.Label(total_frame, text="总体进度:").pack(side="left")
        self.total_progress_var = tk.DoubleVar()
        self.total_progress_bar = ttk.Progressbar(
            total_frame, variable=self.total_progress_var, length=250, mode='determinate'
        )
        self.total_progress_bar.pack(side="left", padx=5)
        self.total_pct_label = ttk.Label(total_frame, text="0%", width=5)
        self.total_pct_label.pack(side="left")

        tree_frame = ttk.Frame(self, padding=(10, 4, 10, 4))
        tree_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Transfer.Treeview", rowheight=26, font=('Segoe UI', 9))
        style.configure("Transfer.Treeview.Heading", font=('Segoe UI', 9, 'bold'))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
            style="Transfer.Treeview",
        )

        for col in self.COLUMNS:
            self.tree.heading(col, text=self.COL_HEADERS[col])
            self.tree.column(col, width=self.COL_WIDTHS[col], minwidth=50)

        self.tree.column("filename", anchor="w", minwidth=100)
        self.tree.column("size", anchor="center")
        self.tree.column("progress", anchor="center")
        self.tree.column("speed", anchor="center")
        self.tree.column("eta", anchor="center")
        self.tree.column("status", anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        footer = ttk.Frame(self, padding=(10, 6, 10, 8))
        footer.pack(fill="x")

        self.cancel_btn = ttk.Button(footer, text="取消所有", command=self._cancel_all)
        self.cancel_btn.pack(side="right")
        ttk.Button(footer, text="隐藏窗口", command=self.hide).pack(side="right", padx=5)

        self._update_stats()

    def _get_task_tag(self, task_id: int) -> str:
        if task_id not in self.task_tags:
            self._next_tag += 1
            tag = f"task_{task_id}"
            self.task_tags[task_id] = tag
            bg_colors = ["#E8F0FE", "#FFF3E0", "#E8F5E9", "#FCE4EC", "#F3E5F5", "#E0F7FA"]
            bg = bg_colors[(task_id - 1) % len(bg_colors)]
            self.tree.tag_configure(tag, background=bg)
        return self.task_tags[task_id]

    def _process_queue(self):
        if not self.running:
            return
        processed = 0
        try:
            while True:
                msg = self.queue.get_nowait()
                kind = msg[0]
                if kind == 'task_add':
                    self._add_task(msg[1])
                elif kind == 'progress':
                    self._update_progress(msg[1], msg[2], msg[3], msg[4], msg[5], msg[6])
                elif kind == 'status':
                    self._update_status(msg[1], msg[2], msg[3], msg[4])
                elif kind == 'size':
                    self._update_size(msg[1], msg[2], msg[3])
                elif kind == 'task_complete':
                    self._task_complete(msg[1])
                processed += 1
                if processed >= 50:
                    break
        except queue.Empty:
            pass
        if processed > 0:
            self.update_idletasks()
        self.after(50, self._process_queue)

    def _add_task(self, task: TransferTask):
        tag = self._get_task_tag(task.task_id)

        dir_count = sum(1 for i in task.items if i.is_dir)
        file_count = sum(1 for i in task.items if not i.is_dir)
        task_type = "\u2B06 上传" if task.is_upload else "\u2B07 下载"
        detail = f"{file_count}个文件"
        if dir_count > 0:
            detail = f"{dir_count}个目录, {detail}"

        header_text = f"--- {task_type}任务 #{task.task_id}  ({detail}) ---"
        header_iid = f"header_{task.task_id}"
        self.tree.insert("", "end", iid=header_iid, values=(header_text, "", "", "", "", ""),
                         tags=(tag,), open=False)
        self.tree.item(header_iid, tags=(tag,))

        children = self.tree.get_children()
        for idx, child in enumerate(children):
            if child == header_iid and idx > 0:
                self.tree.move(child, "", idx)
                break

        # 先插入所有项并建立映射
        item_node_map: Dict[int, str] = {}  # item.id -> tree item id
        item_name_map: Dict[str, TransferItem] = {}  # filename -> item

        for item in task.items:
            iid = f"item_{item.id}"
            icon = "\U0001F4C1" if item.is_dir else "\U0001F4C4"
            self.tree.insert(header_iid, "end", iid=iid,
                             values=(f"  {icon} {item.filename}", "-", "0%", "", "", "等待中"),
                             tags=(tag,))
            self.item_iids[item.id] = iid
            item_node_map[item.id] = iid
            item_name_map[item.filename] = item

        # 建立目录与子项的关系
        for item in task.items:
            if item.is_dir:
                # 找到属于这个目录的所有子项（通过路径前缀匹配）
                child_items = []
                dir_prefix = item.filename + "/"
                for other_item in task.items:
                    if other_item.id != item.id:
                        if other_item.filename.startswith(dir_prefix):
                            # 检查它是否是直接子项（路径中没有额外的/）
                            sub_path = other_item.filename[len(dir_prefix):]
                            if "/" not in sub_path:
                                child_items.append(other_item.id)
                self.dir_item_map[item.id] = child_items

        self.tree.item(header_iid, open=True)
        self._update_stats()

    def _update_dir_progress(self, task_id: int, dir_item_id: int):
        dir_iid = self.item_iids.get(dir_item_id)
        if not dir_iid or not self.tree.exists(dir_iid):
            return

        task = self.manager.get_task(task_id)
        if not task:
            return

        child_ids = self.dir_item_map.get(dir_item_id, [])
        if not child_ids:
            return

        total_child_items = 0  # 子项总数
        completed_child_items = 0  # 已完成子项
        all_complete = True
        any_running = False
        all_speed = 0.0
        active_count = 0

        for child_id in child_ids:
            child_item = None
            for it in task.items:
                if it.id == child_id:
                    child_item = it
                    break
            if not child_item:
                continue

            total_child_items += 1

            if child_item.is_dir:
                # 子目录，递归处理并更新
                self._update_dir_progress(task_id, child_id)
                
                # 获取子目录的统计
                child_iid = self.item_iids.get(child_id)
                if child_iid and self.tree.exists(child_iid):
                    # 获取子目录的统计信息
                    child_completed, child_total = self._calculate_dir_child_stats(task_id, child_id)
                    completed_child_items += child_completed
                    total_child_items += child_total
                    
                    # 读取子目录的状态
                    child_vals = self.tree.item(child_iid, "values")
                    child_status_text = child_vals[5] if len(child_vals) > 5 else ""
                    if "传输中" in child_status_text:
                        any_running = True
                    
                    # 检查子目录是否完成
                    child_pct_str = child_vals[2] if len(child_vals) > 2 else ""
                    child_pct = float(child_pct_str.strip("%")) if child_pct_str else 0
                    if child_pct < 100:
                        all_complete = False
                    else:
                        completed_child_items += 1
            else:
                # 文件
                if child_item.speed > 0:
                    all_speed += child_item.speed
                    active_count += 1
                
                if child_item.status == "completed" or child_item.status == "failed":
                    completed_child_items += 1
                else:
                    all_complete = False
                
                if child_item.status == "running":
                    any_running = True

        # 更新目录项显示
        dir_vals = list(self.tree.item(dir_iid, "values"))
        
        if total_child_items > 0:
            dir_progress = completed_child_items / total_child_items
            dir_pct = int(dir_progress * 100)
            dir_vals[2] = f"{dir_pct}%"
            dir_vals[1] = f"{completed_child_items}/{total_child_items}"
            if active_count > 0:
                avg_speed = all_speed / active_count
                dir_vals[3] = _format_speed(avg_speed)
        else:
            dir_vals[2] = "100%"
            dir_vals[1] = "-"

        if all_complete:
            dir_vals[5] = "\u2705 完成"
            dir_vals[3] = ""
            dir_vals[4] = ""
        elif any_running:
            dir_vals[5] = "\u2B07 传输中"
        elif completed_child_items > 0:
            dir_vals[5] = "\u2705 完成"
        else:
            dir_vals[5] = "等待中"

        self.tree.item(dir_iid, values=tuple(dir_vals))

    def _calculate_dir_child_stats(self, task_id: int, dir_item_id: int) -> tuple[int, int]:
        """计算一个目录的子项统计：(已完成, 总子项数)"""
        task = self.manager.get_task(task_id)
        if not task:
            return (0, 0)

        child_ids = self.dir_item_map.get(dir_item_id, [])
        total_child = 0
        completed_child = 0

        for child_id in child_ids:
            child_item = None
            for it in task.items:
                if it.id == child_id:
                    child_item = it
                    break
            if not child_item:
                continue

            total_child += 1

            if child_item.is_dir:
                # 递归计算子目录
                child_comp, child_tot = self._calculate_dir_child_stats(task_id, child_id)
                completed_child += child_comp
                total_child += child_tot
                
                # 检查当前子目录项是否完成
                child_iid = self.item_iids.get(child_id)
                if child_iid and self.tree.exists(child_iid):
                    child_vals = self.tree.item(child_iid, "values")
                    child_pct_str = child_vals[2] if len(child_vals) > 2 else ""
                    child_pct = float(child_pct_str.strip("%")) if child_pct_str else 0
                    if child_pct >= 100:
                        completed_child += 1
            else:
                # 文件
                if child_item.status == "completed" or child_item.status == "failed":
                    completed_child += 1

        return (completed_child, total_child)

    def _find_parent_dirs(self, task_id: int, item_id: int) -> List[int]:
        """找出一个项所属的所有父目录（从上到下）"""
        task = self.manager.get_task(task_id)
        if not task:
            return []

        # 找到当前项
        current_item = None
        for it in task.items:
            if it.id == item_id:
                current_item = it
                break
        if not current_item:
            return []

        parent_dirs = []
        for dir_id, child_ids in self.dir_item_map.items():
            if item_id in child_ids:
                parent_dirs.append(dir_id)
                # 递归查找父目录的父目录
                grandparents = self._find_parent_dirs(task_id, dir_id)
                parent_dirs.extend(grandparents)
                break

        return parent_dirs

    def _update_size(self, task_id: int, item_id: int, size: int):
        iid = self.item_iids.get(item_id)
        if iid and self.tree.exists(iid):
            vals = list(self.tree.item(iid, "values"))
            vals[1] = _format_size(size)
            self.tree.item(iid, values=tuple(vals))

    def _update_progress(self, task_id: int, item_id: int, progress: float,
                         speed_str: str, transferred: int, speed_bps: float):
        iid = self.item_iids.get(item_id)
        if iid and self.tree.exists(iid):
            vals = list(self.tree.item(iid, "values"))
            pct = int(progress * 100)
            vals[2] = f"{pct}%"
            if speed_str:
                vals[3] = speed_str
            if transferred > 0:
                task = self.manager.get_task(task_id)
                if task:
                    for it in task.items:
                        if it.id == item_id:
                            vals[1] = f"{_format_size(transferred)}/{_format_size(it.size)}"
                            break
                else:
                    vals[1] = _format_size(transferred)
            if speed_bps > 0 and 0 < progress < 1.0:
                remaining_bytes = 0
                task = self.manager.get_task(task_id)
                if task:
                    for it in task.items:
                        if it.id == item_id:
                            remaining_bytes = it.size - transferred
                            break
                if remaining_bytes > 0:
                    eta_secs = remaining_bytes / speed_bps
                    vals[4] = _format_time(eta_secs)
            self.tree.item(iid, values=tuple(vals))

            # 更新所有父目录的进度
            parent_dirs = self._find_parent_dirs(task_id, item_id)
            for dir_id in parent_dirs:
                self._update_dir_progress(task_id, dir_id)

        self._update_stats()

    def _update_status(self, task_id: int, item_id: int, status: str, error: str):
        iid = self.item_iids.get(item_id)
        if iid and self.tree.exists(iid):
            vals = list(self.tree.item(iid, "values"))

            if status == "pending":
                vals[5] = "等待中"
            elif status == "running":
                vals[5] = "\u2B07 传输中"
            elif status == "completed":
                vals[2] = "100%"
                vals[3] = ""
                vals[4] = ""
                vals[5] = "\u2705 完成"
            elif status == "failed":
                vals[3] = ""
                vals[4] = ""
                err_short = error[:15] if len(error) > 15 else error
                vals[5] = f"\u274C {err_short}"

            self.tree.item(iid, values=tuple(vals))

            # 更新所有父目录的进度
            parent_dirs = self._find_parent_dirs(task_id, item_id)
            for dir_id in parent_dirs:
                self._update_dir_progress(task_id, dir_id)

        self._update_stats()

    def _task_complete(self, task_id: int):
        self._update_stats()

    def _update_stats(self):
        stats = self.manager.get_statistics()
        status_text = (
            f"文件: {stats['total_files']}  目录: {stats['total_dirs']}  |  "
            f"等待: {stats['pending']}  "
            f"传输中: {stats['running']}  "
            f"\u2705完成: {stats['completed']}  "
            f"\u274C失败: {stats['failed']}"
        )
        self.stats_label.config(text=status_text)

        total = stats['total_files'] + stats['total_dirs']
        completed = stats['completed'] + stats['failed']
        if total > 0:
            progress_pct = (completed / total) * 100
            self.total_progress_var.set(progress_pct)
            self.total_pct_label.config(text=f"{progress_pct:.0f}%")
        else:
            self.total_progress_var.set(0)
            self.total_pct_label.config(text="0%")

    def _cancel_all(self):
        if messagebox.askyesno("确认", "确定要取消所有正在进行的传输吗？"):
            self.hide()

    def show(self):
        self.deiconify()
        self.lift()
        self._update_stats()

    def hide(self):
        self.withdraw()

    def destroy(self):
        self.running = False
        super().destroy()


_transfer_manager = None


def get_transfer_manager() -> TransferManager:
    global _transfer_manager
    if _transfer_manager is None:
        _transfer_manager = TransferManager()
    return _transfer_manager
