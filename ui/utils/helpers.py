import os
import sys
import datetime
import re


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/(1024 * 1024):.1f} MB"
    else:
        return f"{size/(1024 * 1024 * 1024):.1f} GB"


def parse_size(size_str: str) -> int:
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


def parse_date(date_str: str) -> float:
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


def get_local_drives():
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


def sort_items(treeview, items, col: str, reverse: bool):
    def get_sort_value(item):
        val, item_id = item
        if col == "Size":
            return parse_size(val)
        elif col == "Modified":
            return parse_date(val)
        elif col == "Type":
            return val.lower() if val else ""
        else:
            natural_key = [int(s) if s.isdigit() else s.lower()
                          for s in re.split(r'(\d+)', val)]
            return natural_key

    dir_items = []
    file_items = []
    for item in items:
        val, item_id = item
        tags = treeview.item(item_id, "tags")
        is_dir = tags and "dir" in tags
        if is_dir:
            dir_items.append(item)
        else:
            file_items.append(item)

    dir_items.sort(key=get_sort_value, reverse=reverse)
    file_items.sort(key=get_sort_value, reverse=reverse)

    sorted_items = dir_items + file_items

    for index, (val, item) in enumerate(sorted_items):
        treeview.move(item, '', index)
