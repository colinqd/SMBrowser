import os
import sys
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.scrollview import ScrollView

from connection import SMBConnectionManager
from file_browser import FileBrowser


KV = '''
<MainScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "SMB文件管理器"
            left_action_items: [["menu", lambda x: root.nav_drawer.set_state("open")]]
            right_action_items: [["refresh", lambda x: root.refresh()]]
        
        MDNavigationDrawer:
            id: nav_drawer
            
            MDBoxLayout:
                orientation: 'vertical'
                padding: "8dp"
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
        
        FileBrowser:
            id: file_browser
'''


class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn_manager = SMBConnectionManager()
        self.dialog = None
    
    def on_kv_post(self, base_widget):
        self.load_connections()
    
    def load_connections(self):
        self.ids.connection_list.clear_widgets()
        for conn_name in self.conn_manager.get_saved_connections():
            item = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height='48dp',
                padding='8dp'
            )
            item.add_widget(MDLabel(text=conn_name))
            item.add_widget(MDRaisedButton(
                text='连接',
                on_release=lambda x, name=conn_name: self.connect_to_server(name)
            ))
            self.ids.connection_list.add_widget(item)
    
    def show_connect_dialog(self):
        if not self.dialog:
            self.dialog = MDDialog(
                title="新建连接",
                type="custom",
                content_cls=ConnectDialogContent(),
                buttons=[
                    MDFlatButton(
                        text="取消",
                        on_release=self.close_dialog
                    ),
                    MDFlatButton(
                        text="保存",
                        on_release=self.save_connection
                    ),
                ],
            )
        self.dialog.open()
    
    def close_dialog(self, *args):
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
            if self.conn_manager.connect(conn_data):
                self.ids.nav_drawer.set_state("close")
                self.ids.file_browser.set_connection(self.conn_manager)
                self.ids.file_browser.load_path('/')
    
    def refresh(self):
        self.ids.file_browser.refresh()


class ConnectDialogContent(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = '300dp'
        self.padding = '20dp'
        self.spacing = '10dp'
        
        self.add_widget(MDTextField(
            id='name',
            hint_text="连接名称",
            mode="fill"
        ))
        self.add_widget(MDTextField(
            id='server_ip',
            hint_text="服务器IP",
            mode="fill"
        ))
        self.add_widget(MDTextField(
            id='port',
            hint_text="端口 (默认445)",
            mode="fill"
        ))
        self.add_widget(MDTextField(
            id='username',
            hint_text="用户名",
            mode="fill"
        ))
        self.add_widget(MDTextField(
            id='password',
            hint_text="密码",
            password=True,
            mode="fill"
        ))
        self.add_widget(MDTextField(
            id='share_name',
            hint_text="共享名称",
            mode="fill"
        ))


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
