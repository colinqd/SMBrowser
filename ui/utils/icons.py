import tkinter as tk
from PIL import Image, ImageDraw
from io import BytesIO
import base64


def create_icons():
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

    return {
        'folder': img_to_photo(create_folder_icon(16)),
        'file': img_to_photo(create_file_icon(16)),
        'drive': img_to_photo(create_drive_icon(16)),
        'server': img_to_photo(create_server_icon(16)),
        'share': img_to_photo(create_folder_icon(16))
    }
