import os
import threading
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.recycleview import MDRecycleView
from kivymd.uix.card import MDCard
from kivymd.theming import ThemeManager

from connection import SMBConnectionManager
from file_browser import FileBrowser
from settings import Settings


KV = '''
<MainScreen>:
    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            id: toolbar
            title: "SMB文件管理器"
            left_action_items: [["menu", lambda x: root.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.refresh()]]

        MDNavigationDrawer:
            id: nav_drawer

            MDBoxLayout:
                orientation: 'vertical'
                padding: "16dp"
                spacing: "8dp"

                MDLabel:
                    text: "连接管理"
                    font_style: "H5"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDRaisedButton:
                    text: "新建连接"
                    on_release: root.show_connect_dialog()

                ScrollView:
                    MDList:
                        id: connection_list

        MDBoxLayout:
            orientation: 'vertical'
            padding: "8dp"
            spacing: "8dp"

            MDBoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: "48dp"
                spacing: "8dp"

                MDIconButton:
                    icon: "arrow-up"
                    on_release: root.go_up()

                MDTextField:
                    id: path_input
                    hint_text: "当前路径"
                    text: "/"
                    on_text_validate: root.navigate_to_path(self.text)

                MDIconButton:
                    icon: "arrow-right"
                    on_release: root.navigate_to_path(root.ids.path_input.text)

            MDLabel:
                id: status_label
                text: "未连接"
                size_hint_y: None
                height: "24dp"

            MDRecycleView:
                id: file_list
                viewclass: 'OneLineListItem'
                on_kv_post: root.populate_file_list()

                RecycleBoxLayout:
                    orientation: 'vertical'
                    spacing: "4dp"
                    padding: "8dp"
'''


class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn_manager = SMBConnectionManager()
        self.file_browser = FileBrowser()
        self.file_browser.set_connection(self.conn_manager)
        self.dialog = None

    def on_kv_post(self, base_widget):
        self.load_connections()

    def load_connections(self):
        self.ids.connection_list.clear_widgets()
        for conn_name in self.conn_manager.get_saved_connections():
            item = OneLineListItem(
                text=conn_name,
                on_release=lambda x, name=conn_name: self.connect_to_server(name)
            )
            self.ids.connection_list.add_widget(item)

    def show_connect_dialog(self):
        if not self.dialog:
            content = ConnectDialogContent()
            self.dialog = MDDialog(
                title="新建连接",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(text="取消", on_release=self.close_dialog),
                    MDFlatButton(text="保存", on_release=self.save_connection),
                ],
            )
        self.dialog.open()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()

    def save_connection(self, *args):
        content = self.dialog.content_cls
        conn_data = {
            'name': content.ids.name.text,
            'server_ip': content.ids.server_ip.text,
            'port': content.ids.port.text,
            'username': content.ids.username.text,
            'password': content.ids.password.text,
            'share_name': content.ids.share_name.text,
        }
        self.conn_manager.save_connection(conn_data)
        self.close_dialog()
        self.load_connections()

    def connect_to_server(self, conn_name):
        conn_data = self.conn_manager.get_connection(conn_name)
        if conn_data:
            def do_connect():
                success, msg = self.conn_manager.connect(
                    server_ip=conn_data.get('server_ip', ''),
                    port=conn_data.get('port', '445'),
                    username=conn_data.get('username', ''),
                    password=conn_data.get('password', ''),
                    share_name=conn_data.get('share_name', ''),
                )
                self.ids.status_label.text = msg
                if success:
                    self.ids.nav_drawer.set_state("close")
                    self.file_browser.load_path('/')
                    self.ids.path_input.text = "/"
                    self.populate_file_list()

            threading.Thread(target=do_connect, daemon=True).start()

    def refresh(self):
        self.file_browser.refresh()
        self.populate_file_list()

    def navigate_to_path(self, path):
        self.file_browser.load_path(path)
        self.ids.path_input.text = self.file_browser.current_path
        self.populate_file_list()

    def go_up(self):
        self.file_browser.navigate_up()
        self.ids.path_input.text = self.file_browser.current_path
        self.populate_file_list()

    def populate_file_list(self):
        self.ids.file_list.data = []
        files = self.file_browser.get_current_files()
        for f in files:
            is_dir = f.isDirectory
            icon = "folder" if is_dir else "file"
            text = f"{f.filename}"
            if not is_dir:
                text += f" ({f.file_size} bytes)"
            self.ids.file_list.data.append({
                'text': text,
                'on_release': lambda x, item=f: self.on_file_click(item)
            })

    def on_file_click(self, item):
        if item.isDirectory:
            path = self.file_browser.current_path
            if path == "/":
                new_path = "/" + item.filename
            else:
                new_path = path + "/" + item.filename
            self.navigate_to_path(new_path)


class ConnectDialogContent(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = '400dp'
        self.padding = '16dp'
        self.spacing = '12dp'

        self.ids.name = MDTextField(hint_text="连接名称", mode="fill")
        self.ids.server_ip = MDTextField(hint_text="服务器IP", mode="fill")
        self.ids.port = MDTextField(hint_text="端口 (默认445)", mode="fill", text="445")
        self.ids.username = MDTextField(hint_text="用户名", mode="fill")
        self.ids.password = MDTextField(hint_text="密码", mode="fill", password=True)
        self.ids.share_name = MDTextField(hint_text="共享名称", mode="fill")

        for widget in [
            self.ids.name,
            self.ids.server_ip,
            self.ids.port,
            self.ids.username,
            self.ids.password,
            self.ids.share_name
        ]:
            self.add_widget(widget)


class SMBClientApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        Builder.load_string(KV)
        return MainScreen()


def run_app():
    app = SMBClientApp()
    app.run()


if __name__ == '__main__':
    run_app()
