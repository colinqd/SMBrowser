import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
import threading
import queue
import time
import os


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
        self.speed = ""
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

    def update_task_progress(self, task_id: int, item: TransferItem, progress: float, speed: str = ""):
        item.progress = progress
        if speed:
            item.speed = speed
        if self.window and self.window.winfo_exists():
            self.queue.put(('progress', task_id, item.id, progress, speed))

    def update_task_status(self, task_id: int, item: TransferItem, status: str, error: str = ""):
        item.status = status
        if error:
            item.error = error
        if status == "completed" and item.end_time == 0:
            item.end_time = time.time()
        if self.window and self.window.winfo_exists():
            self.queue.put(('status', task_id, item.id, status, error))

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
                self.queue.put(('status', task.task_id, item.id, item.status, item.error))
                if item.progress > 0:
                    self.queue.put(('progress', task.task_id, item.id, item.progress, item.speed))

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
    def __init__(self, parent: tk.Tk, manager: TransferManager):
        super().__init__(parent)
        self.title("文件传输")
        self.geometry("900x600")
        self.minsize(700, 450)
        self.resizable(True, True)
        self.manager = manager
        self.queue = manager.queue
        self.item_widgets: Dict[int, List] = {}
        self.task_frames: Dict[int, ttk.LabelFrame] = {}
        self.running = True

        self._setup_ui()
        self._process_queue()

        self.protocol("WM_DELETE_WINDOW", self.hide)

    def _setup_ui(self):
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill="x")

        self.stats_label = ttk.Label(header_frame, text="准备就绪", font=('Segoe UI', 9))
        self.stats_label.pack(side="left")

        total_progress_frame = ttk.Frame(header_frame)
        total_progress_frame.pack(side="right", fill="x", expand=True, padx=20)
        ttk.Label(total_progress_frame, text="总体进度:").pack(side="left")
        self.total_progress_var = tk.DoubleVar()
        self.total_progress_bar = ttk.Progressbar(
            total_progress_frame, variable=self.total_progress_var, length=300
        )
        self.total_progress_bar.pack(side="left", padx=5)
        self.total_pct_label = ttk.Label(total_progress_frame, text="0%")
        self.total_pct_label.pack(side="left")

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(main_frame, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.content_frame = ttk.Frame(self.canvas)

        self.content_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw", tags="content_frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        footer = ttk.Frame(self, padding="10")
        footer.pack(fill="x")

        self.cancel_btn = ttk.Button(footer, text="取消所有", command=self._cancel_all)
        self.cancel_btn.pack(side="right")
        ttk.Button(footer, text="隐藏窗口", command=self.hide).pack(side="right", padx=5)

        self._update_stats()

    def _process_queue(self):
        if not self.running:
            return
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == 'task_add':
                    self._add_task(msg[1])
                elif msg[0] == 'progress':
                    self._update_progress(msg[1], msg[2], msg[3], msg[4])
                elif msg[0] == 'status':
                    self._update_status(msg[1], msg[2], msg[3], msg[4])
                elif msg[0] == 'task_complete':
                    self._task_complete(msg[1])
        except queue.Empty:
            pass
        self.after(50, self._process_queue)

    def _add_task(self, task: TransferTask):
        if task.task_id in self.task_frames:
            return

        task_label = "上传任务" if task.is_upload else "下载任务"
        dir_count = sum(1 for i in task.items if i.is_dir)
        file_count = sum(1 for i in task.items if not i.is_dir)
        detail = f"{file_count} 个文件"
        if dir_count > 0:
            detail = f"{dir_count} 个目录, {detail}"

        frame = ttk.LabelFrame(
            self.content_frame,
            text=f"{task_label} #{task.task_id}  ({detail})",
            padding="10"
        )
        frame.pack(fill="x", padx=5, pady=5)
        self.task_frames[task.task_id] = frame

        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text="文件名", width=35).pack(side="left")
        ttk.Label(header, text="进度", width=25).pack(side="left")
        ttk.Label(header, text="状态", width=20).pack(side="left")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

        for item in task.items:
            self._create_item_widget(item, frame)

        self._update_stats()

    def _create_item_widget(self, item: TransferItem, parent_frame):
        row_frame = ttk.Frame(parent_frame, padding="3")
        row_frame.pack(fill="x", padx=5, pady=1)

        prefix = "\U0001F4C1" if item.is_dir else "\U0001F4C4"
        filename_label = ttk.Label(row_frame, text=f"{prefix} {item.filename}", width=35, anchor="w")
        filename_label.pack(side="left")

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(row_frame, variable=progress_var, length=180)
        progress_bar.pack(side="left", padx=5)

        pct_label = ttk.Label(row_frame, text="0%", width=5)
        pct_label.pack(side="left")

        status_label = ttk.Label(row_frame, text="等待中", width=20)
        status_label.pack(side="left")

        self.item_widgets[item.id] = [status_label, progress_bar, filename_label, progress_var, pct_label]

    def _update_progress(self, task_id: int, item_id: int, progress: float, speed: str):
        if item_id in self.item_widgets:
            widgets = self.item_widgets[item_id]
            status_label, progress_bar, filename_label, progress_var, pct_label = widgets
            pct = int(progress * 100)
            progress_var.set(pct)
            pct_label.config(text=f"{pct}%")
            if speed:
                status_label.config(text=f"\U0001F4E4 {speed}")
        self._update_stats()

    def _update_status(self, task_id: int, item_id: int, status: str, error: str):
        if item_id in self.item_widgets:
            widgets = self.item_widgets[item_id]
            status_label, progress_bar, filename_label, progress_var, pct_label = widgets

            if status == "pending":
                status_label.config(text="等待中", foreground="")
            elif status == "running":
                status_label.config(text="\U0001F4E4 传输中...", foreground="")
            elif status == "completed":
                status_label.config(text="\u2705 成功", foreground="green")
                progress_var.set(100)
                pct_label.config(text="100%")
            elif status == "failed":
                err_short = error[:20] if len(error) > 20 else error
                status_label.config(text=f"\u274C {err_short}", foreground="red")
        self._update_stats()

    def _task_complete(self, task_id: int):
        self._update_stats()

    def _update_stats(self):
        stats = self.manager.get_statistics()
        status_text = (
            f"文件: {stats['total_files']} | "
            f"目录: {stats['total_dirs']} | "
            f"等待: {stats['pending']} | "
            f"传输中: {stats['running']} | "
            f"\u2705完成: {stats['completed']} | "
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
