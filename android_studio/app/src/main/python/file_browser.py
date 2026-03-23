import os
from kivy.lang import Builder
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivy.clock import Clock


KV = '''
<FileBrowser>:
    orientation: 'vertical'
    
    MDTopAppBar:
        id: path_bar
        title: "/"
        left_action_items: [["arrow-left", lambda x: root.go_up()]]
        elevation: 2
    
    MDScrollView:
        MDList:
            id: file_list
'''


class FileBrowser(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn_manager = None
        self.current_path = "/"
        Builder.load_string(KV)
    
    def set_connection(self, conn_manager):
        self.conn_manager = conn_manager
        self.current_path = "/"
    
    def load_path(self, path: str):
        if not self.conn_manager or not self.conn_manager.is_connected():
            return
        
        self.current_path = path
        self.ids.path_bar.title = path
        self.ids.file_list.clear_widgets()
        
        Clock.schedule_once(lambda dt: self._load_files_async(), 0)
    
    def _load_files_async(self):
        if not self.conn_manager:
            return
        
        files = self.conn_manager.list_path(self.current_path)
        
        for file_info in files:
            icon = 'folder' if file_info.isDirectory else self._get_file_icon(file_info.filename)
            
            item = OneLineIconListItem(
                text=file_info.filename,
                on_release=lambda x, f=file_info: self._on_item_click(f)
            )
            item.add_widget(IconLeftWidget(icon=icon))
            self.ids.file_list.add_widget(item)
    
    def _get_file_icon(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        
        ext_map = {
            ('.doc', '.docx'): 'file-word',
            ('.xls', '.xlsx'): 'file-excel',
            ('.ppt', '.pptx'): 'file-powerpoint',
            ('.pdf',): 'file-pdf',
            ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'): 'image',
            ('.zip', '.rar', '.7z', '.tar', '.gz'): 'folder-zip',
            ('.mp3', '.wav', '.flac', '.aac', '.ogg'): 'music',
            ('.mp4', '.avi', '.mov', '.wmv', '.mkv'): 'video',
            ('.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h'): 'code-tags',
        }
        
        for extensions, icon_type in ext_map.items():
            if ext in extensions:
                return icon_type
        
        return 'file'
    
    def _on_item_click(self, file_info):
        if file_info.isDirectory:
            new_path = os.path.join(self.current_path, file_info.filename).replace('\\', '/')
            if new_path.startswith('//'):
                new_path = new_path[1:]
            self.load_path(new_path)
        else:
            self._open_file(file_info)
    
    def _open_file(self, file_info):
        pass
    
    def go_up(self):
        if self.current_path != "/":
            parent_path = os.path.dirname(self.current_path)
            if parent_path == "":
                parent_path = "/"
            self.load_path(parent_path)
    
    def refresh(self):
        self.load_path(self.current_path)
