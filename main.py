# -*- coding: utf-8 -*-
"""
qasas-agent  |  V10 TREND HUNTER
---------------------------------
كل يوم: ترند (Google Trends RSS) -> موضوع جديد غير مكرر -> قصة -> فيديو (صوت فقط، بدون موسيقى)
-> عنوان + وصف + tags -> رفع على يوتيوب (فيديو واحد يوميا) -> تسجيل في history.json

ENV:
    GEMINI_API_KEY   مفتاح Gemini
    TOKEN_B64        ملف token.json الخاص بيوتيوب مشفر base64
    PEXELS_API_KEY   (اختياري) وبدونه تُستخدم خلفية متدرجة
    TTS_VOICE        (اختياري) الافتراضي ar-SA-HamedNeural  (أو ar-SA-ZariyahNeural)

pip install:
    google-generativeai edge-tts gTTS moviepy==1.0.3 pillow numpy requests pytrends
    arabic-reshaper python-bidi google-api-python-client google-auth
apt-get install -y ffmpeg fonts-noto-core fonts-dejavu-core
"""

import os
import re
import sys
import json
import time
import base64
import random
import asyncio
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests
import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# توافق moviepy 1.0.3 مع Pillow >= 10
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import arabic_reshaper
from bidi.algorithm import get_display
from gtts import gTTS
import google.generativeai as genai
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, vfx,
)

# ----------------------------------------------------------------------------
# الإعدادات
# ----------------------------------------------------------------------------
W, H, FPS = 1280, 720, 24
SEG_MIN = 4.0
FONT_SIZE = 58
ZOOM_AMOUNT = 0.06
DIM = 0.55
MAX_SEGMENTS = 30
OUT_VIDEO = "final_video.mp4"
MARKER = ".last_upload"          # يُكتب عند uploadLimitExceeded حتى لا نعيد المحاولة
HISTORY_FILE = "history.json"    # سجل المواضيع والفيديوهات
HISTORY_DAYS = 30
SIMILARITY_LIMIT = 0.5

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TOKEN_B64 = os.environ.get("TOKEN_B64", "").strip()
PEXELS_API_KEY =
