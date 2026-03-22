from django import template
import os

register = template.Library()

IMAGE_EXTS  = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
VIDEO_EXTS  = {'.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv'}
AUDIO_EXTS  = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
PDF_EXTS    = {'.pdf'}

@register.filter
def file_preview_type(filename):
    """Return preview type: 'image' | 'video' | 'audio' | 'pdf' | 'none'."""
    ext = os.path.splitext(str(filename).lower())[1]
    if ext in IMAGE_EXTS:  return 'image'
    if ext in VIDEO_EXTS:  return 'video'
    if ext in AUDIO_EXTS:  return 'audio'
    if ext in PDF_EXTS:    return 'pdf'
    return 'none'

@register.filter
def file_icon(filename):
    """Return an emoji icon for file types that can't be previewed."""
    ext = os.path.splitext(str(filename).lower())[1]
    icons = {
        '.doc': '📝', '.docx': '📝',
        '.xls': '📊', '.xlsx': '📊',
        '.ppt': '📽', '.pptx': '📽',
        '.zip': '🗜', '.rar': '🗜', '.7z': '🗜', '.tar': '🗜', '.gz': '🗜',
        '.txt': '📄',
        '.py':  '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
        '.json': '📋', '.xml': '📋', '.csv': '📋',
        '.exe': '⚙️', '.dmg': '⚙️',
    }
    return icons.get(ext, '📎')
