import tkinter as tk
from PIL import Image, ImageDraw
from io import BytesIO
import base64
import os


def create_icons():
    def create_folder_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        folder_color = '#FFD700'
        darker_color = '#DAA520'

        draw.rectangle([2, 5, size-2, size-2], fill=folder_color, outline=darker_color)
        draw.rectangle([2, 3, size-6, 6], fill=darker_color, outline=darker_color)

        return img

    def create_file_icon(size=16, color='#FFFFFF', accent_color='#808080'):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        paper_color = color
        line_color = accent_color
        corner_color = '#E0E0E0'

        draw.rectangle([3, 1, size-4, size-2], fill=paper_color, outline=line_color)
        draw.polygon([size-7, 1, size-4, 1, size-4, 5, size-7, 5], fill=corner_color, outline=line_color)
        draw.line([size-7, 1, size-4, 4], fill=line_color)

        draw.line([6, 7, size-7, 7], fill=line_color)
        draw.line([6, 10, size-7, 10], fill=line_color)
        draw.line([6, 13, size-10, 13], fill=line_color)

        return img

    def create_doc_icon(size=16):
        return create_file_icon(size, '#E8F0FE', '#2E75B5')

    def create_xls_icon(size=16):
        return create_file_icon(size, '#E8F5E9', '#217346')

    def create_ppt_icon(size=16):
        return create_file_icon(size, '#FCE4EC', '#D24726')

    def create_pdf_icon(size=16):
        return create_file_icon(size, '#FFE0E0', '#C00000')

    def create_image_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_color = '#E3F2FD'
        outline_color = '#1976D2'

        draw.rectangle([3, 2, size-3, size-2], fill=bg_color, outline=outline_color)
        draw.rectangle([5, 4, size-5, size-4], fill='#FFFFFF', outline=outline_color)
        draw.rectangle([6, 5, 9, 8], fill=outline_color)
        draw.line([8, 6, size-7, size-6], fill=outline_color, width=1)
        draw.rectangle([size-10, size-9, size-6, size-5], fill='#4CAF50', outline='#2E7D32')

        return img

    def create_zip_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_color = '#FFF8E1'
        outline_color = '#F57C00'

        draw.rectangle([3, 2, size-3, size-2], fill=bg_color, outline=outline_color)
        draw.rectangle([3, 2, 9, size-2], fill='#FFE082', outline=outline_color)

        return img

    def create_audio_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_color = '#F3E5F5'
        outline_color = '#7B1FA2'

        draw.rectangle([4, 2, size-4, size-2], fill=bg_color, outline=outline_color)
        draw.rectangle([5, 4, 8, size-4], fill=outline_color)
        draw.rectangle([9, 6, 12, 9], fill=outline_color)
        draw.rectangle([9, 10, 12, 13], fill=outline_color)

        return img

    def create_video_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_color = '#ECEFF1'
        outline_color = '#455A64'

        draw.rectangle([3, 3, size-3, size-3], fill=bg_color, outline=outline_color)
        draw.polygon([6, 5, 11, 8, 6, 11], fill=outline_color)

        return img

    def create_code_icon(size=16):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_color = '#E0F7FA'
        outline_color = '#0097A7'

        draw.rectangle([3, 1, size-3, size-2], fill=bg_color, outline=outline_color)
        draw.line([5, 4, 8, 7], fill=outline_color)
        draw.line([5, 7, 8, 4], fill=outline_color)

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
        return tk.PhotoImage(data=base64.b64encode(data).decode('ascii'))

    icons = {
        'folder': img_to_photo(create_folder_icon(16)),
        'file': img_to_photo(create_file_icon(16)),
        'drive': img_to_photo(create_drive_icon(16)),
        'server': img_to_photo(create_server_icon(16)),
        'share': img_to_photo(create_folder_icon(16)),
        'doc': img_to_photo(create_doc_icon(16)),
        'xls': img_to_photo(create_xls_icon(16)),
        'ppt': img_to_photo(create_ppt_icon(16)),
        'pdf': img_to_photo(create_pdf_icon(16)),
        'image': img_to_photo(create_image_icon(16)),
        'zip': img_to_photo(create_zip_icon(16)),
        'audio': img_to_photo(create_audio_icon(16)),
        'video': img_to_photo(create_video_icon(16)),
        'code': img_to_photo(create_code_icon(16))
    }

    return icons


def get_file_icon(icons, filename: str):
    ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''
    
    ext_map = {
        ('.doc', '.docx'): 'doc',
        ('.xls', '.xlsx'): 'xls',
        ('.ppt', '.pptx'): 'ppt',
        ('.pdf',): 'pdf',
        ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'): 'image',
        ('.zip', '.rar', '.7z', '.tar', '.gz'): 'zip',
        ('.mp3', '.wav', '.flac', '.aac', '.ogg'): 'audio',
        ('.mp4', '.avi', '.mov', '.wmv', '.mkv'): 'video',
        ('.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.ts', '.json', '.xml', '.yaml', '.yml'): 'code'
    }

    for extensions, icon_type in ext_map.items():
        if ext in extensions:
            return icons[icon_type]

    return icons['file']
