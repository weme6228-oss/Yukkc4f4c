# -*- coding: utf-8 -*-
"""
دستیار هوشمند - ربات جامع فال، تاروت، سرگرمی و مدیریت گروه تلگرام - نسخه ۷۱ (Final Hardening، قفل بازی‌ها، پنل مالک، پایداری و بهینه‌سازی نهایی)
====================================================================
تغییرات نسبت به نسخه ۶:
  ✅ تغییر نام و هویت بصری: از «فال و سرگرمی» به «دستیار هوشمند» — منوها،
     پیام خوش‌آمد و متن‌های راهنما به‌روزرسانی شد تا یه دستیار حرفه‌ای و
     یکپارچه حس بشه، نه یه ربات ساده‌ی فال.
  ✅ منبع واقعی و آنلاین برای تاروت: هر بار تلاش می‌کنه یه کارت واقعی از
     سایت رایگان tarotapi.dev بگیره (بدون نیاز به کلید API)، و اگه در دسترس
     نبود، خودکار و بی‌صدا میره سراغ موتور کاملاً آفلاینِ داخلی خودش.
  ✅ تنوع فال/تاروت چند برابر شد: به‌جای چند جمله‌ی ثابت، یه موتور ترکیبی
     (opener + حوزه‌ی زندگی + توصیه + رنگ/عدد شانس) هزاران حالت متفاوت
     می‌سازه، و هر ۵۶ کارت کوچک تاروت هم معنی مستقل و معنادار خودشون رو دارن
     (نه یه جمله‌ی تکراری برای کل یه دسته).
  ✅ «هوشمندی» بدون سرویس پولی: چون از Gemini/OpenRouter استفاده نمی‌کنیم،
     یه موتور پاسخ‌گویی قانون‌محورِ آفلاین اضافه شد که وقتی کسی مستقیم با
     ربات حرف بزنه (اسمشو بیاره یا ریپلاش کنه) جواب طبیعی و مرتبط می‌ده.
  ✅ حذف قابلیت‌های غیرفعال/گمراه‌کننده: دستور /translate که دیگه کار
     نمی‌کرد (چون به سرویس هوش مصنوعی نیاز داشت) کامل حذف شد.
  ✅ رفع باگ چند تابعِ تکراری (generate_fal دوبار تعریف شده بود) و پاکسازی
     کدهای مرده‌ی مرتبط با سرویس‌های هوش مصنوعیِ حذف‌شده.

نصب پیش‌نیازها:
    pip install "python-telegram-bot[job-queue]" requests

قبل از اجرا، این متغیر محیطی رو تنظیم کن (توکن رو هاردکد نکن!):
    export BOT_TOKEN="توکن ربات از BotFather"

اجرا:
    python bot_v71.py
"""

# v6: ارتقای مدیریت گروه بدون حذف قابلیت‌های نسخه قبل؛ Reminder و متن‌های آن عمداً حفظ شده‌اند.

import os
import re
import html
import json
import time
import random
import asyncio
import logging
import unicodedata
import traceback
import tempfile
import secrets
import io
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta
from collections import defaultdict, deque

import requests

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest, TelegramError, Forbidden

# ============================================================
# تنظیمات اصلی — از متغیرهای محیطی خونده می‌شه، هرگز داخل کد ننویس
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BOT_VERSION = "71.0.0"
BOT_USERNAME = ""  # در startup از Telegram گرفته می‌شود؛ برای deep-link بدون تأخیر کلیک

DATA_DIR = Path(__file__).parent
BAD_WORDS_FILE = DATA_DIR / "bad_words.json"
# فضای ذخیره‌سازی جداگانه‌ی روی سرور، مخصوص کلماتی که ادمین‌ها از توی خودِ ربات
# (با دکمه‌ی شیشه‌ای پنل مدیریت) اضافه می‌کنن. این فایل کاملاً جدا از لیست پیش‌فرضه
# تا هیچ‌وقت با آپدیت لیست پیش‌فرض قاطی/بازنویسی نشه.
CUSTOM_BAD_WORDS_FILE = DATA_DIR / "bad_words_custom.json"
WARN_FILE = DATA_DIR / "warns.json"
# فضای ذخیره‌سازی وضعیت یادآور زمان‌بندی‌شده (فعال/غیرفعال) به ازای هر گروه
REMINDER_FILE = DATA_DIR / "reminder_state.json"
# پروفایل‌های رفتاری کاربر؛ فقط تنظیمات غیرحساس مثل لحن و سبک پاسخ نگه‌داری می‌شود.
USER_PROFILES_FILE = DATA_DIR / "user_profiles.json"
# رسانه‌های بازی: URLها فقط برای اولین ارسال/در صورت نبودن file_id هستند.
# بعد از ارسال موفق، file_id تلگرام ذخیره می‌شود تا دفعات بعد از همان فایل استفاده شود.
GAME_MEDIA_CACHE_FILE = DATA_DIR / "game_media_cache.json"
GAME_MEDIA_RESOURCE_STATE_FILE = DATA_DIR / "game_media_resource_state.json"
GAME_MEDIA = {
    # منابع عمداً محدود، مرتبط با خود بازی و از صفحات رسمی منبع انتخاب شده‌اند.
    # Pixabay: Free for use under Pixabay Content License.
    # Wikimedia Commons: CC0/Public Domain برای فایل‌های زیر.
    "werewolf": {
        "lobby": [
            "https://pixabay.com/gifs/wolf-night-art-mask-silhouette-3489/",
            "https://pixabay.com/gifs/wolf-wolf-man-werewolf-5945/",
        ],
        "night": [
            "https://pixabay.com/gifs/wolf-wolf-man-werewolf-5945/",
            "https://pixabay.com/gifs/wolf-night-art-mask-silhouette-3489/",
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Animated_moon.gif",
        ],
        "morning": [
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Animated_moon.gif",
            "https://pixabay.com/gifs/wolf-night-art-mask-silhouette-3489/",
        ],
        "wolf": [
            "https://pixabay.com/gifs/wolf-wolf-man-werewolf-5945/",
            "https://pixabay.com/gifs/wolf-night-art-mask-silhouette-3489/",
        ],
        "win": [
            "https://pixabay.com/gifs/wolf-night-art-mask-silhouette-3489/",
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Animated_moon.gif",
        ],
    },
    "uno": {
        "start": [
            "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
        ],
        "deal": [
            "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
        ],
        "win": [
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
            "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
        ],
        "uno": [
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
            "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
        ],
        "special": [
            "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
            "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
        ],
    },
}


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_http_session = requests.Session()
_http_session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; FalBot/1.0)"})

PRICE_CACHE = {"data": None, "time": None}
CACHE_SECONDS = 90

FLOOD_WINDOW = 10
FLOOD_LIMIT = 5
user_message_times = defaultdict(lambda: deque(maxlen=FLOOD_LIMIT))

# قفل ساده‌ی نوشتن فایل، تا اگه دو تا کاربر همزمان کلمه اضافه کردن، فایل خراب/overwrite نشه
_file_write_lock = asyncio.Lock()

# ============================================================
# لیست کلمات نامناسب (پیش‌فرض)
# ============================================================
DEFAULT_BAD_WORDS_FA = [
    "کصکش", "کصکشش", "کیری", "کیر", "جنده", "کونی", "کون",
    "لاشی", "عوضی", "حرومزاده", "مادرجنده", "خارکسه", "گاییدم",
    "کسکش", "ننتو", "زنیکه", "کثافت", "جاکش", "عنتر",
    "کصکش", "کسکش", "گائیدم", "گاییدنت", "بگا", "بگایی",
    "خایه", "تخم سگ", "حروم‌زاده", "مادرقحبه", "قحبه", "منگل",
    "عقب‌مونده", "احمق جان", "کره خر", "خر کثیف", "آشغال عوضی",
    "بی‌ناموس", "بی ناموس", "ناموس نداری", "پدرسگ", "سگ پدر",
    "کیرم", "کیرتو", "کونده", "کونی خان", "خایمال", "چاقال",
    "بی‌شرف", "هرزه", "فاحشه", "دیوث", "قرمساق", "لجن", "لاشخور",
]
DEFAULT_BAD_WORDS_EN = [
    "fuck", "fucking", "fucker", "fck", "shit", "bullshit", "bitch",
    "asshole", "bastard", "cunt", "dick", "dickhead", "pussy", "whore",
    "slut", "motherfucker", "retard", "faggot", "nigger", "cock",
    "wanker", "twat", "douchebag", "piece of shit", "jackass",
]

LEET_MAP = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}


def load_json_safe(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"خطا در خواندن {path}: {e}")
    return default


def save_json_safe(path: Path, data):
    """ذخیره‌ی امن JSON؛ ابتدا در فایل موقت می‌نویسد و بعد اتمیک جایگزین می‌کند.
    این کار جلوی خراب شدن فایل‌های تنظیمات در صورت قطع ناگهانی پردازش را می‌گیرد.
    رابط قبلی تابع حفظ شده تا هیچ قابلیت فعلی تغییر نکند.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception as e:
        logger.warning(f"خطا در ذخیره {path}: {e}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


# ============================================================
# Gemini AI — ماژول کاملاً مستقل (v69)
# کلید هرگز داخل سورس ذخیره نمی‌شود؛ فقط از Environment خوانده می‌شود.
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
GEMINI_API_BASE = os.environ.get(
    "GEMINI_API_BASE",
    "https://generativelanguage.googleapis.com/v1beta",
).rstrip("/")
GEMINI_TIMEOUT = max(10, int(os.environ.get("GEMINI_TIMEOUT", "45") or 45))
GEMINI_MAX_OUTPUT_TOKENS = max(128, int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "1200") or 1200))
GEMINI_STATE_FILE = DATA_DIR / "gemini_state.json"
GEMINI_STATE = load_json_safe(GEMINI_STATE_FILE, {})
GEMINI_CHAT_LOCKS = {}
GEMINI_HISTORY = {}
GEMINI_HISTORY_MAX = 8
GEMINI_HISTORY_TTL = 30 * 60
GEMINI_IDLE_TIMEOUT = 120  # اگر ۲ دقیقه هیچ سؤال Gemini دریافت نشود، خودکار خاموش می‌شود.
GEMINI_IDLE_STATE = {}  # chat_id -> آخرین زمان دریافت سؤال
GEMINI_MODEL_FALLBACKS = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)
GEMINI_MODEL_CACHE_TTL = 10 * 60
GEMINI_MODEL_CACHE = []
GEMINI_MODEL_CACHE_AT = 0.0
GEMINI_HEALTH = {}  # model -> {ok, checked_at, failures}; فقط برای انتخاب مدل‌های تست‌شده
GEMINI_HEALTH_TTL = 15 * 60
GEMINI_PANEL_MESSAGES = {}  # chat_id -> message_id; فقط برای به‌روزرسانی پنل هنگام auto-off


def save_gemini_state():
    save_json_safe(GEMINI_STATE_FILE, GEMINI_STATE)


def gemini_enabled(chat_id):
    return bool(GEMINI_STATE.get(str(chat_id), False))


def set_gemini_enabled(chat_id, enabled):
    key = str(chat_id)
    GEMINI_STATE[key] = bool(enabled)
    if enabled:
        GEMINI_IDLE_STATE[key] = time.time()
    else:
        GEMINI_IDLE_STATE.pop(key, None)
        GEMINI_HISTORY.pop(key, None)
    save_gemini_state()


def gemini_touch_question(chat_id):
    """فقط با دریافت یک سؤال واقعی، تایمر ۲ دقیقه‌ای Gemini را تازه می‌کند."""
    if gemini_enabled(chat_id):
        GEMINI_IDLE_STATE[str(chat_id)] = time.time()


def gemini_disable(chat_id):
    """خاموش‌سازی کامل Gemini برای یک چت؛ هیچ درخواست بعدی مجاز نیست."""
    set_gemini_enabled(chat_id, False)


async def gemini_idle_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """بعد از ۲ دقیقه بی‌سؤالی، Gemini را خودکار خاموش می‌کند و پنل باز را هم به‌روز می‌کند."""
    now = time.time()
    changed = False
    for key, enabled in list(GEMINI_STATE.items()):
        if not enabled:
            GEMINI_IDLE_STATE.pop(key, None)
            continue
        last = GEMINI_IDLE_STATE.get(key)
        if last is None:
            # حالت‌های قدیمی که قبل از اجرای v70 ذخیره شده‌اند، از همین لحظه شمارش می‌شوند.
            GEMINI_IDLE_STATE[key] = now
            continue
        if now - last >= GEMINI_IDLE_TIMEOUT:
            GEMINI_STATE[key] = False
            GEMINI_IDLE_STATE.pop(key, None)
            GEMINI_HISTORY.pop(key, None)
            changed = True
            logger.info("Gemini auto-disabled after %ss of inactivity for chat %s", GEMINI_IDLE_TIMEOUT, key)
            panel_message_id = GEMINI_PANEL_MESSAGES.pop(key, None)
            if panel_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=int(key),
                        message_id=int(panel_message_id),
                        text=gemini_control_text(int(key)),
                        parse_mode="HTML",
                        reply_markup=gemini_control_keyboard(int(key)),
                    )
                except Exception as exc:
                    # حذف شدن پیام پنل یا بسته شدن چت نباید جاب زمان‌بندی را متوقف کند.
                    logger.info("Gemini panel refresh skipped for chat %s: %s", key, exc)
    if changed:
        save_gemini_state()


def gemini_control_keyboard(chat_id):
    if gemini_enabled(chat_id):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Gemini روشن است — خاموش کردن", callback_data="gemini_off")],
            [InlineKeyboardButton("⬅️ منوی اصلی", callback_data="back_main")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ روشن کردن Gemini", callback_data="gemini_on")],
        [InlineKeyboardButton("⬅️ منوی اصلی", callback_data="back_main")],
    ])


def gemini_control_text(chat_id):
    if gemini_enabled(chat_id):
        return (
            "✨ <b>Gemini AI</b>\n\n"
            "وضعیت: 🟢 <b>روشن</b>\n\n"
            "Gemini فقط به سؤال‌هایی که بعد از روشن شدن ارسال می‌شوند پاسخ می‌دهد؛ پیام‌های عادی، بازی‌ها، "
            "دکمه‌ها، دستورات و مدیریت گروه مسیر مستقل خودشان را دارند.\n\n"
            "⏱️ اگر تا ۲ دقیقه هیچ سؤال جدیدی پرسیده نشود، Gemini خودکار خاموش می‌شود."
        )
    return (
        "✨ <b>Gemini AI</b>\n\n"
        "وضعیت: 🔴 <b>خاموش</b>\n\n"
        "در این حالت هیچ درخواست Gemini ارسال نمی‌شود و این ماژول هیچ اثری روی بخش‌های دیگر ربات ندارد."
    )


def _gemini_extract_text(payload):
    try:
        candidates = payload.get("candidates") or []
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        chunks = []
        for part in parts:
            if isinstance(part, dict) and part.get("text"):
                chunks.append(str(part["text"]))
        text = "\n".join(chunks).strip()
        if text:
            return text
    except Exception:
        pass
    return ""


def _gemini_error_message(status, body):
    body_text = str(body or "")
    low = body_text.lower()
    if status == 400:
        return "❌ Gemini درخواست را نپذیرفت (400). معمولاً مدل/ساختار درخواست یا تنظیمات API مشکل دارد."
    if status == 401:
        return "🔐 Gemini کلید API را معتبر تشخیص نداد (401). کلید Environment را بررسی کن."
    if status == 402:
        return "💳 Gemini برای این درخواست وضعیت 402 برگرداند؛ وضعیت Billing/Quota پروژه را در Google AI Studio بررسی کن."
    if status == 403:
        if "leaked" in low or "reported as leaked" in low:
            return "🔐 این کلید توسط Google به‌عنوان کلید افشاشده/لو رفته شناسایی شده؛ باید یک کلید جدید بسازی."
        return "⛔ Gemini دسترسی را رد کرد (403). محدودیت کلید، مجوز API، منطقه یا وضعیت پروژه را بررسی کن."
    if status == 404:
        return "🔎 مدل Gemini پیدا نشد (404). نام مدل تنظیم‌شده معتبر نیست یا endpoint با آن مدل سازگار نیست."
    if status == 429:
        return "⏳ سهمیه یا نرخ درخواست Gemini پر شده (429). چند لحظه بعد دوباره امتحان کن یا وضعیت Quota را بررسی کن."
    if status in (500, 502, 503, 504):
        return f"🌐 سرویس Gemini موقتاً خطا داد ({status}). بعداً دوباره امتحان کن."
    return f"⚠️ Gemini خطای HTTP {status} برگرداند."


async def _gemini_discover_models(force=False):
    """مدل‌های متنیِ واقعاً قابل استفاده را از خود API می‌گیرد."""
    global GEMINI_MODEL_CACHE, GEMINI_MODEL_CACHE_AT
    now = time.time()
    if not force and GEMINI_MODEL_CACHE and now - GEMINI_MODEL_CACHE_AT < GEMINI_MODEL_CACHE_TTL:
        return list(GEMINI_MODEL_CACHE)
    if not GEMINI_API_KEY:
        return []
    try:
        response = await asyncio.to_thread(
            requests.get,
            f"{GEMINI_API_BASE}/models",
            headers={"x-goog-api-key": GEMINI_API_KEY},
            params={"pageSize": 100},
            timeout=min(GEMINI_TIMEOUT, 20),
        )
        if not response.ok:
            logger.warning("Gemini models.list failed with HTTP %s", response.status_code)
            return []
        listing = response.json()
        names = []
        for item in listing.get("models", []):
            name = str(item.get("name", ""))
            methods = item.get("supportedGenerationMethods") or []
            clean = name.split("/", 1)[1] if name.startswith("models/") else name
            # فقط مدل‌هایی که generateContent دارند و برای متن عمومی مناسب‌اند.
            if clean and "generateContent" in methods and not any(
                marker in clean.lower() for marker in ("-image", "-tts", "-live", "transcribe", "embedding", "robotics")
            ):
                names.append(clean)
        GEMINI_MODEL_CACHE = sorted(set(names))
        GEMINI_MODEL_CACHE_AT = now
        return list(GEMINI_MODEL_CACHE)
    except Exception as exc:
        logger.info("Gemini model discovery failed: %s", exc)
        return []


def _gemini_model_order(available):
    """مدل‌ها را بر اساس ترجیح کاربر + مدل‌های پایدار موجود مرتب می‌کند."""
    preferred = []
    if GEMINI_MODEL:
        preferred.append(GEMINI_MODEL)
    preferred.extend(GEMINI_MODEL_FALLBACKS)
    # stable text models فعلی Google؛ previewها فقط در صورت نبود مدل پایدار قابل استفاده می‌شوند.
    stable = [
        "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
        "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
    ]
    preferred.extend(stable)
    available_set = set(available or [])
    if available_set:
        preferred.extend(sorted(available_set))
    result = []
    for model in preferred:
        if model in available_set or not available_set:
            if model not in result:
                result.append(model)
    return result


async def _gemini_generate_once(model, payload, headers):
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    return await asyncio.to_thread(
        requests.post, url, headers=headers, json=payload, timeout=GEMINI_TIMEOUT
    )


async def gemini_generate(prompt, chat_id=None, user_name="دوست"):
    if not GEMINI_API_KEY:
        return False, "🔑 کلید Gemini روی سرور تنظیم نشده است. متغیر GEMINI_API_KEY را تنظیم کن."
    prompt = str(prompt or "").strip()
    if not prompt:
        return False, "پیام خالی است."

    key = str(chat_id) if chat_id is not None else "global"
    lock = GEMINI_CHAT_LOCKS.setdefault(key, asyncio.Lock())
    if lock.locked():
        return False, "⏳ یک درخواست Gemini برای این گفتگو هنوز در حال پردازش است؛ کمی صبر کن."

    async with lock:
        now = time.time()
        history = GEMINI_HISTORY.setdefault(key, [])
        history[:] = [x for x in history if now - x.get("ts", 0) <= GEMINI_HISTORY_TTL][-GEMINI_HISTORY_MAX:]
        contents = []
        for item in history:
            role = item.get("role")
            text = str(item.get("text") or "").strip()
            if role in ("user", "model") and text:
                contents.append({"role": role, "parts": [{"text": text}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS,
            },
        }
        headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}

        available = await _gemini_discover_models()
        models = _gemini_model_order(available)
        if not models:
            models = list(dict.fromkeys([GEMINI_MODEL, *GEMINI_MODEL_FALLBACKS]))

        # مدل‌هایی که قبلاً در همین بازه شکست خورده‌اند اولویت پایین‌تری دارند.
        now_health = time.time()
        healthy = [m for m in models if GEMINI_HEALTH.get(m, {}).get("ok") and now_health - GEMINI_HEALTH[m].get("checked_at", 0) < GEMINI_HEALTH_TTL]
        unknown = [m for m in models if m not in healthy and not (GEMINI_HEALTH.get(m, {}).get("failures", 0) >= 2 and now_health - GEMINI_HEALTH[m].get("checked_at", 0) < GEMINI_HEALTH_TTL)]
        models = healthy + unknown
        if not models:
            models = list(dict.fromkeys([GEMINI_MODEL, *GEMINI_MODEL_FALLBACKS]))

        last_error = None
        for model in models:
            try:
                response = await _gemini_generate_once(model, payload, headers)
                status = response.status_code
                if status >= 400:
                    last_error = _gemini_error_message(status, response.text)
                    info = GEMINI_HEALTH.setdefault(model, {"failures": 0})
                    info["checked_at"] = time.time()
                    info["ok"] = False
                    info["failures"] = int(info.get("failures", 0)) + 1
                    # 401/403/429 معمولاً مشکل سراسری کلید/سهمیه هستند؛ مدل دیگری آن را حل نمی‌کند.
                    if status in (401, 403, 429):
                        return False, last_error
                    # 400/404/5xx: مدل بعدی را واقعاً امتحان می‌کنیم.
                    if status in (400, 404, 500, 502, 503, 504):
                        if status == 404:
                            await _gemini_discover_models(force=True)
                        continue
                    return False, last_error

                try:
                    data = response.json()
                except Exception:
                    last_error = "⚠️ پاسخ Gemini JSON معتبر نبود."
                    continue
                answer = _gemini_extract_text(data)
                if not answer:
                    last_error = "⚠️ Gemini پاسخ متنی خالی برگرداند."
                    info = GEMINI_HEALTH.setdefault(model, {"failures": 0})
                    info.update({"checked_at": time.time(), "ok": False, "failures": int(info.get("failures", 0)) + 1})
                    continue

                # این درخواست واقعی، سلامت مدل را هم تأیید کرده است.
                GEMINI_HEALTH[model] = {"checked_at": time.time(), "ok": True, "failures": 0}
                history.append({"ts": now, "role": "user", "text": prompt})
                history.append({"ts": time.time(), "role": "model", "text": answer})
                del history[:-GEMINI_HISTORY_MAX]
                return True, answer
            except requests.RequestException as exc:
                logger.warning("Gemini network error on %s: %s", model, exc)
                info = GEMINI_HEALTH.setdefault(model, {"failures": 0})
                info.update({"checked_at": time.time(), "ok": False, "failures": int(info.get("failures", 0)) + 1})
                last_error = "🌐 اتصال به Gemini برقرار نشد؛ DNS/اتصال سرور یا تنظیمات Proxy را بررسی کن."
                # مدل دیگر از همان API ممکن است قابل دسترسی باشد، پس ادامه می‌دهیم.
                continue
            except Exception as exc:
                logger.exception("Gemini unexpected error on %s: %s", model, exc)
                last_error = "⚠️ خطای داخلی هنگام ارتباط با Gemini رخ داد."
                continue
        return False, last_error or "⚠️ هیچ مدل سالم و قابل استفاده‌ای از Gemini پیدا نشد."


def gemini_blocked_by_game(chat):
    """Gemini نباید وسط state machine بازی‌های گروهی وارد مسیر پیام شود."""
    if not chat or getattr(chat, "type", None) == "private":
        return False
    try:
        busy, _ = group_game_is_busy(chat.id)
        return bool(busy)
    except Exception:
        # اگر وضعیت بازی قابل خواندن نبود، به‌جای شکستن پیام‌رسانی، Gemini را وارد مسیر نمی‌کنیم.
        return True


def gemini_should_handle(text, is_reply_to_bot=False):
    """فقط سؤال/درخواست واقعی را به Gemini می‌فرستد؛ پیام عادی نباید فعالش کند."""
    norm = _smart_normalize(text)
    if not norm:
        return False
    if "؟" in text or "?" in text:
        return True
    if _smart_is_question_or_request(text):
        return True
    # خطاب به Gemini به‌تنهایی کافی نیست؛ باید همراه سؤال/درخواست باشد.
    question_starts = ("چرا", "چطور", "چگونه", "چی", "چه", "کجا", "کی", "آیا", "میشه", "میتونی", "به نظرت", "کمک")
    return norm.startswith(question_starts)


async def gemini_answer_message(update, context):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not message.text or not chat or not user or user.is_bot:
        return False
    if str(message.text).lstrip().startswith("/"):
        return False
    if not gemini_enabled(chat.id):
        return False
    if gemini_blocked_by_game(chat):
        return False
        return False
    is_reply_to_bot = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )
    if not gemini_should_handle(message.text, is_reply_to_bot):
        return False
    # فقط سؤال واقعی/ریپلای مستقیم وارد Gemini می‌شود؛ پیام‌های معمولی هیچ اثری ندارند.
    gemini_touch_question(chat.id)
    ok, answer = await gemini_generate(
        message.text, chat_id=chat.id, user_name=user.first_name or "دوست"
    )
    if ok:
        await message.reply_text(answer[:4090])
    else:
        await message.reply_text(answer)
    return True

# ============================================================
# v50 — پنل اختصاصی مالک ربات
# فقط شناسه مالک اصلی اجازه دسترسی به این پنل را دارد.
# ============================================================
try:
    BOT_OWNER_ID = int(os.environ.get("BOT_OWNER_ID", "645253229"))
except ValueError:
    BOT_OWNER_ID = 645253229
OWNER_SETTINGS_FILE = DATA_DIR / "owner_settings.json"
OWNER_SETTINGS = load_json_safe(OWNER_SETTINGS_FILE, {})
OWNER_DEFAULT_SETTINGS = {
    "reminders": True,
    "gaming": True,
    "truth_or_dare": True,
    "assistant": True,
    "game_media": True,
    "welcome": True,
}
for _k, _v in OWNER_DEFAULT_SETTINGS.items():
    OWNER_SETTINGS.setdefault(_k, _v)
save_json_safe(OWNER_SETTINGS_FILE, OWNER_SETTINGS)

def save_owner_settings():
    save_json_safe(OWNER_SETTINGS_FILE, OWNER_SETTINGS)

def owner_is_user(user_id):
    try:
        return int(user_id or 0) == BOT_OWNER_ID
    except (TypeError, ValueError):
        return False

def owner_feature_enabled(name):
    return bool(OWNER_SETTINGS.get(name, OWNER_DEFAULT_SETTINGS.get(name, True)))

def owner_panel_keyboard():
    def label(icon, name, title):
        return f"{icon} {title}: {'🟢 روشن' if owner_feature_enabled(name) else '🔴 خاموش'}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label("⏰", "reminders", "یادآورها"), callback_data="owner_toggle_reminders")],
        [InlineKeyboardButton(label("🎮", "gaming", "بازی‌ها"), callback_data="owner_toggle_gaming"),
         InlineKeyboardButton(label("🕵️", "truth_or_dare", "جرأت/حقیقت"), callback_data="owner_toggle_truth_or_dare")],
        [InlineKeyboardButton(label("🧠", "assistant", "Smart Assistant"), callback_data="owner_toggle_assistant"),
         InlineKeyboardButton(label("🎞️", "game_media", "GIF و مدیا"), callback_data="owner_toggle_game_media")],
        [InlineKeyboardButton(label("👋", "welcome", "خوش‌آمدگویی"), callback_data="owner_toggle_welcome")],
        [InlineKeyboardButton("📊 وضعیت و آمار فنی", callback_data="owner_status")],
        [InlineKeyboardButton("🔄 بازنشانی تنظیمات", callback_data="owner_reset")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="owner_close")],
    ])

def owner_panel_text():
    active = []
    if 'UNO_GAMES' in globals() and UNO_GAMES:
        active.append(f"🃏 UNO: {len(UNO_GAMES)}")
    if 'ww_games' in globals() and ww_games:
        active.append(f"🐺 گرگینه: {len(ww_games)}")
    if 'TD_GAMES' in globals() and TD_GAMES:
        active.append(f"🕵️ جرأت/حقیقت: {len(TD_GAMES)}")
    media_sources = 0
    if 'TD_MEDIA' in globals() and isinstance(TD_MEDIA, dict):
        media_sources = sum(len(v) for v in TD_MEDIA.values())
    return (
        "👑 <b>پنل اختصاصی مالک ربات</b>\n\n"
        f"🆔 Owner ID: <code>{BOT_OWNER_ID}</code>\n"
        "🔐 این پنل فقط در Private و فقط برای مالک اصلی قابل استفاده است.\n\n"
        "⚙️ <b>کنترل‌های عمومی</b>\n"
        f"⏰ یادآورها: {'🟢' if owner_feature_enabled('reminders') else '🔴'}\n"
        f"🎮 بازی‌ها: {'🟢' if owner_feature_enabled('gaming') else '🔴'}\n"
        f"🕵️ جرأت/حقیقت: {'🟢' if owner_feature_enabled('truth_or_dare') else '🔴'}\n"
        f"🧠 Smart Assistant: {'🟢' if owner_feature_enabled('assistant') else '🔴'}\n"
        f"🎞️ GIF/Media: {'🟢' if owner_feature_enabled('game_media') else '🔴'}\n"
        f"👋 خوش‌آمدگویی: {'🟢' if owner_feature_enabled('welcome') else '🔴'}\n\n"
        f"🎯 بازی‌های فعال فعلی: {', '.join(active) if active else 'هیچ‌کدام'}\n"
        f"🎞️ منابع GIF ثبت‌شده: {media_sources}"
    )

def owner_runtime_health():
    import shutil
    try:
        disk=shutil.disk_usage(DATA_DIR)
        disk_text=f"{disk.free/1024/1024:.0f}MB آزاد / {disk.total/1024/1024:.0f}MB"
    except Exception:
        disk_text="نامشخص"
    return (
        f"🃏 UNO فعال: {len(UNO_GAMES) if 'UNO_GAMES' in globals() else 0}\n"
        f"🐺 گرگینه فعال: {len(ww_games) if 'ww_games' in globals() else 0}\n"
        f"🕵️ جرأت/حقیقت فعال: {len(TD_GAMES) if 'TD_GAMES' in globals() else 0}\n"
        f"🔒 TD task خصوصی: {len(TD_PRIVATE_TASKS) if 'TD_PRIVATE_TASKS' in globals() else 0}\n"
        f"💾 فضای آزاد: {disk_text}\n"
        f"🧠 نسخه: {BOT_VERSION}"
        f"\n🧪 Smart state: {len(SMART_DIALOGUE_STATE) if 'SMART_DIALOGUE_STATE' in globals() else 0}"
    )

async def owner_health_cmd(update, context):
    user=update.effective_user
    if not user or not owner_is_user(user.id):
        return
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    await update.effective_message.reply_text("🩺 <b>وضعیت داخلی ربات</b>\n\n"+owner_runtime_health(), parse_mode="HTML")

async def owner_panel_cmd(update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not user or not owner_is_user(user.id):
        if chat and chat.type == "private":
            await update.effective_message.reply_text("⛔ این پنل فقط برای مالک اصلی ربات فعال است.")
        return
    if not chat or chat.type != "private":
        await update.effective_message.reply_text("🔐 پنل مالک فقط در Private ربات قابل استفاده است.")
        return
    await update.effective_message.reply_text(owner_panel_text(), parse_mode="HTML", reply_markup=owner_panel_keyboard())

async def owner_callback_handler(update, context):
    query = update.callback_query
    user = query.from_user
    if not owner_is_user(user.id):
        await query.answer("⛔ این پنل فقط برای مالک ربات است.", show_alert=True)
        return
    if not query.message or query.message.chat.type != "private":
        await query.answer("🔐 پنل مالک فقط در Private قابل استفاده است.", show_alert=True)
        return
    await query.answer()
    data = query.data or ""
    if data == "owner_close":
        try:
            await query.message.delete()
        except TelegramError:
            await query.edit_message_text("👑 پنل مالک بسته شد.")
        return
    if data == "owner_reset":
        OWNER_SETTINGS.clear()
        OWNER_SETTINGS.update(OWNER_DEFAULT_SETTINGS)
        save_owner_settings()
    elif data == "owner_status":
        await query.edit_message_text(
            owner_panel_text() +
            "\n\n🩺 حافظه‌های موقت: فعال"
            "\n💾 ذخیره تنظیمات: فعال"
            "\n🛡️ احراز مالک: فعال"
            "\n🔒 دسترسی پنل در گروه: مسدود",
            parse_mode="HTML", reply_markup=owner_panel_keyboard()
        )
        return
    elif data.startswith("owner_toggle_"):
        feature = data[len("owner_toggle_"):]
        if feature in OWNER_DEFAULT_SETTINGS:
            OWNER_SETTINGS[feature] = not owner_feature_enabled(feature)
            save_owner_settings()
    await query.edit_message_text(owner_panel_text(), parse_mode="HTML", reply_markup=owner_panel_keyboard())


bad_data = load_json_safe(BAD_WORDS_FILE, {"fa": DEFAULT_BAD_WORDS_FA, "en": DEFAULT_BAD_WORDS_EN})
BAD_WORDS_FA = bad_data.get("fa", DEFAULT_BAD_WORDS_FA)
BAD_WORDS_EN = bad_data.get("en", DEFAULT_BAD_WORDS_EN)
if not BAD_WORDS_FILE.exists():
    save_json_safe(BAD_WORDS_FILE, {"fa": BAD_WORDS_FA, "en": BAD_WORDS_EN})

# ساختار فایل سفارشی: {"<chat_id>": ["کلمه۱", "کلمه۲", ...], ...}
# هر گروه لیست کلمات سفارشی خودش رو داره، تا کلمه‌ای که یک ادمین توی یک گروه اضافه
# می‌کنه، توی گروه‌های دیگه اعمال نشه (مگر اینکه بخوای سراسری باشه - قابل تغییره).
custom_bad_words = load_json_safe(CUSTOM_BAD_WORDS_FILE, {})
if not CUSTOM_BAD_WORDS_FILE.exists():
    save_json_safe(CUSTOM_BAD_WORDS_FILE, custom_bad_words)

warns_data = load_json_safe(WARN_FILE, {})  # {"chat_id:user_id": count}

# وضعیت یادآور: {"<chat_id>": true/false}
reminder_enabled = load_json_safe(REMINDER_FILE, {})
if not REMINDER_FILE.exists():
    save_json_safe(REMINDER_FILE, reminder_enabled)

# v13: پروفایل رفتاری پایدار؛ پروفایل فقط برای کاربرانی که رفتار سفارشی دارند
# ذخیره می‌شود تا بی‌دلیل اطلاعات همه اعضای گروه روی دیسک نوشته نشود.
user_profiles = load_json_safe(USER_PROFILES_FILE, {})
if not USER_PROFILES_FILE.exists():
    save_json_safe(USER_PROFILES_FILE, user_profiles)
# جلوگیری از ارسال تکراری در یک ساعت مشخص (in-memory، نیازی به دیسک نداره)
reminder_last_sent_hour = {}

# کاربرانی که الان توی «حالت افزودن کلمه نامناسب» هستن: {user_id: chat_id}
pending_badword_add = {}  # کلید: chat_id:user_id

# حافظه‌ی کوتاه‌مدت مکالمه؛ فقط برای تشخیص پیام‌های دنباله‌دار در همان گروه/کاربر.
# این داده عمداً در RAM نگه داشته می‌شود و با ری‌استارت پاک می‌شود تا فایل‌های قبلی دست‌نخورده بمانند.
conversation_context = {}
CONVERSATION_TTL = 20 * 60
CONVERSATION_MAX = 10
# حافظه‌ی غنی‌ترِ کوتاه‌مدت، کاملاً جداگانه برای هر (chat_id, user_id).
# ساختار هر ورودی: timestamp, text, topic, reply. این حافظه هم مثل حافظه‌ی قبلی
# فقط در RAM است و بعد از ری‌استارت پاک می‌شود؛ بنابراین اطلاعات قدیمی به‌صورت
# ناخواسته روی مکالمه‌های آینده اثر نمی‌گذارد.
user_short_memory = {}
USER_MEMORY_TTL = 20 * 60
USER_MEMORY_MAX = 10

conversation_topic_memory = {}

FOLLOWUP_MARKERS = {
    "اون", "همون", "همونو", "این", "این یکی", "اون یکی", "بیشتر", "ادامه",
    "ادامه بده", "توضیح بده", "واضحتر", "واضح تر", "چرا", "چطور", "یعنی چی",
    "پس چی", "بعدش", "خب بعد", "چی شد", "کدوم", "همین", "همین رو", "همینو",
    "اینم", "اونم", "مثالش", "مثال", "بیشتر توضیح بده",
}

def _memory_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"

def _is_followup_message(text: str) -> bool:
    norm = _smart_normalize(text)
    if not norm:
        return False
    if len(norm.split()) <= 5:
        return True if any(marker in norm for marker in FOLLOWUP_MARKERS) else False
    return any(marker in norm for marker in FOLLOWUP_MARKERS)

def _get_user_memory(chat_id, user_id):
    key = _memory_key(chat_id, user_id)
    now = time.time()
    items = user_short_memory.get(key, [])
    items = [x for x in items if now - x["ts"] <= USER_MEMORY_TTL]
    user_short_memory[key] = items[-USER_MEMORY_MAX:]
    return user_short_memory[key]

def _remember_user_turn(chat_id, user_id, text, reply, topic):
    key = _memory_key(chat_id, user_id)
    items = _get_user_memory(chat_id, user_id)
    items.append({"ts": time.time(), "text": text[:500], "reply": (reply or "")[:700], "topic": (topic or "")[:200]})
    user_short_memory[key] = items[-USER_MEMORY_MAX:]

def _last_user_context_phrase(chat_id, user_id):
    items = _get_user_memory(chat_id, user_id)
    if not items:
        return ""
    last = items[-1]
    return last.get("topic") or last.get("text", "")[:300]


# ============================================================
# 🧠 حافظه موضوعی v9
# علاوه بر تاریخچه پیام‌ها، برای هر (chat_id, user_id) چند «موضوع فعال» نگه می‌داریم.
# این حافظه فقط RAM است و با ری‌استارت پاک می‌شود.
# ============================================================
TOPIC_MEMORY_MAX = 6
TOPIC_MEMORY_TTL = 30 * 60
TOPIC_HINTS = {
    "بازی": {"بازی", "بازیها", "بازیهایی", "سرگرمی", "گرگینه", "جرأت", "حقیقت", "اونو", "uno"},
    "تاروت": {"تاروت", "کارت", "کارتها", "آرکانا"},
    "فال": {"فال", "حافظ", "شانس"},
    "مدیریت گروه": {"ادمین", "مدیر", "گروه", "میوت", "بن", "اخطار", "اسپم", "پین", "قوانین"},
    "یادآور": {"یادآور", "یادآوری", "reminder"},
    "قیمت": {"قیمت", "دلار", "بیتکوین", "بیت کوین", "btc"},
    "زمان و تاریخ": {"ساعت", "امروز", "فردا", "تاریخ", "روز", "ماه"},
    "ربات": {"ربات", "دستیار", "امکانات", "دستور", "کمک"},
}

def _extract_topic(text: str):
    norm = _smart_normalize(text)
    scores = []
    for topic, hints in TOPIC_HINTS.items():
        score = sum(1 for h in hints if _smart_normalize(h) in norm)
        if score:
            scores.append((score, topic))
    scores.sort(reverse=True)
    return scores[0][1] if scores else None

def _topic_memory(chat_id, user_id):
    key = _memory_key(chat_id, user_id)
    now = time.time()
    data = conversation_topic_memory.get(key, [])
    data = [x for x in data if now - x["ts"] <= TOPIC_MEMORY_TTL]
    conversation_topic_memory[key] = data[-TOPIC_MEMORY_MAX:]
    return conversation_topic_memory[key]

def _remember_topic(chat_id, user_id, topic, text):
    if not topic:
        return
    key = _memory_key(chat_id, user_id)
    data = _topic_memory(chat_id, user_id)
    # اگر موضوع فعلی همان موضوع قبلی است، فقط زمان و نمونه را تازه کن.
    if data and data[-1]["topic"] == topic:
        data[-1].update({"ts": time.time(), "text": text[:300]})
    else:
        data.append({"ts": time.time(), "topic": topic, "text": text[:300]})
    conversation_topic_memory[key] = data[-TOPIC_MEMORY_MAX:]

def _is_topic_switch_request(text: str) -> bool:
    n = _smart_normalize(text)
    markers = ("بریم سراغ", "بریم روی", "موضوع رو عوض", "یه موضوع دیگه", "موضوع دیگه", "ولش کن", "بیخیال", "حالا درباره")
    return any(_smart_normalize(m) in n for m in markers)

def _find_topic_in_memory(chat_id, user_id, text: str):
    n = _smart_normalize(text)
    data = _topic_memory(chat_id, user_id)
    for item in reversed(data):
        topic = item["topic"]
        hints = TOPIC_HINTS.get(topic, set())
        if any(_smart_normalize(h) in n for h in hints):
            return topic
    return None

def _current_topic(chat_id, user_id):
    data = _topic_memory(chat_id, user_id)
    return data[-1]["topic"] if data else None

def _previous_topic(chat_id, user_id):
    data = _topic_memory(chat_id, user_id)
    return data[-2]["topic"] if len(data) >= 2 else None

def _topic_context_phrase(chat_id, user_id, topic):
    data = _topic_memory(chat_id, user_id)
    for item in reversed(data):
        if item["topic"] == topic:
            return item.get("text", "")
    return ""


# پیام‌هایی که در حالت ضداسپمِ ادمین‌ها ثبت شده‌اند؛ برای جلوگیری از ارسال هشدارهای تکراری
# در یک بازه کوتاه استفاده می‌شود.
admin_spam_last_warn = {}
ADMIN_SPAM_WARN_COOLDOWN = 60

REMINDER_EVEN_TEXT = "🔔 دینگ دینگ! وقت پاچیدن چاهه 🕳️"
REMINDER_ODD_TEXT = "🔔 دینگ دینگ! بدو که شام ننه‌جون سرد شد 🍽️"
GOODNIGHT_TEXT = "🌙 شب همگی به‌خیر و خوش، خواب‌های آروم ببینید 😴✨"


def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKC", text)
    text = "".join(LEET_MAP.get(ch, ch) for ch in text)
    text = re.sub(r"[\s\.\-_\*]+", "", text)
    text = re.sub(r"(.)\1{1,}", r"\1", text)
    return text


def get_custom_words_for_chat(chat_id) -> list:
    return custom_bad_words.get(str(chat_id), [])


def contains_bad_word(text: str, chat_id=None):
    """چک می‌کنه که متن شامل ناسزا هست یا نه - هم لیست پیش‌فرض هم لیست سفارشی همون گروه."""
    norm = normalize_text(text)
    all_words = BAD_WORDS_FA + BAD_WORDS_EN
    if chat_id is not None:
        all_words = all_words + get_custom_words_for_chat(chat_id)
    for w in all_words:
        normalized_word = normalize_text(w)
        if normalized_word and normalized_word in norm:
            return True
    return False


async def get_group_owner(chat_id, context):
    """مالک واقعی گروه/سوپرگروه را از Telegram Bot API پیدا می‌کند."""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.status == "creator":
                return admin.user
    except TelegramError as e:
        logger.warning(f"خطا در پیدا کردن مالک گروه {chat_id}: {e}")
    return None


async def is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        return False
    owner = await get_group_owner(chat.id, context)
    return bool(owner and owner.id == user.id)


_ADMIN_CACHE = {}
_ADMIN_CACHE_TTL = 45


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    if chat.type == "private":
        return True
    key = (chat.id, user.id)
    hit = _ADMIN_CACHE.get(key)
    now = time.time()
    if hit and now - hit[1] < _ADMIN_CACHE_TTL:
        return hit[0]
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        result = member.status in ("administrator", "creator")
    except Exception:
        return False
    _ADMIN_CACHE[key] = (result, now)
    return result


def mention_html(user) -> str:
    name = html.escape(user.first_name or "کاربر")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


GROUP_RULES_TEXT = (
    "📜 قوانین گروه:\n\n"
    "۱. احترام به همه اعضا الزامیه\n"
    "۲. استفاده از الفاظ رکیک ممنوعه (تشخیص خودکار)\n"
    "۳. تبلیغات بدون هماهنگی ادمین ممنوعه\n"
    "۴. اسپم و ارسال پی‌درپی پیام ممنوعه"
)

# لحظه‌ی روشن شدن پردازه‌ی ربات - برای محاسبه‌ی دقیق «از کی فعالی؟» استفاده می‌شه
BOT_START_TIME = datetime.now()


# ============================================================
# 🧠 «هوشمندی» بدون نیاز به سرویس هوش مصنوعی پولی
# چون از سرویس‌های پولی هوش مصنوعی (Gemini/OpenRouter) استفاده نمی‌کنیم، به‌جاش
# دو موتور جایگزین ساختیم که کاملاً آفلاین، رایگان و سریع کار می‌کنن:
#   ۱) موتور تولید ترکیبی (فال/تاروت): قطعات مختلف متن رو تصادفی و هوشمندانه
#      کنار هم می‌چینه؛ نتیجه هزاران حالت متفاوت ممکنه، نه چند جمله‌ی تکراری.
#   ۲) دستیار مکالمه‌ی قانون‌محور (زیر همین بخش): وقتی کسی مستقیم با ربات
#      حرف بزنه، هم تشخیص نیت (Intent) با دقت بیشتر انجام می‌ده، هم برای
#      سؤالاتی مثل ساعت/تاریخ، محاسبه‌ی واقعی و دقیق (نه متن ثابت) برمی‌گردونه.
# ============================================================

# ------------------------------------------------------------
# 📅 تبدیل دقیق میلادی به شمسی - محاسبه‌ی واقعی، بدون نیاز به کتابخانه‌ی جانبی
# (الگوریتم استاندارد تقویم جلالی؛ برای پاسخ «امروز چندمه؟» استفاده می‌شه)
# ------------------------------------------------------------
def gregorian_to_jalali(gy: int, gm: int, gd: int):
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    for i in range(gm2):
        g_day_no += g_days_in_month[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    jm, jd = 12, j_day_no + 1
    for i in range(11):
        if j_day_no < j_days_in_month[i]:
            jm, jd = i + 1, j_day_no + 1
            break
        j_day_no -= j_days_in_month[i]
    return jy, jm, jd


PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
PERSIAN_WEEKDAYS = {5: "شنبه", 6: "یک‌شنبه", 0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه"}


def get_persian_datetime_text() -> str:
    now = datetime.now()
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday = PERSIAN_WEEKDAYS[now.weekday()]
    return (
        f"📅 امروز {weekday}، {jd} {PERSIAN_MONTHS[jm - 1]} {jy} هست "
        f"(برابر با {now.strftime('%Y-%m-%d')} میلادی).\n"
        f"🕒 ساعت دقیق سرور الان: {now.strftime('%H:%M:%S')}"
    )


def get_time_text() -> str:
    now = datetime.now()
    return f"🕒 ساعت دقیق الان: {now.strftime('%H:%M:%S')}"


# ------------------------------------------------------------
# 💬 دستیار مکالمه‌ی قانون‌محور (Rule-Based Intent Matching) - کاملاً آفلاین
# نسخه‌ی حرفه‌ای: به‌جای «اولین دسته‌ای که match شد»، یه سیستم امتیازدهی داره -
# هر عبارت کلیدی چندکلمه‌ای امتیاز بیشتری از یه کلمه‌ی تنها می‌گیره، پس اگه
# پیام هم‌زمان با چند دسته هم‌پوشانی داشته باشه، دقیق‌ترین/مشخص‌ترین دسته
# انتخاب می‌شه، نه هر چیزی که اول پیدا شد. علاوه بر این، چند نیت «پویا» هم
# داره که به‌جای متن ثابت، داده‌ی واقعیِ همون لحظه (تعداد اعضا، لیست ادمین‌ها،
# مدت‌زمان فعالیت ربات، ساعت/تاریخ دقیق) رو محاسبه و برمی‌گردونه.
# فقط وقتی فعال می‌شه که پیام مستقیماً خطاب به رباته (اسمش بیاد یا ریپلای
# روی پیام خودش باشه)، تا مزاحم گفت‌وگوی عادی گروه نشه.
# ------------------------------------------------------------
_SMART_PUNCT_RE = re.compile(r"[؟?!.,،:؛;\-_]+")
_QUESTION_WORDS = ["چرا", "چطور", "چگونه", "کجا", "کِی", "کی", "چند", "کدوم", "کدام", "آیا", "چی", "چیه"]


def _smart_normalize(text: str) -> str:
    """متن رو برای تشخیص نیت یکدست می‌کنه تا املاهای مختلف یه کلمه، یکی حساب بشن:
    ي/ك عربی → ی/ک فارسی، حذف اعراب و کشیده، نیم‌فاصله → حذف (می‌کنی = میکنی)،
    ارقام فارسی/عربی → لاتین، حذف علائم نگارشی، و فشرده‌کردن حروف تکراری
    (سلاااام → سلام). همین نرمال‌سازی روی کلیدواژه‌ها هم اعمال می‌شه."""
    t = unicodedata.normalize("NFKC", text).lower()
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه")
    t = t.replace("أ", "ا").replace("إ", "ا")
    t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)          # اعراب و کشیده
    t = t.replace("\u200c", "").replace("\u200f", "").replace("\u200e", "")
    t = t.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    t = _SMART_PUNCT_RE.sub(" ", t)
    t = re.sub(r"[^\w\s]", " ", t)                              # ایموجی و علائم دیگه
    t = re.sub(r"(.)\1+", r"\1", t)                             # سلاااام → سلام
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _time_of_day_greeting() -> str:
    h = datetime.now().hour
    if 5 <= h < 12:
        return "صبح بخیر"
    if 12 <= h < 16:
        return "روز بخیر"
    if 16 <= h < 20:
        return "عصر بخیر"
    return "شب بخیر"


# ---------------- پاسخ‌های پویا (محاسبه‌ی واقعی، نه متن ثابت) ----------------
async def _dyn_member_count(name, norm, context, chat) -> str:
    try:
        count = await context.bot.get_chat_member_count(chat.id)
        return f"👥 در حال حاضر این گروه {count} عضو داره."
    except Exception:
        return "⚠️ الان نتونستم تعداد دقیق اعضا رو بگیرم؛ دوباره امتحان کن."


async def _dyn_owner(name, norm, context, chat) -> str:
    if chat.type == "private":
        return "👑 چت خصوصی مالک گروه نداره."
    owner = await get_group_owner(chat.id, context)
    if not owner:
        return "⚠️ نتونستم مالک گروه رو از Telegram دریافت کنم."
    return f"👑 مالک گروه: {mention_html(owner)}"


async def _dyn_admins_list(name, norm, context, chat) -> str:
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        names = [a.user.first_name for a in admins if not a.user.is_bot]
        if not names:
            return "فعلاً ادمین انسانی برای این گروه ثبت نشده."
        return "👑 ادمین‌های این گروه: " + "، ".join(names)
    except Exception:
        return "⚠️ الان نتونستم لیست ادمین‌ها رو بگیرم؛ دوباره امتحان کن."


async def _dyn_group_title(name, norm, context, chat) -> str:
    if chat.type == "private":
        return "الان توی چت خصوصی باهامی، نه یه گروه."
    return f"📛 اسم این گروه «{chat.title}» هست."


async def _dyn_uptime(name, norm, context, chat) -> str:
    delta = datetime.now() - BOT_START_TIME
    days, rem = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} روز")
    if hours:
        parts.append(f"{hours} ساعت")
    parts.append(f"{minutes} دقیقه")
    return f"⏱️ از آخرین راه‌اندازیم دقیقاً {' و '.join(parts)} می‌گذره؛ در تمام این مدت بدون وقفه فعال بودم."


async def _dyn_time(name, norm, context, chat) -> str:
    return get_time_text()


async def _dyn_date(name, norm, context, chat) -> str:
    return get_persian_datetime_text()


async def _dyn_rules(name, norm, context, chat) -> str:
    return GROUP_RULES_TEXT


async def _dyn_fal_request(name, norm, context, chat) -> str:
    return f"🔮 فال امروز {name}:\n\n{await generate_fal(name)}"


async def _dyn_tarot_request(name, norm, context, chat) -> str:
    return await generate_tarot()


async def _dyn_hafez_request(name, norm, context, chat) -> str:
    return await generate_hafez()


async def _dyn_joke_request(name, norm, context, chat) -> str:
    return f"😂 {random.choice(JOKES_FALLBACK)}"


async def _dyn_proverb_request(name, norm, context, chat) -> str:
    return f"💬 {random.choice(PROVERBS_FA)}"


async def _dyn_luck(name, norm, context, chat) -> str:
    return f"🎯 شانس امروزت: {random.randint(1, 100)}٪"


async def _dyn_btc_request(name, norm, context, chat) -> str:
    p = await fetch_prices()
    if not p["btc_usd"]:
        return "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن، چند لحظه دیگه دوباره بپرس."
    text = f"₿ قیمت بیت‌کوین: ${p['btc_usd']:,}\n(منبع: {p['btc_source']})"
    if p["btc_toman"]:
        text += f"\nمعادل: {p['btc_toman']:,} تومان"
    return text


async def _dyn_usd_request(name, norm, context, chat) -> str:
    p = await fetch_prices()
    if not p["usd_toman"]:
        return "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن، چند لحظه دیگه دوباره بپرس."
    return f"💵 قیمت دلار: {p['usd_toman']:,} تومان\n(منبع: {p['usd_source']})"


# ------------------------------------------------------------
# 💎 مخاطبین ویژه - لحن این دو نفر «گرم، محترمانه و صمیمی» می‌شه: ادب و مهربانی
# بیشتر، واژه‌های دلنشین، ولی بدون هیچ محتوای عاشقانه‌ی افراطی یا نامناسب.
# با بقیه‌ی اعضا ربات کاملاً عادی و معمولی صحبت می‌کنه.
# کلید: آیدی تلگرام (بدون @ و با حروف کوچک). هر دو یک «خانواده‌ی لحن» دارن
# (گرم و مؤدب)، فقط واژه‌ها و تعابیرشون کمی با هم فرق داره.
# ------------------------------------------------------------
# ------------------------------------------------------------
# 🧠 موتور پروفایل رفتاری v13
#
# در نسخه‌های قبلی رفتار ویژه مستقیماً از روی username خوانده می‌شد.
# v13 همان رفتار را حفظ می‌کند، اما بعد از اولین شناسایی، پروفایل با user_id
# ذخیره می‌شود تا تغییر username باعث از بین رفتن رفتار اختصاصی نشود.
# ساختار هر پروفایل فقط شامل اطلاعات غیرحساس مربوط به تجربه‌ی گفتگو است:
# style / display_name / enabled.
# ------------------------------------------------------------

def _profile_user_key(user_id):
    return str(user_id)


def _profile_username(username):
    return (username or "").strip().lstrip("@").lower()


def _legacy_special_profile(username):
    return SPECIAL_CONTACTS.get(_profile_username(username))


def get_user_profile(user_id, username=None):
    """پروفایل رفتاری کاربر را برمی‌گرداند؛ رفتار قدیمی را هم پشتیبانی می‌کند."""
    key = _profile_user_key(user_id)
    profile = user_profiles.get(key)
    if isinstance(profile, dict) and profile.get("enabled", True):
        return profile

    legacy = _legacy_special_profile(username)
    if legacy:
        # مهاجرت خودکار از username به user_id؛ رفتار v12 بدون تغییر حفظ می‌شود.
        profile = {
            "style": legacy.get("style"),
            "display_name": legacy.get("display_name"),
            "enabled": True,
            "source": "legacy_special_contact",
        }
        user_profiles[key] = profile
        try:
            save_json_safe(USER_PROFILES_FILE, user_profiles)
        except Exception:
            pass
        return profile
    return None


def profile_display_name(user, profile=None):
    if profile and profile.get("display_name"):
        return profile["display_name"]
    return user.first_name or "دوست عزیز"


def profile_style(user_id, username=None):
    profile = get_user_profile(user_id, username)
    return profile.get("style") if profile else None

SPECIAL_CONTACTS = {
    "karninc": {"display_name": "پری جان", "style": "sweet_a"},
    "yuzishtain": {"display_name": "دوست خوبم", "style": "sweet_b"},
}

SPECIAL_DYNAMIC_PREFIX = {
    "sweet_a": ["بفرمایید {name} 🌸\n", "با کمال میل {name} 🌙\n", "چشم {name}، این هم از این ✨\n"],
    "sweet_b": ["بفرمایید {name} 🧃\n", "حتماً {name}، این هم پاسخ شما 🌿\n", "با کمال میل {name} ✨\n"],
}

SPECIAL_STYLE_RESPONSES = {
    "sweet_a": {
        "greeting": [
            "{tod} {name}! چه خوب شد سر زدید، دلم خوش شد 🌸 بفرمایید در خدمتم.",
            "سلام {name}، خوش اومدید! امیدوارم روزتون پر از آرامش و خبرهای خوب باشه 🌙",
            "درود بر شما {name}؛ دیدن پیامتون همیشه مایه‌ی خوشحالیه ✨ چه کاری از دستم برمیاد؟",
            "سلام {name}، وقتتون بخیر! افتخار دادید که صدام کردید، بفرمایید 🌷",
            "{tod} {name}؛ خیلی خوش اومدید، امروز چطورید؟ 🌸",
        ],
        "call_only": [
            "بله {name}، بفرمایید؛ در خدمتم 🌸",
            "جانم {name}؟ بفرمایید، گوش به فرمانم ✨",
            "بله {name}؛ صدام کردید؟ اینجام 🌙",
        ],
        "wellbeing": [
            "ممنون از لطفتون {name}، به لطف شما حالم عالیه 🌸 شما چطورید؟ امیدوارم روزتون خوب بگذره.",
            "سپاس که احوالم رو پرسیدید {name}؛ خوبم و آماده‌ی خدمت. امیدوارم شما هم سرحال و شاد باشید ✨",
            "مرسی {name}، همیشه با دیدن پیام شما حالم بهتر می‌شه 🌷 شما چه خبر؟ حالتون خوبه؟",
        ],
        "identity": [
            "من «دستیار هوشمند» این گروهم {name}؛ با افتخار و احترام در خدمت شما و دوستان گروهم 🌸",
            "دستیار هوشمند این جمع هستم {name}؛ فال، تاروت، مدیریت گروه و بازی از کارهامه. با /start همه‌ی امکاناتم رو می‌بینید ✨",
        ],
        "creator": [
            "ادمین‌های همین گروه من رو با دقت راه‌اندازی و پیکربندی کردن {name}؛ همیشه در خدمت شما و دوستانم 🌸",
        ],
        "real_ai_question": [
            "سؤال دقیقی بود {name}؛ من یه دستیار قانون‌محور و آفلاینم، نه یه مدل زبانی متصل به اینترنت. "
            "ولی در فال، تاروت، مدیریت گروه و محاسبه‌ی دقیق ساعت و تاریخ کاملاً قابل اعتمادم 🌙",
        ],
        "capabilities": [
            "با کمال میل {name}؛ فال، تاروت، فال حافظ، بازی گروهی، مدیریت گروه، یادآور و چند سرگرمی دیگه از خدمات منه. "
            "منوی کامل با دستور /start در دسترس شماست 🌸",
        ],
        "joke_request": ["با کمال میل {name}، این یکی رو تقدیم می‌کنم 🌸"],
        "compliment_me": [
            "شما آدم مهربون و بااخلاقی هستید {name}؛ حضورتون به این گروه گرمی و زیبایی می‌ده 🌸",
            "از لحن و ادب‌تون در هر پیام معلومه که چقدر با شخصیت و دلنشین هستید {name} ✨",
            "وجود آدم‌هایی مثل شما، فضای گروه رو قشنگ‌تر می‌کنه {name}؛ واقعاً جای قدردانی داره 🌷",
        ],
        "loneliness": [
            "متأسفم که دلتون گرفته {name}؛ من همیشه اینجام و خوشحال می‌شم کنارتون باشم. اگه دوست داشتید، یه فال یا تاروت با هم بگیریم تا کمی حالتون بهتر بشه 🤍",
            "می‌فهمم {name}؛ گاهی همه‌ی ما به یه لحظه‌ی آرام نیاز داریم. هر وقت خواستید صحبت کنیم، در خدمتم. امیدوارم زودتر حالتون بهتر بشه 🌙",
        ],
        "sadness": [
            "ناراحت شدم که حالتون خوب نیست {name}؛ امیدوارم این روزها هرچه زودتر بگذره و آرامش برگرده 🌷 اگه صحبت کردن کمک می‌کنه، من اینجام.",
        ],
        "angry": [
            "کاملاً درکتون می‌کنم {name}؛ یه نفس عمیق بکشید، همه‌چی درست می‌شه 🌿 اگه بخواید در مورد اون موضوع حرف بزنیم، گوش می‌دم.",
        ],
        "missing": [
            "لطف دارید {name}؛ منم از دیدن و صحبت با شما خوشحال می‌شم 🌸 همیشه اینجام.",
            "چه حرف قشنگی {name} ✨ ممنون از محبتتون، هر وقت بخواید در خدمتم.",
        ],
        "are_you_there": [
            "بله {name}، اینجام و در خدمتتونم 🌸 بفرمایید.",
            "همیشه آماده‌ام {name}؛ بفرمایید چه کاری از دستم برمیاد؟ ✨",
        ],
        "good_morning": [
            "صبح شما هم بخیر و شادی {name} 🌅 امیدوارم امروزتون پر از اتفاق‌های قشنگ باشه.",
            "صبحتون بخیر {name}؛ روز قشنگی رو براتون آرزو می‌کنم ☀️🌸",
        ],
        "good_night": [
            "شبتون بخیر {name}؛ خواب‌های آروم و شیرین ببینید 🌙✨",
            "شب خوبی داشته باشید {name}؛ امیدوارم فردا با انرژی و شادی بیدار بشید 🌙🌸",
        ],
        "sleepy": [
            "پس بهتره استراحت کنید {name}؛ خواب خوب برای آدم لازمه 🌙 شب‌تون بخیر و آروم.",
        ],
        "birthday": [
            "تولدتون مبارک {name}! 🎂🌸 امیدوارم سال جدید زندگی‌تون پر از شادی، سلامتی و موفقیت باشه.",
        ],
        "congrats": [
            "تبریک از صمیم قلب {name}! 🌸 امیدوارم همیشه شاد و موفق باشید.",
        ],
        "good_luck": [
            "با تمام وجود براتون آرزوی موفقیت دارم {name} 🌷 مطمئنم از پسش برمیاید.",
            "از ته دل آرزو می‌کنم همه‌چی به بهترین شکل پیش بره {name} ✨🍀",
        ],
        "apology": [
            "هیچ نیازی به عذرخواهی نیست {name}؛ لطف کردید که پیام دادید 🌸",
            "خواهش می‌کنم {name}، مشکلی پیش نیومده؛ همیشه در خدمتتون هستم ✨",
        ],
        "weather_query": [
            "متأسفانه من به سرویس هواشناسی متصل نیستم {name}؛ برای اطلاع دقیق، سایت هواشناسی کشور یا یه اپ مثل Windy بهترین گزینه‌ست 🌤️",
        ],
        "food_query": [
            "پیشنهاد من یه غذای گرم و دلنشین ایرانیه {name}؛ مثلاً خورشت یا یه چلوکباب خوب. نوش جان 🌸",
        ],
        "boredom": [
            "اگه دوست دارید کمی سرگرم بشید {name}، /wheel (چرخ شانس) یا /tarot رو امتحان کنید؛ مطمئنم لذت می‌برید 🌙",
        ],
        "games": [
            "اگه حوصله‌ی بازی دارید {name}، /gorgineh (گرگینه)، /td (جرأت یا حقیقت) و در خدمتتونه 🎲",
        ],
        "frustration": [
            "بابت این موضوع صمیمانه عذرخواهی می‌کنم {name}؛ اگه بفرمایید دقیقاً چه انتظاری داشتید، تمام تلاشم رو می‌کنم 🌸 فهرست امکاناتم هم با /start در دسترسه.",
        ],
        "thanks": [
            "این وظیفه‌ی منه {name}؛ جای تشکر نیست، همیشه با کمال میل در خدمتم 🌸",
            "لطف دارید {name}؛ خیلی خوشحالم که تونستم کمکی کرده باشم ✨",
            "افتخار من بود {name}؛ هر وقت لازم داشتید در خدمتم 🌷",
        ],
        "affection": [
            "لطف شما بی‌نهایته {name}؛ خیلی ممنونم از محبتتون 🌸",
            "کلام قشنگتون باعث خوشحالی منه {name}؛ سپاس فراوان ✨",
            "دلم گرم شد از حرف‌تون {name}؛ ممنونم که اینقدر مهربونید 🌷",
        ],
        "farewell": [
            "به امید دیدار دوباره {name}؛ مراقب خودتون باشید 🌙",
            "خدانگهدار {name}؛ هر وقت اراده کردید، با کمال احترام در خدمتم 🌸",
            "روز و شبتون خوش {name}؛ منتظر دیدار بعدی هستم ✨",
        ],
    },
    "sweet_b": {
        "greeting": [
            "{tod} {name}! خوش اومدید، خیلی خوشحال شدم 🧃 بفرمایید در خدمتم.",
            "سلام {name}، وقتتون بخیر! امیدوارم روزتون عالی و پر از انرژی باشه 🌿",
            "درود بر شما {name}؛ چه خوب که پیام دادید، چه کاری از دستم برمیاد؟ ✨",
            "سلام {name}، افتخار دادید! بفرمایید، گوش به فرمانم 🧃",
            "{tod} {name}؛ خوش اومدید، امروز حالتون چطوره؟ 🌷",
        ],
        "call_only": [
            "بله {name}، بفرمایید؛ در خدمتم 🧃",
            "جانم {name}؟ گوش به فرمانم ✨",
            "بله {name}؛ اینجام، بفرمایید 🌿",
        ],
        "wellbeing": [
            "ممنون از توجهتون {name}، حالم عالیه 🧃 شما چطورید؟ امیدوارم روز خوبی داشته باشید.",
            "مرسی که پرسیدید {name}؛ خوبم و آماده‌ی خدمت. امیدوارم شما هم شاد و سلامت باشید ✨",
            "لطف دارید {name}، با دیدن پیام شما حالم بهتر هم شد 🌿 شما چه خبر؟",
        ],
        "identity": [
            "من «دستیار هوشمند» این گروهم {name}؛ با افتخار در خدمت شما و دوستان گروه هستم 🧃",
            "دستیار هوشمند این جمع هستم {name}؛ فال، تاروت، مدیریت گروه و بازی از کارهامه. با /start همه‌ی امکاناتم رو ببینید ✨",
        ],
        "creator": [
            "ادمین‌های همین گروه من رو راه‌اندازی و پیکربندی کردن {name}؛ همیشه در خدمت شما هستم 🧃",
        ],
        "real_ai_question": [
            "سؤال جالبی بود {name}؛ من یه دستیار قانون‌محور و آفلاینم، نه یه مدل زبانی متصل به اینترنت. "
            "ولی در فال، تاروت، مدیریت گروه و محاسبات دقیق مثل ساعت و تاریخ کاملاً قابل اتکام 🌿",
        ],
        "capabilities": [
            "با کمال میل {name}؛ فال، تاروت، فال حافظ، بازی گروهی، مدیریت گروه و یادآورها از خدمات منه. منوی کامل با /start در دسترس شماست 🧃",
        ],
        "joke_request": ["حتماً {name}، این یکی رو تقدیم می‌کنم 🧃"],
        "compliment_me": [
            "شما آدم خوش‌اخلاق و باکلاسی هستید {name}؛ حضورتون به گروه گرمی و اعتبار می‌ده 🧃",
            "از رفتار و ادب‌تون پیداست که چقدر دلنشین و باشخصیت هستید {name} ✨",
            "وجود آدم‌هایی مثل شما به فضای گروه انرژی مثبت می‌ده {name}؛ واقعاً قدردانم 🌿",
        ],
        "loneliness": [
            "متأسفم که حالتون خوب نیست {name}؛ من همیشه اینجام و خوشحال می‌شم کنارتون باشم. اگه دوست داشتید یه فال یا جوک با هم داشته باشیم، در خدمتم 🧃",
            "می‌فهمم {name}؛ گاهی همه‌مون به یه استراحت ذهنی نیاز داریم. هر وقت خواستید صحبت کنیم، من هستم 🌿",
        ],
        "sadness": [
            "ناراحت شدم که حالتون خوب نیست {name}؛ امیدوارم زودتر همه‌چی بهتر بشه 🌿 اگه صحبت کردن کمک می‌کنه، من اینجام.",
        ],
        "angry": [
            "کاملاً درکتون می‌کنم {name}؛ یه نفس عمیق بکشید، همه‌چی درست می‌شه 🌿 اگه بخواید درباره‌اش حرف بزنیم، گوش می‌دم.",
        ],
        "missing": [
            "لطف دارید {name}؛ منم از صحبت با شما خوشحال می‌شم 🧃 همیشه اینجام.",
            "چه حرف مهربونانه‌ای {name} ✨ ممنون از محبتتون، هر وقت بخواید در خدمتم.",
        ],
        "are_you_there": [
            "بله {name}، اینجام و در خدمتتونم 🧃 بفرمایید.",
            "همیشه آماده‌ام {name}؛ بفرمایید چه کاری از دستم برمیاد؟ ✨",
        ],
        "good_morning": [
            "صبح شما هم بخیر {name} ☀️ امیدوارم امروزتون پر از اتفاق‌های خوب باشه.",
            "صبحتون بخیر و شادی {name}؛ روز پرانرژی و قشنگی رو براتون آرزو می‌کنم 🧃",
        ],
        "good_night": [
            "شبتون بخیر {name}؛ شب آرومی داشته باشید و فردا با انرژی بیدار بشید 🌙",
            "شب خوش {name}؛ خواب‌های خوب ببینید 🌙🧃",
        ],
        "sleepy": [
            "پس بهتره کمی استراحت کنید {name}؛ خواب خوب برای آدم لازمه 🌙 شبتون بخیر.",
        ],
        "birthday": [
            "تولدتون مبارک {name}! 🎂🧃 امیدوارم سال جدید پر از شادی، سلامتی و موفقیت باشه.",
        ],
        "congrats": [
            "تبریک از ته دل {name}! 🧃 امیدوارم همیشه شاد و موفق باشید.",
        ],
        "good_luck": [
            "از ته دل براتون آرزوی موفقیت دارم {name} 🍀 مطمئنم از پسش برمیاید.",
            "امیدوارم همه‌چی به بهترین شکل پیش بره {name} ✨🌿",
        ],
        "apology": [
            "نیازی به عذرخواهی نیست {name}؛ اتفاقی نیفتاده 🧃",
            "خواهش می‌کنم {name}، مشکلی نیست؛ همیشه در خدمتتون هستم 🌿",
        ],
        "weather_query": [
            "متأسفانه به سرویس هواشناسی متصل نیستم {name}؛ برای اطلاع دقیق، سایت هواشناسی کشور یا اپ Windy پیشنهاد می‌شه 🌤️",
        ],
        "food_query": [
            "پیشنهاد من یه غذای گرم و اصیل ایرانیه {name}؛ مثلاً چلوکباب یا یه خورشت خوب. نوش جان 🧃",
        ],
        "boredom": [
            "برای رفع خستگی پیشنهاد می‌کنم /wheel یا /td رو امتحان کنید {name}؛ مطمئنم لذت می‌برید 🧃",
        ],
        "games": [
            "اگه حال بازی دارید {name}، /gorgineh (گرگینه)، /td (جرأت یا حقیقت) و آماده‌ان 🎲",
        ],
        "frustration": [
            "بابت این موضوع پوزش می‌خوام {name}؛ اگه بفرمایید دقیقاً چه انتظاری بود، تمام تلاشم رو می‌کنم 🧃 فهرست امکاناتم هم با /start در دسترسه.",
        ],
        "thanks": [
            "وظیفه‌ی منه {name}؛ همیشه با کمال میل در خدمتم 🧃",
            "خواهش می‌کنم {name}؛ خوشحالم که مفید بودم ✨",
            "افتخار من بود {name}؛ هر وقت لازم شد در خدمتم 🌿",
        ],
        "affection": [
            "لطف شما رو ارج می‌نهم {name}؛ خیلی ممنونم 🧃",
            "از محبتتون ممنونم {name}؛ واقعاً دلم گرم شد ✨",
            "چه حرف مهربونانه‌ای {name}؛ سپاسگزارم از لطفتون 🌿",
        ],
        "farewell": [
            "به امید دیدار {name}؛ مراقب خودتون باشید 🧃",
            "خدانگهدار {name}؛ هر وقت لازم شد در خدمتم 🌿",
            "روز و شبتون خوش {name}؛ منتظر دیدار بعدی هستم ✨",
        ],
    },
}

SPECIAL_FALLBACK = {
    "sweet_a": [
        "ببخشید {name}، دقیق متوجه منظورتون نشدم؛ اگه لطف کنید واضح‌تر بفرمایید، با کمال میل کمک می‌کنم 🌸 فهرست امکاناتم هم با /start در دسترس شماست.",
        "پوزش می‌خوام {name}، این مورد رو کامل درک نکردم؛ لطفاً یه بار دیگه با عبارت دیگه‌ای بفرمایید، در خدمتم ✨",
    ],
    "sweet_b": [
        "ببخشید {name}، منظورتون رو دقیق متوجه نشدم؛ اگه بفرمایید واضح‌تر، حتماً کمک می‌کنم 🧃 فهرست امکاناتم هم با /start در دسترسه.",
        "پوزش می‌خوام {name}، این مورد رو کامل درک نکردم؛ لطفاً یه بار دیگه با عبارت دیگه‌ای بفرمایید، در خدمتم 🌿",
    ],
}


# هر آیتم: (نام دسته، لیست عبارات کلیدی، پاسخ‌های ثابت یا None اگه پویا باشه، تابع پویا یا None)
# ترتیب مهم نیست؛ دقیق‌ترین (طولانی‌ترین) عبارتِ مطابق، برنده می‌شه.
SMART_INTENTS = [
    ("time_query",
     ["ساعت چنده", "ساعت چند شد", "الان ساعت چنده", "الان چه ساعتیه", "ساعت رو بگو", "ساعت دقیق", "ساعت"],
     None, _dyn_time),
    ("date_query",
     ["امروز چندمه", "تاریخ امروز", "چه روزیه امروز", "چندمه امروز", "امروز چه روزیه", "امروز چندم ماهه",
      "امروز چه تاریخیه", "امروز چه روزی هست", "تاریخ"],
     None, _dyn_date),
    ("member_count",
     ["چند نفریم", "تعداد اعضا", "اعضای گروه چند نفرن", "چند نفر عضو", "چند تا عضو داریم", "گروه چند نفره", "اعضا چند نفرن"],
     None, _dyn_member_count),
    ("admins_list",
     ["ادمینا کین", "لیست ادمین", "ادمین گروه کیه", "چه کسایی ادمینن", "ادمین ها کین", "چه کسی ادمینه", "ادمینا کیا هستن"],
     None, _dyn_admins_list),
    ("group_title",
     ["اسم گروه چیه", "این گروه چیه", "نام گروه چیه", "اسم این گروه چیه", "این گروه اسمش چیه"],
     None, _dyn_group_title),
    ("uptime",
     ["چند وقته روشنی", "از کی فعالی", "چقدر وقته کار میکنی", "آپتایم", "چند وقته آنلاینی", "چند وقته بیداری", "از کی داری کار میکنی"],
     None, _dyn_uptime),
    ("rules_query",
     ["قانون گروه چیه", "قوانین چیه", "قوانین گروه چیه", "قانونای گروه", "قوانین گروه رو بگو", "قوانین رو بگو"],
     None, _dyn_rules),
    ("fal_request",
     ["فالم رو بگیر", "یه فال بگیر", "فال بگیر", "فالمو بگیر", "برام فال بگیر", "فال امروزم چیه", "فالمو ببین",
      "یه فال برام بگیر", "فال روزانه", "فالم رو ببین"],
     None, _dyn_fal_request),
    ("tarot_request",
     ["یه کارت تاروت بنداز", "تاروت بنداز", "برام تاروت بگیر", "کارت تاروت بکش", "یه تاروت بگیر", "کارتمو ببین",
      "یه کارت بکش", "تاروت بکش"],
     None, _dyn_tarot_request),
    ("hafez_request",
     ["فال حافظ بگیر", "یه فال حافظ", "حافظ رو باز کن", "برام حافظ بخون", "فال حافظ", "یه غزل بخون", "یه شعر بخون", "شعر حافظ"],
     None, _dyn_hafez_request),
    ("btc_request",
     ["قیمت بیت کوین چنده", "بیت کوین چنده", "قیمت بیتکوین", "بیتکوین الان چنده", "قیمت بیت کوین", "بیت کوین"],
     None, _dyn_btc_request),
    ("usd_request",
     ["قیمت دلار چنده", "دلار چنده", "نرخ دلار چقدره", "قیمت دلار الان چنده", "قیمت دلار", "نرخ دلار"],
     None, _dyn_usd_request),
    ("joke_request",
     ["یه جوک بگو", "بخندونم", "جوک بگو", "یه چیز خنده دار بگو", "یه جوک بگو برام", "منو بخندون", "جوک"],
     None, _dyn_joke_request),
    ("proverb_request",
     ["یه ضرب المثل بگو", "ضرب المثل بگو", "یه جمله قشنگ بگو", "یه حرف قشنگ بگو", "ضرب المثل"],
     None, _dyn_proverb_request),
    ("luck_request",
     ["شانس امروزم چقدره", "شانس امروز", "شانسم چقدره", "شانس من چقدره"],
     None, _dyn_luck),

    ("call_only", ["__call_only__"], ["بله؟ بفرمایید، در خدمتم 😊", "جانم؟ چه کاری از دستم برمیاد؟", "بله، اینجام! بفرمایید."], None),
    ("greeting",
     ["سلام علیکم", "سلام", "درود", "هلو", "hi", "hello", "علیک سلام", "سلام عزیزم", "وقت بخیر", "روز بخیر", "عصر بخیر", "احوال شما"],
     ["سلام {name} عزیز! خوش اومدی، در خدمتتم 😊",
      "درود بر {name}! من دستیار هوشمند این گروهم؛ برای دیدن امکاناتم دستور /start رو بزن.",
      "سلام! خوشحالم که بهم پیام دادی. چطور می‌تونم دقیقاً کمکت کنم؟",
      "علیک سلام {name} جان! امروز چه کمکی از دستم برمیاد؟",
      "{tod} {name}! خوش اومدی، بگو چیکار می‌تونم برات بکنم."], None),
    ("good_morning",
     ["صبح بخیر", "صبحت بخیر", "صبح شما بخیر", "صبح بخیر و شادی"],
     ["صبح شما هم بخیر {name} ☀️ امیدوارم روز خوبی داشته باشی!",
      "صبح بخیر {name}! روزت پر از اتفاق‌های خوب باشه 🌅"], None),
    ("good_night",
     ["شب بخیر", "شبت بخیر", "شب شما بخیر", "شب خوش"],
     ["شب بخیر {name} 🌙 خواب‌های خوب ببینی!",
      "شب خوش {name}؛ فردا می‌بینمت 😴✨"], None),
    ("sleepy",
     ["خوابم میاد", "خوابم گرفته", "خیلی خوابم میاد", "میرم بخوابم", "برم بخوابم"],
     ["پس بهتره یه استراحت حسابی بکنی {name}؛ خواب خوب لازمه 😴🌙",
      "برو بخواب {name} جان، شب بخیر و خواب‌های خوب! 🌙"], None),
    ("wellbeing",
     ["حالت چطوره", "چه حالی داری", "خسته نباشی", "چطوری", "خوبی", "احوالت چطوره", "اوضاع چطوره", "چه خبرا",
      "چه خبر", "خبری هست", "حالت خوبه", "خوب هستی", "چطور هستی", "سلامتی",
      "چیکار میکنی", "چی کار میکنی", "چیکار میکنی الان", "مشغول چی هستی", "چه میکنی"],
     ["ممنونم، همیشه آماده و سرحالم! تو چطوری {name} جان؟",
      "عالی‌ام، مرسی که پرسیدی. آماده‌ی کمک به توام؛ دقیقاً چی لازم داری؟",
      "همیشه در بهترین حالت کاری‌ام، چون آفلاین و بدون وقفه فعالم! 😄",
      "خوبم، مرسی از توجهت {name} جان! امروز قراره چه کاری با هم انجام بدیم؟"], None),
    ("are_you_there",
     ["هستی", "اونجایی", "اینجایی", "بیداری", "زنده ای", "زنده هستی", "جواب بده", "کجایی"],
     ["بله {name}، اینجام! بفرمایید 😊",
      "همیشه اینجام و آماده‌ام؛ چه کاری از دستم برمیاد؟"], None),
    ("identity",
     ["خودتو معرفی کن", "اسمت چیه", "کی هستی", "معرفی کن", "تو کی هستی", "چی هستی", "تو چه رباتی هستی",
      "چه جور رباتی هستی", "اسم تو چیه", "شما کی هستید", "چه اسمی داری"],
     ["من «دستیار هوشمند» این گروهم؛ امکاناتی مثل فال و تاروت با منبع آنلاین واقعی، "
      "بازی گروهی گرگینه، مدیریت و نظم‌دهی گروه و یادآورهای زمان‌بندی‌شده دارم. با /start شروع کن.",
      "من دستیار هوشمند و چندمنظوره‌ی این گروهم 🤖 — از فال و تاروت گرفته تا مدیریت کامل گروه و بازی گروهی، همه‌چی دارم.",
      "اسمم دستیار هوشمنده! برای دیدن فهرست کامل امکاناتم /start رو بزن."], None),
    ("creator",
     ["برنامه نویست کیه", "سازنده ات کیه", "سازندت کیه", "کی درستت کرد", "کی ساختت", "مالکت کیه",
      "کی تو رو طراحی کرده", "توسعه دهندت کیه", "کی تو رو ساخته", "کی نوشتتت"],
     ["منو ادمین‌های همین گروه راه‌اندازی و پیکربندی کردن؛ در خدمت شما و اعضای گروهم.",
      "یه توسعه‌دهنده‌ی مستقل منو برای این گروه طراحی و تنظیم کرده."], None),
    ("real_ai_question",
     ["واقعا هوش مصنوعی هستی", "واقعا هوشمندی", "ربات واقعی هستی", "chatgpt هستی", "جیپیتی هستی",
      "تو مثل چت جی پی تی هستی", "هوش مصنوعی هستی", "تو هوش مصنوعی هستی", "آدمی یا ربات"],
     ["به‌طور دقیق، من یه دستیار قانون‌محورِ آفلاینم؛ نیت پیامت رو تشخیص می‌دم و بر اساس اون جواب می‌دم - "
      "به یه مدل زبانی بزرگ متصل نیستم، ولی برای فال، تاروت، مدیریت گروه و محاسبات دقیق (مثل ساعت و تاریخ) کاملاً قابل اتکام.",
      "من از یه موتور تشخیص‌الگوی هوشمند و آفلاین استفاده می‌کنم، نه یه سرویس هوش مصنوعیِ متصل به اینترنت. "
      "همینم باعث می‌شه سریع، رایگان و همیشه در دسترس باشم."], None),
    ("capabilities",
     ["چه امکاناتی داری", "چه کاری بلدی", "چیکار بلدی", "چیکارا میکنی", "کمک", "راهنما", "چه کارایی میتونی بکنی",
      "چه دستوراتی داری", "چیکار میتونی بکنی", "چه کارایی بلدی", "کمک میخوام", "راهنمایی میخوام"],
     ["برای دیدن فهرست کامل امکاناتم دستور /start رو بزن؛ یه منوی کامل و دسته‌بندی‌شده براش طراحی شده.",
      "من فال، تاروت (با منبع آنلاین واقعی)، فال حافظ، بازی گروهی گرگینه، مدیریت و نظم‌دهی گروه، "
      "یادآور زمان‌بندی‌شده و چند سرگرمی دیگه هم دارم. با /start شروع کن.",
      "امکانات من رو می‌تونی از منوی /start ببینی؛ هم ابزارهای سرگرمی دارم هم ابزارهای مدیریتیِ حرفه‌ای."], None),
    ("games",
     ["بازی کنیم", "بازی بلدی", "یه بازی بگو", "بازی داری", "بریم بازی", "بازی"],
     ["بازی‌های من: /gorgineh (گرگینه گروهی)، /td (جرأت یا حقیقت)، /wheel (چرخ شانس) و /eightball. کدوم رو دوست داری؟ 🎲"], None),
    ("compliment_me",
     ["یه تعریف از من کن", "بامن تعریف کن", "ازم تعریف کن", "من چطورم", "منو تعریف کن", "از من تعریف کن"],
     ["مطمئنم آدم فوق‌العاده‌ای هستی، همینکه اینجایی و باهام حرف می‌زنی نشونشه! ✨",
      "از لحن پیامت معلومه آدم باحالی هستی 😄"], None),
    ("missing",
     ["دلم برات تنگ شده", "دلتنگتم", "دلم برات تنگ شد", "خیلی دلم برات تنگ شده", "دلم تنگ شده"],
     ["لطف داری {name}! منم از صحبت باهات خوشحال می‌شم، همیشه اینجام 😊"], None),
    ("loneliness",
     ["تنهام", "دلم گرفته", "احساس تنهایی میکنم", "کسی نیست باهام حرف بزنه", "حوصله ندارم کسی نیست"],
     ["می‌فهمم که ممکنه گاهی حس تنهایی بکنی؛ من همیشه اینجام برای گفت‌وگو. "
      "شاید یه سر به /joke یا /wheel بزنی حالت بهتر بشه، یا با یکی از دوستات صحبت کنی 🤍",
      "تنها نیستی، همین‌جا در کنارتم! دوست داری یه فال یا تاروت بگیریم تا حالت عوض شه؟"], None),
    ("sadness",
     ["غمگینم", "ناراحتم", "حالم بده", "حالم خوب نیست", "دلم شکسته", "بغض دارم", "گریه ام گرفته", "افسرده ام"],
     ["متأسفم که حالت خوب نیست {name} جان؛ گاهی حرف زدن کمک می‌کنه، من گوش می‌دم. امیدوارم زودتر بهتر بشی 🤍"], None),
    ("angry",
     ["عصبانیم", "خیلی عصبانی ام", "کلافه ام", "کفری ام", "اعصابم خورده", "حرصم گرفته"],
     ["درکت می‌کنم {name}؛ یه نفس عمیق بکش، بعد اگه خواستی درباره‌اش حرف بزنیم 🌿"], None),
    ("apology",
     ["ببخشید", "معذرت میخوام", "شرمنده", "عذر میخوام", "مزاحم شدم", "ببخشید مزاحم"],
     ["نیازی به عذرخواهی نیست {name} جان، همه‌چی رو به راهه! 😊",
      "مشکلی نیست {name} جان، خیالت راحت باشه."], None),
    ("birthday",
     ["تولدمه", "امروز تولدمه", "تولدم مبارک", "تولد من"],
     ["تولدت مبارک {name}! 🎂🎉 امیدوارم سال جدید زندگیت پر از شادی و موفقیت باشه!"], None),
    ("congrats",
     ["تبریک", "مبارکه", "خبر خوب دارم", "قبول شدم", "استخدام شدم", "موفق شدم"],
     ["تبریک {name}! 🎉 خیلی خوشحال شدم، امیدوارم همیشه موفق باشی!"], None),
    ("good_luck",
     ["برام دعا کن", "آرزوی موفقیت کن", "برام آرزوی موفقیت کن", "امتحان دارم", "مصاحبه دارم", "کنکور دارم", "استرس دارم"],
     ["از ته دل برات آرزوی موفقیت دارم {name}! 🍀 مطمئنم از پسش برمیای.",
      "موفق باشی {name}! خودت رو باور کن، همه‌چی درست می‌شه ✨"], None),
    ("weather_query",
     ["هوا چطوره", "امروز هوا چطوره", "بارون میاد", "هوا سرده یا گرمه", "آب و هوا چطوره", "هوا چطور", "هوا بارونیه"],
     ["متأسفانه من به سرویس آب‌وهوا وصل نیستم، پس نمی‌تونم دقیق بگم؛ می‌تونی از یه اپ هواشناسی مثل "
      "Windy یا سایت هواشناسی کشور استفاده کنی 🌤️"], None),
    ("food_query",
     ["چی بخورم", "گشنمه", "ناهار چی بخورم", "شام چی بپزم", "گرسنمه", "شام چی بخورم", "گرسنه ام", "چی بپزم"],
     ["پیشنهاد من: یه غذای گرم و ساده مثل خورشت یا کباب؛ ولی هرچی دلت می‌خواد بخور، حقته! 😋",
      "گشنگی خطرناکه، سریع یه چیزی بخور! شاید پیتزا یا یه غذای دلچسب ایرانی خوب باشه."], None),
    ("boredom",
     ["حوصلم سررفته", "بی حوصله ام", "حوصله ندارم", "خسته شدم", "چیکار کنیم", "بی حوصلگی", "حوصلم سر رفته", "کسل شدم"],
     ["پیشنهاد می‌کنم یه سر به /wheel (چرخ شانس) یا /td (جرأت یا حقیقت) بزنی - حسابی سرگرمت می‌کنه!",
      "برای رفع بی‌حوصلگی، /joke یا /tarot رو امتحان کن؛ یا بازی گروهی /gorgineh رو راه بنداز."], None),
    ("frustration",
     ["به درد نمیخوری", "بلد نیستی", "کار نمیکنی", "بی فایده ای", "خرابی", "بی مصرفی", "اصلا خوب نیستی", "افتضاحی",
      "چرا جواب نمیدی", "چرا نمیفهمی"],
     ["ببخشید اگه انتظارت رو برآورده نکردم؛ می‌تونی از /start همه‌ی امکاناتم رو دقیق ببینی و امتحان کنی.",
      "متوجه‌ام که شاید دقیقاً چیزی که می‌خواستی نبود؛ برای فهرست کامل و دقیق دستوراتم /start رو بزن."], None),
    ("thanks",
     ["دمت گرم", "ممنون", "مرسی", "تشکر", "سپاس", "خیلی ممنونم", "دستت درد نکنه", "لطف کردی", "ممنونم", "مچکرم", "قربونت"],
     ["خواهش می‌کنم {name} عزیز! هر وقت لازم داشتی در خدمتم 🙌",
      "قابل شما رو نداشت! خوشحال می‌شم بازم کمک کنم.",
      "سپاس از شما {name} جان، همیشه آماده‌ی کمکم."], None),
    ("affection",
     ["دوستت دارم", "عاشقتم", "خیلی خفنی", "محشری", "بهترینی", "عالی هستی", "خیلی خوبی", "مهربونی", "دمت گرم ربات"],
     ["لطف داری {name} جان! از اینکه بهت کمک می‌کنم خیلی خوشحالم 😊",
      "ممنون از محبتت! سعی می‌کنم همیشه بهترین دستیار برای این گروه باشم."], None),
    ("farewell",
     ["خداحافظ", "بای", "فعلا", "میرم", "خدافظ", "فعلا خداحافظ", "میرم دیگه", "تا بعد", "می بینمت"],
     ["خداحافظ {name} جان، هر وقت لازم داشتی صدام کن! 👋",
      "به امید دیدار! من همیشه اینجا و آماده‌ام."], None),
]


# ============================================================
# 🧠 لایه‌ی هوشمندی v7 — پوشش گسترده‌تر و تشخیص محافظه‌کارانه
# چیزی از SMART_INTENTS قبلی حذف نمی‌شود؛ این بخش فقط موضوعات و عبارت‌های
# بیشتری اضافه می‌کند. پیام ناشناخته یا مبهم عمداً بدون پاسخ می‌ماند.
# ============================================================
SMART_INTENTS_V7_EXTRA = [
    ("help_start", ["کمک میخوام", "کمک لازم دارم", "میتونی کمکم کنی", "میشه کمکم کنی", "کمکم میکنی", "راهنمایی میخوام", "یه راهنمایی میخوام", "چطور ازت استفاده کنم", "چجوری ازت استفاده کنم", "چطور با ربات کار کنم", "دستورات ربات", "لیست دستورات", "لیست امکانات", "منوی ربات", "راهنمای ربات"], ["حتماً {name} 🌿 اگر دنبال امکانات و دستورها هستی، /start رو بزن تا منوی کامل ربات رو ببینی.", "حتماً. برای اینکه راهنمایی دقیق بگیری، موضوعت رو مشخص بگو؛ فهرست قابلیت‌ها هم با /start باز می‌شه."], None),
    ("who_am_i", ["من کیم", "من کی هستم", "اسم من چیه", "منو میشناسی", "منو میشناسی ربات", "درباره من چی میدونی"], ["من اطلاعات شخصی قابل اعتمادی درباره هویتت ندارم؛ فقط چیزهایی رو می‌بینم که در همین پیام و اطلاعات مجاز تلگرام در دسترسمه."], None),
    ("thanks_more", ["خیلی لطف کردی", "واقعا ممنون", "واقعاً ممنون", "از کمکت ممنونم", "ممنون بابت کمکت", "مرسی رفیق", "دمت گرم رفیق", "کارت درسته", "عالی بود", "خیلی خوب بود", "زنده باشی"], ["خواهش می‌کنم {name} 🌱 خوشحالم که به کارت اومد.", "قربانت {name}؛ خوشحالم که مفید بودم 🙌", "اختیار داری! هر وقت موضوع مشخصی داشتی بگو."], None),
    ("how_are_you_more", ["خودت خوبی", "خودت چطوری", "اوضاعت چطوره", "همه چی خوبه", "چه خبر از خودت", "امروز چطوری", "روزت چطور بود", "خوب میگذره"], ["خوبم {name} 😊 آماده‌ام کمک کنم. تو چطوری؟", "همه‌چیز مرتبه و آماده‌ام؛ بگو امروز چه کاری داری."], None),
    ("confusion", ["نفهمیدم", "متوجه نشدم", "یعنی چی", "منظورت چیه", "چی میگی", "چی داری میگی", "نفهمیدم چی گفتی", "این یعنی چی", "این چیه"], ["حتماً روشن‌تر توضیح می‌دم؛ فقط بگو کدوم بخش برات نامفهوم بود.", "باشه؛ اگر پیام قبلی من مبهم بود، همون قسمت رو بگو تا دقیق‌تر توضیح بدم."], None),
    ("agreement", ["باشه", "اوکی", "اوکیه", "قبوله", "درسته", "آره درسته", "بله درسته", "باشه ربات", "اوکی ربات"], ["باشه 😊", "اوکی، حله 👍", "حتماً."], None),
    ("disagreement", ["نه اینطور نیست", "اشتباه میکنی", "اشتباه گفتی", "این درست نیست", "درست نگفتی", "جوابت اشتباهه", "جواب اشتباه دادی"], ["ممکنه حق با تو باشه. اگر بگی کدوم بخش اشتباهه، همون مورد رو دوباره بررسی می‌کنم.", "باشه؛ نمی‌خوام روی جواب نادرست پافشاری کنم. بخش موردنظرت رو مشخص کن."], None),
    ("weather_unavailable", ["فردا بارون میاد", "فردا هوا چطوره", "امشب بارون میاد", "هوا فردا چطوره", "پیش بینی هوا", "پیشبینی هوا", "دمای هوا", "چند درجه است", "چند درجه میشه"], ["برای پیش‌بینی لحظه‌ای هوا به سرویس هواشناسی وصل نیستم، پس نمی‌خوام حدس بزنم و جواب اشتباه بدم. 🌤️"], None),
    ("calculation_request", ["حساب کن", "حسابش کن", "محاسبه کن", "این رو حساب کن", "این عدد رو حساب کن", "جمع کن", "تفریق کن", "ضرب کن", "تقسیم کن", "درصدش چنده", "چند درصد میشه"], ["حتماً؛ عبارت یا عددهایی که می‌خوای محاسبه بشن رو کامل بفرست تا دقیق حساب کنم."], None),
    ("reminder_query", ["یادآور داری", "یادآوری داری", "یادآور ربات", "یادآوری ربات", "یادآورها چیه", "یادآور فعاله", "یادآور روشنه", "یادآور خاموشه"], ["یادآورهای زمان‌بندی‌شده از قابلیت‌های ربات هستند؛ وضعیت و تنظیماتشان از پنل مدیریتی گروه قابل کنترل است."], None),
    ("group_management_question", ["میتونی گروه رو مدیریت کنی", "میتونی گروه رو اداره کنی", "مدیریت گروه بلدی", "ادمین گروه چه کارایی داری", "چه کار مدیریتی بلدی", "میتونی کاربر رو میوت کنی", "میتونی کسی رو بن کنی", "میتونی اخطار بدی", "میتونی پیام رو پاک کنی"], ["بله؛ ابزارهای مدیریتی مثل اخطار، محدودکردن، آزادکردن، حذف پیام و چند ابزار مدیریتی دیگر دارم. جزئیات دستورها را می‌توانی با /start ببینی."], None),
    ("games_more", ["چه بازی هایی داری", "چه بازیهایی داری", "چه بازی هایی بلدی", "بازی هات چیه", "چه سرگرمی هایی داری", "سرگرمی چی داری", "یه سرگرمی بگو"], ["چند بازی و سرگرمی دارم؛ از گرگینه و جرأت یا حقیقت گرفته تا چرخ شانس و چند مورد دیگر. /start فهرست را نشان می‌دهد."], None),
    ("tarot_explain", ["تاروت چیه", "فال تاروت چیه", "تاروت یعنی چی", "تاروت چطور کار میکنه", "فال تاروت چطور کار میکنه", "کارت تاروت یعنی چی"], ["تاروت یک روش نمادین برای تفسیر کارت‌هاست؛ من آن را به‌عنوان سرگرمی و تفسیر نمادین ارائه می‌کنم، نه پیش‌بینی قطعی آینده."], None),
    ("fal_explain", ["فال چیه", "فال یعنی چی", "فال چطور کار میکنه", "فال گرفتن یعنی چی", "فال واقعی هست", "فال آینده رو میگه"], ["فال را بهتره به چشم سرگرمی و تفسیر نمادین دید، نه یک روش قطعی برای پیش‌بینی آینده."], None),
    ("privacy_question", ["پیام منو میبینی", "چه چیزایی از من میبینی", "اطلاعات منو داری", "اطلاعات من دستته", "اطلاعات منو ذخیره میکنی", "پیامام ذخیره میشه", "اطلاعات کاربر رو نگه میداری"], ["من فقط به اطلاعات و پیام‌هایی دسترسی دارم که تلگرام و کد ربات در همان لحظه در اختیارم می‌گذارند؛ درباره داده‌ای که واقعاً ذخیره می‌شود، باید به کد و فایل‌های تنظیمات ربات رجوع کرد."], None),
    ("thanks_after_help", ["حل شد", "درست شد", "مشکلم حل شد", "مشکل حل شد", "الان درست شد", "اوکی شد"], ["عالیه 😄 خوشحالم که حل شد.", "چه خوب! پس مشکل برطرف شد 🙌"], None),
    ("encouragement", ["خسته نباشی", "خسته نباشید", "موفق باشی", "برات آرزوی موفقیت دارم", "امیدوارم موفق بشی", "دمت گرم که هستی"], ["ممنون {name} 🌿 همچنین برای تو بهترین‌ها رو آرزو می‌کنم.", "مرسی از انرژی خوبت {name} ✨"], None),
]
SMART_INTENTS.extend(SMART_INTENTS_V7_EXTRA)

# ============================================================
# v25 — Smart Assistant 2.5: واژگان و مکالمهٔ طبیعی‌تر
# فقط قابلیت اضافه می‌شود؛ Intentهای قبلی حذف یا جایگزین نمی‌شوند.
# ============================================================
SMART_INTENTS_V25_EXTRA = [
    ("thanks", ["ممنون", "مرسی", "خیلی ممنون", "دمت گرم", "دستت درد نکنه", "ممنونم", "سپاس", "متشکرم", "مرسی ازت"],
     ["خواهش می‌کنم {name} 🌿 خوشحالم که به دردت خورد.", "قربانت {name} ✨ هر وقت کاری داشتی بگو.", "خواهش می‌کنم 😊 خوشحال شدم که تونستم کمکت کنم."], None),
    ("apology", ["ببخشید", "ببخش", "معذرت میخوام", "شرمنده", "ببخشید که", "معذرت"],
     ["اشکالی نداره {name} 🌿 راحت باش.", "اصلاً مشکلی نیست {name}؛ ادامه بدیم 😊", "نگران نباش، پیش میاد ✨ بگو ببینم چی شده."], None),
    ("agreement", ["باشه", "اوکی", "اوکیه", "قبوله", "درسته", "آره درسته", "حتماً", "حتما"],
     ["عالیه {name} ✨ پس بریم ادامه بدیم.", "باشه 😊 هر وقت آماده بودی ادامه می‌دیم.", "حتماً {name} 🌿"], None),
    ("confusion", ["نفهمیدم", "متوجه نشدم", "نفهمیدم چی شد", "یعنی چی", "منظورت چیه", "منظورت چیست", "واضح نیست", "گیج شدم"],
     ["حق داری؛ بذار ساده‌تر توضیحش بدم {name}. 🌿", "حتماً، از اول و مرحله‌به‌مرحله می‌گم تا واضح‌تر بشه.", "اشکالی نداره 😊 بگو کدوم قسمت نامفهوم بود تا همون بخش رو توضیح بدم."], None),
    ("continue_request", ["ادامه بده", "ادامه شو بگو", "ادامه اش", "بعدش چی", "بعدش چه شد", "حالا چی", "خب بعدش", "ادامه"],
     ["حتماً {name}؛ ادامه می‌دم و از همون‌جایی که موندیم پیش می‌ریم. ✨", "باشه 🌿 بریم سراغ ادامه‌ش.", "چشم {name}؛ ادامه‌ی همون موضوع رو می‌گم."], None),
    ("explain_request", ["توضیح بده", "بیشتر توضیح بده", "کامل توضیح بده", "ساده توضیح بده", "یه کم توضیح بده", "با مثال توضیح بده", "مثال بزن"],
     ["حتماً {name}؛ ساده و مرحله‌به‌مرحله توضیح می‌دم. 🌿", "چشم 😊 اول اصل موضوع رو می‌گم، بعد اگر لازم بود مثال هم می‌زنم.", "حتماً؛ بریم از بخش ساده‌تر شروع کنیم تا قاطی نشه."], None),
    ("boredom", ["حوصله ام سر رفته", "حوصله‌ام سر رفته", "حوصلم سر رفته", "حوصله ندارم", "حوصله نیست", "کسل شدم", "حوصلم نیست"],
     ["پس یه چیزی پیدا کنیم که از این حالت دربیای 😄 می‌خوای بازی کنیم یا یه گپ کوتاه داشته باشیم؟", "حوصله‌ات سر رفته؟ 🎮 می‌تونیم UNO، گرگینه، جرأت یا حقیقت یا یه گفت‌وگوی خودمونی داشته باشیم.", "باشه، یه تنوع کوچیک بد نیست 😄 بازی یا گپ؟"], None),
    ("happy", ["خوشحالم", "خیلی خوشحالم", "امروز خوب بود", "امروز عالی بود", "خیلی خوب شد", "حال کردم", "خیلی حال داد"],
     ["چه خوب {name} ✨ همین حس خوب رو نگه دار.", "عالیه 😄 خوشحالم که روزت خوب گذشته. چی بیشتر خوشحالت کرد؟", "چه خوب 🌿 از این خبرها بیشتر بگو."], None),
    ("frustrated", ["اعصابم خورده", "کلافه ام", "کلافه‌ام", "روی اعصابمه", "حرصم گرفته", "اعصاب ندارم", "خیلی حرصم گرفته"],
     ["آروم‌تر {name} 🌿 اگر دوست داری بگو چی اذیتت کرده تا با هم مرتبش کنیم.", "می‌فهمم که کلافه‌کننده‌ست؛ بگو دقیقاً کدوم قسمت اذیتت کرده.", "یه نفس و بعد از اول نگاهش کنیم؛ شاید راه ساده‌تری داشته باشه."], None),
    ("check_in", ["هنوز هستی", "هنوز اینجایی", "جواب میدی", "صدای منو داری", "پیامم رسید", "پیام منو دیدی"],
     ["آره {name}، اینجام 😊 ادامه بده.", "بله، پیامت رسید 🌿 بگو ببینم.", "اینجام و حواسم به پیامت هست ✨"], None),
    ("choice_help", ["کدوم رو انتخاب کنم", "کدوم بهتره", "کدومو بردارم", "چه کار کنم", "چی کار کنم", "چیکار کنم", "پیشنهادت چیه"],
     ["اول گزینه‌هات رو بگو {name}؛ با هم مزایا و معایبشون رو بررسی می‌کنیم.", "حتماً. گزینه‌ها رو بفرست تا بدون حدس و گمان مقایسه‌شون کنیم.", "بگو بین چه چیزهایی مرددی تا قدم‌به‌قدم بررسی کنیم."], None),
    ("short_chat", ["خب", "خوب", "اوکی", "باشه خب", "آها", "آهان", "عه", "جدی", "واقعاً", "راستی"],
     ["هوم 😄 بگو ببینم.", "آها، دارم گوش می‌دم 🌿 ادامه بده.", "خب خب 😄 منتظرم ببینم چی می‌خوای بگی."], None),
]
SMART_INTENTS.extend(SMART_INTENTS_V25_EXTRA)

# v40 — چند intent کم‌ریسک برای راهنمایی بهتر Gaming Center و مدیریت بازی
SMART_INTENTS_V40_EXTRA = [
    ("td_rules", ["قوانین جرأت حقیقت", "قانون جرأت حقیقت", "چطور جرأت حقیقت", "جرأت حقیقت چطوریه"], ["🎭 جرأت یا حقیقت نوبتی است؛ انتخاب داخل گروه انجام می‌شود، سؤال/چالش در گروه دیده می‌شود و پاسخ فقط در Private بررسی می‌شود. پاسخ برای استفاده بعدی ذخیره نمی‌شود و نوبت بعدی خودکار ادامه پیدا می‌کند."], None),
    ("td_scoring", ["امتیاز جرأت حقیقت", "امتیاز بازی", "امتیازها چطور", "امتیازدهی بازی"], ["🏆 امتیاز جرأت یا حقیقت بر اساس انجام موفق نوبت ثبت می‌شود؛ حقیقت و جرأت امتیاز پایه متفاوت دارند و پاسخ موفق در تلاش اول پاداش دارد."], None),
    ("gaming_help", ["چه بازی هایی داری", "بازی ها چیه", "بازی چی داریم", "لیست بازی ها"], ["🎮 در Gaming Center بازی‌هایی مثل گرگینه، UNO، جرأت یا حقیقت در دسترس هستند."], None),
]
SMART_INTENTS.extend(SMART_INTENTS_V40_EXTRA)




# کلیدواژه‌ها هم با همون نرمال‌سازیِ متن ورودی، یکدست می‌شن (فقط یک بار، موقع بارگذاری)
_SMART_INTENTS_NORM = [
    (label, [(_smart_normalize(kw) or kw).split() for kw in kws], responses, dyn)
    for label, kws, responses, dyn in SMART_INTENTS
]


def _best_intent_match(norm: str):
    """تشخیص محافظه‌کارانه‌ی نیت؛ عبارت‌های دقیق‌تر امتیاز بیشتری می‌گیرند."""
    tokens=[t for t in norm.split() if t]
    if not tokens:
        return None
    weak={"سلام","بازی","فال","تاروت","ساعت","تاریخ","کمک","راهنما","ممنون","مرسی","نه","خب","خوب","باشه","اوکی","هستی","کجایی"}
    # نفی نزدیک به کلیدواژه یعنی کاربر احتمالاً آن کار را نمی‌خواهد/درخواست نکرده.
    negations={"نمیخوام","نمیخواد","نمیخوامش","نکن","نکنه","نزن","نزنش","نه","نباشه","نیست","نمیشه","نمیخوام"}
    candidates=[]
    for label,kw_lists,responses,dyn in _SMART_INTENTS_NORM:
        if label=="call_only": continue
        for kw_tokens in kw_lists:
            k=len(kw_tokens)
            if not k or k>len(tokens): continue
            for i in range(len(tokens)-k+1):
                if tokens[i:i+k]==kw_tokens:
                    # اگر در سه واژه‌ی قبل نفی آمده باشد، این تطابق را نادیده بگیر.
                    before=tokens[max(0,i-3):i]
                    if any(n in before for n in negations):
                        continue
                    score=100+k*35
                    if k==1 and kw_tokens[0] in weak: score-=45
                    if i==0 and i+k==len(tokens): score+=30
                    if k==1 and len(tokens)>=5: score-=30
                    candidates.append((score,k,label,responses,dyn)); break
    if not candidates: return None
    candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
    best=candidates[0]
    second=candidates[1] if len(candidates)>1 else None
    if second and best[0]==second[0] and best[1]==second[1] and best[1]<=1: return None
    if best[0]<125: return None
    return best[2],best[3],best[4]


# v52 — Smart Dialogue state: اجرای واقعی و مقاومِ حافظهٔ مکالمهٔ هوشمند.
# این state فقط در RAM نگه‌داری می‌شود و هرگز متن پیام را روی دیسک ذخیره نمی‌کند.
SMART_DIALOGUE_STATE = {}
SMART_DIALOGUE_STATE_TTL = 20 * 60


def _dialogue_topic(text: str) -> str:
    n = _smart_normalize(text)
    topic = _extract_topic(n)
    if topic:
        return topic
    # دسته‌بندی محافظه‌کارانه برای ادامهٔ مکالمه
    if any(x in n for x in ("فنی", "سرور", "ربات", "کد", "گیتهاب", "لینوکس", "وای فای", "روتر")):
        return "tech"
    if any(x in n for x in ("بازی", "اونو", "گرگینه", "جرأت", "حقیقت")):
        return "games"
    if any(x in n for x in ("گروه", "ادمین", "مدیر", "عضو", "یادآور")):
        return "group"
    if any(x in n for x in ("فیلم", "سریال", "انیمه", "موسیقی", "بازی")):
        return "entertainment"
    return "general"


def _analyze_message_state(text: str, previous_state=None):
    n = _smart_normalize(text)
    words = n.split()
    continuation = _is_followup_message(text)
    topic = _dialogue_topic(text)
    negations = ("نمی", "نه", "نیست", "نمیشه", "نمیخوام", "نکن")
    emotion = "neutral"
    intensity = 0
    if any(x in n for x in ("خوشحالم", "عالیه", "عالی بود", "خیلی خوب", "حال کردم", "ذوق")):
        emotion, intensity = "positive", 2
    elif any(x in n for x in ("خسته", "کلافه", "اعصابم", "حرصم", "ناراحتم", "بد بود", "حالم بده")):
        emotion, intensity = "negative", 2
    elif any(x in n for x in ("ممنون", "مرسی", "دمت گرم", "سپاس")):
        emotion, intensity = "grateful", 1
    elif any(x in n for x in ("نگران", "استرس", "میترسم", "می ترسم")):
        emotion, intensity = "concerned", 2
    # اگر پیام کوتاه ادامه‌ای است، موضوع قبلی را فقط در صورت نبودن موضوع تازه نگه می‌داریم.
    if topic == "general" and continuation and previous_state:
        topic = previous_state.get("topic", "general")
    return {
        "topic": topic,
        "emotion": emotion,
        "intensity": intensity,
        "continuation": continuation,
        "negated": any(x in n for x in negations),
        "length": len(words),
        "ts": time.time(),
    }


def _contextual_emotion_reply(name: str, state: dict, previous_state=None):
    if not state or state.get("negated"):
        return None
    emotion = state.get("emotion")
    if emotion == "positive":
        return random.choice([
            f"چه خوب {name} ✨ خوشحالم که حالت خوبه. اگر دوست داری بگو چی باعثش شد.",
            f"عالیه {name} 😄 این حس خوب رو نگه دار؛ بگو ببینم چه خبر خوبی افتاده؟",
        ])
    if emotion == "negative":
        return random.choice([
            f"می‌فهمم {name} 🌿 اگر دوست داری، بگو دقیقاً کدوم قسمت اذیتت کرده تا مرتب بررسیش کنیم.",
            f"آروم‌تر {name}؛ از همون بخش اصلی شروع کنیم و ببینیم چه کاری از دستمون برمیاد.",
        ])
    if emotion == "grateful":
        return random.choice([
            f"خواهش می‌کنم {name} 🌿 خوشحالم که به کارت اومد.",
            f"قابلی نداشت {name} ✨ هر وقت لازم داشتی ادامه می‌دیم.",
        ])
    if emotion == "concerned":
        return random.choice([
            f"قابل درکه {name} 🌿 بگو نگرانی دقیقاً درباره چیه تا مرحله‌به‌مرحله بررسیش کنیم.",
            f"باشه {name}؛ عجله نکنیم. اول مسئله رو دقیق مشخص کنیم، بعد سراغ راه‌حل بریم.",
        ])
    return None


async def smart_rule_based_reply(
    text: str, name: str, context: ContextTypes.DEFAULT_TYPE, chat, username: "str | None" = None, user_id=None
) -> "str | None":
    if not text or not text.strip():
        return None
    norm = _smart_normalize(text)
    if not norm or len(norm) < 2:
        return None

    # v29: تحلیل مستقل پیام؛ فقط وقتی پیام واقعاً احساسی/دنباله‌ای است از آن برای
    # تغییر لحن استفاده می‌کنیم تا پاسخ‌های قبلی و intentهای موجود از بین نروند.
    state_key = (getattr(chat, "id", 0), user_id)
    previous_state = SMART_DIALOGUE_STATE.get(state_key)
    if previous_state and time.time() - previous_state.get("ts", 0) > SMART_DIALOGUE_STATE_TTL:
        previous_state = None
        SMART_DIALOGUE_STATE.pop(state_key, None)
    common_answer = _smart_common_answer(text)
    if common_answer:
        return common_answer
    state = _analyze_message_state(text, previous_state)
    # v30: اگر پیام کوتاه و ادامه‌ای است و موضوع تازه‌ای ندارد، موضوع قبلی را حفظ کن.
    if previous_state and state.get("continuation") and state.get("topic") == "general":
        state["topic"] = previous_state.get("topic", "general")
    state["ts"] = time.time()
    SMART_DIALOGUE_STATE[state_key] = state
    contextual = _contextual_emotion_reply(name, state, previous_state)
    if contextual and state["emotion"] != "neutral" and (state["continuation"] or state["intensity"] >= 2):
        return contextual

    # پاسخ پویا برای شناخت مالک گروه؛ از اطلاعات واقعی Telegram استفاده می‌کند.
    owner_phrases = ("مالک گروه کیه", "مالک گروه کیه", "صاحب گروه کیه", "گروه مال کیه", "ادمین اصلی کیه", "owner گروه")
    if any(_smart_normalize(x) in norm for x in owner_phrases):
        return await _dyn_owner(name, norm, context, chat)

    match = _best_intent_match(norm)

    # v13: پروفایل رفتاری بر پایه user_id؛ fallback به username قدیمی برای مهاجرت.
    profile = get_user_profile(user_id, username) if user_id is not None else None
    style = profile.get("style") if profile else None
    if profile:
        name = profile.get("display_name") or name
        special_chat = _special_conversation_reply(style, norm, name)
        if special_chat:
            return special_chat

    if match is None:
        # v30: پاسخ ادامه‌ای وابسته به موضوع؛ به‌جای یک «بیشتر بگو» ثابت،
        # از موضوع قبلی استفاده می‌کنیم و فقط در صورت اطمینان کافی پاسخ می‌دهیم.
        if state.get("continuation") and previous_state and previous_state.get("topic") not in (None, "general"):
            topic = previous_state.get("topic")
            if topic == "games":
                return random.choice([
                    f"حتماً {name} 🎮 همون بحث بازی رو ادامه می‌دیم؛ بگو کدوم بخشش رو بیشتر می‌خوای.",
                    f"آره {name}، هنوز توی همون بحث بازی هستیم 🎲؛ جزئیات بیشتری از همون قسمت می‌خوای؟",
                ])
            if topic == "tech":
                return random.choice([
                    f"حتماً {name} 🛠️ همون موضوع فنی رو ادامه می‌دیم؛ آخرین بخشش رو بازتر می‌کنم.",
                    f"باشه {name}، از همون مسئلهٔ فنی ادامه می‌دیم؛ بگو کدوم قسمت برات مبهم‌تره.",
                ])
            if topic == "group":
                return f"حتماً {name} 👥 همون موضوع گروه رو ادامه می‌دیم؛ بگو دقیقاً کدوم بخشش رو می‌خوای."
            if topic == "entertainment":
                return f"حتماً {name} ✨ همون بحث سرگرمی رو ادامه می‌دیم؛ بگو کدوم قسمت رو بیشتر می‌خوای."

        # v25: برای خطاب مستقیم به ربات، چند الگوی بسیار عمومی داریم؛
        # اما پیام‌های نامرتبط همچنان بی‌پاسخ می‌مانند تا ربات مزاحم گفت‌وگوی گروه نشود.
        if any(x in norm for x in ("کمک میخوام", "کمکم کن", "کمک کن", "راهنمایی میخوام", "یه سوال دارم", "سوالی دارم")):
            generic = [
                "حتماً {name} 🌿 سؤال یا مشکلت رو بگو تا با هم بررسیش کنیم.",
                "در خدمتم {name} ✨ موضوع رو بگو؛ اگر بتونم، قدم‌به‌قدم راهنماییت می‌کنم.",
                "بگو {name}، گوش می‌دم. اگر اطلاعات بیشتری لازم باشه هم ازت می‌پرسم."
            ]
            return random.choice(generic).format(name=name)
        return _smart_general_fallback(text, name)

    label, responses, dyn = match
    if dyn is not None:
        result = await dyn(name, norm, context, chat)
        if style and style in SPECIAL_DYNAMIC_PREFIX:
            result = random.choice(SPECIAL_DYNAMIC_PREFIX[style]).format(name=name) + result
        return result

    if style:
        overrides = SPECIAL_STYLE_RESPONSES.get(style, {})
        if label in overrides:
            responses = overrides[label]
    return random.choice(responses).format(name=name, tod=_time_of_day_greeting())



# ============================================================
# v14 — گفت‌وگوی غنی‌تر برای پروفایل‌های ویژه
# پاسخ‌های v13 حذف نشده‌اند؛ این بخش فقط تنوع و مکالمه‌های بیشتری اضافه می‌کند.
# ============================================================
SPECIAL_STYLE_EXTRA_RESPONSES = {
    "sweet_a": {
        "greeting": [
            "سلام {name} 🌸 خوش اومدی، چه خبر ازت؟",
            "آخ جون، {name} اومد 😄🌸 بگو ببینم امروز چه خبر داری؟",
            "سلام {name} جان 🌙 من اینجام؛ هرچی دوست داری بگو، گوش می‌دم.",
            "خوش اومدی {name} ✨ امروز دلت بیشتر گپ می‌خواد یا کمک؟",
        ],
        "call_only": [
            "بله {name}؟ 🌸 اینجام، بگو ببینم چی شده.",
            "جانم {name}؟ 😄 گوشم با توئه، بفرما.",
            "بله، صدام کردی؟ 🌙 بگو، حواسم هست.",
            "در خدمتم {name} ✨ از کجا شروع کنیم؟",
        ],
        "wellbeing": [
            "من خوبم {name} 🌸 ممنون که پرسیدی. تو امروز چه حالی داری؟",
            "فعلاً که خوبم و سرحالم 😄 تو چطور؟ روزت چطور گذشت؟",
            "خوبم {name} جان 🌙 حالا تو بگو؛ امروز بهت خوش گذشت؟",
        ],
        "thanks": [
            "خواهش می‌کنم {name} 🌸 خوشحالم که به کارت اومد.",
            "قابلی نداشت {name}؛ هر وقت لازم داشتی صدام کن ✨",
            "خواهش می‌کنم 😄 حالا بگو ببینم چیز دیگه‌ای هم هست؟",
        ],
        "affection": [
            "چه حرف قشنگی زدی {name} 🌸 مرسی از مهربونیت.",
            "این محبتت واقعاً قشنگه {name} ✨",
            "قربون محبتت برم؟ 😄🌸 خیلی لطف داری.",
        ],
        "compliment_me": [
            "این تعریف رو می‌ذارم به حساب لطف خودت {name} 🌸",
            "مرسی {name} 😄 با این حرفت دستیارمون هم ذوق کرد.",
            "چه تعریف خوبی ✨ ولی تو هم کم لطف نیستی {name}.",
        ],
        "joke_request": [
            "باشه {name} 😄 یه لحظه بذار مغزم رو روی حالت شوخی بذارم...",
            "چشم {name} 🌸 آماده‌ای؟ این یکی رو باید با لبخند بخونی.",
        ],
        "boredom": [
            "اگه حوصله‌ات سر رفته {name}، می‌تونیم یه بازی راه بندازیم یا همین‌جا کمی گپ بزنیم 🌸",
            "پس وقتشه یه کاری کنیم 😄 بازی، فال یا یه گپ کوتاه؟ انتخاب با تو.",
        ],
        "farewell": [
            "فعلاً {name} 🌙 مراقب خودت باش و هر وقت برگشتی من اینجام.",
            "به سلامت {name} 🌸 امیدوارم دفعه بعد با خبرهای خوب برگردی.",
        ],
    },
    "sweet_b": {
        "greeting": [
            "سلام {name} 🌿 خوش اومدی، چه خبر؟",
            "اوه، {name} پیداش شد 😄🧃 بگو ببینم امروز چه خبر داری؟",
            "سلام {name} ✨ من اینجام؛ هرچی دوست داری بگو.",
            "خوش اومدی {name} 🌙 امروز دنبال گپ اومدی یا کمک؟",
        ],
        "call_only": [
            "بله {name}؟ 🧃 اینجام، بگو ببینم چی شده.",
            "جانم {name}؟ 😄 بفرما، حواسم کاملاً هست.",
            "بله، صدام کردی؟ 🌿 بگو، گوش می‌دم.",
            "در خدمتم {name} ✨ بگو از کجا شروع کنیم.",
        ],
        "wellbeing": [
            "من خوبم {name} 🌿 ممنون که پرسیدی. خودت چطوری؟",
            "خوبم و آماده‌ام 😄 تو امروز چه خبر داشتی؟",
            "مرسی که پرسیدی {name} 🧃 حالا نوبت توئه، روزت چطور بود؟",
        ],
        "thanks": [
            "خواهش می‌کنم {name} 🌿 خوشحالم که مفید بود.",
            "قابلی نداشت 🧃 هر وقت لازم داشتی بگو.",
            "خواهش می‌کنم {name} ✨ چیز دیگه‌ای هم خواستی بگو.",
        ],
        "affection": [
            "لطف داری {name} 🌿 حرفت خیلی قشنگ بود.",
            "مرسی از محبتت {name} ✨ واقعاً لطف داری.",
            "این همه مهربونی از کجا میاد؟ 😄🧃 ممنونم.",
        ],
        "compliment_me": [
            "مرسی {name} 🧃 این تعریف رو با افتخار قبول می‌کنم.",
            "چه لطفی داری {name} 🌿 خوشحالم این حس رو داری.",
            "با این تعریف دیگه نمی‌تونم معمولی جواب بدم 😄✨ ممنون.",
        ],
        "joke_request": [
            "چشم {name} 😄 بریم سراغ یه شوخی سبک و جمع‌وجور.",
            "باشه 🧃 آماده‌ای؟ امیدوارم حداقل یه لبخند ازت بگیرم.",
        ],
        "boredom": [
            "حوصله‌ات سر رفته؟ 🌿 می‌تونیم بازی کنیم یا همین‌جا یه کم گپ بزنیم.",
            "پس یه چیزی برای سرگرمی پیدا کنیم 😄 بازی، فال یا گپ؟",
        ],
        "farewell": [
            "فعلاً {name} 🌿 مراقب خودت باش؛ هر وقت برگشتی من اینجام.",
            "به امید دیدار {name} ✨ امیدوارم باقی روزت خوب بگذره.",
        ],
    },
}

for _style_name, _extra_map in SPECIAL_STYLE_EXTRA_RESPONSES.items():
    _target_map = SPECIAL_STYLE_RESPONSES.setdefault(_style_name, {})
    for _intent_name, _extra_items in _extra_map.items():
        _target_map.setdefault(_intent_name, []).extend(_extra_items)


SPECIAL_CONVERSATION_PATTERNS = {
    "sweet_a": [
        ("خودت چی", "من؟ 😄 من فعلاً اینجام که باهات گپ بزنم و هر کمکی از دستم برمیاد انجام بدم {name} 🌸"),
        ("تو چی", "من که همیشه آماده‌ام 😄🌙 ولی این بار تو بگو؛ امروز چه چیزی بیشتر ذهنت رو مشغول کرده؟ {name}"),
        ("چه خبر", "خبر خاصی نیست {name} 🌸 همین که اومدی خودش یه خبر خوبه. تو چه خبر؟"),
        ("امروز چه خبر", "امروز هم طبق معمول اینجام و منتظر حرفاتم 😄🌸 تو بگو روزت چطور گذشته؟"),
        ("حوصله داری", "برای گپ با تو که همیشه حوصله دارم {name} 🌸 بگو ببینم درباره چی حرف بزنیم؟"),
        ("حرف بزن", "باشه 😄 از خودت شروع کنیم؛ این روزها بیشتر سرت با چی گرمه {name}؟ 🌙"),
        ("گپ بزن", "حتماً 🌸 یه گپ خودمونی خوبه. تو شروع کن، من همراهتم."),
        ("بگو ببینم", "چشم {name} 😄 فقط موضوع رو بده دستم تا شروع کنم."),
        ("یه چیزی بگو", "باشه 🌸 امروز یه چیز ساده: گاهی یه گفت‌وگوی کوتاه می‌تونه حال آدم رو بهتر کنه. حالا تو بگو، چه خبر؟"),
        ("دلم گرفته", "اوه {name} 🌸 اگر دوست داری حرف بزن، من گوش می‌دم. لازم نیست همه‌چیز رو یک‌دفعه توضیح بدی."),
        ("خسته ام", "پس یکم آروم‌تر پیش بریم {name} 🌙 اگر دوست داری فقط گپ بزنیم، من هستم."),
        ("خوابم نمیبره", "اگه خوابت نمی‌بره {name} 🌙 می‌تونیم یه گپ آروم داشته باشیم تا ذهنت کمی از شلوغی فاصله بگیره."),
    ],
    "sweet_b": [
        ("خودت چی", "من؟ 😄🧃 من فعلاً اینجام که باهات گپ بزنم و کمکت کنم {name}."),
        ("تو چی", "من همیشه آماده‌ام 🌿 ولی این بار تو بگو؛ امروز چه چیزی بیشتر فکرت رو درگیر کرده؟"),
        ("چه خبر", "خبر خاصی نیست {name} 🌿 همین که اومدی خوبه. از خودت بگو، چه خبر؟"),
        ("امروز چه خبر", "امروز هم اینجام و طبق معمول آماده‌ی گپم 😄 تو بگو روزت چطور گذشت؟"),
        ("حوصله داری", "برای یه گپ خوب که حتماً 🧃 بگو ببینم درباره چی حرف بزنیم؟"),
        ("حرف بزن", "چشم 😄 تو موضوع رو بده، من ادامه‌ش می‌دم {name} 🌿"),
        ("گپ بزن", "حتماً 🌿 یه گپ خودمونی بد نیست. تو شروع کن."),
        ("بگو ببینم", "چشم {name} 🧃 بگو دنبال چه جور جوابی هستی؟"),
        ("یه چیزی بگو", "باشه 😄 یه چیز ساده: بعضی وقت‌ها یه گفت‌وگوی کوتاه هم می‌تونه روز رو بهتر کنه. تو چه خبر؟"),
        ("دلم گرفته", "اگه دوست داری حرف بزنی {name} 🌿 من گوش می‌دم. لازم نیست عجله کنی."),
        ("خسته ام", "پس آروم‌تر پیش می‌ریم {name} 🧃 اگه خواستی فقط گپ بزنیم، من هستم."),
        ("خوابم نمیبره", "اگر خوابت نمی‌بره 🌙 می‌تونیم یه گپ آروم داشته باشیم تا ذهنت کمی مشغول بشه."),
        ("ممنون", "خواهش می‌کنم {name} 🌸 خوشحالم که تونستم کمکت کنم."),
        ("دمت گرم", "قربونت {name} 😄🌸 خوشحالم که به کارت اومد."),
        ("ببخشید", "اشکالی نداره {name} 🌸 راحت باش، ادامه بده."),
        ("نفهمیدم", "اشکالی نداره {name} 🌸 بذار ساده‌تر و قدم‌به‌قدم توضیحش بدم."),
        ("یعنی چی", "حتماً {name} 🌙 منظورم رو ساده‌تر می‌گم تا کامل روشن بشه."),
        ("ادامه بده", "چشم {name} 🌸 از همون‌جایی که موندیم ادامه می‌دیم."),
        ("بیشتر توضیح بده", "حتماً {name}؛ این بار جزئی‌تر و با مثال توضیح می‌دم. ✨"),
        ("حوصله ام سر رفته", "پس یه تنوع کوچیک بد نیست {name} 😄🌸 بازی کنیم یا یه گپ خودمونی؟"),
        ("چی کار کنم", "اول بگو چه گزینه‌هایی جلوت هست {name}؛ با هم مرتبشون می‌کنیم 🌙"),
        ("راستی", "جانم {name} 🌸 راستی چی؟ بگو، کنجکاو شدم."),
    ],
}


def _special_conversation_reply(style, norm, name):
    """پاسخ‌های مکالمه‌ای ویژه؛ فقط برای پروفایل‌های ویژه فعال می‌شود."""
    if not style:
        return None
    patterns = SPECIAL_CONVERSATION_PATTERNS.get(style, [])
    for phrase, response in patterns:
        if _smart_normalize(phrase) in norm:
            return response.format(name=name)
    return None

# ============================================================
# آرکانای بزرگ (۲۲ کارت) و کوچک (۵۶ کارت)
# ============================================================
MAJOR_ARCANA = [
    ("دلقک", "The Fool", "شروع تازه، ماجراجویی و اعتماد به مسیر جدید."),
    ("جادوگر", "The Magician", "قدرت اراده، مهارت و به‌کارگیری استعدادها."),
    ("کاهنه", "The High Priestess", "شهود، رازها و دانش پنهان."),
    ("امپراتریس", "The Empress", "فراوانی، خلاقیت و رشد."),
    ("امپراتور", "The Emperor", "نظم، ساختار و کنترل بر شرایط."),
    ("پاپ / خردمند", "The Hierophant", "سنت، آموزش و راهنمایی معنوی."),
    ("عاشقان", "The Lovers", "انتخاب مهم، هماهنگی و رابطه."),
    ("ارابه", "The Chariot", "اراده قوی، پیروزی با تلاش و کنترل."),
    ("قدرت", "Strength", "شجاعت درونی و کنترل احساسات."),
    ("زاهد", "The Hermit", "درون‌نگری، تنهایی سازنده و جست‌وجوی حقیقت."),
    ("چرخ بخت", "Wheel of Fortune", "تغییر ناگهانی سرنوشت، فرصت‌های تازه."),
    ("عدالت", "Justice", "انصاف، حقیقت و پیامدهای اعمال."),
    ("مرد آویزان", "The Hanged Man", "تعلیق، دیدگاه تازه، فداکاری."),
    ("مرگ", "Death", "پایان یک دوره و آغاز تحول بزرگ."),
    ("اعتدال", "Temperance", "تعادل، صبر و ترکیب هماهنگ."),
    ("اهریمن", "The Devil", "وابستگی، محدودیت‌های خودساخته."),
    ("برج", "The Tower", "تغییر ناگهانی و فروریختن باورهای غلط."),
    ("ستاره", "The Star", "امید، الهام و آرامش پس از سختی."),
    ("ماه", "The Moon", "ابهام، ترس‌های پنهان و ناخودآگاه."),
    ("خورشید", "The Sun", "شادی، موفقیت و انرژی مثبت."),
    ("داوری", "Judgement", "بیداری، ارزیابی و تصمیم سرنوشت‌ساز."),
    ("دنیا", "The World", "تکمیل یک دوره، رسیدن به هدف."),
]
MINOR_SUITS = {
    "جام (Cups)": "احساسات، روابط و عشق",
    "پنتاکل (Pentacles)": "مال، کار و مسائل مادی",
    "شمشیر (Swords)": "فکر، چالش و تصمیم‌گیری",
    "چوبدستی (Wands)": "انرژی، خلاقیت و شور",
}
MINOR_RANKS = [
    "آس", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده",
    "پیک (Page)", "شوالیه (Knight)", "ملکه (Queen)", "شاه (King)",
]

# نیّتِ/انرژیِ هر «رتبه» - برای اینکه معنی کارت‌های کوچک به‌جای یه جمله‌ی
# تکراری («مرتبط با ...»)، هرکدوم شخصیت مستقل و معنادار خودشون رو داشته باشن
RANK_NUANCE_FA = {
    "آس": "یک شروع تازه، خام و پرانرژی؛ بذر یه اتفاق نو که تازه کاشته شده",
    "دو": "یک انتخاب یا توازن مهم بین دو مسیر",
    "سه": "رشد اولیه، همکاری و جوونه زدن نتیجه‌ی تلاش‌های قبلی",
    "چهار": "ثبات، آرامش نسبی و تثبیت شرایط فعلی",
    "پنج": "یک چالش یا کشمکش موقتی که باید ازش عبور کنی",
    "شش": "بازگشت هماهنگی و تعادل بعد از یه دوره‌ی سخت",
    "هفت": "زمان ارزیابی، صبر و بازبینی مسیر",
    "هشت": "تلاش پیوسته، تمرکز و پیشرفت آروم ولی مطمئن",
    "نه": "نزدیک شدن به نتیجه؛ یه قدم تا هدف فاصله داری",
    "ده": "تکمیل یک چرخه و آماده شدن برای فصل بعدی زندگی",
    "پیک (Page)": "یه پیام، خبر یا یادگیری تازه که داره بهت می‌رسه",
    "شوالیه (Knight)": "حرکت، جسارت و یه اقدام جدی که باید انجامش بدی",
    "ملکه (Queen)": "بلوغ درونی، شهود و مدیریت هوشمندانه‌ی احساسات",
    "شاه (King)": "تسلط بیرونی، مسئولیت‌پذیری و تصمیم‌گیری قاطع",
}

TAROT_REVERSED_NOTE = "\n\n(این کارت امروز به‌صورت معکوس اومده، یعنی همین انرژی داره از درون یا با تأخیر خودشو نشون می‌ده.)"

TAROT_ADVICE_CLOSERS = [
    "🔎 جمع‌بندی و توصیه: امروز رو با آرامش جلو برو و به دلت گوش بده.",
    "🔎 جمع‌بندی و توصیه: یه قدم کوچیک ولی مطمئن بردار، نتیجه‌ش رو خیلی زود می‌بینی.",
    "🔎 جمع‌بندی و توصیه: قبل از هر تصمیمی، یه نفس عمیق بکش و دوباره فکر کن.",
    "🔎 جمع‌بندی و توصیه: با کسی که بهش اعتماد داری مشورت کن، دیدگاه تازه‌ای می‌گیری.",
    "🔎 جمع‌بندی و توصیه: امروز روز خوبیه برای شفاف‌سازی یه رابطه یا موضوع نیمه‌کاره.",
    "🔎 جمع‌بندی و توصیه: به‌جای عجله، روی کیفیت کارت تمرکز کن.",
    "🔎 جمع‌بندی و توصیه: یه فرصت کوچیک رو دست‌کم نگیر، می‌تونه شروع چیز بزرگی باشه.",
    "🔎 جمع‌بندی و توصیه: به خودت زمان بده؛ همه‌چی لازم نیست همین امروز حل بشه.",
]

# نگاشت انگلیسی↔فارسی، برای وقتی که یه کارت واقعی از سایت tarotapi.dev گرفته می‌شه
RANK_EN2FA = {
    "ace": "آس", "two": "دو", "three": "سه", "four": "چهار", "five": "پنج",
    "six": "شش", "seven": "هفت", "eight": "هشت", "nine": "نه", "ten": "ده",
    "page": "پیک (Page)", "knight": "شوالیه (Knight)",
    "queen": "ملکه (Queen)", "king": "شاه (King)",
}
SUIT_EN2FA = {
    "cups": "جام (Cups)", "pentacles": "پنتاکل (Pentacles)",
    "swords": "شمشیر (Swords)", "wands": "چوبدستی (Wands)",
}
MAJOR_EN2FA = {en: (fa, meaning) for fa, en, meaning in MAJOR_ARCANA}


def build_full_tarot_deck():
    deck = [(f"{fa} ({en})", meaning) for fa, en, meaning in MAJOR_ARCANA]
    for suit, theme in MINOR_SUITS.items():
        for rank in MINOR_RANKS:
            nuance = RANK_NUANCE_FA.get(rank, "")
            deck.append((f"{rank} {suit}", f"{nuance}، در حوزه‌ی {theme}."))
    return deck


TAROT_DECK_FULL = build_full_tarot_deck()


def map_tarotapi_card_to_persian(name_en: str):
    """اسم کارتی که از سایت واقعی tarotapi.dev گرفته می‌شه رو به معادل فارسیِ
    خودمون توی دک آفلاین نگاشت می‌کنه. اگه نتونه match کنه None برمی‌گردونه
    (و کد صدازننده خودکار می‌ره سراغ یه کارت کاملاً آفلاین)."""
    name_en = (name_en or "").strip().lower()
    if not name_en:
        return None
    # آرکانای بزرگ: اسم دقیقاً باید با یکی از ۲۲ تا برابر باشه
    for en, (fa, meaning) in MAJOR_EN2FA.items():
        if en.lower() == name_en:
            return f"{fa} ({en})", meaning
    # آرکانای کوچک: فرمت رایج API چیزی شبیه "ace of cups" یا "two of wands"
    if " of " in name_en:
        rank_part, suit_part = name_en.split(" of ", 1)
        rank_fa = RANK_EN2FA.get(rank_part.strip())
        suit_fa = SUIT_EN2FA.get(suit_part.strip())
        if rank_fa and suit_fa:
            key = f"{rank_fa} {suit_fa}"
            for deck_name, meaning in TAROT_DECK_FULL:
                if deck_name == key:
                    return deck_name, meaning
    return None


def _fetch_tarot_card_online_blocking():
    """یه کارت واقعی و تصادفی از یه منبع آنلاینِ واقعی (tarotapi.dev - رایگان،
    بدون نیاز به کلید API) می‌گیره. اگه اینترنت/سایت در دسترس نباشه، None
    برمی‌گردونه و کد صدازننده خودکار میره سراغ حالت کاملاً آفلاین."""
    try:
        r = _http_session.get("https://tarotapi.dev/api/v1/cards/random", params={"n": 1}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            cards = data.get("cards", [])
            if cards:
                card = cards[0]
                return {
                    "name_en": card.get("name", ""),
                    "meaning_up": card.get("meaning_up", ""),
                    "meaning_rev": card.get("meaning_rev", ""),
                }
    except Exception as e:
        logger.warning(f"tarotapi.dev fetch failed: {e}")
    return None


FAL_OPENERS = [
    "امروز روز خوبیه برای شروع یه کار جدید.", "امروز حال‌وهوای متفاوتی در انتظارته.",
    "یه اتفاق کوچیک ولی معنادار امروز میفته.", "امروز روزیه که باید به شهودت اعتماد کنی.",
    "انرژی امروزت رو به بالاست، ازش خوب استفاده کن.", "امروز یکم غیرمنتظره پیش می‌ره، ولی به نفعته.",
    "امروز روز آرامشه، لازم نیست عجله کنی.", "یه فرصت کوچیک امروز سر راهت قرار می‌گیره.",
]
FAL_LIFE_AREAS = [
    "توی کار و درس، تمرکزت بیشتر از همیشه جواب می‌ده.",
    "توی روابطت، صداقت امروز بهترین انتخابه.",
    "از نظر مالی، یه خبر یا فرصت کوچیک در راهه.",
    "توی خانواده یا دوستی‌هات، یه گفت‌وگوی مهم پیش میاد.",
    "از نظر احساسی، امروز حس‌های قوی‌تری تجربه می‌کنی.",
    "سلامتیت رو دست‌کم نگیر، بدنت به استراحت نیاز داره.",
    "یه تصمیم قدیمی داره بالاخره جواب می‌ده.",
    "یه دوست یا آشنای قدیمی به یادت می‌افته.",
]
FAL_ADVICE = [
    "فقط حواست باشه عجله نکنی و قدم‌به‌قدم پیش بری. 🌊",
    "ذهنت رو باز نگه دار، همه‌چی همون‌جوری نیست که فکر می‌کنی. 📩",
    "با آرامش و صداقت جلو برو، نتیجه بهتره. 👂",
    "ترست رو کنار بذار و شروع کن، الان بهترین زمانه. 🚀",
    "زودتر قدم اول رو بردار، این ارتباط دوباره جون می‌گیره. 💬",
    "قبل از هر تصمیمی، همه جوانب رو بررسی کن. 💰",
    "به خودت اجازه بده کمی استراحت کنی. ☕",
    "با فکر باز تصمیم بگیر، نه احساسی و ناگهانی. 🧠",
    "چشمات رو باز نگه دار، شاید یه نفر همین نزدیکی‌ها منتظرته. ❤️",
    "یه ریسک حساب‌شده رو امتحان کن؛ می‌تونه جواب بده. 🎲",
]
FAL_LUCKY_COLORS = ["آبی", "قرمز", "سبز", "طلایی", "بنفش", "نارنجی", "سفید", "فیروزه‌ای"]


async def generate_fal(name: str) -> str:
    # موتور ترکیبی: هر بار قطعات مختلف رو تصادفی کنار هم می‌چینه - آفلاین و سریع
    opener = random.choice(FAL_OPENERS)
    area = random.choice(FAL_LIFE_AREAS)
    advice = random.choice(FAL_ADVICE)
    lucky_color = random.choice(FAL_LUCKY_COLORS)
    lucky_number = random.randint(1, 99)
    return (
        f"{opener} {area} {advice}\n\n"
        f"🎨 رنگ شانس امروزت: {lucky_color} | 🔢 عدد شانس: {lucky_number}"
    )


HAFEZ_VERSES = [
    "الا یا ایها الساقی ادر کاسا و ناولها / که عشق آسان نمود اول ولی افتاد مشکل‌ها",
    "بیا تا گل برافشانیم و می در ساغر اندازیم / فلک را سقف بشکافیم و طرحی نو دراندازیم",
    "دوش وقت سحر از غصه نجاتم دادند / وندر آن ظلمت شب آب حیاتم دادند",
    "یوسف گم‌گشته باز آید به کنعان غم مخور / کلبهٔ احزان شود روزی گلستان غم مخور",
    "اگر آن ترک شیرازی به دست آرد دل ما را / به خال هندویش بخشم سمرقند و بخارا را",
    "سال‌ها دل طلب جام جم از ما می‌کرد / وان چه خود داشت ز بیگانه تمنا می‌کرد",
    "صبا به لطف بگو آن غزال رعنا را / که سر به کوه و بیابان تو داده‌ای ما را",
    "بلبلی برگ گلی خوش‌رنگ در منقار داشت / وندر آن برگ و نوا خوش ناله‌های زار داشت",
    "حسن تو همیشه در فزون باد / رویت همه ساله لاله‌گون باد",
    "دل می‌رود ز دستم صاحب‌دلان خدا را / دردا که راز پنهان خواهد شد آشکارا",
    "بنال بلبل اگر با منت سر یاری است / که ما دو عاشق زاریم و کار ما زاری است",
    "مرا می‌بینی و هر دم زیادت می‌کنی دردم / تو را می‌بینم و میلم زیادت می‌شود هر دم",
    "زلف آشفته و خوی‌کرده و خندان‌لب و مست / پیرهن چاک و غزل‌خوان و صراحی در دست",
    "ای پادشه خوبان داد از غم تنهایی / دل بی تو به جان آمد وقت است که بازآیی",
    "گفتم غم تو دارم گفتا غمت سرآید / گفتم که ماه من شو گفتا اگر برآید",
    "روزگاری است که سودای بتان دین من است / غم این کار نشاط دل غمگین من است",
]

PROVERBS_FA = [
    "کار نیکو کردن از پر کردن است؛ هر کاری با تمرین جا می‌افته.",
    "آدمی به فکر نیک، به گفتار نیک، به کردار نیک می‌رسه.",
    "تا نباشد چیزکی، مردم نگویند چیزها.",
    "آب رفته به جوی باز نمی‌گرده، پس قدر لحظه رو بدون.",
    "سنگ بزرگ علامت نزدن است.",
    "کبوتر با کبوتر، باز با باز؛ کند همجنس با همجنس پرواز.",
    "هر که بامش بیش، برفش بیشتر.",
    "دیر رسیدن بهتر از هرگز نرسیدنه.",
    "از کوزه همان برون تراود که در اوست.",
    "با یک گل بهار نمی‌شه؛ صبر و پشتکار کلیده.",
    "آدم عاقل دوبار از یه سوراخ گزیده نمی‌شه.",
    "کوه به کوه نمی‌رسه، آدم به آدم می‌رسه.",
    "هر که خربزه می‌خوره، پای لرزش هم می‌شینه.",
    "آب که سر از سر گذشت، چه یک وجب چه صد وجب.",
]

JOKES_FALLBACK = [
    "یارو رفته دکتر می‌گه دکتر یادم میره... دکتر می‌گه از کِی؟ می‌گه چی از کِی؟ 😄",
    "به کامپیوترم گفتم رمزتو بگو، گفت: 404 not found! 🤖",
    "رفتم آرایشگاه گفتم مثل بازیگرا کوتاه کن، الان مثل صحنه فیلم ترسناکم! ✂️",
    "دیشب خواب دیدم پولدار شدم، صبح بیدار شدم دیدم فقط خوابم زیاد شده! 😂",
    "به دوستم گفتم وای‌فای نداره خونه‌شون، گفت مگه هوا مهمه؟! 📶",
    "رفتم بانک گفتم حسابمو چک کن، گفت واقعاً می‌خوای؟ گفتم آره، گفت خب گریه نکن! 😅",
    "معلم پرسید فرق «شاید» و «حتماً» چیه؟ بچه گفت: شاید بیام مدرسه، حتماً نمیام! 🎒",
    "زنگ زدم پیتزا سفارش بدم، گفتن آدرس بدید، گفتم دلم! 🍕",
]

# پاسخ‌های کلاسیک «توپ جادویی هشت» - قابلیت جدید و سرگرم‌کننده
EIGHTBALL_ANSWERS = [
    "بله، قطعاً! ✅", "به احتمال زیاد آره 🙂", "نشونه‌ها می‌گن بله 🔮",
    "الان نمی‌تونم بگم، بعداً بپرس 🤔", "بهتره الان جوابشو نگم 🙊",
    "تمرکز کن و دوباره بپرس 🌀", "نه، اصلاً 🚫", "به احتمال زیاد نه ❌",
    "امیدت رو زیاد نکن 😅", "مطمئناً 💯",
]

# ------------------------------------------------------------
# 🎡 چرخ شانس - قابلیت جدید: یه چرخ شوخی که جایزه/اتفاق تصادفی بهت می‌ده
# ------------------------------------------------------------
WHEEL_PRIZES = [
    "🎉 تبریک! امروز افتخاری «خوش‌شانس‌ترین عضو گروه» رو گرفتی!",
    "☕ یه فنجون چای مجازی از طرف ربات بهت تعارف می‌شه.",
    "😴 امروز روز تنبلیته، به خودت سخت نگیر.",
    "📵 یه ساعت بدون گوشی امتحان کن، حالش رو ببر.",
    "🍕 امشب شب سفارش پیتزاست، دلت بخواد یا نخواد!",
    "🧹 نوبت توئه که گروه رو جارو بزنی (شوخی بود 😄).",
    "🎁 هیچی نبردی، ولی حداقل خندیدی!",
    "🚀 امروز روز شروع یه کار بزرگه، برو که رفتیم!",
    "🐌 امروز باید صبور باشی، کارها کمی کند پیش می‌رن.",
    "🏆 تو قهرمان بی‌رقیب امروز گروه هستی!",
]


def spin_wheel() -> str:
    return random.choice(WHEEL_PRIZES)


# ------------------------------------------------------------
# 🕵️ جرأت یا حقیقت — نسخه گروهی حرفه‌ای
# انتخاب در خصوصی، اعلام نتیجه در گروه، نوبت چرخشی و ضدتداخل
# ------------------------------------------------------------
TRUTH_QUESTIONS = [
    "اگر می‌توانستی یکی از تصمیم‌های مهم گذشته‌ات را دوباره بگیری، کدام تصمیم بود و امروز چه تغییری در آن می‌دادی؟",
    "چه چیزی درباره خودت هست که دوست داری دیگران زودتر متوجهش شوند؟",
    "کدام اتفاق کوچک در زندگی‌ات تأثیر خیلی بزرگ‌تری از چیزی که انتظار داشتی روی تو گذاشت؟",
    "اگر یک سال آینده دقیقاً همان‌طور که دوست داری پیش برود، مهم‌ترین چیزی که تا آن زمان به دست آورده‌ای چیست؟",
    "چه چیزی برایت از یک دوستی واقعی غیرقابل‌جایگزین است؟",
    "آخرین باری که واقعاً به خودت افتخار کردی چه زمانی بود و چرا؟",
    "اگر قرار باشد فقط یک خاطره از یک دوره مهم زندگی‌ات را برای همیشه نگه داری، کدام را انتخاب می‌کنی؟",
    "چه ویژگی‌ای در آدم‌ها باعث می‌شود خیلی سریع به آن‌ها احترام بگذاری؟",
    "چه چیزی هست که قبلاً درباره‌اش اشتباه فکر می‌کردی اما نظرت کاملاً تغییر کرده است؟",
    "اگر می‌توانستی یک روز از زندگی آینده‌ات را ببینی، دوست داشتی چه روزی باشد؟",
    "کدام انتخاب بین «امنیت» و «تجربه تازه» برایت سخت‌تر است و چرا؟",
    "چه نوع حرفی از یک دوست می‌تواند در یک روز بد واقعاً حالت را بهتر کند؟",
    "اگر می‌توانستی یک مهارت را بدون هیچ تمرینی در سطح حرفه‌ای یاد بگیری، چه مهارتی را انتخاب می‌کردی و چرا؟",
    "کدام مکان برایت حس خاصی دارد و چه خاطره یا حسی آن را خاص کرده است؟",
    "اگر مجبور باشی یکی از عادت‌های خودت را برای همیشه کنار بگذاری، کدام را انتخاب می‌کنی؟",
    "چه چیزی باعث می‌شود احساس کنی یک نفر واقعاً به حرفت گوش داده است؟",
    "کدام تجربه باعث شد نگاهت به زندگی یا آدم‌ها پخته‌تر شود؟",
    "اگر می‌توانستی از خودِ چند سال قبلت فقط یک سؤال بپرسی، چه می‌پرسیدی؟",
    "کدام ویژگی خودت را بیشتر از چیزی که دیگران فکر می‌کنند دوست داری؟",
    "چه چیزی را در یک رابطه دوستانه هرگز حاضر نیستی با چیز دیگری عوض کنی؟",
    "اگر یک نفر بخواهد تو را واقعاً بشناسد، به نظرت باید چه چیزی را درباره تو بداند؟",
    "کدام شکست یا اشتباه در نهایت یک چیز ارزشمند به تو یاد داد؟",
    "اگر فردا کاملاً آزاد باشی و هیچ کاری روی سرت نباشد، یک روز ایده‌آل برایت چگونه می‌گذرد؟",
    "چه چیزی بیشتر از همه انگیزه‌ات را برمی‌گرداند وقتی مدت زیادی خسته یا بی‌حوصله‌ای؟",
    "کدام فیلم، سریال، کتاب یا بازی روی طرز فکرت اثر گذاشته و چرا؟",
    "اگر مجبور باشی بین زندگی آرام و زندگی پر از تجربه‌های تازه یکی را انتخاب کنی، کدام را ترجیح می‌دهی و چرا؟",
    "چه چیزی هست که دوست داری در آینده درباره امروزت با لبخند به یاد بیاوری؟",
    "اگر یک دوست قدیمی بعد از سال‌ها برگردد، اولین چیزی که دوست داری از او بپرسی چیست؟",
    "کدام ارزش اخلاقی برایت آن‌قدر مهم است که حاضر نیستی به خاطر منفعت خودت کنار بگذاری؟",
    "چه چیزی می‌تواند اعتماد تو را خیلی سریع از بین ببرد؟",
    "اگر قرار باشد یک سنت یا عادت خوب از خانواده یا فرهنگت را برای نسل بعد نگه داری، چه چیزی است؟",
    "کدام لحظه ساده زندگی برایت از یک اتفاق بزرگ ارزشمندتر بوده است؟",
    "اگر می‌توانستی فقط یک نگرانی را برای همیشه از ذهنت حذف کنی، کدام نگرانی بود؟",
    "چه نوع آدم‌هایی معمولاً باعث می‌شوند احساس راحتی کنی و خود واقعی‌ات باشی؟",
    "اگر قرار باشد یک جمله به کسی بگویی که مدتی است احساس می‌کند کافی نیست، چه می‌گویی؟",
    "کدام آرزو را هنوز جدی دنبال نکرده‌ای اما ته دلت دوست داری روزی به آن برسی؟",
    "چه چیزی در یک گفت‌وگو باعث می‌شود از صحبت‌کردن با یک نفر لذت ببری؟",
    "اگر بتوانی یک روز را دوباره زندگی کنی، کدام روز را انتخاب می‌کنی و چرا؟",
    "کدام انتخاب کوچک اخیرت بیشتر از چیزی که فکر می‌کردی روی حال و آینده‌ات اثر گذاشت؟",
    "چه چیزی را در دوست‌هایت تحسین می‌کنی اما کمتر به آن‌ها می‌گویی؟",
    "اگر قرار باشد سه چیز را برای داشتن یک زندگی خوب انتخاب کنی، چه سه چیز مهم‌ترند؟",
    "چه چیزی باعث می‌شود یک مکان برایت تبدیل به «خانه» شود، حتی اگر واقعاً خانه‌ات نباشد؟",
    "اگر بتوانی یک گفت‌وگوی مهم را با کسی که دیگر در کنارت نیست دوباره داشته باشی، درباره چه چیزی حرف می‌زنی؟",
    "کدام تصمیم را بیشتر با احساس می‌گیری و کدام تصمیم را بیشتر با منطق؟",
    "اگر یک نفر فقط یک ویژگی خوب از تو به یاد داشته باشد، دوست داری آن ویژگی چه باشد؟",
    "چه چیزی هست که زمانی فکر می‌کردی خیلی مهم است اما امروز دیگر آن‌قدر برایت مهم نیست؟",
    "اگر بتوانی یک ماه را در هر جای دنیا زندگی کنی، کجا را انتخاب می‌کنی و دوست داری چه چیزی را تجربه کنی؟",
    "کدام خاطره دوستانه هنوز با یک آهنگ، بو یا جمله خاص دوباره برایت زنده می‌شود؟",
    "چه چیزی در یک بازی گروهی باعث می‌شود واقعاً بخواهی دوباره بازی کنی؟",
    "اگر امروز بخواهی یک تغییر کوچک اما واقعی در زندگی‌ات ایجاد کنی، چه تغییری خواهد بود؟",
]

# جرأت‌ها عمداً «چالش‌های معنادار و قابل‌بررسی» هستند؛ نه تکرار عدد و ایموجی.
# همه در داخل چت انجام می‌شوند و برای هرکدام verifier مشخص وجود دارد.
DARE_ACTIONS = [
    "در یک پیام، یک خاطره کوتاه و واقعی از یک لحظه خنده‌دار تعریف کن؛ حداقل ۲ جمله باشد و حداقل ۱۵ کلمه داشته باشد.",
    "در یک پیام، سه ویژگی مثبت و واقعی درباره خودت بنویس و برای هرکدام یک توضیح کوتاه اضافه کن.",
    "در یک پیام، یک توصیه‌ای که واقعاً به آن باور داری بنویس و در یک جمله توضیح بده چرا به آن باور داری.",
    "در یک پیام، یک اتفاق خوب کوچک که اخیراً برایت افتاده تعریف کن و بگو چرا برایت مهم بود؛ حداقل ۲ جمله.",
    "در یک پیام، یک شخصیت خیالی را بدون گفتن نامش با ۳ نشانه توصیف کن تا بقیه بتوانند حدس بزنند؛ حداقل ۳ جمله.",
    "در یک پیام، یک مقصدی که دوست داری به آن سفر کنی انتخاب کن و سه دلیل واقعی برای انتخابت بنویس.",
    "در یک پیام، یک فیلم، سریال، انیمه یا بازی را بدون گفتن نامش با سه سرنخ توصیف کن؛ حداقل ۳ جمله.",
    "در یک پیام، یک سؤال جالب و عمیق طراحی کن که اگر از همه بازیکنان پرسیده شود، جواب‌های متفاوتی ایجاد کند.",
    "در یک پیام، یک خاطره را بدون گفتن زمان و مکان دقیقش تعریف کن و اجازه بده بقیه حدس بزنند مربوط به چه دوره‌ای بوده؛ حداقل ۳ جمله.",
    "در یک پیام، یک انتخاب سخت بین دو چیز طراحی کن و خودت هم انتخابت را با یک دلیل توضیح بده.",
    "در یک پیام، سه چیز کوچک که معمولاً روزت را بهتر می‌کنند بنویس و برای هرکدام یک توضیح کوتاه بده.",
    "در یک پیام، یک جمله درباره چیزی که می‌خواهی در آینده یاد بگیری بنویس و حداقل دو دلیل برای انتخابت بیاور.",
    "در یک پیام، یک تعریف صادقانه و مشخص از فضای همین گروه بنویس؛ تعریف باید درباره یک ویژگی یا رفتار باشد، نه فقط «خوبه».",
    "در یک پیام، یک داستان خیلی کوتاه در ۳ جمله بساز که کلمات «باران»، «چراغ» و «پنجره» در آن باشند.",
    "در یک پیام، یک پایان متفاوت برای یک داستان یا فیلم معروف پیشنهاد کن و در دو جمله توضیح بده چرا این پایان را انتخاب کردی.",
    "در یک پیام، یک سؤال درباره آینده از خودت بپرس و سپس خودت به همان سؤال جواب بده؛ حداقل ۲ جمله.",
    "در یک پیام، یک خاطره شیرین از دوران کودکی یا مدرسه تعریف کن؛ حداقل ۳ جمله و بدون اشاره به اطلاعات خصوصی دیگران.",
    "در یک پیام، یک ویژگی اخلاقی را انتخاب کن و توضیح بده چرا فکر می‌کنی داشتن آن ویژگی مهم است؛ حداقل ۲ جمله.",
    "در یک پیام، سه گزینه برای یک شب دوستانه پیشنهاد بده و یکی را به عنوان انتخاب خودت با دلیل انتخاب کن.",
    "در یک پیام، یک چیز را که قبلاً دوست نداشتی اما بعدها به آن علاقه‌مند شدی تعریف کن و توضیح بده چه چیزی نظرت را تغییر داد.",
    "در یک پیام، یک معمای کوتاه و منصفانه برای بقیه طراحی کن و پاسخ آن را در همان پیام ننویس؛ حداقل ۳ جمله باشد.",
    "در یک پیام، یک موقعیت فرضی بساز که در آن باید بین «وقت بیشتر» و «پول بیشتر» یکی را انتخاب کنی و دلیل انتخابت را بگو.",
    "در یک پیام، یک آهنگ یا سبک موسیقی را انتخاب کن و بدون نوشتن متن ترانه، توضیح بده چه حسی در تو ایجاد می‌کند؛ حداقل ۲ جمله.",
    "در یک پیام، یک مکان آرامش‌بخش را توصیف کن بدون اینکه نام آن را بگویی؛ حداقل ۳ ویژگی از آن مکان بنویس.",
    "در یک پیام، یک جمله انگیزشی مخصوص یکی از بازیکنان بنویس، بدون اینکه درباره ظاهر، بدن یا مسائل خصوصی او صحبت کنی؛ حداقل ۲ جمله.",
    "در یک پیام، یک «اگر...» جالب درباره آینده طراحی کن و خودت هم بگو در آن شرایط چه انتخابی می‌کنی و چرا.",
    "در یک پیام، یک اتفاق معمولی را طوری تعریف کن که انگار صحنه‌ای از یک فیلم است؛ حداقل ۳ جمله.",
    "در یک پیام، سه چیز را که برای داشتن یک دوستی خوب ضروری می‌دانی بنویس و یکی را مهم‌تر از بقیه انتخاب کن.",
    "در یک پیام، یک تصمیم فرضی درباره سفر، شغل یا یادگیری مطرح کن و بین دو مسیر یکی را انتخاب کن؛ حداقل دو دلیل بده.",
    "در یک پیام، یک خاطره یا اتفاق را فقط با احساس و فضای آن توصیف کن، بدون اینکه نام افراد دیگر را بیاوری؛ حداقل ۳ جمله.",
]

# ------------------------------------------------------------
# v40 — بانک محتوای باکیفیت و دسته‌بندی‌شده
# سؤال‌ها برای «شناخت، خاطره، انتخاب، دیدگاه و خلاقیت» طراحی شده‌اند؛
# چالش‌های جرأت همگی داخل چت و ایمن‌اند و برای هر الگوی جدید verifier دارند.
# ------------------------------------------------------------
V40_TRUTH_QUESTIONS = [
    "اگر قرار باشد یکی از سال‌های زندگی‌ات را دوباره تجربه کنی، کدام سال را انتخاب می‌کنی و این بار چه چیزی را متفاوت انجام می‌دهی؟",
    "چه چیزی باعث می‌شود به یک نفر احساس امنیت و راحتی داشته باشی؟",
    "کدام تصمیم ساده در گذشته، امروز تبدیل به یک تصمیم مهم برایت شده است؟",
    "اگر یک نفر بخواهد دوست خوبی برای تو باشد، چه چیزی را باید درباره مرزها و حساسیت‌هایت بداند؟",
    "چه نوع عذرخواهی‌ای را واقعاً صادقانه می‌دانی و چه چیزی باعث می‌شود عذرخواهی را باور نکنی؟",
    "کدام خاطره را هر بار تعریف می‌کنی هنوز بخشی از حس همان روز را با خودت داری؟",
    "اگر می‌توانستی یک مهارت را از یکی از دوستانت یاد بگیری، از چه کسی و چه مهارتی؟",
    "چه چیزی در یک آدم معمولاً بیشتر از ظاهر یا حرف‌هایش توجهت را جلب می‌کند؟",
    "آخرین چیزی که درباره خودت فهمیدی و واقعاً غافلگیرت کرد چه بود؟",
    "اگر مجبور باشی بین داشتن وقت آزاد بیشتر و داشتن امکانات بیشتر یکی را انتخاب کنی، کدام را انتخاب می‌کنی و چرا؟",
    "کدام رفتار کوچک از طرف یک دوست می‌تواند برایت خیلی باارزش باشد؟",
    "اگر بتوانی یک سوءتفاهم قدیمی را برای همیشه روشن کنی، کدام را انتخاب می‌کنی؟",
    "چه چیزی باعث می‌شود یک گفت‌وگو از نظر تو واقعاً ارزش وقت گذاشتن داشته باشد؟",
    "اگر قرار باشد یک روز کامل را بدون اینترنت بگذرانی، دوست داری آن روز را چطور سپری کنی؟",
    "کدام تجربه باعث شد بفهمی یک چیز برایت مهم‌تر از چیزی است که قبلاً تصور می‌کردی؟",
    "اگر بتوانی یک ویژگی خوب را در همه آدم‌های گروه بیشتر کنی، چه ویژگی‌ای را انتخاب می‌کنی؟",
    "چه چیزی را دیرتر از بقیه یاد گرفتی اما وقتی فهمیدی، نگاهت را تغییر داد؟",
    "اگر زندگی‌ات یک فصل از یک داستان بود، عنوان این فصل را چه می‌گذاشتی؟",
    "کدام انتخاب بین ماندن در منطقه امن و امتحان‌کردن چیز تازه بیشتر شبیه توست؟ چرا؟",
    "چه چیزی باعث می‌شود بعد از یک روز سخت دوباره انرژی بگیری؟",
    "اگر می‌توانستی یک خاطره را فقط برای چند دقیقه دوباره ببینی، کدام را انتخاب می‌کنی؟",
    "کدام ویژگی در یک دوست باعث می‌شود حتی بعد از مدت طولانی هنوز به او اعتماد داشته باشی؟",
    "چه چیزی هست که دوست داری مردم درباره شخصیتت بدانند اما معمولاً از روی ظاهر یا رفتار اولت متوجه نمی‌شوند؟",
    "اگر یک سال هیچ ترسی از شکست نداشتی، چه کاری را جدی‌تر امتحان می‌کردی؟",
    "کدام تجربه باعث شد ارزش یک آدم یا یک رابطه را بیشتر بفهمی؟",
    "اگر قرار باشد یک قانون شخصی برای زندگی خودت بنویسی، چه می‌نویسی؟",
    "چه نوع شوخی‌ای را دوست داری و چه نوع شوخی‌ای معمولاً برایت آزاردهنده است؟",
    "کدام مکان، حتی اگر خیلی ساده باشد، برایت حس آرامش یا خاطره دارد؟",
    "اگر بتوانی یک سؤال از آینده خودت بپرسی و جواب دقیق بگیری، چه می‌پرسی؟",
    "کدام انتخاب را بیشتر دوست داری با منطق انجام دهی و کدام را با احساس؟",
    "اگر یک دوستت درباره تصمیم مهمی از تو نظر بخواهد، ترجیح می‌دهی حقیقت را مستقیم بگویی یا اول احساسش را در نظر بگیری؟ چرا؟",
    "چه چیزی باعث می‌شود یک نفر در نگاهت قابل احترام شود؟",
    "کدام تجربه را دوست داری یک بار دیگر با همان آدم‌ها تکرار کنی؟",
    "اگر مجبور باشی یک عادت خوب را به همه دوستانت پیشنهاد بدهی، چه عادتی را انتخاب می‌کنی؟",
    "چه چیزی بیشتر از هر چیز دیگری می‌تواند یک روز معمولی را برایت خاص کند؟",
    "اگر بتوانی یک استعداد پنهان در خودت را کشف کنی، دوست داری چه باشد؟",
    "کدام نوع موفقیت برایت ارزشمندتر است: رسیدن به هدف شخصی یا کمک‌کردن به یک نفر دیگر برای رسیدن به هدفش؟ چرا؟",
    "اگر یک فیلم از زندگی‌ات ساخته شود، دوست داری کدام بخش زندگی‌ات بیشتر در آن دیده شود؟",
    "چه چیزی را در دوستی‌هایت خیلی جدی می‌گیری که شاید برای دیگران کوچک به نظر برسد؟",
    "اگر بتوانی یک تصمیم آینده را از قبل باخبر شوی، دوست داری درباره چه چیزی باشد؟",
    "کدام جمله یا نصیحت را زمانی ساده می‌دانستی اما بعدها فهمیدی واقعاً درست بوده است؟",
    "اگر بخواهی یک خاطره را با یک آهنگ، یک بو یا یک فصل از سال توصیف کنی، کدام را انتخاب می‌کنی و چرا؟",
    "چه چیزی باعث می‌شود از یک بازی گروهی واقعاً لذت ببری، حتی اگر برنده نشوی؟",
    "اگر بین داشتن یک زندگی کاملاً قابل‌پیش‌بینی و یک زندگی پر از اتفاق‌های تازه مجبور به انتخاب باشی، کدام را انتخاب می‌کنی؟",
    "چه چیزی را دوست داری در سال آینده درباره خودت تغییر بدهی، حتی اگر تغییر کوچکی باشد؟",
    "اگر بتوانی یک روز را با هر شخصیت واقعی یا خیالی بگذرانی، چه کسی را انتخاب می‌کنی و چه چیزی از او می‌پرسی؟",
    "کدام ویژگی در خودت را دوست داری بیشتر تقویت کنی؟",
    "چه چیزی در یک دوست باعث می‌شود بتوانی بدون ترس خود واقعی‌ات باشی؟",
    "اگر بخواهی یک خاطره خوب برای چند سال آینده بسازی، دوست داری چه جور روزی باشد؟",
    "کدام سؤال را همیشه دوست داری از دیگران بپرسی چون جوابش آدم‌ها را بهتر نشان می‌دهد؟",
    "اگر بتوانی یک موضوع را برای یک ساعت با همه اعضای گروه بحث کنی، چه موضوعی را انتخاب می‌کنی؟",
]

V40_DARE_ACTIONS = [
    "🎬 یک اتفاق معمولی از امروزت را در حداقل ۳ جمله طوری تعریف کن که انگار صحنه‌ای از یک فیلم است؛ بدون نام واقعی افراد.",
    "🧠 یک سؤال عمیق طراحی کن که جوابش فقط بله یا خیر نباشد و حداقل یک دلیل بخواهد؛ بعد خودت هم به آن جواب بده.",
    "✍️ یک پیام کوتاه برای «خودِ پنج سال بعدت» بنویس؛ حداقل ۳ جمله و درباره امید، هدف یا چیزی که می‌خواهی حفظش کنی.",
    "🎭 یک شخصیت خیالی بساز و در حداقل ۴ جمله معرفی‌اش کن: یک ویژگی، یک هدف، یک نقطه‌ضعف و یک راز داستانی بی‌خطر.",
    "🌧️ یک خاطره واقعی را بدون گفتن نام افراد و مکان دقیق، در حداقل ۳ جمله با تمرکز روی حس و فضای آن تعریف کن.",
    "🎮 یک بازی را بدون گفتن اسمش در حداقل ۴ جمله توصیف کن؛ سه نشانه بده و در پایان بگو چرا هنوز دوستش داری.",
    "🎵 یک سبک موسیقی یا یک آهنگ را معرفی کن و در حداقل ۳ جمله توضیح بده چه زمانی بیشتر به سراغش می‌روی و چه حسی برایت دارد؛ متن ترانه ننویس.",
    "🗺️ یک سفر خیالی برای جمع دوستانه طراحی کن: مقصد، یک فعالیت و دلیل انتخاب هرکدام را در حداقل ۳ جمله بگو.",
    "💡 یک ایده ساده برای بهترشدن فضای همین گروه پیشنهاد بده و در حداقل ۲ جمله توضیح بده چرا فکر می‌کنی مفید است.",
    "🎥 یک فیلم، سریال یا انیمه را بدون گفتن نامش با چهار سرنخ توصیف کن و بگو کدام بخشش بیشتر برایت جذاب است.",
    "📖 یک پایان متفاوت برای یک داستان خیالی بساز؛ حداقل ۳ جمله بنویس و توضیح بده چرا این پایان را انتخاب کردی.",
    "🤝 سه ویژگی یک دوست قابل‌اعتماد را بنویس و در یک جمله توضیح بده کدام‌یک برای خودت مهم‌تر است.",
    "🌟 یک تعریف صادقانه و مشخص از یکی از رفتارهای خوب گروه بنویس؛ تعریف باید درباره رفتار یا فضای جمع باشد، نه ظاهر افراد.",
    "🧩 یک معمای کوتاه و منصفانه برای گروه طراحی کن؛ حداقل ۳ جمله باشد و پاسخ معما را در همان پیام ننویس.",
    "⏳ یک تصمیم فرضی بساز که در آن باید بین «زمان بیشتر» و «پول بیشتر» یکی را انتخاب کنی؛ انتخاب و حداقل دو دلیل را توضیح بده.",
    "🏠 یک مکان خیالی را توصیف کن که اگر بعد از یک روز شلوغ به آنجا برسی آرام می‌شوی؛ حداقل ۴ ویژگی بگو و اسم مکان را خودت بساز.",
    "🎨 یک تصویر خیالی را فقط با کلمات توصیف کن: رنگ، نور، صدا و فضای آن را در حداقل ۴ جمله بیان کن.",
    "🗣️ یک سؤال جالب از یکی از بازیکنان بپرس که درباره علایق یا دیدگاهش باشد، نه اطلاعات خصوصی؛ بعد توضیح بده چرا این سؤال را انتخاب کردی.",
    "📚 یک چیزی را که واقعاً بلد هستی به شکل یک آموزش کوتاه ۳ مرحله‌ای برای بقیه توضیح بده.",
    "🔮 یک پیش‌بینی کاملاً دوستانه و غیرجدی درباره یک اتفاق مثبت در آینده گروه بنویس و حداقل دو دلیل خلاقانه برایش بیاور.",
    "☕ سه چیز کوچک را که یک روز معمولی را برایت بهتر می‌کنند بنویس و یکی را انتخاب کن که اگر حذف شود بیشتر دلت برایش تنگ می‌شود.",
    "🎭 یک موقعیت خنده‌دار و کاملاً خیالی بساز که اگر همه اعضای گروه در آن باشند چه اتفاقی می‌افتد؛ حداقل ۳ جمله.",
    "🪄 اگر یک قانون جادویی برای یک روز زندگی داشتی، آن قانون را انتخاب کن و در حداقل ۳ جمله توضیح بده چه اتفاقی می‌افتاد.",
    "🌱 یک عادت کوچک و مفید را که واقعاً به آن باور داری معرفی کن و توضیح بده چطور می‌تواند در طول زمان اثر بگذارد.",
    "🎯 یک هدف کوچک و واقعی برای یک ماه آینده تعریف کن و سه قدم مشخص برای نزدیک‌شدن به آن بنویس.",
    "🧭 دو انتخاب کاملاً متفاوت برای یک آخرهفته پیشنهاد بده، یکی آرام و یکی ماجراجویانه؛ سپس انتخاب خودت را با دلیل بگو.",
    "📸 بدون فرستادن عکس، یک صحنه‌ای را که دوست داشتی از آن عکس بگیری با حداقل ۴ جزئیات توصیف کن.",
    "🌙 یک خاطره شبانه یا صبحگاهی تعریف کن که هنوز حس خاصی برایت دارد؛ حداقل ۳ جمله و بدون نام افراد دیگر.",
    "🧠 یک باور یا نظریه شخصی درباره یک موضوع روزمره بنویس و یک دلیل یا تجربه برایش ارائه کن.",
    "🎲 یک بازی خیلی کوتاه برای جمع طراحی کن که قوانینش در ۳ تا ۵ جمله قابل توضیح باشد.",
    "💬 یک پیام تشکر فرضی برای کسی بنویس که یک کمک کوچک اما مهم در زندگی‌ات کرده؛ حداقل ۲ جمله.",
    "🌍 یک شهر یا کشور را انتخاب کن و سه چیز را بگو که اگر به آنجا بروی دوست داری تجربه کنی؛ دلیل انتخابت را هم اضافه کن.",
    "🕰️ یک خاطره را بدون گفتن تاریخ دقیق تعریف کن و اجازه بده بقیه حدس بزنند مربوط به چه دوره‌ای از زندگی‌ات بوده؛ حداقل ۳ جمله.",
    "🎤 یک موضوع کاملاً معمولی را انتخاب کن و درباره‌اش یک سخنرانی ۴ جمله‌ای کاملاً جدی و خنده‌دار بنویس.",
    "🧩 یک انتخاب سخت بین دو ارزش متفاوت طراحی کن و خودت یکی را انتخاب کن؛ حداقل دو دلیل برای انتخابت بده.",
    "🌤️ یک برنامه برای یک روز ایده‌آل خودت بنویس که حداقل چهار بخش داشته باشد و بگو کدام بخش برایت مهم‌تر است.",
    "📦 سه چیز غیرقابل‌خطر و غیرشخصی را که اگر مجبور شوی یک ماه فقط همان‌ها را برای سرگرمی داشته باشی انتخاب کن و دلیل هرکدام را بگو.",
    "🎬 یک صحنه کوتاه ۴ جمله‌ای بنویس که دو شخصیت خیالی در آن درباره یک سوءتفاهم خنده‌دار صحبت می‌کنند.",
    "🪶 یک جمله کوتاه بساز که اگر روی جلد یک کتاب درباره زندگی تو نوشته شود، به نظرت مناسب باشد؛ سپس در دو جمله توضیحش بده.",
]

# بانک جدید را به بانک قبلی اضافه می‌کنیم تا هیچ محتوای نسخه‌های قبل حذف نشود.
TRUTH_QUESTIONS.extend(V40_TRUTH_QUESTIONS)
DARE_ACTIONS.extend(V40_DARE_ACTIONS)

# قوانین دقیق verifier برای چالش‌های جدید؛ کلیدها عمداً بخشی از متن ثابت هر چالش هستند.
V40_DARE_RULES = {
    "خودِ پنج سال بعدت": (3, 15, "پیام باید حداقل ۳ جمله و ۱۵ کلمه باشد."),
    "یک شخصیت خیالی بساز": (4, 18, "شخصیت باید حداقل ۴ جمله و شامل چند جزئیات مشخص باشد."),
    "یک خاطره واقعی را بدون گفتن نام افراد": (3, 15, "خاطره باید حداقل ۳ جمله و ۱۵ کلمه باشد و نام افراد را وارد نکند."),
    "یک بازی را بدون گفتن اسمش": (4, 16, "حداقل ۴ جمله و چند نشانه روشن درباره بازی لازم است."),
    "یک سبک موسیقی یا یک آهنگ را معرفی کن": (3, 14, "انتخاب موسیقی و توضیح حس/زمان استفاده باید در حداقل ۳ جمله باشد."),
    "یک سفر خیالی برای جمع دوستانه طراحی کن": (3, 14, "مقصد، فعالیت و دلیل‌ها باید مشخص باشند."),
    "یک ایده ساده برای بهترشدن فضای همین گروه": (2, 10, "ایده و دلیل مفیدبودنش را در حداقل ۲ جمله بنویس."),
    "یک پایان متفاوت برای یک داستان خیالی بساز": (3, 14, "پایان و دلیل انتخابش را در حداقل ۳ جمله توضیح بده."),
    "سه ویژگی یک دوست قابل‌اعتماد": (3, 10, "سه ویژگی و یک توضیح روشن لازم است."),
    "یک معمای کوتاه و منصفانه برای گروه طراحی کن": (3, 12, "معما باید حداقل ۳ جمله داشته باشد و پاسخ را ننویسی."),
    "یک تصویر خیالی را فقط با کلمات توصیف کن": (4, 14, "توصیف باید حداقل ۴ جمله و چند جزئیات حسی داشته باشد."),
    "یک چیزی را که واقعاً بلد هستی": (3, 12, "آموزش باید حداقل ۳ مرحله/بخش قابل تشخیص داشته باشد."),
    "یک هدف کوچک و واقعی برای یک ماه آینده": (3, 12, "هدف و سه قدم مشخص لازم است."),
    "یک بازی خیلی کوتاه برای جمع طراحی کن": (3, 12, "قوانین بازی باید حداقل ۳ جمله و قابل اجرا باشند."),
    "یک پیام تشکر فرضی": (2, 8, "پیام تشکر باید حداقل ۲ جمله و مشخص باشد."),
    "یک شهر یا کشور را انتخاب کن": (3, 12, "مقصد و سه تجربه پیشنهادی باید مشخص باشند."),
    "یک موضوع کاملاً معمولی را انتخاب کن": (4, 14, "سخنرانی باید حداقل ۴ جمله داشته باشد."),
    "یک انتخاب سخت بین دو ارزش متفاوت": (3, 12, "دو گزینه، انتخاب و دلیل‌ها باید مشخص باشند."),
    "یک برنامه برای یک روز ایده‌آل خودت": (4, 14, "برنامه باید حداقل چهار بخش مشخص داشته باشد."),
    "سه چیز غیرقابل‌خطر و غیرشخصی": (3, 12, "سه انتخاب و دلیل آن‌ها لازم است."),
    "یک صحنه کوتاه ۴ جمله‌ای": (4, 14, "دقیقاً یک صحنه کوتاه با حداقل ۴ جمله لازم است."),
    "یک جمله کوتاه بساز که اگر روی جلد یک کتاب": (3, 10, "جمله اصلی و توضیح آن در حداقل ۳ جمله لازم است."),
    "سه چیز کوچک را که یک روز معمولی": (3, 10, "سه مورد و توضیح انتخاب مهم‌تر لازم است."),
    "یک پیش‌بینی کاملاً دوستانه و غیرجدی": (2, 10, "پیش‌بینی و حداقل دو دلیل خلاقانه لازم است."),
    "یک موقعیت خنده‌دار و کاملاً خیالی": (3, 12, "موقعیت باید حداقل ۳ جمله و واقعاً مشخص باشد."),
    "یک قانون جادویی برای یک روز زندگی": (3, 12, "قانون و پیامدهایش را حداقل در ۳ جمله توضیح بده."),
    "یک عادت کوچک و مفید": (2, 10, "عادت و دلیل اثرگذاری آن باید مشخص باشد."),
    "دو انتخاب کاملاً متفاوت برای یک آخرهفته": (3, 12, "هر دو گزینه و انتخاب نهایی با دلیل لازم است."),
    "یک صحنه‌ای را که دوست داشتی از آن عکس بگیری": (3, 12, "صحنه باید حداقل ۳ جمله و ۴ جزئیات داشته باشد."),
    "یک خاطره شبانه یا صبحگاهی": (3, 12, "خاطره باید حداقل ۳ جمله و بدون نام افراد دیگر باشد."),
    "یک باور یا نظریه شخصی": (2, 10, "باور و حداقل یک دلیل یا تجربه لازم است."),
}

# وضعیت بازی‌های جرأت/حقیقت به‌ازای هر گروه؛ داده‌های موقت هستند و با ری‌استارت پاک می‌شوند.
TD_GAMES = {}
TD_PRIVATE_TASKS = {}  # (chat_id, user_id) -> task information; جداسازی کامل گروه‌ها
TD_PRIVATE_READY_USERS = set()  # کاربرانی که /start را در Private زده‌اند؛ فقط یک نشانهٔ اجرایی، نه جایگزین تست واقعی ارسال
TD_MAX_PLAYERS = 20
TD_MIN_PLAYERS = 2
TD_TASK_TIMEOUT_MINUTES = 30
TD_MAX_VALIDATION_ATTEMPTS = 4
TD_STATE_LOCK = asyncio.Lock()
TD_CLEANUP_INTERVAL_SECONDS = 60

# رسانه‌های انتخاب‌شده با سخت‌گیری بالا: فقط فایل‌های متحرک سالم و با مجوز روشن.
# Wikimedia Commons: CC0 / Public Domain. Pixabay: محتوای رایگان تحت Content License.
# رسانه صرفاً تزئینی است و شکست آن هرگز بازی را متوقف نمی‌کند.
TD_MEDIA = {
    # فقط منابعی که در Wikimedia Commons به‌عنوان فایل GIF موجودند و صفحهٔ منبع/مجوزشان
    # قابل بررسی است. چند منبع در هر event داریم تا خرابی یک منبع بازی را متوقف نکند.
    # فایل‌های زیر بر اساس صفحات فعلی Commons انتخاب شده‌اند:
    # Rotating-questionmark.gif / Question-mark-red-orange-animated.gif: CC BY-SA 3.0
    # Animated_moon.gif / Cards.gif / Cards_2.gif / Maze_simple_-_path_animated.gif: PD/CC0
    "lobby": [
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Rotating-questionmark.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Question-mark-red-orange-animated.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Animated_moon.gif",
    ],
    "truth": [
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Rotating-questionmark.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Question-mark-red-orange-animated.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Questionmark.gif",
    ],
    "dare": [
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Maze_simple_-_path_animated.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Picture_maze_solving.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Animated_moon.gif",
    ],
    "success": [
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Cards_2.gif",
        "https://upload.wikimedia.org/wikipedia/commons/e/e5/Cards.gif",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/First_bump_celebration.gif",
    ],
}
TD_MEDIA_CACHE = load_json_safe(DATA_DIR / "td_media_cache.json", {})
# وضعیت موقت منابع: منبع خراب برای مدت کوتاه کنار گذاشته می‌شود، نه برای همیشه.
TD_MEDIA_SOURCE_COOLDOWN = {}
TD_MEDIA_SOURCE_FAIL_SECONDS = 15 * 60
TD_MEDIA_LAST_SOURCE = {}
TD_MEDIA_CAPTIONS = {
    "truth": "❓",
    "lobby": "🎭",
    "dare": "🧩",
    "success": "🎉",
}


def td_task_key(chat_id, user_id):
    return (int(chat_id), int(user_id))


def td_make_task_token():
    """توکن کوتاه و غیرقابل‌حدس برای اتصال لینک Private به همان نوبت."""
    return "tdr_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")


def td_find_task_by_token(user_id, token):
    token = str(token or "").strip()
    if not token:
        return None, None
    for key, task in list(TD_PRIVATE_TASKS.items()):
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        if int(key[1]) != int(user_id):
            continue
        if task.get("task_token") == token:
            return key, task
    return None, None


async def td_private_deeplink(bot, token):
    """لینک اختصاصی همین نوبت؛ کلیک افراد دیگر در start رد می‌شود."""
    try:
        me = await bot.get_me()
        if me and me.username:
            return f"https://t.me/{me.username}?start={token}"
    except TelegramError as e:
        logger.warning("TD bot username lookup failed: %s", e)
    return None


def td_question_meta(question):
    """طبقه‌بندی معنایی سؤال برای انتخاب verifier مناسب؛ دروغ‌سنج نیست."""
    q = td_norm_text(question)
    if any(x in q for x in ("کدام فیلم", "فیلم، سریال", "فیلم یا سریال", "انیمه", "اثر مورد علاقه")):
        return "named_choice"
    if "کدام فصل" in q or "چه فصلی" in q:
        return "season"
    if "شب" in q and "صبح" in q and any(x in q for x in ("ترجیح", "انتخاب", "کدام")):
        return "night_morning"
    if "مهارت" in q or "یاد بگیر" in q or "یادگیری" in q:
        return "skill"
    if any(x in q for x in ("کجا", "مقصد", "سفر", "شهر", "کشور")):
        return "place"
    if any(x in q for x in ("اگر می‌توانستی", "اگر می تونستی", "فرض کن", "تصور کن", "در آینده")):
        return "hypothetical"
    if any(x in q for x in ("خاطره", "یادت", "دوران کودکی", "مدرسه", "اولین بار")):
        return "memory"
    if any(x in q for x in ("دوست", "دوستی", "اعتماد", "رابطه", "آدمی که")):
        return "relationship"
    if any(x in q for x in ("هدف", "آرزو", "آینده", "پنج سال", "سال بعد", "می‌خواهی")):
        return "future"
    if any(x in q for x in ("چرا", "دلیل", "به چه دلیل", "چه چیزی باعث")):
        return "reason"
    if any(x in q for x in ("چه چیزی در مورد خودت", "ویژگی", "عادت", "باور", "نگاهت", "شخصیت")):
        return "self"
    if any(x in q for x in ("آهنگ", "موسیقی", "فیلم", "سریال", "بازی", "کتاب")):
        return "media"
    if any(x in q for x in ("بهترین توصیه", "چه توصیه", "نصیحت")):
        return "advice"
    if any(x in q for x in ("چه چیزی را دوست", "چه چیزی را دوست نداری", "ترجیح", "مورد علاقه")):
        return "preference"
    return "open"


def td_game_key(chat_id):
    return int(chat_id)


def td_display_name(user):
    return user.first_name or user.username or "بازیکن"


def td_clean_name(name):
    return str(name).replace("\n", " ").strip()[:40] or "بازیکن"


def td_new_game(chat_id, owner_id):
    return {
        "chat_id": chat_id,
        "owner_id": owner_id,
        "target_players": None,
        "players": {},
        "turn_order": [],
        "turn_index": 0,
        "started": False,
        "round": 0,
        "used_truth": set(),
        "used_dare": set(),
        "active_task": None,
        # امتیاز فقط نتیجه‌ی نوبت را نگه می‌دارد؛ متن پاسخ هرگز در امتیاز ذخیره نمی‌شود.
        "scores": {},
        "successful_turns": {},
        "failed_turns": {},
        "last_truth_category": None,
        "last_dare_category": None,
        "total_turns": 0,
    }


def td_keyboard(game):
    if not game.get("started"):
        target = game.get("target_players")
        count_label = f"👥 تعداد بازیکنان: {target}" if target else "👥 انتخاب تعداد بازیکنان"
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(count_label, callback_data="tdg_count")],
            [InlineKeyboardButton("➕ ورود به بازی", callback_data="tdg_join"),
             InlineKeyboardButton("🚪 خروج", callback_data="tdg_leave")],
            [InlineKeyboardButton("▶️ شروع بازی", callback_data="tdg_start")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 وضعیت بازی", callback_data="tdg_status"),
         InlineKeyboardButton("🏆 امتیازها", callback_data="tdg_score")],
        [InlineKeyboardButton("🚪 خروج", callback_data="tdg_leave"),
         InlineKeyboardButton("🛑 پایان بازی", callback_data="tdg_end")],
    ])


def td_content_category(text):
    t = td_norm_text(text) if "td_norm_text" in globals() else str(text).lower()
    groups = {
        "memory": ("خاطره", "گذشته", "کودکی", "مدرسه", "یاد"),
        "friendship": ("دوست", "دوستی", "اعتماد", "رابطه", "گروه"),
        "future": ("آینده", "هدف", "سال بعد", "پنج سال", "یادگیری"),
        "choice": ("انتخاب", "بین", "ترجیح", "تصمیم"),
        "creative": ("خیالی", "داستان", "شخصیت", "فیلم", "بازی", "معما", "کتاب"),
        "music_media": ("آهنگ", "موسیقی", "فیلم", "سریال", "انیمه", "بازی"),
        "self": ("خودت", "شخصیت", "ویژگی", "عادت", "نگاهت", "باورت"),
        "daily": ("روز", "صبح", "شب", "زندگی", "معمولی"),
    }
    for name, words in groups.items():
        if any(w in t for w in words):
            return name
    return "other"


def td_pick(game, kind):
    pool = TRUTH_QUESTIONS if kind == "truth" else DARE_ACTIONS
    used_key = "used_truth" if kind == "truth" else "used_dare"
    last_key = "last_truth_category" if kind == "truth" else "last_dare_category"
    used = game[used_key]
    available = [i for i in range(len(pool)) if i not in used]
    if not available:
        used.clear()
        available = list(range(len(pool)))
    last_cat = game.get(last_key)
    preferred = [i for i in available if td_content_category(pool[i]) != last_cat]
    candidates = preferred or available
    idx = random.choice(candidates)
    used.add(idx)
    game[last_key] = td_content_category(pool[idx])
    return pool[idx]



TD_TRUTH_REJECTS = {
    "نمیدونم", "نمی‌دونم", "نمی دونم", "هیچی", "هیچچی", "ولش", "بیخیال", "بی‌خیال", "...", "؟", "نمیخوام بگم"
}
TD_STOPWORDS = {"من", "تو", "و", "یا", "که", "از", "به", "را", "در", "با", "برای", "یک", "این", "آن", "چه", "چی", "اگر", "می", "کنم", "کردم", "است", "هست", "بود", "شد", "چون", "چطور", "چرا"}


def td_norm_text(text):
    text = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    text = re.sub(r"[\u200c\u200d]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def td_words(text):
    return [w for w in re.findall(r"[\wآ-ی]+", td_norm_text(text), flags=re.UNICODE) if w]


def td_is_filler(text):
    n = td_norm_text(text)
    if n in TD_TRUTH_REJECTS:
        return True
    if len(n) < 4:
        return True
    if re.fullmatch(r"[.!؟?…\-_=]+", n):
        return True
    # تکرار یک حرف/کاراکتر برای دور زدن بررسی
    if len(set(n.replace(" ", ""))) <= 2 and len(n.replace(" ", "")) >= 5:
        return True
    return False


def td_answer_quality_score(question, answer):
    """امتیاز چندعاملی برای تشخیص پاسخ‌های تصادفی/تکراری؛ هرگز ادعای تشخیص دروغ ندارد."""
    q = td_norm_text(question)
    a = td_norm_text(answer)
    q_words = set(w for w in td_words(q) if w not in TD_STOPWORDS and len(w) > 2)
    a_words = set(w for w in td_words(a) if w not in TD_STOPWORDS and len(w) > 2)
    if not a_words:
        return 0.0
    overlap = len(q_words & a_words) / max(1, len(q_words)) if q_words else 0.0
    unique_ratio = len(a_words) / max(1, len(td_words(a)))
    # شباهت بالا به خود سؤال علامت بدی است؛ تنوع واژگان و توضیح مستقل امتیاز مثبت می‌گیرد.
    similarity = SequenceMatcher(None, q, a).ratio() if q and a else 0.0
    length_bonus = min(0.25, len(a_words) / 24.0)
    independence = max(0.0, 1.0 - min(1.0, similarity * 1.35))
    return max(0.0, min(1.0, 0.38 * unique_ratio + 0.27 * independence + 0.20 * (1.0 - min(overlap, 0.9)) + 0.15 * length_bonus))


def td_truth_structure(question, answer):
    """بررسی ساختار معنایی سؤال؛ متن پاسخ نگهداری نمی‌شود و فقط در همین نوبت استفاده می‌شود."""
    raw = str(answer or '').strip()
    words = td_words(raw)
    sentences = [x.strip() for x in re.split(r'[.!؟?]+', raw) if x.strip()]
    meta = td_question_meta(question)
    minimums = {
        'memory': (14, 2), 'relationship': (10, 2), 'future': (10, 2),
        'reason': (9, 2), 'self': (8, 1), 'media': (7, 1),
        'advice': (10, 2), 'hypothetical': (10, 2), 'preference': (7, 1),
        'open': (7, 1), 'named_choice': (4, 1), 'place': (5, 1),
        'skill': (5, 1), 'season': (4, 1), 'night_morning': (4, 1),
    }
    min_words, min_sentences = minimums.get(meta, (7, 1))
    if len(words) < min_words and len(raw) < max(18, min_words * 3):
        return False, f'برای این سؤال پاسخ کامل‌تری لازم است؛ حداقل حدود {min_words} کلمه و توضیح مشخص بفرست.'
    if min_sentences > 1 and len(sentences) < min_sentences and len(words) < min_words + 5:
        return False, 'پاسخ خیلی کوتاه است؛ انتخاب یا نظر خودت را همراه با توضیح و دلیل بنویس.'
    return True, ''


def td_validate_truth(question, answer):
    """اعتبارسنجی پیشرفته و محافظه‌کارانه؛ مرتبط‌بودن را می‌سنجد، نه راست/دروغ را."""
    raw = str(answer or '').strip()
    if td_is_filler(raw):
        return False, 'این پاسخ شبیه طفره‌رفتن یا پیام آزمایشی است. یک جواب واقعی و مرتبط بفرست.'
    if len(raw) > 700:
        return False, 'پاسخ بیش از حد طولانی است؛ چند جمله‌ی مشخص و طبیعی کافی است.'
    words = td_words(raw)
    meaningful = [w for w in words if w not in TD_STOPWORDS and len(w) > 1]
    if not meaningful:
        return False, 'پاسخ معنی‌دار پیدا نشد؛ جواب مشخص خودت را بفرست.'

    q = td_norm_text(question)
    meta = td_question_meta(question)
    ok, reason = td_truth_structure(question, raw)
    if not ok:
        return False, reason

    if meta == 'season' and not any(x in raw for x in ('بهار','تابستان','پاییز','زمستان')):
        return False, 'یکی از فصل‌ها را مشخصاً انتخاب کن و اگر سؤال دلیل می‌خواهد، توضیحت را هم بنویس.'
    if meta == 'night_morning' and not any(x in raw for x in ('شب','صبح')):
        return False, 'باید بین شب و صبح انتخاب مشخصی در پاسخ دیده شود.'
    if meta == 'named_choice' and len(meaningful) < 2:
        return False, 'نام اثر را همراه با یک توضیح کوتاه درباره انتخابت بنویس.'
    if meta == 'place' and len(meaningful) < 2:
        return False, 'مقصد یا مکان را مشخص کن و کمی درباره دلیل انتخابت بگو.'
    if meta == 'skill' and len(meaningful) < 2:
        return False, 'مهارتی که انتخاب کردی را مشخص کن و بگو چرا آن را می‌خواهی.'

    # سؤال را کپی نکن؛ شباهت متنی بالا یا پوشش غیرعادی کلمات سؤال، پاسخ را مشکوک می‌کند.
    q_tokens = [w for w in td_words(q) if w not in TD_STOPWORDS and len(w) > 2]
    a_tokens = [w for w in meaningful if len(w) > 2]
    similarity = SequenceMatcher(None, q, td_norm_text(raw)).ratio() if q and raw else 0.0
    same_ratio = sum(1 for w in a_tokens if w in set(q_tokens)) / max(1, len(a_tokens))
    if similarity > 0.78 or (same_ratio > 0.78 and len(a_tokens) <= max(7, len(q_tokens) + 2)):
        return False, 'پاسخ بیش از حد شبیه خود سؤال است؛ جواب واقعی و با کلمات خودت بنویس.'

    # پاسخ‌هایی که فقط یک انتخاب را بدون توضیح می‌فرستند، برای سؤال‌های عمیق کافی نیستند.
    if meta in {'reason','relationship','future','memory','hypothetical','advice','self'} and len(a_tokens) < 5:
        return False, 'این سؤال نیاز به پاسخ شخصی‌تر و کمی توضیح دارد؛ فقط یک عبارت کوتاه کافی نیست.'

    # الگوهای اسپم/تکرار کاراکتر/کلمات یکسان.
    compact = re.sub(r'\s+', '', td_norm_text(raw))
    if len(compact) >= 8 and len(set(compact)) <= 2:
        return False, 'پاسخ شبیه اسپم یا متن آزمایشی است؛ یک پاسخ طبیعی بفرست.'
    repeated = [w for w in words if words.count(w) >= 4 and len(w) > 2]
    if repeated and len(set(words)) <= 3:
        return False, 'تکرار بیش از حد کلمات قابل قبول نیست؛ پاسخ واقعی خودت را بنویس.'

    score = td_answer_quality_score(question, raw)
    threshold = 0.30 if meta in {'open','preference','named_choice','place','skill','season','night_morning'} else 0.34
    if score < threshold:
        return False, 'پاسخ از نظر محتوایی برای این سؤال کافی یا مستقل به نظر نمی‌رسد؛ واضح‌تر و مرتبط‌تر جواب بده.'
    return True, 'پاسخ از نظر ارتباط، استقلال و کامل‌بودن قابل تأیید است.'


def _td_base_validate_dare(task, answer):
    """اعتبارسنجی سخت‌گیرانه‌ی جرأت‌ها؛ جرأت ناشناخته هرگز خودکار معتبر نمی‌شود."""
    task_text = str(task or "").strip()
    a = td_norm_text(answer)
    raw = str(answer or "").strip()
    if len(raw) > 700:
        return False, "پاسخ خیلی طولانی است؛ فقط نتیجه‌ی همان چالش را بفرست."

    # Verifierهای مخصوص چالش‌های معنادار نسخه 39. اگر شرط مشخص رعایت نشده باشد، رد می‌شود.
    words = td_words(raw)
    sentences = [x.strip() for x in re.split(r"[.!؟?]+", raw) if x.strip()]
    if len(words) < 3 and len(raw) < 10:
        return False, "پاسخ برای بررسی کافی نیست؛ خودِ جرأت را کامل انجام بده."
    # اگر چالش توصیفی است، پاسخ صرفاً تکرار متن چالش نباشد.
    similarity = SequenceMatcher(None, td_norm_text(task_text), a).ratio() if task_text and a else 0.0
    if similarity > 0.82:
        return False, "پاسخ بیشتر شبیه تکرار متن چالش است؛ نتیجه‌ی واقعی انجام چالش را بفرست."

    if "خاطره کوتاه و واقعی" in task_text:
        if len(words) < 15 or len(sentences) < 2:
            return False, "خاطره باید حداقل ۲ جمله و ۱۵ کلمه داشته باشد."
        return True, "خاطره با حداقل شرایط چالش ثبت شد."

    if "سه ویژگی مثبت و واقعی" in task_text:
        if len(sentences) < 3 or len(words) < 9:
            return False, "سه ویژگی مثبت را با توضیح کوتاه برای هرکدام بنویس."
        return True, "هر سه ویژگی با توضیح کافی دریافت شد."

    if "توصیه‌ای که واقعاً به آن باور داری" in task_text:
        if len(sentences) < 2 or len(words) < 12:
            return False, "یک توصیه و دلیل واقعی برای باورداشتن به آن بنویس."
        return True, "توصیه و دلیل آن دریافت شد."

    if "اتفاق خوب کوچک" in task_text:
        if len(sentences) < 2 or len(words) < 12:
            return False, "اتفاق را در حداقل دو جمله تعریف کن و بگو چرا مهم بود."
        return True, "توضیح اتفاق و دلیل اهمیت آن دریافت شد."

    if "با ۳ نشانه توصیف کن" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "حداقل سه سرنخ و توضیح کافی برای حدس‌زدن بده؛ نام شخصیت را ننویس."
        return True, "سه سرنخ قابل‌بررسی دریافت شد."

    if "سه دلیل واقعی" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "انتخابت را با سه دلیل مشخص توضیح بده."
        return True, "انتخاب و سه دلیل آن دریافت شد."

    if "با سه سرنخ توصیف کن" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "سه سرنخ مشخص و حداقل سه جمله بنویس و نام اثر را نگو."
        return True, "سرنخ‌های کافی دریافت شد."

    if "یک سؤال جالب و عمیق طراحی کن" in task_text:
        if len(words) < 8 or "؟" not in raw and "?" not in raw:
            return False, "یک سؤال کامل و قابل‌بحث با حداقل ۸ کلمه بنویس."
        return True, "سؤال کامل دریافت شد."

    if "یک خاطره را بدون گفتن زمان و مکان دقیقش" in task_text:
        if len(sentences) < 3 or len(words) < 15:
            return False, "خاطره باید حداقل ۳ جمله و ۱۵ کلمه داشته باشد و وارد جزئیات زمانی یا مکانی دقیق نشود."
        return True, "خاطره با شرایط چالش دریافت شد."

    if "یک انتخاب سخت بین دو چیز" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "دو انتخاب را مشخص کن و حداقل یک دلیل برای انتخابت بنویس."
        return True, "انتخاب و دلیل آن دریافت شد."

    if "سه چیز کوچک که معمولاً روزت را بهتر می‌کنند" in task_text:
        if len(sentences) < 3 or len(words) < 10:
            return False, "سه مورد را با توضیح کوتاه برای هرکدام بنویس."
        return True, "سه مورد و توضیح آن‌ها دریافت شد."

    if "یک تغییر کوچک اما واقعی" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "تغییر را مشخص کن و بگو چرا واقعاً می‌خواهی انجامش بدهی."
        return True, "تغییر و دلیل آن دریافت شد."

    if "یک تعریف صادقانه و مشخص از فضای همین گروه" in task_text:
        if len(sentences) < 2 or len(words) < 8:
            return False, "تعریف باید مشخص باشد و حداقل دو جمله داشته باشد."
        return True, "تعریف مشخص دریافت شد."

    if "باران»، «چراغ» و «پنجره" in task_text:
        required = {"باران", "چراغ", "پنجره"}
        if not required.issubset(set(words)) or len(sentences) < 3:
            return False, "داستان باید هر سه کلمه را داشته باشد و حداقل ۳ جمله باشد."
        return True, "داستان سه‌جمله‌ای با هر سه کلمه دریافت شد."

    if "پایان متفاوت برای یک داستان یا فیلم" in task_text:
        if len(sentences) < 2 or len(words) < 12:
            return False, "پایان پیشنهادی و دلیل انتخابش را در حداقل دو جمله توضیح بده."
        return True, "پایان متفاوت و دلیل آن دریافت شد."

    if "یک سؤال درباره آینده از خودت بپرس" in task_text:
        if len(sentences) < 2 or len(words) < 10 or ("؟" not in raw and "?" not in raw):
            return False, "یک سؤال آینده‌محور و سپس پاسخ خودت را بنویس."
        return True, "سؤال و پاسخ دریافت شد."

    if "خاطره شیرین از دوران کودکی یا مدرسه" in task_text:
        if len(sentences) < 3 or len(words) < 15:
            return False, "خاطره باید حداقل ۳ جمله و ۱۵ کلمه داشته باشد."
        return True, "خاطره دریافت شد."

    if "ویژگی اخلاقی را انتخاب کن" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "ویژگی اخلاقی و دلیل اهمیت آن را توضیح بده."
        return True, "ویژگی و توضیح آن دریافت شد."

    if "سه گزینه برای یک شب دوستانه" in task_text:
        if len(sentences) < 4 or len(words) < 15:
            return False, "سه گزینه و سپس انتخاب خودت با دلیل را بنویس."
        return True, "سه گزینه و انتخاب نهایی دریافت شد."

    if "قبلاً دوست نداشتی" in task_text:
        if len(sentences) < 2 or len(words) < 12:
            return False, "چیزی را که نظرت درباره‌اش تغییر کرده و دلیل تغییر را توضیح بده."
        return True, "تجربه و دلیل تغییر نظر دریافت شد."

    if "معمای کوتاه و منصفانه" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "معما باید حداقل ۳ جمله و ۱۲ کلمه داشته باشد و پاسخ را داخل همان پیام ننویس."
        return True, "معمای قابل‌طرح دریافت شد."

    if "وقت بیشتر" in task_text and "پول بیشتر" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "یکی از دو گزینه را انتخاب کن و حداقل یک دلیل بیاور."
        return True, "انتخاب و دلیل دریافت شد."

    if "آهنگ یا سبک موسیقی" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "سبک یا انتخاب موسیقی و حسی که ایجاد می‌کند را توضیح بده."
        return True, "انتخاب موسیقی و توضیح احساس دریافت شد."

    if "مکان آرامش‌بخش" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "حداقل سه ویژگی از مکان را در سه جمله یا بیشتر توصیف کن و نام مکان را نگو."
        return True, "توصیف مکان دریافت شد."

    if "جمله انگیزشی مخصوص یکی از بازیکنان" in task_text:
        if len(sentences) < 2 or len(words) < 8:
            return False, "یک پیام انگیزشی مشخص و حداقل دو جمله‌ای بنویس."
        return True, "پیام انگیزشی دریافت شد."

    if "اگر..." in task_text and "آینده" in task_text:
        if len(sentences) < 2 or len(words) < 10:
            return False, "شرایط فرضی، انتخاب خودت و دلیل انتخاب را توضیح بده."
        return True, "سناریو و انتخاب دریافت شد."

    if "انگار صحنه‌ای از یک فیلم" in task_text:
        if len(sentences) < 3 or len(words) < 15:
            return False, "صحنه را حداقل در ۳ جمله و ۱۵ کلمه روایت کن."
        return True, "روایت دریافت شد."

    if "سه چیز را که برای داشتن یک دوستی خوب" in task_text:
        if len(sentences) < 4 or len(words) < 14:
            return False, "سه مورد را بنویس و یکی را به عنوان مهم‌ترین انتخاب کن و دلیلش را بگو."
        return True, "سه مورد و انتخاب مهم‌تر دریافت شد."

    if "تصمیم فرضی درباره سفر، شغل یا یادگیری" in task_text:
        if len(sentences) < 3 or len(words) < 14:
            return False, "دو مسیر را مشخص کن، یکی را انتخاب کن و حداقل دو دلیل بده."
        return True, "تصمیم و دلایل دریافت شد."

    if "فقط با احساس و فضای آن توصیف کن" in task_text:
        if len(sentences) < 3 or len(words) < 12:
            return False, "فضای خاطره را حداقل در سه جمله و بدون نام افراد دیگر توصیف کن."
        return True, "توصیف دریافت شد."

    # v40: verifierهای محتوایی جدید. پاسخ فقط با حداقل ساختار لازم پذیرفته می‌شود.
    for marker, (min_sentences, min_words, fail_message) in V40_DARE_RULES.items():
        if marker in task_text:
            if len(sentences) < min_sentences or len(words) < min_words:
                return False, fail_message
            # جلوگیری از پیام‌های صرفاً تکراری/اسپمی؛ حداقل دو توکن معنادار باید وجود داشته باشد.
            meaningful = [w for w in words if len(w) > 2 and w not in TD_STOPWORDS]
            if len(set(meaningful)) < 3:
                return False, "پاسخ بیش از حد تکراری یا خالی از محتوای مشخص است؛ نتیجه‌ی واقعی چالش را بنویس."
            return True, "چالش با حداقل شرایط محتوایی تأیید شد."

    # هر جرأت باید یک verifier مشخص داشته باشد.
    # توجه: اینجا عمداً قبل از td_is_filler وارد verifierهای دقیق می‌شویم؛
    # چون پاسخ‌های مجاز مثل «7 7 7 7 7» یا «ماه» ذاتاً کوتاه‌اند و نباید اشتباهاً اسپم تلقی شوند. این فهرست عمداً fail-closed است:
    # اگر متن جرأت جدیدی اضافه شود ولی verifier آن نوشته نشده باشد، پاسخ الکی پذیرفته نمی‌شود.
    if "دقیقاً با ۳ ایموجی" in task_text:
        chars = [c for c in raw if unicodedata.category(c) in ("So", "Sk")]
        if len(chars) != 3 or len(td_words(raw)) != 0:
            return False, "باید دقیقاً ۳ ایموجی و بدون متن بفرستی."
        return True, "چالش دقیقاً مطابق الگو انجام شده است."

    if "باران» را برعکس" in task_text:
        if a != "ناراب":
            return False, "کلمه‌ی «باران» را دقیقاً برعکس بفرست."
        return True, "چالش دقیقاً مطابق الگو انجام شده است."

    if "عدد 7 را پنج بار" in task_text:
        if a != "7 7 7 7 7":
            return False, "باید دقیقاً 7 را پنج بار با فاصله بفرستی."
        return True, "چالش دقیقاً مطابق الگو انجام شده است."

    if "دقیقاً ۵ کلمه" in task_text:
        if len(td_words(raw)) != 5:
            return False, "جمله باید دقیقاً ۵ کلمه داشته باشد."
        return True, "تعداد کلمات درست است."

    if "ماه / باران / جنگل" in task_text:
        if a not in {"ماه", "باران", "جنگل"}:
            return False, "فقط یکی از «ماه»، «باران» یا «جنگل» را بفرست."
        return True, "انتخاب معتبر است."

    if "🌙 ⭐ 🌙 ⭐" in task_text:
        if raw != "🌙 ⭐ 🌙 ⭐":
            return False, "الگو را دقیقاً مثل نمونه بفرست."
        return True, "الگو دقیقاً درست است."

    if "با حرف «م» شروع" in task_text:
        if not a.startswith("م") or len(td_words(raw)) != 1 or len(a) < 4:
            return False, "یک کلمه‌ی حداقل ۴ حرفی که با حرف «م» شروع شود بفرست."
        return True, "کلمه با شرط چالش مطابقت دارد."

    if "من آماده‌ام" in task_text:
        if a not in {"من آمادهام", "من آماده‌ام"}:
            return False, "عبارت «من آماده‌ام» را دقیقاً یک بار بفرست."
        return True, "عبارت درست است."

    if "حرف «ا» در آن نباشد" in task_text:
        if "ا" in a or len(td_words(raw)) < 2:
            return False, "یک جمله‌ی واقعی بدون حرف «ا» بفرست."
        return True, "جمله با شرط چالش مطابقت دارد."

    if "عدد بین 10 و 99" in task_text:
        if not re.fullmatch(r"\d{2}", a) or a[0] == a[1]:
            return False, "یک عدد دو رقمی بین 10 و 99 با دو رقم متفاوت بفرست."
        return True, "عدد با شرط چالش مطابقت دارد."

    if "سه کلمه‌ی مثبت" in task_text:
        positive = {"خوب", "عالی", "زیبا", "آرام", "شاد", "دوستداشتنی", "امید", "امیدوار", "مهربان", "موفق", "خوشحال", "مثبت", "قشنگ"}
        words = td_words(raw)
        if len(words) != 3 or len(set(words)) != 3 or not any(w in positive for w in words):
            return False, "دقیقاً سه کلمه‌ی متفاوت بفرست که دست‌کم یکی از آن‌ها معنای مثبت داشته باشد."
        return True, "چالش با شرط تعداد و محتوای آن مطابقت دارد."

    if "معمای خیلی کوتاه" in task_text:
        words = td_words(raw)
        if len(words) < 8:
            return False, "معما باید حداقل ۸ کلمه داشته باشد."
        # برای معما پاسخ را «درست» اعلام نمی‌کنیم؛ فقط انجام‌دادن قابل‌بررسیِ حداقل شرط را می‌پذیریم.
        return True, "حداقل شرط چالش رعایت شده است."

    if "کلمه «جنگل» را برعکس" in task_text:
        if a != "لگنج":
            return False, "کلمه‌ی «جنگل» را دقیقاً برعکس بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "کلمه «کتاب» را برعکس" in task_text:
        if a != "باتک":
            return False, "کلمه‌ی «کتاب» را دقیقاً برعکس بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "عدد 4 را دقیقاً شش بار" in task_text:
        if a != "4 4 4 4 4 4":
            return False, "باید دقیقاً 4 را شش بار با فاصله بفرستی."
        return True, "چالش دقیقاً انجام شد."

    if "عدد 9 را دقیقاً چهار بار" in task_text:
        if a != "9 9 9 9":
            return False, "باید دقیقاً 9 را چهار بار با فاصله بفرستی."
        return True, "چالش دقیقاً انجام شد."

    if "دقیقاً ۴ ایموجی متفاوت" in task_text:
        chars = [c for c in raw if unicodedata.category(c) in ("So", "Sk")]
        if len(chars) != 4 or len(set(chars)) != 4 or len(td_words(raw)) != 0:
            return False, "باید دقیقاً ۴ ایموجی متفاوت و بدون متن بفرستی."
        return True, "چالش دقیقاً انجام شد."

    if "دقیقاً ۵ ایموجی بفرست" in task_text:
        chars = [c for c in raw if unicodedata.category(c) in ("So", "Sk")]
        if len(chars) != 5 or len(set(chars)) < 3 or len(td_words(raw)) != 0:
            return False, "باید دقیقاً ۵ ایموجی بفرستی که حداقل ۳ تای آن‌ها متفاوت باشند."
        return True, "چالش دقیقاً انجام شد."

    if "⭐ 🌙 ☁️ ⭐ 🌙 ☁️" in task_text:
        if raw != "⭐ 🌙 ☁️ ⭐ 🌙 ☁️":
            return False, "الگو را دقیقاً مثل نمونه بفرست."
        return True, "الگو دقیقاً درست است."

    if "برف / باران / آفتاب" in task_text:
        if a not in {"برف", "باران", "آفتاب"}:
            return False, "فقط یکی از «برف»، «باران» یا «آفتاب» را بفرست."
        return True, "انتخاب معتبر است."

    if "دریا / جنگل / کوه" in task_text:
        if a not in {"دریا", "جنگل", "کوه"}:
            return False, "فقط یکی از «دریا»، «جنگل» یا «کوه» را بفرست."
        return True, "انتخاب معتبر است."

    if "با «س» شروع شود" in task_text:
        if len(td_words(raw)) != 1 or not a.startswith("س") or len(a) < 5:
            return False, "یک کلمه‌ی حداقل ۵ حرفی که با «س» شروع شود بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "با «ب» شروع شود" in task_text:
        if len(td_words(raw)) != 1 or not a.startswith("ب") or len(a) < 5:
            return False, "یک کلمه‌ی حداقل ۵ حرفی که با «ب» شروع شود بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "عبارت «من انتخاب کردم»" in task_text:
        if a != "من انتخاب کردم":
            return False, "عبارت «من انتخاب کردم» را دقیقاً یک بار بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "عبارت «نوبت من است»" in task_text:
        if a != "نوبت من است":
            return False, "عبارت «نوبت من است» را دقیقاً یک بار بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "عدد دو رقمی بین 20 و 80" in task_text:
        if not re.fullmatch(r"\d{2}", a) or not (20 <= int(a) <= 80) or a[0] == a[1]:
            return False, "یک عدد دو رقمی بین 20 و 80 با دو رقم متفاوت بفرست."
        return True, "عدد با شرط چالش مطابقت دارد."

    if "عدد سه رقمی" in task_text:
        if not re.fullmatch(r"\d{3}", a) or len(set(a)) != 3:
            return False, "یک عدد سه رقمی بفرست که هر سه رقمش متفاوت باشند."
        return True, "عدد با شرط چالش مطابقت دارد."

    if "سه کلمه متفاوت بنویس که هر سه با حرف «م»" in task_text:
        words = td_words(raw)
        if len(words) != 3 or len(set(words)) != 3 or not all(w.startswith("م") for w in words):
            return False, "دقیقاً سه کلمه‌ی متفاوت بفرست که هر سه با «م» شروع شوند."
        return True, "چالش دقیقاً انجام شد."

    if "کلمه «امروز» وجود داشته باشد" in task_text:
        words = td_words(raw)
        if len(words) < 4 or "امروز" not in words:
            return False, "یک جمله‌ی حداقل ۴ کلمه‌ای بفرست که کلمه «امروز» در آن باشد."
        return True, "چالش دقیقاً انجام شد."

    if "کلمه «دوست» وجود داشته باشد" in task_text:
        words = td_words(raw)
        if len(words) < 4 or "دوست" not in words:
            return False, "یک جمله‌ی حداقل ۴ کلمه‌ای بفرست که کلمه «دوست» در آن باشد."
        return True, "چالش دقیقاً انجام شد."

    if "یک جمله ۶ کلمه‌ای" in task_text:
        if len(td_words(raw)) != 6:
            return False, "جمله باید دقیقاً ۶ کلمه داشته باشد."
        return True, "تعداد کلمات درست است."

    if "یک جمله ۷ کلمه‌ای" in task_text:
        if len(td_words(raw)) != 7:
            return False, "جمله باید دقیقاً ۷ کلمه داشته باشد."
        return True, "تعداد کلمات درست است."

    if "🟦 🟨 🟦 🟨 🟦" in task_text:
        if raw != "🟦 🟨 🟦 🟨 🟦":
            return False, "الگو را دقیقاً مثل نمونه بفرست."
        return True, "الگو دقیقاً درست است."

    if "🌧️ 🌙 🌧️ 🌙" in task_text:
        if raw != "🌧️ 🌙 🌧️ 🌙":
            return False, "الگو را دقیقاً مثل نمونه بفرست."
        return True, "الگو دقیقاً درست است."

    if "آرام / شاد / امیدوار" in task_text:
        if a not in {"آرام", "شاد", "امیدوار"}:
            return False, "فقط یکی از «آرام»، «شاد» یا «امیدوار» را بفرست."
        return True, "انتخاب معتبر است."

    if "کلمه «دوستی» را برعکس" in task_text:
        if a != "یتسود":
            return False, "کلمه‌ی «دوستی» را دقیقاً برعکس بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "کلمه «ماه» را سه بار" in task_text:
        if a != "ماه ماه ماه":
            return False, "کلمه «ماه» را دقیقاً سه بار با فاصله بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "کلمه «باران» را سه بار" in task_text:
        if a != "باران باران باران":
            return False, "کلمه «باران» را دقیقاً سه بار با فاصله بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "دقیقاً ۶ کلمه بنویس" in task_text:
        if len(td_words(raw)) != 6:
            return False, "باید دقیقاً ۶ کلمه بفرستی."
        return True, "چالش دقیقاً انجام شد."

    if "دقیقاً ۴ کلمه متفاوت بنویس که با حرف «خ»" in task_text:
        words = td_words(raw)
        if len(words) != 4 or len(set(words)) != 4 or not all(w.startswith("خ") for w in words):
            return False, "دقیقاً ۴ کلمه متفاوت بفرست که با «خ» شروع شوند."
        return True, "چالش دقیقاً انجام شد."

    if "با «ر» شروع شود" in task_text:
        if len(td_words(raw)) != 1 or not a.startswith("ر") or len(a) < 5:
            return False, "یک کلمه‌ی حداقل ۵ حرفی که با «ر» شروع شود بفرست."
        return True, "چالش دقیقاً انجام شد."

    if "عدد زوج بین 20 و 50" in task_text:
        if not re.fullmatch(r"\d{2}", a):
            return False, "یک عدد دو رقمی بفرست."
        n = int(a)
        if not (20 <= n <= 50 and n % 2 == 0 and n % 4 == 0):
            return False, "یک عدد زوج بین 20 و 50 که بر 4 بخش‌پذیر باشد بفرست."
        return True, "عدد با شرط چالش مطابقت دارد."

    if "عدد فرد بین 21 و 49" in task_text:
        if not re.fullmatch(r"\d{2}", a):
            return False, "یک عدد دو رقمی بفرست."
        n = int(a)
        if not (21 <= n <= 49 and n % 2 == 1 and a[0] != a[1]):
            return False, "یک عدد فرد بین 21 و 49 با رقم‌های متفاوت بفرست."
        return True, "عدد با شرط چالش مطابقت دارد."

    # برای verifierهای شناخته‌شده هم پاسخ بسیار شبیه متن خود چالش یا یک متن بی‌معنی رد می‌شود.
    # Fail closed: هیچ جرأت جدیدی بدون verifier نباید با یک متن تصادفی قبول شود.
    if td_is_filler(raw):
        return False, "این پیام برای بررسی چالش کافی نیست؛ خودِ چالش را دقیق انجام بده."
    return False, "این چالش هنوز verifier دقیق ندارد؛ برای جلوگیری از تأیید اشتباه، این پاسخ پذیرفته نشد."

def td_task_is_current(game, task, user_id):
    """اعتبارسنجی سخت‌گیرانهٔ task: گروه، کاربر، راند و اندیس نوبت باید همگی یکی باشند."""
    if not game or not task or not game.get("started"):
        return False
    current = td_current_player(game)
    if not current or int(current.get("id", -1)) != int(user_id):
        return False
    return (
        int(task.get("chat_id", 0)) == int(game.get("chat_id", 0)) and
        int(task.get("user_id", -1)) == int(user_id) and
        int(task.get("turn_index", -1)) == int(game.get("turn_index", -2)) and
        int(task.get("round", -1)) == int(game.get("round", -2))
    )


def td_expired(task, now=None):
    now = time.time() if now is None else now
    return now - float(task.get("created", 0)) > TD_TASK_TIMEOUT_MINUTES * 60


async def td_cleanup_expired_tasks(bot):
    """پاکسازی taskهای منقضی؛ خرابی Telegram نباید نوبت بازی را متوقف کند."""
    now = time.time()
    for key, task in list(TD_PRIVATE_TASKS.items()):
        if not isinstance(key, tuple) or len(key) != 2 or not td_expired(task, now):
            continue
        chat_id, user_id = key
        game = TD_GAMES.get(int(chat_id))
        try:
            if game and game.get("started") and td_task_is_current(game, task, user_id):
                name = td_clean_name(game.get("players", {}).get(user_id, {}).get("name", "بازیکن"))
                # State را قبل از ارسال شبکه‌ای جلو می‌بریم تا شکست Telegram باعث گیرکردن بازی نشود.
                async with TD_STATE_LOCK:
                    if td_task_is_current(game, task, user_id):
                        game["active_task"] = None
                        td_add_failed_turn(game, user_id)
                        TD_PRIVATE_TASKS.pop(key, None)
                        td_advance(game)
                    else:
                        TD_PRIVATE_TASKS.pop(key, None)
                        continue
                try:
                    await bot.send_message(
                        chat_id,
                        f"⌛ نوبت <b>{name}</b> به‌دلیل پایان مهلت بسته شد.\n"
                        "🚫 هیچ پاسخی ذخیره نشد؛ نوبت به بازیکن بعدی رسید.",
                        parse_mode="HTML",
                    )
                except TelegramError as exc:
                    logger.warning("TD expired-task announcement failed for %s/%s: %s", chat_id, user_id, exc)
                try:
                    await td_announce_turn(bot, game, None)
                except Exception as exc:
                    logger.warning("TD next-turn announcement failed for %s: %s", chat_id, exc)
            else:
                TD_PRIVATE_TASKS.pop(key, None)
        except Exception as exc:
            logger.exception("TD expired-task cleanup crashed for %s/%s: %s", chat_id, user_id, exc)
            TD_PRIVATE_TASKS.pop(key, None)


async def td_cleanup_job(context):
    await td_cleanup_expired_tasks(context.bot)


def td_current_player(game):
    order = game.get("turn_order", [])
    if not order:
        return None
    if game["turn_index"] >= len(order):
        game["turn_index"] = 0
    return game["players"].get(order[game["turn_index"]])


def td_advance(game):
    if not game.get("turn_order"):
        return None
    game["turn_index"] = (game["turn_index"] + 1) % len(game["turn_order"])
    if game["turn_index"] == 0:
        game["round"] += 1
    return td_current_player(game)


def td_score_for(kind, attempts):
    """امتیاز نوبت؛ فقط متادیتای بازی است و هیچ متن پاسخی ذخیره نمی‌شود."""
    base = 10 if kind == "truth" else 15
    # پاسخ معتبر در اولین تلاش یک پاداش کوچک می‌گیرد.
    clean_bonus = 5 if int(attempts or 0) == 1 else 0
    return base + clean_bonus


def td_init_scores(game):
    game.setdefault("scores", {})
    game.setdefault("successful_turns", {})
    game.setdefault("failed_turns", {})
    for uid in game.get("players", {}):
        game["scores"].setdefault(uid, 0)
        game["successful_turns"].setdefault(uid, 0)
        game["failed_turns"].setdefault(uid, 0)


def td_add_score(game, user_id, kind, attempts):
    td_init_scores(game)
    game["total_turns"] = int(game.get("total_turns", 0)) + 1
    uid = int(user_id)
    points = td_score_for(kind, attempts)
    game["scores"][uid] = int(game["scores"].get(uid, 0)) + points
    game["successful_turns"][uid] = int(game["successful_turns"].get(uid, 0)) + 1
    return points


def td_add_failed_turn(game, user_id):
    td_init_scores(game)
    game["total_turns"] = int(game.get("total_turns", 0)) + 1
    uid = int(user_id)
    game["failed_turns"][uid] = int(game["failed_turns"].get(uid, 0)) + 1


def td_scoreboard_text(game, final=False):
    td_init_scores(game)
    rows = []
    for uid, player in game.get("players", {}).items():
        rows.append((int(game["scores"].get(uid, 0)), int(game["successful_turns"].get(uid, 0)), int(game["failed_turns"].get(uid, 0)), td_clean_name(player.get("name", "بازیکن"))))
    rows.sort(key=lambda x: (x[0], x[1], -x[2]), reverse=True)
    title = "🏆 <b>نتیجه نهایی جرأت یا حقیقت</b>" if final else "📊 <b>امتیاز فعلی بازی</b>"
    lines = [title, ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, (score, ok, failed, name) in enumerate(rows, 1):
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} <b>{name}</b> — ⭐ {score} امتیاز | ✅ {ok} موفق | 🛑 {failed} نوبت از دست‌رفته")
    if final and rows:
        top = rows[0][0]
        winners = [r[3] for r in rows if r[0] == top]
        if len(winners) == 1:
            lines.append(f"\n🎉 قهرمان این دور: <b>{winners[0]}</b> با {top} امتیاز!")
        else:
            lines.append("\n🤝 این دور مساوی شد: " + "، ".join(winners) + f" — {top} امتیاز")
    return "\n".join(lines)


async def td_finalize_game(bot, game, reason="manual"):
    """پایان بازی، اعلام امتیاز و ثبت فقط نتیجه‌ی بازی در آمار عمومی."""
    if not game:
        return
    td_init_scores(game)
    chat_id = game.get("chat_id")
    # ثبت آمار عمومی فقط پس از پایان؛ متن پاسخ‌ها وارد آمار نمی‌شود.
    rows = sorted(game.get("scores", {}).items(), key=lambda kv: kv[1], reverse=True)
    top_score = rows[0][1] if rows else 0
    for uid, score in rows:
        player = game.get("players", {}).get(uid, {})
        try:
            record_game_result(chat_id, uid, player.get("name", "بازیکن"), "truth_or_dare", bool(score == top_score and top_score > 0))
        except Exception as exc:
            logger.warning("TD final stats failed for %s/%s: %s", chat_id, uid, exc)
    try:
        await bot.send_message(chat_id, td_scoreboard_text(game, final=True), parse_mode="HTML")
    except TelegramError as exc:
        logger.warning("TD final scoreboard send failed: %s", exc)


def td_status_text(game):
    players = game.get("players", {})
    order = game.get("turn_order", list(players))
    target = game.get("target_players")
    lines = [f"🕵️ <b>اتاق جرأت یا حقیقت</b>", f"👥 بازیکنان: {len(players)}" + (f" / {target}" if target else "")]
    if not game.get("started"):
        if target:
            lines.append(f"\n🎯 ظرفیت این دور: <b>{target} نفر</b> — با رسیدن به ظرفیت، بازی آماده شروع خودکار می‌شود.")
        else:
            lines.append("\n⏳ اول تعداد بازیکنان این دور را مشخص کنید، سپس بقیه وارد بازی شوند.")
    else:
        current = td_current_player(game)
        if current:
            lines.append(f"\n🎯 نوبت: <b>{td_clean_name(current['name'])}</b>")
            lines.append(f"🔢 راند: {game.get('round', 1)}")
            td_init_scores(game)
            lines.append(f"⭐ امتیاز این دور: {sum(game.get('scores', {}).values())}")
    lines.append("\n" + "\n".join(f"{i+1}. {td_clean_name(players[uid]['name'])}" for i, uid in enumerate(order) if uid in players))
    return "\n".join(lines)


async def td_send_media(bot, chat_id, event, caption=None):
    if not owner_feature_enabled("game_media"):
        return False
    """Robust optional GIF sender.
    Priority: cached Telegram file_id -> direct URL -> resolved URL -> temporary download.
    Media failures are isolated and can never stop the game flow.
    """
    sources = TD_MEDIA.get(event, [])
    cache_key = f"td:{event}"
    candidates = []
    cached = TD_MEDIA_CACHE.get(cache_key)
    if cached:
        candidates.append(("cache", cached))
    now = time.time()
    healthy_sources = [
        src for src in sources
        if src != cached and now >= float(TD_MEDIA_SOURCE_COOLDOWN.get(src, 0))
    ]
    # منبع آخر را پشت سر هم تکرار نکن؛ ولی اگر فقط همان منبع سالم باشد، دوباره مجاز است.
    last_src = TD_MEDIA_LAST_SOURCE.get(cache_key)
    if len(healthy_sources) > 1 and last_src in healthy_sources:
        healthy_sources.remove(last_src)
        healthy_sources.append(last_src)
    random.shuffle(healthy_sources)
    candidates.extend(("source", src) for src in healthy_sources)
    for kind, src in candidates:
        try:
            media_caption = caption if caption is not None else TD_MEDIA_CAPTIONS.get(event)
            try:
                msg = await asyncio.wait_for(
                    bot.send_animation(chat_id=chat_id, animation=src, caption=media_caption),
                    timeout=10,
                )
                fid = getattr(getattr(msg, "animation", None), "file_id", None)
                if fid:
                    TD_MEDIA_CACHE[cache_key] = fid
                    try:
                        # Cache is best-effort; media must never depend on disk I/O.
                        save_json_safe(DATA_DIR / "td_media_cache.json", TD_MEDIA_CACHE)
                    except Exception:
                        pass
                if kind == "source":
                    TD_MEDIA_LAST_SOURCE[cache_key] = src
                    TD_MEDIA_SOURCE_COOLDOWN.pop(src, None)
                return True
            except (TelegramError, asyncio.TimeoutError, Exception) as direct_exc:
                if kind == "cache":
                    TD_MEDIA_CACHE.pop(cache_key, None)
                    logger.info("TD cached media invalid for %s: %s", event, direct_exc)
                # Try resolving/downloading a real GIF when Telegram cannot fetch the URL.
                resolved = await asyncio.wait_for(
                    asyncio.to_thread(_resolve_media_for_download, src), timeout=12
                )
                if not resolved:
                    raise direct_exc
                data, filename = resolved
                if not data or len(data) > 20 * 1024 * 1024 or data[:6] not in (b"GIF87a", b"GIF89a"):
                    raise ValueError("media empty, too large, or not a GIF")
                upload = io.BytesIO(data)
                upload.name = filename or f"{event}.gif"
                msg = await asyncio.wait_for(
                    bot.send_animation(chat_id=chat_id, animation=upload, caption=media_caption),
                    timeout=12,
                )
                fid = getattr(getattr(msg, "animation", None), "file_id", None)
                if fid:
                    TD_MEDIA_CACHE[cache_key] = fid
                    try:
                        save_json_safe(DATA_DIR / "td_media_cache.json", TD_MEDIA_CACHE)
                    except Exception:
                        pass
                return True
        except Exception as exc:
            if kind == "source":
                TD_MEDIA_SOURCE_COOLDOWN[src] = time.time() + TD_MEDIA_SOURCE_FAIL_SECONDS
            logger.info("TD media attempt failed for %s: %s", event, exc)
    return False


async def td_send_private_response_notice(bot, user_id, chat_id, player_name):
    """بعد از انتخاب گروهی، فقط راهنمای پاسخ خصوصی را برای بازیکن می‌فرستد."""
    try:
        sent = await bot.send_message(
            chat_id=user_id,
            text=(
                f"📩 <b>نوبت {td_clean_name(player_name)}</b>\n\n"
                "سؤال/چالش را همین حالا در گروه می‌بینی.\n"
                "🔒 فقط <b>پاسخ همان سؤال/چالش</b> را همین‌جا برای ربات بفرست.\n\n"
                "🧹 پیام پاسخ بعد از بررسی خودکار حذف می‌شود.\n"
                "🚫 متن یا جزئیات پاسخ در گروه منتشر نمی‌شود و پاسخ برای استفادهٔ بعدی ذخیره نمی‌شود.\n"
                "🧠 بررسی سخت‌گیرانه است و پاسخ فقط برای <b>همین نوبت و همین بازیکن</b> پذیرفته می‌شود."
            ),
            parse_mode="HTML",
        )
        TD_PRIVATE_READY_USERS.add(int(user_id))
        task = TD_PRIVATE_TASKS.get(td_task_key(chat_id, user_id))
        if task and sent:
            task["private_notice_message_id"] = sent.message_id
        return True
    except Forbidden:
        return False
    except TelegramError as e:
        logger.warning(f"TD private response notice failed for {user_id}: {e}")
        return False


async def td_announce_turn(bot, game, context):
    player = td_current_player(game)
    if not player:
        return
    game["active_task"] = None
    name = td_clean_name(player["name"])
    try:
        await bot.send_message(
            game["chat_id"],
            f"🎯 <b>نوبت {name} است!</b>\n\n"
        "از همین پیام یکی از دو گزینه را انتخاب کن:\n"
        "🗣️ <b>حقیقت</b> یا 🔥 <b>جرأت</b>\n\n"
        "📩 بعد از انتخاب، سؤال/چالش در همین گروه نمایش داده می‌شود و فقط پاسخ را باید در Private ربات بفرستی.\n"
        "🧹 پیام پاسخ در Private بعد از بررسی پاک می‌شود و متن یا جزئیات پاسخ در گروه گفته نمی‌شود.\n"
        "🔒 هر پاسخ فقط به همین بازیکن و همین نوبت متصل است.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗣️ حقیقت", callback_data=f"tdg_choice_truth:{game['chat_id']}:{player['id']}:{game.get('turn_index', 0)}:{game.get('round', 1)}"),
             InlineKeyboardButton("🔥 جرأت", callback_data=f"tdg_choice_dare:{game['chat_id']}:{player['id']}:{game.get('turn_index', 0)}:{game.get('round', 1)}")],
        ]),
    )
    except TelegramError as exc:
        logger.warning("TD turn announcement failed for %s: %s", game.get("chat_id"), exc)
        try:
            await bot.send_message(game["chat_id"], f"🎯 نوبت {name} است! حقیقت یا جرأت را انتخاب کنید.")
        except Exception:
            pass
    except Exception as exc:
        logger.warning("TD turn announcement unexpected failure for %s: %s", game.get("chat_id"), exc)
    try:
        await td_send_media(bot, game["chat_id"], "lobby")
    except Exception as exc:
        logger.debug("TD lobby media skipped: %s", exc)


async def td_finish_turn(bot, chat_id, user_id, kind):
    game = TD_GAMES.get(chat_id)
    if not game or not game.get("started"):
        return False, "این بازی دیگر فعال نیست."
    async with TD_STATE_LOCK:
        current = td_current_player(game)
        if not current or int(current["id"]) != int(user_id):
            return False, "الان نوبت تو نیست."
        key = td_task_key(chat_id, user_id)
        task = TD_PRIVATE_TASKS.get(key)
        if not task or int(task.get("chat_id", 0)) != int(chat_id) or task.get("kind") != kind:
            return False, "برای این نوبت هنوز انتخاب معتبر یا task معتبر ثبت نشده."
        if not task.get("verified") or not td_task_is_current(game, task, user_id):
            return False, "ربات هنوز این نوبت را تأیید نکرده است."
        # همه تغییرات حیاتی قبل از شبکه انجام می‌شوند؛ Telegram هرگز نباید state بازی را قفل کند.
        TD_PRIVATE_TASKS.pop(key, None)
        game["active_task"] = None
        name = td_clean_name(current["name"])
        td_add_score(game, user_id, kind, int(task.get("attempts", 1) or 1))
        td_advance(game)

    announcement = (
        f"🗣️ <b>{name}</b> حقیقتِ نوبتش را در خصوصی ربات با موفقیت پاسخ داد. ✅"
        if kind == "truth" else
        f"🔥 <b>{name}</b> چالش نوبتش را در خصوصی ربات با موفقیت انجام داد. ✅"
    )
    try:
        await bot.send_message(chat_id, announcement, parse_mode="HTML")
    except TelegramError as exc:
        logger.warning("TD result announcement failed for %s: %s", chat_id, exc)
    try:
        await td_send_media(bot, chat_id, "success")
    except Exception as exc:
        logger.debug("TD success media failed: %s", exc)
    try:
        await td_announce_turn(bot, game, None)
    except Exception as exc:
        logger.warning("TD next-turn announcement failed for %s: %s", chat_id, exc)
    return True, "نوبت ثبت شد."


def fetch_hafez_from_ganjoor():
    try:
        r = _http_session.get(
            "https://api.ganjoor.net/api/ganjoor/poem/random",
            params={"poetId": 2},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            title = data.get("title", "")
            verses = data.get("verses", [])
            if verses:
                lines = [v.get("text", "") for v in verses[:4] if v.get("text")]
                if lines:
                    text = "\n".join(lines)
                    return f"{text}\n\n📌 از غزلیات حافظ - «{title}»"
    except Exception as e:
        logger.warning(f"Ganjoor fetch failed: {e}")
    return None


async def generate_hafez() -> str:
    # منبع واقعی و آنلاین: گنجور (api.ganjoor.net) - بزرگ‌ترین آرشیو شعر کلاسیک فارسی
    verse = await asyncio.to_thread(fetch_hafez_from_ganjoor)
    source_note = " (🌐 منبع: ganjoor.net)"
    if not verse:
        # اگه سایت در دسترس نبود، کاملاً آفلاین از دیوان حافظِ داخلیِ ربات میاد
        verse = random.choice(HAFEZ_VERSES)
        source_note = " (📴 آفلاین - از دیوان حافظ)"
    return f"📖 {verse}{source_note}"


async def generate_tarot() -> str:
    # ابتدا تلاش می‌کنه یه کارت واقعی از سایت tarotapi.dev (منبع آنلاینِ واقعی
    # و رایگان RWS Tarot) بگیره؛ اگه نشد یا نتونست match کنه، کاملاً آفلاین از
    # دکِ ۷۸ کارتیِ داخلی ربات یه کارت انتخاب می‌کنه - همیشه جواب می‌ده.
    online = await asyncio.to_thread(_fetch_tarot_card_online_blocking)
    source_note = ""
    mapped = None
    if online:
        mapped = map_tarotapi_card_to_persian(online.get("name_en", ""))

    reversed_card = random.random() < 0.3  # حدود ۳۰٪ موارد به‌صورت معکوس

    if mapped:
        card, base_meaning = mapped
        # فقط اسم منبع رو نگه می‌داریم (شفافیت درباره‌ی این‌که کارت واقعاً از
        # کجا اومده)، بدون اینکه متن انگلیسیِ خام سایت رو توی پیام بیاریم.
        source_note = "\n\n🌐 منبع این کارت: tarotapi.dev"
    else:
        card, base_meaning = random.choice(TAROT_DECK_FULL)
        source_note = "\n\n📴 منبع این کارت: دکِ آفلاین داخلی ربات"

    text = f"🃏 کارت: {card}{' (معکوس)' if reversed_card else ''}\n\n{base_meaning}"
    if reversed_card:
        text += TAROT_REVERSED_NOTE
    text += source_note
    text += f"\n\n{random.choice(TAROT_ADVICE_CLOSERS)}"
    return text



# ============================================================
# قیمت دلار و بیت‌کوین
# ============================================================
def fetch_usd_price():
    try:
        r = _http_session.get(
            "https://api.nobitex.ir/market/stats",
            params={"srcCurrency": "usdt", "dstCurrency": "rls"},
            timeout=7,
        )
        if r.status_code == 200:
            data = r.json()
            stats = data.get("stats", {}).get("usdt-rls", {})
            latest = stats.get("latest")
            if latest:
                toman = int(float(latest)) // 10
                if toman > 1000:
                    return toman, "نوبیتکس (نرخ تتر)"
    except Exception as e:
        logger.warning(f"Nobitex USD fetch failed: {e}")

    try:
        r = _http_session.get("https://call1.tgju.org/ajax.json", timeout=7)
        if r.status_code == 200:
            data = r.json()
            price_raw = data.get("current", {}).get("price_dollar_rl", {}).get("p")
            if price_raw:
                clean = str(price_raw).replace(",", "").strip()
                rial = int(clean)
                toman = rial // 10
                if toman > 1000:
                    return toman, "TGJU"
    except Exception as e:
        logger.warning(f"TGJU USD fetch failed: {e}")

    return None, None


def fetch_btc_price():
    headers = {"Accept": "application/json"}

    # منبع ۱: نوبیتکس - صرافی ایرانی، معمولاً از داخل ایران هم بدون مشکل باز می‌شه
    try:
        r = _http_session.get(
            "https://api.nobitex.ir/market/stats",
            params={"srcCurrency": "btc", "dstCurrency": "usdt"},
            headers=headers, timeout=7,
        )
        if r.status_code == 200:
            data = r.json()
            stats = (data or {}).get("stats", {}).get("btc-usdt", {})
            latest = stats.get("latest")
            if latest:
                price = float(latest)
                if price > 1000:  # عدد منطقی، جلوگیری از داده‌ی خراب
                    return price, "نوبیتکس"
    except Exception as e:
        logger.warning(f"Nobitex BTC fetch failed: {e}")

    # منبع ۲: بایننس - بدون نیاز به کلید API، معمولاً خیلی پایداره
    try:
        r = _http_session.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            headers=headers, timeout=7,
        )
        if r.status_code == 200:
            data = r.json()
            price_raw = (data or {}).get("price")
            if price_raw:
                price = float(price_raw)
                if price > 1000:
                    return price, "Binance"
    except Exception as e:
        logger.warning(f"Binance BTC fetch failed: {e}")

    # منبع ۳: CoinGecko
    try:
        r = _http_session.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            headers=headers, timeout=7,
        )
        if r.status_code == 200:
            data = r.json()
            price_raw = (data or {}).get("bitcoin", {}).get("usd")
            if price_raw:
                price = float(price_raw)
                if price > 1000:
                    return price, "CoinGecko"
    except Exception as e:
        logger.warning(f"CoinGecko BTC fetch failed: {e}")

    # منبع ۴: CoinCap
    try:
        r = _http_session.get("https://api.coincap.io/v2/assets/bitcoin", headers=headers, timeout=7)
        if r.status_code == 200:
            data = r.json()
            price_raw = (data or {}).get("data", {}).get("priceUsd")
            if price_raw:
                price = float(price_raw)
                if price > 1000:
                    return price, "CoinCap"
    except Exception as e:
        logger.warning(f"CoinCap BTC fetch failed: {e}")

    return None, None


async def fetch_prices():
    now = datetime.now()
    if PRICE_CACHE["data"] and PRICE_CACHE["time"] and now - PRICE_CACHE["time"] < timedelta(seconds=CACHE_SECONDS):
        return PRICE_CACHE["data"]

    (usd_toman, usd_source), (btc_usd, btc_source) = await asyncio.gather(
        asyncio.to_thread(fetch_usd_price),
        asyncio.to_thread(fetch_btc_price),
    )

    result = {
        "usd_toman": usd_toman, "usd_source": usd_source,
        "btc_usd": btc_usd, "btc_source": btc_source,
        "btc_toman": int(btc_usd * usd_toman) if (btc_usd and usd_toman) else None,
    }
    PRICE_CACHE["data"] = result
    PRICE_CACHE["time"] = now
    return result


# ============================================================
# منوی شیک (Inline Keyboard)
# ============================================================
def gaming_center_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐺 گرگینه", callback_data="game_werewolf"), InlineKeyboardButton("🃏 اونو", callback_data="game_uno")],
        [InlineKeyboardButton("🕵️ جرأت یا حقیقت", callback_data="game_td")],
        [InlineKeyboardButton("⬅️ منوی اصلی", callback_data="back_main")],
    ])


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔮 فال روزانه", callback_data="fal"),
         InlineKeyboardButton("🃏 تاروت", callback_data="tarot")],
        [InlineKeyboardButton("📖 فال حافظ", callback_data="hafez"),
         InlineKeyboardButton("🎯 شانس امروز", callback_data="shans")],
        [InlineKeyboardButton("💵 قیمت دلار", callback_data="dollar"),
         InlineKeyboardButton("₿ قیمت بیت‌کوین", callback_data="bitcoin")],
        [InlineKeyboardButton("😂 جوک", callback_data="joke"),
         InlineKeyboardButton("💬 ضرب‌المثل", callback_data="quote")],
        [InlineKeyboardButton("🎱 توپ جادویی", callback_data="eightball"),
         InlineKeyboardButton("🎡 چرخ شانس", callback_data="wheel")],
        [InlineKeyboardButton("🎮 Gaming Center", callback_data="gaming_center")],
        [InlineKeyboardButton("✨ Gemini AI", callback_data="gemini_panel")],
        [InlineKeyboardButton("🕵️ جرأت یا حقیقت", callback_data="td_start"),
         InlineKeyboardButton("🐺 بازی گرگینه", callback_data="start_werewolf")],
        [InlineKeyboardButton("🛡️ پنل مدیریت گروه", callback_data="adminpanel")],
        [InlineKeyboardButton("📜 قوانین گروه", callback_data="rules"),
         InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_panel_keyboard(chat_id):
    reminder_on = bool(reminder_enabled.get(str(chat_id), False))
    reminder_label = "⏰ یادآور: 🟢 روشنه (خاموش کن)" if reminder_on else "⏰ یادآور: 🔴 خاموشه (روشن کن)"
    keyboard = [
        [InlineKeyboardButton("➕ افزودن الفاظ نامناسب", callback_data="badword_add_prompt")],
        [InlineKeyboardButton("📋 تعداد الفاظ فیلترشده", callback_data="badword_list")],
        [InlineKeyboardButton(reminder_label, callback_data="toggle_reminder")],
        [InlineKeyboardButton("⬅️ برگشت به منو", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ثبت اینکه کاربر Private ربات را باز کرده و /start زده است.
    # ارسال واقعی پیام خصوصی همچنان تست نهایی است؛ چون این وضعیت ممکن است بعد از ری‌استارت ربات پاک شود.
    if update.effective_chat and update.effective_chat.type == "private" and update.effective_user:
        TD_PRIVATE_READY_USERS.add(update.effective_user.id)

        # لینک خصوصی جرأت/حقیقت یک توکن اختصاصی دارد؛ فقط همان بازیکن می‌تواند آن را فعال کند.
        args = context.args or []
        if args and str(args[0]).startswith("tdr_"):
            token = str(args[0])[:80]
            task_key, task = td_find_task_by_token(update.effective_user.id, token)
            if task:
                game = TD_GAMES.get(task.get("chat_id"))
                current = td_current_player(game) if game else None
                if (game and game.get("started") and current and
                        current.get("id") == update.effective_user.id and
                        task.get("chat_id") == game.get("chat_id") and
                        task.get("turn_index") == int(game.get("turn_index", -1)) and
                        task.get("round") == int(game.get("round", -1))):
                    label = "حقیقت" if task.get("kind") == "truth" else "جرأت"
                    await update.message.reply_text(
                        f"🔐 <b>نوبت {td_clean_name(current.get('name', 'بازیکن'))}</b>\n\n"
                        f"🎭 انتخاب تو: <b>{label}</b>\n"
                        "سؤال/چالش در گروه نمایش داده شده است.\n\n"
                        "📩 فقط پاسخ همان سؤال/چالش را همین‌جا بفرست.\n"
                        "🧹 پیام پاسخ بعد از بررسی برای حذف به Telegram سپرده می‌شود.\n"
                        "🔒 متن پاسخ در گروه منتشر نمی‌شود و برای استفاده بعدی ذخیره نمی‌شود.\n"
                        "🛡️ این نوبت فقط به حساب همین بازیکن و همین دور متصل است.",
                        parse_mode="HTML",
                    )
                    return
            # توکن برای کاربر دیگری یا نوبت قدیمی قابل استفاده نیست.
            await update.message.reply_text(
                "⛔ این لینک خصوصی برای این حساب یا این نوبت معتبر نیست.\n"
                "اگر نوبت فعلی توست، فقط از دکمه‌ی پاسخ همان پیام گروه وارد شو."
            )
            return

    text = (
        "🤖 به دستیار هوشمند خوش اومدی! ✨\n\n"
        "من فقط یه ربات فال نیستم — دستیار کامل این گروهم: فال و تاروت با منبع واقعی آنلاین، "
        "بازی گروهی، مدیریت و نظم‌دهی، یادآور خودکار و کلی امکانات دیگه.\n"
        "از دکمه‌های زیر استفاده کن یا از منوی دستورات (کنار جعبه پیام).\n"
        "این ربات همچنین به‌صورت خودکار پیام‌های نامناسب رو تشخیص می‌ده."
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


_CALLBACK_ACKED = {}

async def _cb_answer(query, *args, **kwargs):
    """Answer a Telegram callback at most once per callback id.
    This also gives a safe no-op for stale/expired callback queries.
    """
    qid = getattr(query, "id", None) or id(query)
    if qid in _CALLBACK_ACKED:
        return False
    try:
        await query.answer(*args, **kwargs)
    except TelegramError as exc:
        # A callback can expire between the button click and processing.
        logger.debug("Callback answer skipped: %s", exc)
        _CALLBACK_ACKED[qid] = time.time()
        return False
    _CALLBACK_ACKED[qid] = time.time()
    if len(_CALLBACK_ACKED) > 5000:
        cutoff = time.time() - 600
        for k, ts in list(_CALLBACK_ACKED.items())[:1000]:
            if ts < cutoff:
                _CALLBACK_ACKED.pop(k, None)
    return True

async def _ensure_callback_ack(query):
    return await _cb_answer(query)

def _callback_ack_guard(handler):
    async def _wrapped(update, context):
        query = getattr(update, "callback_query", None)
        try:
            return await handler(update, context)
        finally:
            if query is not None:
                await _ensure_callback_ack(query)
    _wrapped.__name__ = getattr(handler, "__name__", "callback_handler")
    _wrapped.__doc__ = getattr(handler, "__doc__", None)
    return _wrapped

@_callback_ack_guard
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    # مهم: این handler نباید callback را از قبل answer کند.
    # هر مسیر باید خودش دقیقاً یک query.answer() انجام دهد؛ answer دوباره
    # می‌تواند باعث BadRequest شود و در نتیجه دکمه ظاهراً هیچ کاری نکند.
    chat = query.message.chat

    if data.startswith("ww_"):
        # این‌ها توسط ww_button_handler جدا مدیریت می‌شن؛ اینجا کاری نکن تا تداخل نشه.
        return

    if data == "smart_assistant":
        if not owner_feature_enabled("assistant"):
            await _cb_answer(query, "🧠 Smart Assistant فعلاً غیرفعال است.", show_alert=True)
            return
        await query.message.reply_text(
            "🧠 Smart Assistant\n\n"
            "من پیام‌های مستقیم به ربات و ریپلای‌های روی پیام‌های خودم رو بررسی می‌کنم و سعی می‌کنم منظور پیام رو از روی زمینه‌ی مکالمه بفهمم.\n\n"
            "مثلاً می‌تونی بگی: «درباره بازی‌ها بگو»، بعد «بیشتر توضیح بده» یا «حالا برگردیم به تاروت».\n\n"
            "برای امکانات گروه هم می‌تونی بپرسی: «مالک گروه کیه؟»، «ادمین‌ها کیا هستن؟»، «چند نفر عضو داریم؟»",
            reply_markup=main_menu_keyboard(),
        )
        return
    if data == "gemini_panel":
        await _cb_answer(query)
        panel = await query.message.reply_text(
            gemini_control_text(chat.id),
            parse_mode="HTML",
            reply_markup=gemini_control_keyboard(chat.id),
        )
        GEMINI_PANEL_MESSAGES[str(chat.id)] = panel.message_id
        return
    if data == "gemini_on":
        if chat.type != "private" and not await is_admin(update, context):
            await _cb_answer(query, "⛔ فقط ادمین گروه می‌تواند Gemini را روشن یا خاموش کند.", show_alert=True)
            return
        if not GEMINI_API_KEY:
            await _cb_answer(query, "🔑 کلید Gemini روی سرور تنظیم نشده است.", show_alert=True)
            return
        set_gemini_enabled(chat.id, True)
        GEMINI_PANEL_MESSAGES[str(chat.id)] = query.message.message_id
        await _cb_answer(query, "✨ Gemini روشن شد.")
        await query.message.edit_text(
            gemini_control_text(chat.id),
            parse_mode="HTML",
            reply_markup=gemini_control_keyboard(chat.id),
        )
        return
    if data == "gemini_off":
        if chat.type != "private" and not await is_admin(update, context):
            await _cb_answer(query, "⛔ فقط ادمین گروه می‌تواند Gemini را روشن یا خاموش کند.", show_alert=True)
            return
        gemini_disable(chat.id)
        GEMINI_PANEL_MESSAGES.pop(str(chat.id), None)
        await _cb_answer(query, "🔴 Gemini خاموش شد.")
        await query.message.edit_text(
            gemini_control_text(chat.id),
            parse_mode="HTML",
            reply_markup=gemini_control_keyboard(chat.id),
        )
        return
    if data == "gaming_center":
        if not owner_feature_enabled("gaming"):
            await _cb_answer(query, "🎮 بخش بازی‌ها فعلاً غیرفعال است.", show_alert=True)
            return
        await query.message.reply_text("🎮 Gaming Center\n\nبازی گروهی موردنظرت رو انتخاب کن:", reply_markup=gaming_center_keyboard())
        return
    if data == "game_werewolf":
        if not owner_feature_enabled("gaming"):
            await _cb_answer(query, "🎮 بازی‌ها فعلاً غیرفعال‌اند.", show_alert=True)
            return
        if chat.type == "private":
            await query.message.reply_text("🐺 گرگینه فقط داخل گروه اجرا می‌شه.")
        else:
            await ww_start_lobby(chat.id, query.from_user.id, context)
        return
    if data == "game_uno":
        if not owner_feature_enabled("gaming"):
            await _cb_answer(query, "🎮 بازی‌ها فعلاً غیرفعال‌اند.", show_alert=True)
            return
        if chat.type == "private":
            await query.message.reply_text("🃏 اونو یک بازی گروهیه؛ ربات رو به گروه اضافه کن و /uno رو بزن.")
        else:
            await uno_start_cmd(update, context)
        return
    if data == "game_td":
        if not owner_feature_enabled("truth_or_dare"):
            await _cb_answer(query, "🕵️ جرأت یا حقیقت فعلاً غیرفعال است.", show_alert=True)
            return
        if chat.type == "private":
            await query.message.reply_text("🕵️ جرأت یا حقیقت برای بازی گروهی طراحی شده؛ ربات را داخل گروه باز کن و /td را بزن.")
            return
        chat_id = chat.id
        busy, game_name = group_game_is_busy(chat_id, "truth_or_dare")
        if busy:
            await _cb_answer(query, f"الان بازی {game_name} در این گروه در جریانه.", show_alert=True)
            return
        game = TD_GAMES.get(chat_id)
        if game and game.get("started"):
            await query.message.reply_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
            return
        if not game:
            game = td_new_game(chat_id, query.from_user.id)
            TD_GAMES[chat_id] = game
        game["players"].setdefault(query.from_user.id, {"id": query.from_user.id, "name": td_display_name(query.from_user)})
        await query.message.reply_text(
            "🕵️ <b>اتاق جرأت یا حقیقت</b>\n\n"
            "هرکس وارد شود، در نوبت خودش انتخاب را در خصوصی ربات انجام می‌دهد.\n"
            "حداقل ۲ نفر برای شروع لازم است.",
            parse_mode="HTML", reply_markup=td_keyboard(game)
        )
        return
    if data == "tdg_count":
        if chat.type == "private":
            await _cb_answer(query, "این گزینه فقط داخل گروه است.", show_alert=True); return
        game = TD_GAMES.get(chat.id)
        if not game or game.get("started"):
            await _cb_answer(query, "این بازی در حال حاضر قابل تنظیم نیست.", show_alert=True); return
        if query.from_user.id != game.get("owner_id") and not await is_admin(update, context):
            await _cb_answer(query, "فقط سازنده بازی یا ادمین می‌تواند تعداد بازیکنان را تعیین کند.", show_alert=True); return
        rows = []
        for start in range(2, 20, 5):
            row = []
            for n in range(start, min(start + 5, TD_MAX_PLAYERS + 1)):
                row.append(InlineKeyboardButton(str(n), callback_data=f"tdg_setcount:{n}"))
            rows.append(row)
        rows.append([InlineKeyboardButton("❌ لغو انتخاب", callback_data="tdg_setcount:0")])
        await _cb_answer(query, )
        await query.message.reply_text("👥 <b>تعداد بازیکنان این دور را انتخاب کن:</b>\n\nبا رسیدن به این تعداد، همان افراد برای نوبت‌ها ثبت می‌شوند و ترتیب نوبت‌ها ثابت می‌ماند.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
        return
    if data.startswith("tdg_setcount:"):
        if chat.type == "private":
            await _cb_answer(query, "این گزینه فقط داخل گروه است.", show_alert=True); return
        game = TD_GAMES.get(chat.id)
        if not game or game.get("started"):
            await _cb_answer(query, "این بازی دیگر در مرحله تنظیم نیست.", show_alert=True); return
        if query.from_user.id != game.get("owner_id") and not await is_admin(update, context):
            await _cb_answer(query, "فقط سازنده بازی یا ادمین می‌تواند تعداد را تعیین کند.", show_alert=True); return
        try:
            target = int(data.split(":", 1)[1])
        except Exception:
            target = 0
        if target == 0:
            game["target_players"] = None
            await _cb_answer(query, "انتخاب تعداد لغو شد.")
        elif not (TD_MIN_PLAYERS <= target <= TD_MAX_PLAYERS):
            await _cb_answer(query, "تعداد باید بین ۲ تا ۲۰ نفر باشد.", show_alert=True); return
        else:
            if len(game["players"]) > target:
                await _cb_answer(query, f"الان {len(game['players'])} نفر داخل بازی‌اند؛ ابتدا تعداد بازیکنان را حداقل {len(game['players'])} انتخاب کن.", show_alert=True); return
            game["target_players"] = target
            await _cb_answer(query, f"ظرفیت روی {target} نفر تنظیم شد. 🎭")
        await query.message.reply_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        return
    if data.startswith("tdg_private:"):
        try:
            _, target_chat_raw, target_user_raw, turn_raw, round_raw = data.split(":", 4)
            target_chat = int(target_chat_raw); target_user = int(target_user_raw)
            button_turn = int(turn_raw); button_round = int(round_raw)
        except Exception:
            await _cb_answer(query, "درخواست نامعتبر است.", show_alert=True); return
        game = TD_GAMES.get(target_chat)
        current = td_current_player(game) if game else None
        if (not game or not game.get("started") or not current or
            query.from_user.id != target_user or current.get("id") != target_user or
            button_turn != int(game.get("turn_index", -1)) or button_round != int(game.get("round", -1))):
            await _cb_answer(query, "این دکمه دیگر برای نوبت فعلی معتبر نیست.", show_alert=True); return
        await _cb_answer(query, "راهنمای Private برایت ارسال می‌شود…")
        async def _private_notice():
            try:
                await td_send_private_response_notice(context.bot, target_user, target_chat, current.get("name", "بازیکن"))
            except Exception as exc:
                logger.debug("TD private notice failed: %s", exc)
        asyncio.create_task(_private_notice())
        return

    if data.startswith("tdg_retry:"):
        try:
            _, chat_raw, user_raw, turn_raw, round_raw = data.split(":", 4)
            target_chat = int(chat_raw)
            target_user = int(user_raw)
            button_turn = int(turn_raw)
            button_round = int(round_raw)
        except Exception:
            await _cb_answer(query, "درخواست نامعتبر است.", show_alert=True); return
        game = TD_GAMES.get(target_chat)
        current = td_current_player(game) if game else None
        if (not game or not game.get("started") or not current or
                current.get("id") != query.from_user.id or target_user != query.from_user.id or
                button_turn != int(game.get("turn_index", -1)) or button_round != int(game.get("round", -1))):
            await _cb_answer(query, "این دکمه دیگر برای نوبت فعلی معتبر نیست.", show_alert=True); return
        await _cb_answer(query, "Private را دوباره بررسی می‌کنم…")
        ok = await td_send_private_response_notice(context.bot, current["id"], target_chat, current["name"])
        if not ok:
            await query.message.reply_text("⚠️ هنوز Private ربات در دسترس نیست؛ ابتدا /start را در Private بزن و دوباره تلاش کن.")
        else:
            await query.message.reply_text(f"📩 {td_clean_name(current['name'])}، راهنمای پاسخ دوباره به Private تو ارسال شد.")
        return
    if data == "tdg_join":
        if chat.type == "private":
            await _cb_answer(query, "بازی گروهی است.", show_alert=True); return
        game = TD_GAMES.setdefault(chat.id, td_new_game(chat.id, query.from_user.id))
        if game.get("started"):
            await _cb_answer(query, "بازی شروع شده؛ برای ورود باید صبر کنی.", show_alert=True); return
        if len(game["players"]) >= TD_MAX_PLAYERS and query.from_user.id not in game["players"]:
            await _cb_answer(query, "ظرفیت بازی پر شده.", show_alert=True); return
        game["players"][query.from_user.id] = {"id": query.from_user.id, "name": td_display_name(query.from_user)}
        await _cb_answer(query, "وارد بازی شدی! 🎭")
        await query.message.edit_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        target = game.get("target_players")
        if target and len(game["players"]) == target:
            game["started"] = True
            game["turn_order"] = list(game["players"].keys())
            random.shuffle(game["turn_order"])
            game["turn_index"] = 0
            game["round"] = 1
            await query.message.reply_text(f"🎉 ظرفیت {target} نفر کامل شد؛ بازی خودکار شروع شد!\n\n" + td_status_text(game), parse_mode="HTML")
            await td_announce_turn(context.bot, game, context)
        return
    if data == "tdg_leave":
        game = TD_GAMES.get(chat.id)
        if not game:
            await _cb_answer(query, "بازی فعالی نیست.", show_alert=True); return
        uid = query.from_user.id
        if uid not in game.get("players", {}):
            await _cb_answer(query, "تو عضو این بازی نیستی.", show_alert=True); return
        was_started = bool(game.get("started"))
        current_id = None
        if was_started and game.get("turn_order"):
            idx = int(game.get("turn_index", 0)) % len(game["turn_order"])
            current_id = game["turn_order"][idx]
        was_current = current_id == uid
        TD_PRIVATE_TASKS.pop(td_task_key(chat.id, uid), None)
        game["players"].pop(uid, None)
        old_idx = None
        if uid in game.get("turn_order", []):
            old_idx = game["turn_order"].index(uid)
            game["turn_order"].remove(uid)
        if not game["players"]:
            TD_GAMES.pop(chat.id, None)
            await _cb_answer(query, "از بازی خارج شدی.")
            try: await query.message.edit_text("🕵️ اتاق بازی بسته شد؛ بازیکنی باقی نمانده.")
            except TelegramError: pass
            return
        if was_started and len(game["players"]) < TD_MIN_PLAYERS:
            TD_GAMES.pop(chat.id, None)
            await _cb_answer(query, "بازی متوقف شد؛ بازیکنان کافی باقی نماندند.", show_alert=True)
            await query.message.reply_text("🛑 جرأت یا حقیقت متوقف شد؛ حداقل ۲ بازیکن لازم است.")
            return
        if was_started and game.get("turn_order"):
            idx = int(game.get("turn_index", 0))
            if old_idx is not None and old_idx < idx: idx -= 1
            if idx >= len(game["turn_order"]): idx = 0
            game["turn_index"] = idx
            if was_current: game["active_task"] = None
        if int(game.get("owner_id", 0)) == uid:
            game["owner_id"] = next(iter(game["players"].keys()))
        await _cb_answer(query, "از بازی خارج شدی. 👋")
        try: await query.message.edit_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        except TelegramError: pass
        if was_started and was_current and game.get("started"):
            await td_announce_turn(context.bot, game, context)
        return
    if data == "tdg_start":
        game = TD_GAMES.get(chat.id)
        if not game:
            await _cb_answer(query, "اول /td را بزن.", show_alert=True); return
        if game.get("started"):
            await _cb_answer(query, "بازی قبلاً شروع شده.", show_alert=True); return
        if not game.get("target_players"):
            await _cb_answer(query, "اول تعداد بازیکنان این دور را انتخاب کن.", show_alert=True); return
        if len(game["players"]) != game.get("target_players"):
            await _cb_answer(query, f"برای شروع باید دقیقاً {game['target_players']} نفر وارد بازی باشند؛ الان {len(game['players'])} نفر هستند.", show_alert=True); return
        if len(game["players"]) < TD_MIN_PLAYERS:
            await _cb_answer(query, "حداقل ۲ بازیکن لازم است.", show_alert=True); return
        game["started"] = True
        game["turn_order"] = list(game["players"].keys())
        random.shuffle(game["turn_order"])
        game["turn_index"] = 0
        game["round"] = 1
        await _cb_answer(query, "بازی شروع شد! 🎭")
        await query.message.edit_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        await td_announce_turn(context.bot, game, context)
        return
    if data == "tdg_status":
        game = TD_GAMES.get(chat.id)
        if not game:
            await _cb_answer(query, "بازی فعالی نیست.", show_alert=True); return
        await _cb_answer(query, )
        await query.message.reply_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        return
    if data == "tdg_score":
        game = TD_GAMES.get(chat.id)
        if not game or not game.get("started"):
            await _cb_answer(query, "بازی فعالی نیست.", show_alert=True); return
        await _cb_answer(query, "امتیازهای فعلی نمایش داده شد.")
        await query.message.reply_text(td_scoreboard_text(game, final=False), parse_mode="HTML")
        return
    if data == "tdg_end":
        game = TD_GAMES.get(chat.id)
        if not game:
            await _cb_answer(query, "بازی فعالی نیست.", show_alert=True); return
        if query.from_user.id != game.get("owner_id") and not await is_admin(update, context):
            await _cb_answer(query, "فقط سازنده بازی یا ادمین می‌تواند بازی را تمام کند.", show_alert=True); return
        for uid in list(game.get("players", {})):
            TD_PRIVATE_TASKS.pop(td_task_key(chat_id, uid), None)
        await _cb_answer(query, "بازی تمام شد.")
        await query.message.reply_text("🛑 اتاق جرأت یا حقیقت به پایان رسید؛ امتیازها محاسبه می‌شوند. 🏆")
        await td_finalize_game(context.bot, game, reason="manual")
        TD_GAMES.pop(chat.id, None)
        return
    if data.startswith("tdg_choice_"):
        try:
            prefix, chat_id_raw, user_id_raw, turn_raw, round_raw = data.split(":", 4)
            target_chat = int(chat_id_raw)
            target_user = int(user_id_raw)
            button_turn = int(turn_raw)
            button_round = int(round_raw)
        except (ValueError, TypeError):
            await _cb_answer(query, "درخواست نامعتبر است.", show_alert=True); return
        game = TD_GAMES.get(target_chat)
        current = td_current_player(game) if game else None
        if not game or not game.get("started") or not current:
            await _cb_answer(query, "این بازی دیگر فعال نیست.", show_alert=True); return
        if chat.type == "private" or chat.id != target_chat:
            await _cb_answer(query, "انتخاب حقیقت/جرأت فقط از داخل همان گروه انجام می‌شود.", show_alert=True); return
        if query.from_user.id != target_user or query.from_user.id != current.get("id"):
            await _cb_answer(query, "این دکمه فقط برای بازیکنِ نوبت فعلی است.", show_alert=True); return
        if button_turn != int(game.get("turn_index", -1)) or button_round != int(game.get("round", -1)):
            await _cb_answer(query, "این دکمه مربوط به یک نوبت قدیمی است.", show_alert=True); return
        if game.get("active_task") is not None or td_find_private_task(query.from_user.id)[1]:
            await _cb_answer(query, "برای این نوبت قبلاً انتخاب ثبت شده؛ دوباره انتخاب نکن.", show_alert=True); return
        # یک کاربر همزمان فقط یک نوبت خصوصی فعال دارد؛ این جلوی قاطی‌شدن دو گروه را می‌گیرد.
        if td_has_other_active_task(query.from_user.id, target_chat):
            await _cb_answer(query, "تو در یک گروه دیگر هنوز یک نوبت خصوصی فعال داری؛ اول همان نوبت را تمام کن.", show_alert=True); return

        kind = "truth" if prefix == "tdg_choice_truth" else "dare"
        task = td_pick(game, kind)
        task_key = td_task_key(target_chat, query.from_user.id)
        async with TD_STATE_LOCK:
            # دوباره داخل lock بررسی می‌کنیم تا دو کلیک همزمان نتوانند دو task بسازند.
            if game.get("active_task") is not None or td_find_private_task(query.from_user.id)[1]:
                await _cb_answer(query, "این نوبت قبلاً انتخاب شده است.", show_alert=True); return
            TD_PRIVATE_TASKS[task_key] = {
            "chat_id": target_chat,
            "user_id": query.from_user.id,
            "kind": kind,
            "task": task,
            "created": datetime.now().timestamp(),
            "prompt_message_id": query.message.message_id,
            "answer_message_id": None,
            "verified": False,
            "attempts": 0,
            "feedback_message_id": None,
            "turn_index": int(game.get("turn_index", 0)),
            "round": int(game.get("round", 1)),
            "task_token": td_make_task_token(),
            "state_version": secrets.token_hex(8),
            "processing": False,
        }
        game["active_task"] = query.from_user.id
        label = "حقیقت" if kind == "truth" else "جرأت"
        await _cb_answer(query, f"{label} انتخاب شد. سؤال/چالش در گروه آمد.", show_alert=False)

        # سؤال/چالش عمداً در گروه منتشر می‌شود؛ پاسخ هرگز به گروه فرستاده نمی‌شود.
        # DM و GIF غیرحیاتی در پس‌زمینه انجام می‌شوند تا دکمه سریع پاسخ بگیرد.
        # لینک Private از username کش‌شده ساخته می‌شود؛ بنابراین کلیک منتظر get_me نمی‌ماند.
        private_url = f"https://t.me/{BOT_USERNAME}?start={task['task_token']}" if BOT_USERNAME else None
        buttons = []
        if private_url:
            buttons.append([InlineKeyboardButton("📩 ارسال پاسخ در Private ربات", url=private_url)])
        else:
            buttons.append([InlineKeyboardButton("📩 ارسال پاسخ در Private ربات", callback_data=f"tdg_private:{target_chat}:{current['id']}:{game.get('turn_index', 0)}:{game.get('round', 1)}")])
        buttons.append([InlineKeyboardButton("🔄 بررسی Private", callback_data=f"tdg_retry:{target_chat}:{current['id']}:{game.get('turn_index', 0)}:{game.get('round', 1)}")])
        sent_prompt = await context.bot.send_message(
            target_chat,
            f"🎭 <b>{td_clean_name(current.get('name', 'بازیکن'))}</b> {label} را انتخاب کرد.\n\n"
            f"{'🗣️ <b>حقیقت:</b>' if kind == 'truth' else '🔥 <b>جرأت:</b>'}\n\n"
            f"<blockquote>{html.escape(str(task))}</blockquote>\n\n"
            "📩 <b>پاسخ را فقط در Private ربات بفرست.</b>\n"
            "👤 <b>این دکمه فقط برای بازیکن نوبت فعلی معتبر است.</b>\n"
            "🧹 پیام پاسخ بعد از بررسی پاک می‌شود و متن پاسخ در گروه نمایش داده نمی‌شود.\n"
            "🔒 پاسخ فقط به همین بازیکن و همین نوبت متصل است.",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons),
        )
        task["prompt_group_message_id"] = sent_prompt.message_id if sent_prompt else None
        async def _td_background_extras():
            try: await td_send_private_response_notice(context.bot, query.from_user.id, target_chat, current.get("name", "بازیکن"))
            except Exception as exc: logger.debug("TD private notice skipped: %s", exc)
            try: await td_send_media(context.bot, target_chat, "truth" if kind == "truth" else "dare")
            except Exception as exc: logger.debug("TD media skipped: %s", exc)
        asyncio.create_task(_td_background_extras())
        return
    if data.startswith("tdg_done_"):
        try:
            prefix, chat_id_raw = data.split(":", 1)
            target_chat = int(chat_id_raw)
        except (ValueError, TypeError):
            await _cb_answer(query, "درخواست نامعتبر است.", show_alert=True); return
        kind = "truth" if prefix == "tdg_done_truth" else "dare"
        ok, msg = await td_finish_turn(context.bot, target_chat, query.from_user.id, kind)
        await _cb_answer(query, msg, show_alert=not ok)
        return

    if data == "td_truth":
        await query.message.reply_text(f"🕵️ حقیقت:\n\n{random.choice(TRUTH_QUESTIONS)}")
        return
    if data == "td_dare":
        await query.message.reply_text(f"🕵️ جرأت:\n\n{random.choice(DARE_ACTIONS)}")
        return
    if data == "td_start":
        if not owner_feature_enabled("truth_or_dare"):
            await _cb_answer(query, "🕵️ جرأت یا حقیقت فعلاً غیرفعال است.", show_alert=True)
            return
        if chat.type == "private":
            await query.message.reply_text("🕵️ این بازی را باید داخل گروه شروع کنی.")
            return
        chat_id = chat.id
        game = TD_GAMES.get(chat_id)
        if not game:
            game = td_new_game(chat_id, query.from_user.id)
            TD_GAMES[chat_id] = game
        game["players"].setdefault(query.from_user.id, {"id": query.from_user.id, "name": td_display_name(query.from_user)})
        await query.message.reply_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        return

    if data == "start_werewolf":
        if not owner_feature_enabled("gaming"):
            await _cb_answer(query, "🎮 بازی‌ها فعلاً غیرفعال‌اند.", show_alert=True)
            return
        if chat.type == "private":
            await query.message.reply_text("🐺 این بازی فقط توی گروه قابل اجراست.")
        else:
            await ww_start_lobby(chat.id, query.from_user.id, context)
        return

    # -------------------- پنل مدیریت گروه --------------------
    if data == "adminpanel":
        if chat.type == "private":
            await query.message.reply_text("🛡️ پنل مدیریت فقط توی گروه معنی داره.")
            return
        if not await is_admin(update, context):
            await query.message.reply_text("⛔ این پنل فقط برای ادمین‌های گروهه.")
            return
        await query.message.reply_text(
            "🛡️ پنل مدیریت گروه:\n\nاز اینجا می‌تونی الفاظ نامناسب رو مدیریت کنی یا یادآور خودکار رو روشن/خاموش کنی.",
            reply_markup=admin_panel_keyboard(chat.id),
        )
        return

    if data == "back_main":
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    if data == "badword_add_prompt":
        if chat.type == "private":
            await query.message.reply_text("⛔ این گزینه فقط توی گروه کار می‌کنه.")
            return
        if not await is_admin(update, context):
            await query.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن کلمه اضافه کنن.")
            return
        pending_badword_add[f"{chat.id}:{query.from_user.id}"] = chat.id
        await query.message.reply_text(
            "✏️ خب، حالا همون کلمه‌ی نامناسبی که می‌خوای فیلتر بشه رو توی همین گروه بفرست.\n"
            "(این پیام فقط از خودِ تو در همین گروه، به‌عنوان کلمه‌ی جدید ثبت می‌شه)"
        )
        return

    if data == "badword_list":
        if not await is_admin(update, context):
            await query.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن ببینن.")
            return
        default_count = len(BAD_WORDS_FA) + len(BAD_WORDS_EN)
        custom_count = len(get_custom_words_for_chat(chat.id))
        await query.message.reply_text(
            f"📋 کلمات فیلترشده‌ی پیش‌فرض: {default_count}\n"
            f"📋 کلمات سفارشیِ همین گروه: {custom_count}",
            reply_markup=admin_panel_keyboard(chat.id),
        )
        return

    if data == "toggle_reminder":
        if chat.type == "private":
            await query.message.reply_text("⛔ این گزینه فقط توی گروه کار می‌کنه.")
            return
        if not await is_admin(update, context):
            await query.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن این کارو بکنن.")
            return
        key = str(chat.id)
        current = bool(reminder_enabled.get(key, False))
        reminder_enabled[key] = not current
        async with _file_write_lock:
            save_json_safe(REMINDER_FILE, reminder_enabled)
        status_text = "🟢 روشن شد! از این به بعد ساعت‌های زوج و نیم (مثلاً ۸:۳۰) پیام «پاچیدن چاه» و سرِ ساعت‌های فرد (مثلاً ۹:۰۰) پیام «شام ننه‌جون» فرستاده می‌شه." \
            if not current else "🔴 خاموش شد."
        await query.message.reply_text(f"⏰ یادآور خودکار: {status_text}", reply_markup=admin_panel_keyboard(chat.id))
        return

    user_name = query.from_user.first_name or "دوست عزیز"

    try:
        if data == "fal":
            text = f"🔮 فال امروز {user_name}:\n\n{await generate_fal(user_name)}"
        elif data == "tarot":
            text = await generate_tarot()
        elif data == "hafez":
            text = await generate_hafez()
        elif data == "shans":
            text = f"🎯 شانس امروزت: {random.randint(1, 100)}٪"
        elif data == "eightball":
            text = f"🎱 {random.choice(EIGHTBALL_ANSWERS)}"
        elif data == "wheel":
            text = f"🎡 نتیجه‌ی چرخش:\n\n{spin_wheel()}"
        elif data == "dollar":
            p = await fetch_prices()
            text = (f"💵 قیمت دلار: {p['usd_toman']:,} تومان\n(منبع: {p['usd_source']})"
                    if p["usd_toman"] else "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن، چند لحظه دیگه دوباره امتحان کن.")
        elif data == "bitcoin":
            p = await fetch_prices()
            if p["btc_usd"]:
                text = f"₿ قیمت بیت‌کوین: ${p['btc_usd']:,}\n(منبع: {p['btc_source']})"
                if p["btc_toman"]:
                    text += f"\nمعادل: {p['btc_toman']:,} تومان"
            else:
                text = "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن، چند لحظه دیگه دوباره امتحان کن."
        elif data == "joke":
            text = f"😂 {random.choice(JOKES_FALLBACK)}"
        elif data == "quote":
            text = f"💬 {random.choice(PROVERBS_FA)}"
        elif data == "rules":
            text = GROUP_RULES_TEXT
        elif data == "help":
            text = (
                "ℹ️ راهنمای دستورات:\n\n"
                "🎉 سرگرمی: /fal /tarot /hafez /shans /eightball /wheel /td /joke /quote /compliment /roast /love\n"
                "🐺 بازی گروهی: /gorgineh (شروع لابی گرگینه) /startgame /endgame /players\n"
                "💰 قیمت: /dollar /bitcoin /price\n"
                "👥 گروه: /rules /report /id /stats /botstatus\n"
                "🛡️ ادمین: /mute /unmute /kick /ban /warn /warns /unwarn /pin /unpin /purge /addbad /removebad /listbad\n"
                "🛡️ پنل مدیریت شیشه‌ای (افزودن الفاظ + یادآور خودکار): دکمه «پنل مدیریت گروه» توی /start"
            )
        else:
            text = "دستور نامشخص."
    except Exception as e:
        logger.error(f"خطا در button_handler: {e}")
        text = "⚠️ یه مشکل موقتی پیش اومد، لطفاً دوباره امتحان کن."

    try:
        await query.message.reply_text(text, reply_markup=main_menu_keyboard())
    except BadRequest as e:
        logger.warning(f"خطای ارسال پیام دکمه: {e}")
        await query.message.reply_text(text[:4000])


# ============================================================
# دستورات فال
# ============================================================
async def fal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "دوست عزیز"
    await update.message.reply_text(f"🔮 فال امروز {name}:\n\n{await generate_fal(name)}")


async def tarot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await generate_tarot())


async def hafez_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await generate_hafez())


async def shans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎯 شانس امروزت: {random.randint(1, 100)}٪")


async def eightball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎱 {random.choice(EIGHTBALL_ANSWERS)}")


async def wheel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎡 نتیجه‌ی چرخش:\n\n{spin_wheel()}")


async def td_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_feature_enabled("truth_or_dare"):
        await update.effective_message.reply_text("🕵️ جرأت یا حقیقت فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🕵️ جرأت یا حقیقت برای بازی گروهی طراحی شده.\n\n"
            "ربات را داخل گروه باز کن و /td را بزن تا اتاق بازی ساخته شود."
        )
        return
    chat_id = update.effective_chat.id
    busy, game_name = group_game_is_busy(chat_id, "truth_or_dare")
    if busy:
        await update.message.reply_text(f"⚠️ الان بازی {game_name} در این گروه در جریانه. اول همون بازی رو تموم کنید.")
        return
    game = TD_GAMES.get(chat_id)
    if game and game.get("started"):
        await update.message.reply_text(td_status_text(game), parse_mode="HTML", reply_markup=td_keyboard(game))
        return
    if not game:
        game = td_new_game(chat_id, update.effective_user.id)
        TD_GAMES[chat_id] = game
    game["players"].setdefault(update.effective_user.id, {"id": update.effective_user.id, "name": td_display_name(update.effective_user)})
    await update.message.reply_text(
        "╭────── 🕵️ ──────╮\n"
        "       اتاق جرأت یا حقیقت\n"
        "╰────────────────╯\n\n"
        "🎭 بازی گروهی با نوبت‌های خصوصی\n"
        "هر بازیکن در گروه بین «حقیقت» و «جرأت» انتخاب می‌کند؛ سؤال/چالش هم در گروه نمایش داده می‌شود، اما پاسخ فقط در Private ربات ارسال می‌شود.\n\n"
        f"👥 شروع از {TD_MIN_PLAYERS} نفر • حداکثر {TD_MAX_PLAYERS} نفر\n"
        "🔒 پاسخ حقیقت و جزئیات جرأت در گروه نمایش داده نمی‌شود.\n🧹 پیام پاسخ پس از بررسی پاک می‌شود و متن پاسخ دائمی ذخیره نمی‌شود.\n🧠 ربات فقط همان نوبت را موقتاً برای بررسی نگه می‌دارد و ادعای تشخیص دروغ از روی متن نمی‌کند.\n\n"
        + td_status_text(game),
        parse_mode="HTML",
        reply_markup=td_keyboard(game),
    )


async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GROUP_RULES_TEXT)


async def dollar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = await fetch_prices()
    text = (f"💵 قیمت دلار: {p['usd_toman']:,} تومان\n(منبع: {p['usd_source']})"
            if p["usd_toman"] else "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن.")
    await update.message.reply_text(text)


async def bitcoin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = await fetch_prices()
    if p["btc_usd"]:
        text = f"₿ قیمت بیت‌کوین: ${p['btc_usd']:,}\n(منبع: {p['btc_source']})"
        if p["btc_toman"]:
            text += f"\nمعادل: {p['btc_toman']:,} تومان"
    else:
        text = "⚠️ فعلاً هیچ‌کدوم از منابع قیمت در دسترس نیستن."
    await update.message.reply_text(text)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = await fetch_prices()
    lines = ["📊 قیمت‌های لحظه‌ای:\n"]
    lines.append(f"💵 دلار: {p['usd_toman']:,} تومان ({p['usd_source']})" if p["usd_toman"] else "💵 دلار: نامشخص")
    lines.append(f"₿ بیت‌کوین: ${p['btc_usd']:,} ({p['btc_source']})" if p["btc_usd"] else "₿ بیت‌کوین: نامشخص")
    await update.message.reply_text("\n".join(lines))


async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("👑 اینجا چت خصوصی منه؛ مالک گروهی وجود نداره.")
        return
    owner = await get_group_owner(chat.id, context)
    if not owner:
        await update.message.reply_text("⚠️ نتونستم مالک گروه رو از Telegram پیدا کنم.")
        return
    await update.message.reply_text(f"👑 مالک گروه «{chat.title}»: {mention_html(owner)}", parse_mode="HTML")


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    text = f"👤 آیدی تو: {user.id}\n💬 آیدی این چت: {chat.id}"
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        text += f"\n🎯 آیدی کاربر ریپلای‌شده: {target.id}"
    await update.message.reply_text(text)


# ============================================================
# پنل مدیریت گروه (دستور متنی جایگزین دکمه، برای راحتی)
# ============================================================
async def adminpanel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("🛡️ این پنل فقط توی گروه معنی داره.")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ این پنل فقط برای ادمین‌های گروهه.")
        return
    await update.message.reply_text(
        "🛡️ پنل مدیریت گروه:\n\nاز اینجا می‌تونی الفاظ نامناسب رو مدیریت کنی یا یادآور خودکار رو روشن/خاموش کنی.",
        reply_markup=admin_panel_keyboard(chat.id),
    )


# ============================================================
# دستورات سرگرمی
# ============================================================
def get_target_user(update: Update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"😂 {random.choice(JOKES_FALLBACK)}")


async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 {random.choice(PROVERBS_FA)}")


COMPLIMENTS_FA = [
    "{name} جان، همینکه هستی کافیه که روز آدم رو بسازه! ✨",
    "{name}، حضورت مثل یه خبر خوب می‌مونه! 🌟",
    "بگم {name} خفنه کم گفتم، افسانه‌ست! 🔥",
    "{name} جان، لبخندت دلیل خوب بودن امروزه! 😄",
    "هر جا {name} باشه، شادی هم هست! 🎉",
    "{name}، تو دقیقاً همونی که همه آرزوشو دارن! 💎",
]
ROASTS_FA = [
    "{name} جان، امروز حسابی سوژه شدی! 😄",
    "{name}، انگار امروز نوبت توئه که بخندونی‌مون! 😂",
    "{name} جان، یکی بگه امروز آروم‌تر باش! 😆",
    "{name}، همیشه یه چیزی برای خندوندن داری! 🤭",
    "{name} جان، امروز افتخاری «سوژه‌ی گروه» رو گرفتی! 🏅",
]


async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target_user(update)
    name = target.first_name if target else update.effective_user.first_name
    await update.message.reply_text(random.choice(COMPLIMENTS_FA).format(name=name))


async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام کسی که می‌خوای بهش متلک بامزه بندازی ریپلای بزن و بنویس /roast")
        return
    name = target.first_name
    await update.message.reply_text(random.choice(ROASTS_FA).format(name=name))


async def love_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target = get_target_user(update)
    name1 = user.first_name
    name2 = target.first_name if target else (" ".join(context.args) if context.args else None)
    if not name2:
        await update.message.reply_text("یا روی پیام کسی ریپلای بزن، یا بنویس: /love اسم")
        return
    percent = sum(ord(c) for c in (name1 + name2)) % 101
    bar = "❤️" * (percent // 10) + "🖤" * (10 - percent // 10)
    await update.message.reply_text(f"💘 عشق‌سنج {name1} و {name2}:\n{bar}\n{percent}٪")


# ============================================================
# مدیریت لیست کلمات نامناسب (دستورات متنی قدیمی - همچنان کار می‌کنن)
# ============================================================
# ============================================================
# هماهنگ‌کننده بازی‌های گروهی — جلوگیری از تداخل بازی‌های سنگین
# ============================================================
def group_game_is_busy(chat_id, requested_game=None):
    """Single active heavy-game guard per group; prevents state collisions."""
    if requested_game != "uno" and chat_id in UNO_GAMES:
        return True, "اونو"
    if requested_game != "werewolf" and chat_id in ww_games:
        return True, "گرگینه"
    if requested_game != "truth_or_dare":
        td_game = TD_GAMES.get(chat_id)
        if td_game and (td_game.get("started") or td_game.get("players")):
            return True, "جرأت یا حقیقت"
    return False, None


# ============================================================
# 🎞️ رسانه‌های بازی — مستقل از منطق بازی و دارای fallback امن
# ============================================================
GAME_MEDIA_CACHE = load_json_safe(GAME_MEDIA_CACHE_FILE, {})
GAME_MEDIA_SOURCE_COOLDOWN = {}
GAME_MEDIA_SOURCE_FAIL_SECONDS = 15 * 60
GAME_MEDIA_LAST_SOURCE = {}
# Resource Manager: سلامت منابع در حافظه + وضعیت سبک روی دیسک نگه داشته می‌شود.
# این state فقط متادیتای منبع است و هیچ محتوای پاسخ کاربر را ذخیره نمی‌کند.
GAME_MEDIA_RESOURCE_STATE = load_json_safe(GAME_MEDIA_RESOURCE_STATE_FILE, {})
GAME_MEDIA_RESOURCE_STATE_LOCK = asyncio.Lock()
GAME_MEDIA_MAX_BYTES = 20 * 1024 * 1024
GAME_MEDIA_HEALTHY_TTL = 6 * 60 * 60
GAME_MEDIA_FAILED_BACKOFF = 30 * 60

def _media_resource_state(src):
    state = GAME_MEDIA_RESOURCE_STATE.get(src)
    if not isinstance(state, dict):
        state = {}
        GAME_MEDIA_RESOURCE_STATE[src] = state
    return state

async def _mark_media_resource(src, ok, detail=""):
    if not src:
        return
    try:
        async with GAME_MEDIA_RESOURCE_STATE_LOCK:
            st = _media_resource_state(src)
            now = time.time()
            if ok:
                st["last_ok"] = now
                st["fail_count"] = 0
                st["last_error"] = ""
                st["last_error_time"] = 0
                GAME_MEDIA_SOURCE_COOLDOWN.pop(src, None)
            else:
                st["fail_count"] = int(st.get("fail_count", 0)) + 1
                st["last_error"] = str(detail)[:300]
                st["last_error_time"] = now
                # Backoff grows moderately, capped at 6 hours.
                backoff = min(6 * 60 * 60, GAME_MEDIA_FAILED_BACKOFF * min(st["fail_count"], 12))
                GAME_MEDIA_SOURCE_COOLDOWN[src] = now + backoff
            await asyncio.to_thread(save_json_safe, GAME_MEDIA_RESOURCE_STATE_FILE, dict(GAME_MEDIA_RESOURCE_STATE))
    except Exception as exc:
        logger.debug("media resource state update failed: %s", exc)

def _media_source_is_healthy(src):
    st = _media_resource_state(src)
    now = time.time()
    last_ok = float(st.get("last_ok", 0) or 0)
    last_error = float(st.get("last_error_time", 0) or 0)
    if now < float(GAME_MEDIA_SOURCE_COOLDOWN.get(src, 0) or 0):
        return False
    # منابعی که اخیراً موفق بوده‌اند اولویت دارند.
    return last_ok >= last_error or (now - last_ok) <= GAME_MEDIA_HEALTHY_TTL

def _media_direct_is_allowed(url):
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    # تطبیق دقیق دامنه (جلوگیری از evilpixabay.com و مشابه)
    return any(host == d or host.endswith("." + d) for d in ("wikimedia.org", "pixabay.com"))


def _save_game_media_cache():
    try:
        save_json_safe(GAME_MEDIA_CACHE_FILE, GAME_MEDIA_CACHE)
    except Exception as exc:
        logger.warning("ذخیره‌ی cache رسانه بازی ناموفق بود: %s", exc)

def _extract_media_url(page_url: str):
    """Resolve a trusted media page to a direct animated-media URL."""
    if not page_url or not page_url.startswith(("http://", "https://")):
        return page_url
    if "upload.wikimedia.org/" in page_url or "cdn.pixabay.com/" in page_url:
        return page_url
    if not _media_direct_is_allowed(page_url):
        return None
    try:
        r = _http_session.get(page_url, timeout=8, allow_redirects=True)
        r.raise_for_status()
        text = r.text
        for prop in ("og:video", "og:image", "twitter:image"):
            patterns = [
                r'<meta[^>]+(?:property|name)=["\']'+re.escape(prop)+r'["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']'+re.escape(prop)+r'["\']',
            ]
            for pat in patterns:
                m = re.search(pat, text, re.I)
                if m:
                    return html.unescape(m.group(1))
    except Exception as exc:
        logger.info("media resolve failed for %s: %s", page_url, exc)
    return None


def _resolve_media_for_download(url: str):
    """Download a small animated media file for Telegram upload fallback."""
    try:
        direct = _extract_media_url(url) or url
        if not direct or not _media_direct_is_allowed(direct):
            return None
        with _http_session.get(direct, timeout=10, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            content_type = (r.headers.get("content-type") or "").lower()
            length = int(r.headers.get("content-length") or 0)
            if length and length > GAME_MEDIA_MAX_BYTES:
                return None
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > GAME_MEDIA_MAX_BYTES:
                    return None
                chunks.append(chunk)
            data = b"".join(chunks)
            if not data:
                return None
            # صفحهٔ HTML یا پاسخ متنی را هرگز به‌عنوان GIF به Telegram تحویل نده.
            sample = data[:256].lstrip().lower()
            if "text/html" in content_type or sample.startswith((b"<!doctype html", b"<html", b"<head")):
                return None
            is_gif = data[:6] in (b"GIF87a", b"GIF89a") or "image/gif" in content_type
            if not is_gif:
                return None
            lower = direct.lower().split("?", 1)[0]
            filename = Path(lower).name or "game.gif"
            if ".gif" not in filename.lower():
                filename = "game.gif"
            return data, filename
    except Exception as exc:
        logger.info("media download fallback failed for %s: %s", url, exc)
        return None


async def send_game_animation(chat_id, context, game_name, event, caption=None):
    """Maximum-effort GIF delivery; media is optional and isolated from game state."""
    sources = GAME_MEDIA.get(game_name, {}).get(event, [])
    if isinstance(sources, str):
        sources = [sources]
    cache_key = f"{game_name}:{event}"
    candidates = []
    cached = GAME_MEDIA_CACHE.get(cache_key)
    if cached:
        candidates.append(("cache", cached))
    healthy_sources = [
        src for src in sources
        if src != cached and _media_source_is_healthy(src)
    ]
    # اگر همه منابع به‌خاطر backoff کنار گذاشته شدند، یک منبع را در هر حال امتحان می‌کنیم؛
    # اما فقط از allowlist داخلی خودمان. این باعث نمی‌شود خرابی یک منبع بازی را متوقف کند.
    if not healthy_sources:
        healthy_sources = [src for src in sources if _media_direct_is_allowed(src)]
    last_src = GAME_MEDIA_LAST_SOURCE.get(cache_key)
    if len(healthy_sources) > 1 and last_src in healthy_sources:
        healthy_sources.remove(last_src)
        healthy_sources.append(last_src)
    random.shuffle(healthy_sources)
    candidates.extend(("source", src) for src in healthy_sources)

    for kind, src in candidates:
        try:
            media = src
            if kind == "source" and ("pixabay.com/gifs/" in src or "commons.wikimedia.org/wiki/" in src):
                media = await asyncio.wait_for(asyncio.to_thread(_extract_media_url, src), timeout=9)
                if not media:
                    continue
            try:
                msg = await asyncio.wait_for(
                    context.bot.send_animation(chat_id=chat_id, animation=media, caption=caption),
                    timeout=10,
                )
                fid = getattr(getattr(msg, "animation", None), "file_id", None)
                if fid:
                    GAME_MEDIA_CACHE[cache_key] = fid
                    _save_game_media_cache()
                if kind == "source":
                    GAME_MEDIA_LAST_SOURCE[cache_key] = src
                    await _mark_media_resource(src, True, "direct")
                return True
            except Exception as send_exc:
                if kind == "cache":
                    GAME_MEDIA_CACHE.pop(cache_key, None)
                    _save_game_media_cache()
                # Download/upload fallback is the important second chance for URL-based GIFs.
                resolved = await asyncio.wait_for(
                    asyncio.to_thread(_resolve_media_for_download, media), timeout=12
                )
                if resolved:
                    data, filename = resolved
                    upload = io.BytesIO(data)
                    upload.name = filename or f"{event}.gif"
                    msg = await asyncio.wait_for(
                        context.bot.send_animation(chat_id=chat_id, animation=upload, caption=caption),
                        timeout=12,
                    )
                    fid = getattr(getattr(msg, "animation", None), "file_id", None)
                    if fid:
                        GAME_MEDIA_CACHE[cache_key] = fid
                        _save_game_media_cache()
                    if kind == "source":
                        GAME_MEDIA_LAST_SOURCE[cache_key] = src
                        await _mark_media_resource(src, True, "download-upload")
                    return True
                # Last-resort document delivery; still never blocks game state.
                try:
                    msg = await asyncio.wait_for(
                        context.bot.send_document(chat_id=chat_id, document=media, caption=caption),
                        timeout=10,
                    )
                    fid = getattr(getattr(msg, "document", None), "file_id", None)
                    if fid:
                        GAME_MEDIA_CACHE[cache_key] = fid
                        _save_game_media_cache()
                    if kind == "source":
                        GAME_MEDIA_LAST_SOURCE[cache_key] = src
                        await _mark_media_resource(src, True, "document")
                    return True
                except Exception as doc_exc:
                    if kind == "source":
                        await _mark_media_resource(src, False, doc_exc)
                    logger.info("media fallback failed for %s/%s: %s / %s", game_name, event, send_exc, doc_exc)
        except Exception as exc:
            if kind == "source":
                await _mark_media_resource(src, False, exc)
            logger.info("media %s/%s failed: %s", game_name, event, exc)
    return False


# ============================================================
# 🎮 لایه‌ی تجربه‌ی بازی‌ها — فقط ظاهر و فضای بازی، بدون تغییر قوانین
# ============================================================
GAME_SCENES = {
    "uno": {
        "start": "╭────────────── 🃏 ──────────────╮\n        UNO NIGHT\n╰──────────────────────────────╯\n\n🎴 کارت‌ها روی میز پخش شدن...\n👥 بازیکن‌ها آماده‌ان. بازی شروع شد!",
        "turn": "🎴 میز UNO آماده‌ست؛ نوبت بازیکن بعدی رسیده.",
        "win": "🏆🎴 یک دست فوق‌العاده تموم شد!",
    },
    "werewolf": {
        "lobby": "╭──────────── 🐺 ────────────╮\n        روستای مه‌آلود\n╰────────────────────────────╯\n🌲 مه بین درخت‌ها می‌پیچه و چراغ‌های روستا کم‌سو شده...",
        "night": "╭──────────── 🌙 ────────────╮\n        شبِ روستای مه‌آلود\n╰────────────────────────────╯\n🌲 باد آرام از میان درخت‌ها می‌گذره و روستا ساکت می‌شه...",
        "day": "╭──────────── ☀️ ────────────╮\n        صبحِ روستای مه‌آلود\n╰────────────────────────────╯\n🌤️ مه کنار می‌ره و رازهای شب کم‌کم آشکار می‌شن...",
    },
}

def game_scene(game_name, part):
    return GAME_SCENES.get(game_name, {}).get(part, "")


def decorated_game_message(title, body, footer=None):
    parts = [title, "", body]
    if footer:
        parts.extend(["", footer])
    return "\n".join(parts)


# ============================================================
# 🃏 UNO — بازی گروهی ساده و بدون شرط/پول
# ============================================================
UNO_GAMES = {}
UNO_GAME_LOCKS = {}

def uno_game_lock(chat_id):
    return UNO_GAME_LOCKS.setdefault(int(chat_id), asyncio.Lock())

def uno_cleanup_game(chat_id):
    UNO_GAMES.pop(int(chat_id), None)
    UNO_GAME_LOCKS.pop(int(chat_id), None)

UNO_MAX_PLAYERS = 8
UNO_MIN_PLAYERS = 3
UNO_COLORS = ("🔴", "🟢", "🔵", "🟡")
UNO_VALUES = tuple(str(i) for i in range(10)) + ("رد کردن", "برگشت", "+۲")


def uno_build_deck():
    deck = []
    for color in UNO_COLORS:
        deck.append((color, "0"))
        for value in UNO_VALUES[1:]:
            deck.extend([(color, value), (color, value)])
    for _ in range(4):
        deck.append(("🌈", "رنگی"))
        deck.append(("🌈", "+۴"))
    random.shuffle(deck)
    return deck


def uno_card_text(card):
    color, value = card
    return f"{color} {value}"


def uno_can_play(card, top, chosen_color=None):
    color, value = card
    top_color, top_value = top
    active_color = chosen_color or top_color
    return color == active_color or value == top_value or color == "🌈"


def uno_draw(game, count=1):
    drawn=[]
    for _ in range(count):
        if not game["deck"]:
            if len(game["discard"]) <= 1:
                break
            top=game["discard"][-1]
            game["deck"]=game["discard"][1:]
            game["discard"]=[top]
            random.shuffle(game["deck"])
        if game["deck"]:
            drawn.append(game["deck"].pop())
    return drawn


def uno_status_text(game):
    current=game["players"][game["turn"]]
    top=game["discard"][-1]
    active=game.get("color") or top[0]
    lines=["╭──────── 🃏 UNO ────────╮", f"   نوبت: {current['name']}", "╰────────────────────────╯", f"🃏 کارت روی میز: {uno_card_text(top)}", f"🎨 رنگ فعال: {active}", "", "👥 وضعیت دست‌ها:"]
    for uid,p in game["players"].items():
        lines.append(f"• {p['name']}: {len(p['hand'])} کارت")
    return "\n".join(lines)


def uno_keyboard(game, user_id):
    p=game["players"].get(user_id)
    if not p or game["turn"] != user_id:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"uno_refresh_{game['chat_id']}_{game.get('revision', 0)}")]])
    rows=[]
    for i,card in enumerate(p["hand"]):
        if uno_can_play(card, game["discard"][-1], game.get("color")):
            rows.append([InlineKeyboardButton(uno_card_text(card), callback_data=f"uno_play_{game['chat_id']}_{game.get('revision', 0)}_{i}")])
    rows.append([InlineKeyboardButton("➕ کارت بکش", callback_data=f"uno_draw_{game['chat_id']}_{game.get('revision', 0)}")])
    return InlineKeyboardMarkup(rows)


def uno_next_turn(game, steps=1):
    ids=list(game["players"].keys())
    idx=ids.index(game["turn"])
    game["turn"]=ids[(idx + steps*game["direction"]) % len(ids)]

async def uno_start_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بازی‌ها فعلاً توسط مالک ربات غیرفعال شده‌اند.")
        return
    chat=update.effective_chat
    if chat.type == "private":
        await update.effective_message.reply_text("🃏 اونو فقط داخل گروه قابل اجراست.")
        return
    if chat.id in UNO_GAMES:
        await update.effective_message.reply_text("🃏 یک بازی اونو همین الان در جریانه. برای پیوستن /uno_join رو بزن.")
        return
    busy, game_name = group_game_is_busy(chat.id, "uno")
    if busy:
        await update.effective_message.reply_text(f"⚠️ الان بازی {game_name} در این گروه در جریانه. اول اون بازی رو تموم کنید، بعد اونو رو شروع کنید.")
        return
    game={"chat_id":chat.id,"host":update.effective_user.id,"players":{},"deck":uno_build_deck(),"discard":[],"turn":None,"direction":1,"color":None,"started":False,"pending_color":None,"pending_action":None,"revision":0,"processing":False}
    UNO_GAMES[chat.id]=game
    game["players"][update.effective_user.id]={"name":update.effective_user.first_name,"hand":[]}
    await update.effective_message.reply_text("╭──────── 🃏 UNO NIGHT ────────╮\n╰─────────────────────────────╯\n\n🎴 میز بازی آماده شد!\n👥 بازیکن‌ها با /uno_join وارد بشن.\n\nحداقل ۳ نفر و حداکثر ۸ نفر.\nوقتی آماده شدید، /uno_startgame رو بزنید.")

async def uno_join_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    chat=update.effective_chat
    game=UNO_GAMES.get(chat.id)
    if not game or game["started"]:
        await update.effective_message.reply_text("🃏 الان لابی اونو برای پیوستن وجود نداره.")
        return
    if update.effective_user.id in game["players"]:
        await update.effective_message.reply_text("تو از قبل داخل اونو هستی 🙂")
        return
    if len(game["players"]) >= UNO_MAX_PLAYERS:
        await update.effective_message.reply_text("ظرفیت اونو پر شده (حداکثر ۸ نفر).")
        return
    u=update.effective_user
    game["players"][u.id]={"name":u.first_name,"hand":[]}
    await update.effective_message.reply_text(f"🎴 {u.first_name} وارد میز UNO شد!\n👥 بازیکن‌های حاضر: {len(game['players'])}/{UNO_MAX_PLAYERS}")

async def uno_startgame_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    chat=update.effective_chat
    game=UNO_GAMES.get(chat.id)
    if not game:
        await update.effective_message.reply_text("اول /uno رو بزن.")
        return
    if game["host"] != update.effective_user.id and not await is_admin(update, context):
        await update.effective_message.reply_text("⛔ فقط سازنده بازی یا ادمین می‌تونه اونو رو شروع کنه.")
        return
    if len(game["players"]) < UNO_MIN_PLAYERS:
        await update.effective_message.reply_text("حداقل ۳ بازیکن لازمه.")
        return
    for _ in range(7):
        for p in game["players"].values():
            p["hand"].extend(uno_draw(game))
    first=uno_draw(game)[0]
    while first[0] == "🌈":
        game["deck"].append(first); random.shuffle(game["deck"]); first=uno_draw(game)[0]
    game["discard"]=[first]; game["color"]=first[0]; game["started"]=True; game["turn"]=next(iter(game["players"])); game["revision"] += 1
    await send_game_animation(chat.id, context, "uno", "start")
    await update.effective_message.reply_text(game_scene("uno", "start") + "\n\n" + uno_status_text(game))
    await uno_private_turn(game, context)

async def uno_private_turn(game, context):
    uid=game["turn"]
    p=game["players"].get(uid)
    if not p: return
    try:
        await context.bot.send_message(uid, "╭────── 🃏 نوبت تو ──────╮\n🎴 میز منتظر حرکته...\n╰───────────────────────╯\n\nیک کارت قابل بازی رو انتخاب کن:", reply_markup=uno_keyboard(game, uid))
    except TelegramError:
        await context.bot.send_message(game["chat_id"], f"⚠️ {p['name']}، برای بازی اونو باید یک‌بار به ربات خصوصی پیام بدی (/start).")

@_callback_ack_guard
async def uno_button_handler(update, context):
    q=update.callback_query
    if not owner_feature_enabled("gaming"):
        await _cb_answer(q, "🎮 بازی‌ها فعلاً توسط مالک ربات غیرفعال شده‌اند.", show_alert=True)
        return
    parts=q.data.split("_")
    if len(parts)<3: return
    try:
        chat_id=int(parts[2])
    except (TypeError, ValueError):
        await _cb_answer(q, "درخواست نامعتبر است.", show_alert=True); return
    game=UNO_GAMES.get(chat_id)
    if not game or not game["started"]:
        await _cb_answer(q, "🃏 این بازی دیگه فعال نیست.", show_alert=True); return
    uid=q.from_user.id
    if game["turn"] != uid:
        await _cb_answer(q, "هنوز نوبت تو نیست.", show_alert=True); return
    try:
        callback_revision=int(parts[3])
    except (IndexError, ValueError):
        callback_revision=-1
    if callback_revision != int(game.get("revision", 0)):
        await _cb_answer(q, "⚠️ این دکمه مربوط به وضعیت قبلی بازیه.", show_alert=True); return
    lock=uno_game_lock(chat_id)
    if lock.locked():
        await _cb_answer(q, "⏳ حرکت قبلی هنوز در حال ثبت است؛ یک لحظه صبر کن.", show_alert=True); return
    async with lock:
        game=UNO_GAMES.get(chat_id)
        if not game or not game.get("started") or game.get("turn") != uid:
            await _cb_answer(q, "این حرکت دیگر معتبر نیست.", show_alert=True); return
        if int(game.get("revision", 0)) != callback_revision:
            await _cb_answer(q, "⚠️ وضعیت بازی تغییر کرده؛ دکمه قبلی معتبر نیست.", show_alert=True); return
        if parts[1] == "refresh":
            await q.edit_message_reply_markup(reply_markup=uno_keyboard(game, uid)); return
        if parts[1] == "color":
            if game.get("pending_color") != uid:
                await _cb_answer(q, "الان نوبت انتخاب رنگ برای تو نیست.", show_alert=True); return
            try:
                color=parts[4]
            except IndexError:
                await _cb_answer(q, "انتخاب رنگ نامعتبر است.", show_alert=True); return
            if color not in UNO_COLORS:
                await _cb_answer(q, "رنگ نامعتبر است.", show_alert=True); return
            game["color"]=color
            game["pending_color"]=None
            game["revision"] += 1
            pending_action=game.get("pending_action")
            game["pending_action"]=None
            if pending_action == "+۴":
                # +4: بازیکن بعدی چهار کارت می‌گیرد و نوبتش را از دست می‌دهد؛
                # فقط یک بار جلو می‌رویم تا بازیکن بعد از او نوبت بگیرد.
                uno_next_turn(game)
                nxt=game["players"][game["turn"]]
                nxt["hand"].extend(uno_draw(game,4))
                uno_next_turn(game)
            else:
                uno_next_turn(game)
            await q.edit_message_text(f"🎨 رنگ انتخاب شد: {color}")
            await context.bot.send_message(chat_id, "🎴 حرکت انجام شد!\n\n" + uno_status_text(game)); await uno_private_turn(game,context)
            return
        if parts[1] == "draw":
            card=uno_draw(game)
            if not card:
                await _cb_answer(q, "دیگه کارتی برای کشیدن وجود نداره.", show_alert=True); return
            game["players"][uid]["hand"].append(card[0])
            game["revision"] += 1
            if uno_can_play(card[0], game["discard"][-1], game.get("color")):
                await q.edit_message_text(f"🃏 کارت کشیدی: {uno_card_text(card[0])}\nاگه می‌خوای بازی کنی، دکمه پایین رو بزن.", reply_markup=uno_keyboard(game,uid))
            else:
                uno_next_turn(game); await q.edit_message_text("🃏 کارت کشیدی و قابل بازی نبود؛ نوبت نفر بعد شد."); await context.bot.send_message(chat_id, "🎴 حرکت انجام شد!\n\n" + uno_status_text(game)); await uno_private_turn(game,context)
            return
        if parts[1] == "play":
            try:
                idx=int(parts[4])
            except (IndexError, ValueError):
                await _cb_answer(q, "این کارت دیگر معتبر نیست.", show_alert=True); return
            hand=game["players"][uid]["hand"]
            if idx >= len(hand): return
            card=hand[idx]
            if not uno_can_play(card, game["discard"][-1], game.get("color")):
                await _cb_answer(q, "این کارت الان قابل بازی نیست.", show_alert=True); return
            hand.pop(idx); game["discard"].append(card); game["color"]=card[0] if card[0] != "🌈" else None
            game["revision"] += 1
            if not hand:
                record_game_result(chat_id, uid, game['players'][uid]['name'], "uno", True)
                for _uid, _p in game['players'].items():
                    if _uid != uid: record_game_result(chat_id, _uid, _p['name'], "uno", False)
                await send_game_animation(chat_id, context, "uno", "win")
                await context.bot.send_message(chat_id, f"╭──────── 🏆 UNO ────────╮\n🎉 {game['players'][uid]['name']} برنده شد!\n╰────────────────────────╯\n\n{game_scene("uno", "win")}")
                uno_cleanup_game(chat_id); return
            if card[0] == "🌈":
                game["pending_color"]=uid
                game["pending_action"]=card[1]
                rows=[[InlineKeyboardButton(c, callback_data=f"uno_color_{chat_id}_{game.get('revision', 0)}_{c}") for c in UNO_COLORS]]
                await q.edit_message_text(f"🌈 {uno_card_text(card)} بازی شد. رنگ بعدی رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows))
                return
            steps=1
            if card[1] == "برگشت": game["direction"] *= -1; steps=2 if len(game["players"]) == 2 else 1
            elif card[1] == "رد کردن": steps=2
            elif card[1] == "+۲":
                # بازیکن بعدی کارت می‌گیرد و نوبتش رد می‌شود.
                uno_next_turn(game)
                nxt=game["players"][game["turn"]]
                nxt["hand"].extend(uno_draw(game,2))
                uno_next_turn(game)
                steps=0
            elif card[1] == "+۴":
                # برای +4 رنگ بعداً انتخاب می‌شود؛ این شاخه فقط برای دفاع از حالت قدیمی است.
                uno_next_turn(game)
                nxt=game["players"][game["turn"]]
                nxt["hand"].extend(uno_draw(game,4))
                uno_next_turn(game)
                steps=0
            uno_next_turn(game, steps)
            await q.edit_message_text(f"✅ {uno_card_text(card)} بازی شد.")
            await context.bot.send_message(chat_id, "🎴 حرکت انجام شد!\n\n" + uno_status_text(game)); await uno_private_turn(game,context)

async def uno_leave_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    game=UNO_GAMES.get(update.effective_chat.id)
    if not game:
        return await update.effective_message.reply_text("بازی اونو فعالی نیست.")
    uid=update.effective_user.id
    if uid not in game["players"]:
        return await update.effective_message.reply_text("تو داخل این بازی نیستی.")
    name=game["players"][uid]["name"]
    ids=list(game["players"].keys())
    old_index=ids.index(uid)
    was_turn=game.get("started") and game.get("turn") == uid
    del game["players"][uid]

    if len(game["players"]) < UNO_MIN_PLAYERS and game["started"]:
        uno_cleanup_game(update.effective_chat.id)
        return await update.effective_message.reply_text(f"👋 {name} خارج شد و بازی به‌خاطر کمبود بازیکن پایان یافت.")

    if game.get("host") == uid and game["players"]:
        game["host"] = next(iter(game["players"]))

    if game.get("started") and game["players"]:
        remaining=list(game["players"].keys())
        if was_turn:
            # نوبت بازیکن خارج‌شده را به نفر بعدیِ همان جایگاه بده.
            game["turn"] = remaining[min(old_index, len(remaining)-1)]
            game["revision"] += 1
            await context.bot.send_message(update.effective_chat.id, f"👋 {name} از UNO خارج شد.\n🎯 نوبت به {game['players'][game['turn']]['name']} رسید.")
            await uno_private_turn(game, context)
        else:
            game["revision"] += 1
            await context.bot.send_message(update.effective_chat.id, f"👋 {name} از UNO خارج شد.")
    else:
        await update.effective_message.reply_text(f"👋 {name} از UNO خارج شد.")

async def uno_stop_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    game=UNO_GAMES.get(update.effective_chat.id)
    if not game: return await update.effective_message.reply_text("بازی اونو فعالی نیست.")
    if update.effective_user.id != game["host"] and not await is_admin(update,context):
        return await update.effective_message.reply_text("⛔ فقط سازنده بازی یا ادمین می‌تونه UNO رو متوقف کنه.")
    uno_cleanup_game(update.effective_chat.id)
    await update.effective_message.reply_text("🛑 بازی اونو متوقف شد.")


async def addbad_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن کلمه اضافه کنن.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /addbad کلمه_موردنظر")
        return
    word = " ".join(context.args).strip().lower()
    await add_custom_bad_word(update.effective_chat.id, word)
    await update.message.reply_text(f"✅ کلمه «{word}» به لیست سفارشی این گروه اضافه شد.")


async def add_custom_bad_word(chat_id, word: str):
    """کلمه رو توی فضای ذخیره‌سازی جداگانه‌ی سرور (bad_words_custom.json) برای همون گروه ثبت می‌کنه."""
    key = str(chat_id)
    async with _file_write_lock:
        words = custom_bad_words.setdefault(key, [])
        if word not in words:
            words.append(word)
            save_json_safe(CUSTOM_BAD_WORDS_FILE, custom_bad_words)


async def removebad_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن کلمه حذف کنن.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /removebad کلمه_موردنظر")
        return
    word = " ".join(context.args).strip().lower()
    removed = False
    if word in BAD_WORDS_FA:
        BAD_WORDS_FA.remove(word)
        removed = True
    if word in BAD_WORDS_EN:
        BAD_WORDS_EN.remove(word)
        removed = True
    key = str(update.effective_chat.id)
    if word in custom_bad_words.get(key, []):
        custom_bad_words[key].remove(word)
        async with _file_write_lock:
            save_json_safe(CUSTOM_BAD_WORDS_FILE, custom_bad_words)
        removed = True
    if removed:
        save_json_safe(BAD_WORDS_FILE, {"fa": BAD_WORDS_FA, "en": BAD_WORDS_EN})
        await update.message.reply_text(f"✅ کلمه «{word}» از لیست حذف شد.")
    else:
        await update.message.reply_text("این کلمه توی لیست نبود.")


async def listbad_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌های گروه می‌تونن ببینن.")
        return
    default_count = len(BAD_WORDS_FA) + len(BAD_WORDS_EN)
    custom_count = len(get_custom_words_for_chat(update.effective_chat.id))
    await update.message.reply_text(
        f"📋 کلمات فیلترشده‌ی پیش‌فرض: {default_count}\n📋 کلمات سفارشیِ همین گروه: {custom_count}"
    )


# ============================================================
# دستورات مدیریتی گروه (فقط ادمین)
# ============================================================
def parse_duration(value: str):
    """تبدیل مدت‌های ساده مثل 30s، 10m، 2h، 1d به timedelta."""
    m = re.fullmatch(r"(\d{1,5})([smhd])", value.strip().lower())
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2)
    if amount <= 0:
        return None
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    return timedelta(**{units[unit]: amount})


async def bot_can_restrict(chat_id, context) -> bool:
    """بررسی می‌کند ربات واقعاً دسترسی محدودکردن اعضا را دارد."""
    try:
        member = await context.bot.get_chat_member(chat_id, context.bot.id)
        return member.status == "administrator" and bool(member.can_restrict_members)
    except TelegramError:
        return False


async def target_is_admin(chat_id, user_id, context) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except TelegramError:
        return False


async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فردی که می‌خوای سکوتش کنی ریپلای بزن و بنویس /mute یا /mute 10m")
        return
    chat_id = update.effective_chat.id
    if target.id == context.bot.id:
        await update.message.reply_text("🤖 نمی‌تونم خودم رو سکوت کنم.")
        return
    if await target_is_admin(chat_id, target.id, context):
        await update.message.reply_text("⛔ این کار روی ادمین‌ها قابل انجام نیست.")
        return
    if not await bot_can_restrict(chat_id, context):
        await update.message.reply_text("⚠️ من دسترسی «Ban/Restrict users» ندارم.")
        return

    duration = None
    if context.args:
        duration = parse_duration(context.args[0])
        if duration is None:
            await update.message.reply_text("⏱️ مدت نامعتبره. نمونه: /mute 30s ، /mute 10m ، /mute 2h ، /mute 1d")
            return

    try:
        until = datetime.now() + duration if duration else None
        kwargs = {
            "chat_id": chat_id,
            "user_id": target.id,
            "permissions": ChatPermissions(can_send_messages=False),
        }
        if until:
            kwargs["until_date"] = until
        await context.bot.restrict_chat_member(**kwargs)
        if duration:
            unit_text = {"s": "ثانیه", "m": "دقیقه", "h": "ساعت", "d": "روز"}
            raw = context.args[0].lower()
            await update.message.reply_text(f"🔇 {target.first_name} برای {raw[:-1]} {unit_text[raw[-1]]} سکوت شد.")
        else:
            await update.message.reply_text(f"🔇 {target.first_name} تا اطلاع بعدی سکوت شد.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد سکوتش کنم: {e}")


async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فردی که می‌خوای صداش رو باز کنی ریپلای بزن و بنویس /unmute")
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(f"🔊 {target.first_name} دوباره می‌تونه پیام بده.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد: {e}")


async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فردی که می‌خوای اخراجش کنی ریپلای بزن و بنویس /kick")
        return
    try:
        chat_id = update.effective_chat.id
        await context.bot.ban_chat_member(chat_id, target.id)
        await context.bot.unban_chat_member(chat_id, target.id)
        await update.message.reply_text(f"👢 {target.first_name} از گروه اخراج شد.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد: {e}")


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فردی که می‌خوای بنش کنی ریپلای بزن و بنویس /ban")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"⛔ {target.first_name} برای همیشه بن شد.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد: {e}")


async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فردی که می‌خوای اخطار بدی ریپلای بزن و بنویس /warn")
        return
    await apply_warn(update, context, target, reason="دستور دستی ادمین")


async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن سابقه اخطار رو ببینن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فرد ریپلای بزن و /warns رو بفرست.")
        return
    count = int(warns_data.get(f"{update.effective_chat.id}:{target.id}", 0))
    await update.message.reply_text(f"⚠️ اخطارهای {target.first_name}: {count}/۳")


async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن اخطار کم کنن.")
        return
    target = get_target_user(update)
    if not target:
        await update.message.reply_text("روی پیام فرد ریپلای بزن و /unwarn رو بفرست.")
        return
    key = f"{update.effective_chat.id}:{target.id}"
    count = int(warns_data.get(key, 0))
    if count <= 0:
        await update.message.reply_text("ℹ️ این کاربر فعلاً اخطاری نداره.")
        return
    warns_data[key] = count - 1
    async with _file_write_lock:
        save_json_safe(WARN_FILE, warns_data)
    await update.message.reply_text(f"✅ یک اخطار از {target.first_name} کم شد. وضعیت فعلی: {warns_data[key]}/۳")


async def apply_warn(update, context, target_user, reason: str, exempt_auto_action: bool = False):
    chat_id = update.effective_chat.id
    key = f"{chat_id}:{target_user.id}"
    warns_data[key] = warns_data.get(key, 0) + 1
    save_json_safe(WARN_FILE, warns_data)
    count = warns_data[key]

    if count >= 3 and not exempt_auto_action:
        try:
            await context.bot.restrict_chat_member(
                chat_id, target_user.id, permissions=ChatPermissions(can_send_messages=False),
            )
            warns_data[key] = 0
            save_json_safe(WARN_FILE, warns_data)
            await update.effective_chat.send_message(
                f"🔇 {target_user.first_name} به دلیل ۳ اخطار ({reason}) به‌صورت خودکار سکوت شد.\n"
                f"ادمین‌ها می‌تونن با /unmute (ریپلای روی پیامش) بازش کنن."
            )
        except TelegramError as e:
            logger.warning(f"خطای سکوت خودکار: {e}")
    else:
        await update.effective_chat.send_message(
            f"⚠️ اخطار {count}/۳ برای {target_user.first_name} ({reason})."
        )


async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("روی پیامی که می‌خوای پین کنی ریپلای بزن و بنویس /pin")
        return
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text("📌 پیام پین شد.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد: {e}")


async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 پین پیام برداشته شد.")
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد: {e}")


async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین‌ها می‌تونن این کار رو بکنن.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("استفاده: /purge تعداد  (مثلاً /purge 10 — حداکثر ۱۰۰)")
        return
    n = min(int(context.args[0]), 100)
    chat_id = update.effective_chat.id
    start_id = update.message.message_id
    deleted = 0
    for mid in range(start_id, start_id - n - 1, -1):
        try:
            await context.bot.delete_message(chat_id, mid)
            deleted += 1
        except TelegramError:
            continue
    await context.bot.send_message(chat_id, f"🧹 {deleted} پیام پاک شد.")


async def botstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("این دستور فقط توی گروه معنی داره.")
        return
    try:
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        lines = [f"🤖 وضعیت من توی «{chat.title}»: {member.status}"]
        if member.status == "administrator":
            perms = {
                "حذف پیام": member.can_delete_messages,
                "محدود/سکوت کردن اعضا": member.can_restrict_members,
                "پین کردن پیام": member.can_pin_messages,
                "دعوت با لینک": member.can_invite_users,
            }
            for label, val in perms.items():
                lines.append(f"{'✅' if val else '❌'} {label}")
        else:
            lines.append(
                "\n⚠️ من الان ادمین این گروه نیستم، برای همین دستورات /mute /kick /ban /warn کار نمی‌کنن.\n\n"
                "برای ادمین کردنم (این کار رو فقط مالک یا یه ادمین دیگه‌ی گروه می‌تونه انجام بده، ربات نمی‌تونه خودشو ادمین کنه):\n"
                "۱. پروفایل گروه → Administrators → Add Admin\n"
                "۲. من رو از لیست اعضا انتخاب کن\n"
                "۳. حداقل «Delete messages» و «Ban/Restrict users» رو فعال کن\n"
                "۴. ذخیره کن"
            )
        await update.message.reply_text("\n".join(lines))
    except TelegramError as e:
        await update.message.reply_text(f"⚠️ نشد وضعیتم رو بگیرم: {e}")


# ============================================================
# فیلتر ناسزا + ضد اسپم + ترجمه شعر + حالت «افزودن کلمه» روی پیام‌های گروه
# ============================================================
def cleanup_expired_conversation_memory():
    """پاکسازی دوره‌ای حافظه‌های RAM تا رشد بی‌نهایت دیکشنری‌ها اتفاق نیفتد."""
    now = time.time()
    for store, ttl in (
        (conversation_context, CONVERSATION_TTL),
        (user_short_memory, USER_MEMORY_TTL),
        (conversation_topic_memory, TOPIC_MEMORY_TTL),
    ):
        stale = []
        for key, items in list(store.items()):
            if isinstance(items, list):
                fresh = [x for x in items if now - x.get("ts", 0) <= ttl] if items and isinstance(items[0], dict) else items
                if store is conversation_context:
                    fresh = [x for x in items if len(x) >= 1 and now - x[0] <= ttl]
                if fresh:
                    store[key] = fresh[-(CONVERSATION_MAX if store is conversation_context else USER_MEMORY_MAX if store is user_short_memory else TOPIC_MEMORY_MAX):]
                else:
                    stale.append(key)
        for key in stale:
            store.pop(key, None)

    # پاکسازی حافظه‌ی ضداسپم و کش ادمین تا رشد بی‌نهایت نداشته باشند.
    for key, dq in list(user_message_times.items()):
        if not dq or now - dq[-1] > FLOOD_WINDOW * 6:
            user_message_times.pop(key, None)
    for key, ts in list(admin_spam_last_warn.items()):
        if now - ts > 3600:
            admin_spam_last_warn.pop(key, None)
    for key, (_val, ts) in list(_ADMIN_CACHE.items()):
        if now - ts > _ADMIN_CACHE_TTL * 4:
            _ADMIN_CACHE.pop(key, None)

    # حافظه‌ی تحلیل لحن/نیت هم همان TTL حافظه‌ی مکالمه را دارد.
    for key, state in list(SMART_DIALOGUE_STATE.items()):
        if now - state.get("ts", 0) > SMART_DIALOGUE_STATE_TTL:
            SMART_DIALOGUE_STATE.pop(key, None)


async def memory_cleanup_job(context):
    cleanup_expired_conversation_memory()


async def td_delete_private_message(bot, user_id, message_id):
    """حذف واقعی پیام Private با Bot API؛ در صورت خطای موقت یک بار دیگر تلاش می‌کند."""
    if not message_id:
        return False
    for attempt in range(2):
        try:
            await bot.delete_message(chat_id=user_id, message_id=message_id)
            return True
        except BadRequest as e:
            # اگر پیام قبلاً حذف شده باشد، برای کاربر عملاً دیگر وجود ندارد.
            msg = str(e).lower()
            if "message to delete not found" in msg or "message can't be deleted" in msg and attempt == 1:
                logger.info("TD private message already absent/unavailable: %s/%s", user_id, message_id)
                return True if "not found" in msg else False
            if attempt == 1:
                logger.warning("TD private message deletion failed for %s/%s: %s", user_id, message_id, e)
        except TelegramError as e:
            if attempt == 1:
                logger.warning("TD private message deletion failed for %s/%s: %s", user_id, message_id, e)
        await asyncio.sleep(0.15)
    return False


def td_ocr_image(path):
    """استخراج موقت متن تصویر؛ فایل ورودی بعد از استفاده توسط caller حذف می‌شود."""
    if Image is None or pytesseract is None:
        return ""
    try:
        image = Image.open(path)
        # OCR روی تصویر RGB؛ نتیجه فقط در حافظه برمی‌گردد و در هیچ فایل/DB ذخیره نمی‌شود.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        try:
            langs = set(pytesseract.get_languages(config=""))
        except Exception:
            langs = set()
        if "fas" in langs and "eng" in langs:
            lang = "fas+eng"
        elif "fas" in langs:
            lang = "fas"
        elif "ara" in langs and "eng" in langs:
            lang = "ara+eng"
        elif "eng" in langs:
            lang = "eng"
        else:
            lang = None
        if not lang:
            return ""
        text = pytesseract.image_to_string(image, lang=lang, config="--psm 6")
        return str(text or "").strip()[:700]
    except Exception as e:
        logger.warning("TD OCR failed: %s", e)
        return ""


async def td_extract_private_answer(update, context):
    """متن پاسخ خصوصی را بدون نگه‌داری دائمی استخراج می‌کند.

    ترتیب ترجیح: متن/کپشن -> OCR عکس -> متن فایل ساده.
    برای رسانه‌هایی که قابلیت استخراج پاسخ ندارند، رشته خالی برمی‌گردد.
    """
    msg = update.message
    if not msg:
        return ""
    if msg.text:
        return str(msg.text)[:700]
    if msg.caption:
        # کپشن به‌تنهایی پاسخ معتبر محسوب می‌شود؛ OCR فقط وقتی لازم است.
        return str(msg.caption)[:700]

    if msg.photo:
        tmp_path = None
        try:
            photo = msg.photo[-1]
            tg_file = await context.bot.get_file(photo.file_id)
            with tempfile.NamedTemporaryFile(prefix="td_ocr_", suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)
            return td_ocr_image(tmp_path)
        except Exception as e:
            logger.warning("TD photo extraction failed for %s: %s", update.effective_user.id if update.effective_user else "?", e)
            return ""
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    if msg.document:
        # فقط فایل‌های متنی کوچک را در حافظه می‌خوانیم؛ فایل‌های باینری/نامرتبط وارد پردازش نمی‌شوند.
        mime = (msg.document.mime_type or "").lower()
        name = (msg.document.file_name or "").lower()
        is_text = mime.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".json"))
        if not is_text or (msg.document.file_size and msg.document.file_size > 512 * 1024):
            return ""
        tmp_path = None
        try:
            tg_file = await context.bot.get_file(msg.document.file_id)
            with tempfile.NamedTemporaryFile(prefix="td_text_", suffix=".tmp", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)
            with open(tmp_path, "rb") as f:
                data = f.read(512 * 1024)
            return data.decode("utf-8", errors="replace")[:700].strip()
        except Exception as e:
            logger.warning("TD document extraction failed for %s: %s", update.effective_user.id if update.effective_user else "?", e)
            return ""
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    return ""


async def handle_td_private_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """همه پاسخ‌های رسانه‌ای نوبت جرأت/حقیقت را موقتاً بررسی و سپس حذف می‌کند."""
    if not update.message or not update.effective_user or update.effective_chat.type != "private":
        return
    user = update.effective_user
    task_key, task = td_find_private_task(user.id)
    if not task:
        return

    game = TD_GAMES.get(task.get("chat_id"))
    current = td_current_player(game) if game else None
    if (not game or not game.get("started") or not current or
            current.get("id") != user.id or
            task.get("turn_index") != int(game.get("turn_index", -1)) or
            task.get("round") != int(game.get("round", -1))):
        TD_PRIVATE_TASKS.pop(task_key, None)
        await td_delete_private_message(context.bot, user.id, update.message.message_id)
        return

    if not await td_claim_processing(task):
        # درخواست دیگری در حال پردازش است؛ قفلِ آن را آزاد نکن (فقط پیام تکراری حذف می‌شود).
        await td_delete_private_message(context.bot, user.id, update.message.message_id)
        return

    message_id = update.message.message_id
    created = task.get("created", 0)
    if datetime.now().timestamp() - created > TD_TASK_TIMEOUT_MINUTES * 60:
        TD_PRIVATE_TASKS.pop(task_key, None)
        await td_delete_private_message(context.bot, user.id, message_id)
        await update.message.reply_text("⌛ این نوبت منقضی شده؛ اگر بازی هنوز ادامه دارد، نوبت جدیدت را انتخاب کن.")
        await td_release_processing(task)
        return

    # قبل از هر پاسخ به کاربر، خود پیام ورودی را برای حفظ حریم خصوصی حذف می‌کنیم.
    answer = await td_extract_private_answer(update, context)
    delete_ok = await td_delete_private_message(context.bot, user.id, message_id)

    task["attempts"] = int(task.get("attempts", 0)) + 1
    # محتوای استخراج‌شده فقط همینجا مصرف می‌شود؛ داخل task ذخیره نمی‌شود.
    if task.get("kind") == "truth":
        valid, reason = td_validate_truth(task.get("task", ""), answer)
    else:
        valid, reason = td_validate_dare(task.get("task", ""), answer)

    if not valid:
        if task.get("feedback_message_id"):
            await td_delete_private_message(context.bot, user.id, task.get("feedback_message_id"))
        if task.get("attempts", 0) >= TD_MAX_VALIDATION_ATTEMPTS:
            target_chat = task.get("chat_id")
            TD_PRIVATE_TASKS.pop(task_key, None)
            game = TD_GAMES.get(target_chat)
            if game:
                game["active_task"] = None
                td_add_failed_turn(game, user.id)
            await update.message.reply_text(
                "🛑 این نوبت بعد از چند پاسخ نامعتبر بسته شد.\n"
                "🧹 آخرین پیام پاسخ هم برای حذف به Telegram سپرده شد.\n"
                "🚫 هیچ‌کدام از پاسخ‌ها ذخیره نشدند و نوبت به بازیکن بعدی رسید."
            )
            if game and game.get("started"):
                td_advance(game)
                await td_announce_turn(context.bot, game, context)
            await td_release_processing(task)
            return
        feedback = await update.message.reply_text(
            f"⚠️ این پاسخ هنوز قابل تأیید نیست.\n\n{reason}\n\n"
            "🧹 پیام قبلی همین الان پاک شد و متن/رسانه‌ی پاسخ نگه‌داری نشد.\n"
            "دوباره فقط نتیجه‌ی همین چالش را بفرست."
        )
        task["feedback_message_id"] = feedback.message_id
        await td_release_processing(task)
        return

    target_chat = task.get("chat_id")
    kind = task.get("kind")
    game = TD_GAMES.get(target_chat)
    current = td_current_player(game) if game else None
    if not game or not game.get("started") or not current or current.get("id") != user.id:
        TD_PRIVATE_TASKS.pop(task_key, None)
        await update.message.reply_text("⚠️ بازی یا نوبت دیگر فعال نیست؛ این پاسخ وارد بازی نشد و ذخیره هم نشد.")
        await td_release_processing(task)
        return

    task_message_id = task.get("task_message_id") or task.get("private_notice_message_id")
    if task_message_id:
        await td_delete_private_message(context.bot, user.id, task_message_id)
    feedback_message_id = task.get("feedback_message_id")
    if feedback_message_id:
        await td_delete_private_message(context.bot, user.id, feedback_message_id)

    # نتیجه‌ی موفق فقط به‌صورت امتیاز ثبت می‌شود؛ متن/رسانه‌ی پاسخ هرگز در داده‌ی بازی ذخیره نمی‌شود.
    points = td_add_score(game, user.id, kind, task.get("attempts", 0))
    TD_PRIVATE_TASKS.pop(task_key, None)
    game["active_task"] = None
    name = td_clean_name(current.get("name"))
    label = "حقیقت" if kind == "truth" else "جرأت"
    delete_line = (
        "🧹 پیام پاسخ با موفقیت از چت Private حذف شد." if delete_ok
        else "⚠️ Telegram حذف پیام را تأیید نکرد؛ ربات پاسخ را ذخیره نکرد و دیگر به آن دسترسی ندارد."
    )
    await context.bot.send_message(
        target_chat,
        f"✅ <b>{name}</b> نوبت {label} را با موفقیت انجام داد. <b>+{points}⭐</b>\n"
        "🔒 پاسخ/جزئیات پاسخ در گروه گفته نمی‌شود.\n"
        f"{delete_line}\n"
        "🚫 متن پاسخ برای استفاده‌ی بعدی ذخیره نشد.",
        parse_mode="HTML",
    )
    await td_send_media(context.bot, target_chat, "success")
    td_advance(game)
    await td_announce_turn(context.bot, game, context)


def td_find_private_tasks(user_id):
    """همه taskهای فعال کاربر را برمی‌گرداند؛ برای جلوگیری از قاطی‌شدن چند گروه."""
    uid = int(user_id)
    return [(key, task) for key, task in list(TD_PRIVATE_TASKS.items())
            if isinstance(key, tuple) and len(key) == 2 and int(key[1]) == uid]


def td_has_other_active_task(user_id, chat_id=None):
    """آیا کاربر در گروه دیگری نوبت خصوصی فعال دارد؟"""
    for key, task in td_find_private_tasks(user_id):
        if chat_id is None or int(task.get("chat_id", key[0])) != int(chat_id):
            return True
    return False


async def td_claim_processing(task):
    """اتمی‌سازی پردازش پاسخ؛ قفل گیرکرده بعد از زمان کوتاه قابل reclaim است."""
    async with TD_STATE_LOCK:
        now = time.time()
        if task.get("processing"):
            started = float(task.get("processing_since", 0) or 0)
            # اگر یک درخواست شبکه/Telegram در حالت استثنا قفل را جا گذاشت،
            # بعد از 120 ثانیه نوبت را برای پاسخ بعدی آزاد می‌کنیم.
            if started and now - started < 120:
                return False
        task["processing"] = True
        task["processing_since"] = now
        return True


async def td_release_processing(task):
    async with TD_STATE_LOCK:
        task["processing"] = False
        task["processing_since"] = 0


def td_find_private_task(user_id):
    for key, task in TD_PRIVATE_TASKS.items():
        if isinstance(key, tuple) and len(key) == 2 and key[1] == int(user_id):
            return key, task
    return None, None


def _smart_social_fast_key(text: str) -> str:
    """مسیر فوق‌سریع برای احوالپرسی‌های کوتاه؛ مستقل از ترتیب کلمات و علامت‌گذاری."""
    n = _smart_normalize(text)
    if not n:
        return ""
    # خطاب به ربات نباید باعث شکست تشخیص شود.
    n = re.sub(r"\bربات\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    # کلمات تشریفاتی رایج را حذف می‌کنیم تا جمله‌های طبیعی هم match شوند.
    fillers = {"لطفا", "لطفاً", "یه", "یک", "راستی", "خب", "ببین", "ببینم", "امروز", "الان"}
    words = [w for w in n.split() if w not in fillers]
    if not words:
        return ""
    ws = set(words)
    greeting = bool(ws & {"سلام", "درود", "هلو", "hello", "hi"})
    wellbeing = bool(ws & {"خوبی", "خوب", "چطوری", "چطوریی", "چطوریه", "حالت", "اوضاعت", "احوالت"})
    news = bool(ws & {"خبر", "خبری"})
    thanks = bool(ws & {"ممنون", "ممنونم", "مرسی", "سپاس", "متشکرم", "تشکر", "دمت", "دمتگرم"})
    farewell = bool(ws & {"خداحافظ", "بای", "فعلا", "فعلاً", "خدانگهدار"})
    apology = bool(ws & {"ببخشید", "ببخش", "معذرت", "شرمنده"})
    if farewell: return "farewell"
    if apology: return "apology"
    if thanks: return "thanks"
    if greeting and wellbeing: return "greeting_wellbeing"
    if greeting: return "greeting"
    if wellbeing: return "wellbeing"
    if news: return "news"
    return ""

SMART_FAST_SOCIAL_REPLIES = {
    "greeting": [
        "سلام! 🌿 خوش اومدی، چطوری؟",
        "سلام رفیق! 👋 من اینجام، بگو ببینم چه خبر.",
        "درود! 😊 خوشحالم که اومدی.",
        "سلام! ✨ بگو ببینم امروز چه خبر داری؟",
    ],
    "greeting_wellbeing": [
        "سلام! 😊 مرسی، خوبم. تو چطوری؟",
        "سلام رفیق! 🌿 خوبم، تو خوبی؟",
        "علیک سلام! 😄 من خوبم، تو چه خبر؟",
    ],
    "wellbeing": [
        "مرسی که پرسیدی 😊 خوبم و اینجام. تو چطوری؟",
        "خوبم رفیق 🌿 تو خوبی؟ روزت چطور می‌گذره؟",
        "روبه‌راهم 😄 تو چه خبر؟",
    ],
    "news": [
        "خبر خاصی نیست 😄 من اینجام؛ تو چه خبر؟",
        "همه‌چی مرتبه 🌿 تو بگو چه خبر ازت؟",
        "چیز خاصی نیست، آماده‌ام باهات گپ بزنم 😊 تو چه خبر؟",
    ],
    "thanks": [
        "خواهش می‌کنم 🌿 خوشحالم که به کارت اومد.",
        "قابلی نداشت 😊 هر وقت چیزی خواستی بگو.",
        "مرسی از لطفت ✨ در خدمتم.",
    ],
    "apology": [
        "اشکالی نداره 😊 راحت باش و ادامه بده.",
        "خواهش می‌کنم، مشکلی نیست 🌿 بگو ببینم چی شده.",
    ],
    "farewell": [
        "فعلاً رفیق 🌙 مراقب خودت باش.",
        "به سلامت 👋 هر وقت برگشتی من اینجام.",
    ],
}

# Intentهای مکالمه‌ای رایج‌تر؛ این‌ها فقط قابلیت‌های قبلی را گسترده می‌کنند.
SMART_INTENTS_V55_EXTRA = [
    ("greeting_more", ["سلام ربات", "ربات سلام", "سلام خوبی ربات", "ربات سلام خوبی", "سلام چطوری ربات", "ربات چطوری", "ربات خوبی", "خوبی ربات", "ربات حالت چطوره", "حالت چطوره ربات", "ربات چه خبر", "چه خبر ربات"], None, None),
    ("thanks_more_v55", ["خیلی مرسی", "مرسی رفیق", "ممنون رفیق", "ممنون ازت", "مرسی ازت", "دستت درد نکنه", "خیلی لطف کردی", "واقعا ممنون", "واقعاً ممنون", "دمت گرم رفیق"], ["خواهش می‌کنم {name} 🌿 خوشحالم که مفید بودم.", "قابلی نداشت {name} 😊 هر وقت چیزی خواستی بگو."], None),
    ("call_more", ["ربات گوش میدی", "ربات حواست هست", "ربات میشنوی", "ربات صدای منو داری", "ربات جواب بده", "ربات اینجایی", "ربات هستی", "ربات بیداری"], ["بله، حواسم هست 😊 بگو.", "آره، اینجام و گوش می‌دم 🌿 بفرما."], None),
    ("help_more", ["ربات میتونی کمکم کنی", "ربات کمکم میکنی", "ربات یه سوال دارم", "ربات یه چیزی میپرسم", "ربات یه چیزی میخوام بپرسم", "میشه ازت یه سوال بپرسم"], ["حتماً {name} 🌿 بپرس؛ تا جایی که بتونم کمکت می‌کنم.", "آره، در خدمتم 😊 سوالت رو بگو."], None),
    ("chat_more", ["حرف بزنیم", "یه کم حرف بزنیم", "یه کم گپ بزنیم", "با من حرف بزن", "با من گپ بزن", "حوصله گپ داری", "حوصله حرف زدن داری", "بیا حرف بزنیم"], ["حتماً 😄 یه گپ خودمونی بد نیست. تو شروع کن.", "چرا که نه 🌿 بگو دوست داری درباره چی حرف بزنیم؟"], None),
    ("ack_more", ["باشه ربات", "اوکی ربات", "خب ربات", "خوبه ربات", "آها ربات", "فهمیدم ربات", "متوجه شدم ربات"], ["آره 😊 بگو، ادامه بدیم.", "باشه رفیق 🌿 من هستم.", "خوبه 😄 حالا بگو قدم بعدی چیه."], None),
    ("mood_more", ["امروز حالم خوبه", "امروز خوبم", "حالم خوبه", "خیلی خوشحالم", "حالم بده", "امروز حالم بده", "خیلی خسته ام", "خیلی خسته‌ام"], ["چه خوب {name} ✨ خوشحالم که حالت خوبه.", "امیدوارم حالت زودتر بهتر بشه {name} 🌿 اگر دوست داری می‌تونی حرف بزنی."], None),
]
SMART_INTENTS.extend(SMART_INTENTS_V55_EXTRA)
# Rebuild normalized index because the extra intents are appended after the original index.
_SMART_INTENTS_NORM = [
    (label, [(_smart_normalize(kw) or kw).split() for kw in kws], responses, dyn)
    for label, kws, responses, dyn in SMART_INTENTS
]


# ============================================================
# v56 — Smart Assistant Pro fallback
# ============================================================
# ========================= SMART ASSISTANT V58 =========================
# دامنه گسترده‌تر مکالمه + اطلاعات کنکور و دانشگاه.
# اطلاعات آزمون‌ها عمداً سال‌محور هستند تا با قوانین سال‌های دیگر قاطی نشوند.
SMART_CONVERSATION_INTENTS_V58 = [
    ("greeting", ["سلام", "سلام ربات", "سلاممم", "سلوم", "سلااام", "درود", "صبح بخیر", "صبح به خیر", "عصر بخیر", "شب بخیر", "شب به خیر", "خسته نباشی", "های", "هلو", "hello", "hi", "hey"], ["سلام 😊 خوش اومدی!", "سلام رفیق 🌱 در خدمتم.", "سلام! خوبی؟ چه خبر؟ 😊"]),
    ("thanks", ["ممنون", "مرسی", "دمت گرم", "لطف کردی", "خیلی ممنون", "سپاس", "متشکرم", "مرسی رفیق", "دستت درد نکنه", "دمت گرم ربات"], ["خواهش می‌کنم 😊", "قربانت، خوشحالم که به کارت اومد 🌱", "خواهش می‌کنم رفیق، در خدمتم."]),
    ("apology", ["ببخشید", "ببخش", "معذرت میخوام", "معذرت میخوام ربات", "شرمنده", "ببخش که", "اگه ناراحتت کردم"], ["اشکالی نداره 😊", "نگران نباش، مشکلی نیست 🌱"]),
    ("farewell", ["خداحافظ", "فعلا", "فعلاً", "بای", "شب بخیر ربات", "میرم", "من برم", "بعدا میام", "بعداً میام"], ["فعلاً رفیق 👋 هر وقت خواستی برگرد.", "خداحافظ 😊 مراقب خودت باش."]),
    ("self_name", ["اسمت چیه", "اسم خودت چیه", "اسم ربات چیه", "اسمتو بگو", "نامت چیه", "چه اسمی داری", "چی صدات کنم", "چطور صدات کنم"], ["اسمم «دستیار هوشمند»ه 🤖؛ هر اسمی راحت‌تری می‌تونی برای صدام کردن استفاده کنی."]),
    ("self_status", ["خوبی", "خوبی ربات", "ربات خوبی", "حالت خوبه", "حالت چطوره", "چطوری", "چطوری ربات", "چه خبر", "اوضاعت چطوره", "همه چی خوبه"], ["خوبم 😊 ممنون که پرسیدی! آماده‌ام باهات حرف بزنم.", "خوبم رفیق 🌱 تو چطوری؟"]),
    ("self_age", ["چند سالته", "چند سال داری", "سنت چقدره", "سن داری", "کی به دنیا اومدی", "تولدت کیه"], ["من مثل آدم‌ها سن و تاریخ تولد ندارم؛ یک ربات نرم‌افزاری‌ام 🤖."]),
    ("self_nature", ["تو آدمی", "آدم هستی", "رباتی", "ربات هستی", "انسانی", "تو انسان هستی", "واقعی هستی", "هوش مصنوعی هستی", "ai هستی"], ["نه، انسان نیستم؛ یک ربات نرم‌افزاری‌ام 🤖 ولی می‌تونم باهات گفت‌وگوی متنی داشته باشم."]),
    ("self_capability", ["چه کارهایی بلدی", "چه کارایی بلدی", "چه چیزایی بلدی", "چه کار میتونی بکنی", "چه کمکی میتونی بکنی", "بلدی چی کار کنی", "قابلیت هات چیه", "چه قابلیت هایی داری"], ["می‌تونم در گفت‌وگوهای معمولی، سؤال‌های عمومی، اطلاعات دانشگاه و کنکور، و قابلیت‌های بازی و مدیریت گروه کمک کنم. 😊"]),
    ("self_memory", ["حافظه داری", "حرفام یادت میمونه", "چیزایی که میگم یادت میمونه", "منو یادت میمونه", "یادت میمونه"], ["برای بعضی بخش‌های ربات، اطلاعات لازم برای ادامه گفت‌وگو به‌صورت محدود نگه داشته می‌شود؛ اما قرار نیست همه حرف‌ها برای همیشه ذخیره شوند. 🧠"]),
    ("chat_start", ["حرف بزنیم", "بیا حرف بزنیم", "یکم حرف بزنیم", "یه کم حرف بزنیم", "حوصله حرف زدن دارم", "میشه باهات حرف بزنم", "میخوام باهات حرف بزنم", "بیا گپ بزنیم", "گپ بزنیم"], ["حتماً 😊 من اینجام. هر موضوعی دوست داری مطرح کن.", "حتماً رفیق 🌱 از هر چیزی که دوست داری شروع کن."]),
    ("bored", ["حوصلم سر رفته", "حوصله ندارم", "حوصله ام سر رفته", "حوصله‌ام سر رفته", "بی حوصله ام", "بیحوصله ام", "کسل شدم", "حوصله هیچ کاری ندارم"], ["اوه 😅 بیا یه موضوع جالب پیدا کنیم. می‌تونیم گپ بزنیم یا یک بازی داخل ربات شروع کنیم."]),
    ("tired", ["خسته ام", "خیلی خسته ام", "خسته شدم", "امروز خسته ام", "دیگه خسته شدم", "خسته نباشم", "انرژی ندارم"], ["خسته نباشی 🌱 اگر دوست داری یکم استراحت کن و بعد با خیال راحت ادامه بده."]),
    ("sad", ["حالم خوب نیست", "حالم بده", "ناراحتم", "خیلی ناراحتم", "دلگیرم", "اعصابم خورده", "حالم گرفته", "امروز خوب نیستم"], ["متأسفم که حالت خوب نیست 🌱 اگر دوست داری می‌تونی درباره چیزی که اذیتت کرده حرف بزنی."]),
    ("happy", ["خیلی خوشحالم", "خوشحالم", "امروز عالی بود", "خیلی خوبم", "حال کردم", "ذوق دارم", "خیلی ذوق دارم", "یه خبر خوب دارم"], ["چه خوب! 😄 خوشحالم که حالت خوبه. تعریف کن ببینم چه خبر خوبی داری."]),
    ("confused", ["نمیدونم چیکار کنم", "نمی‌دونم چیکار کنم", "نمیدونم چی کار کنم", "گیج شدم", "سردرگمم", "نمیدونم از کجا شروع کنم", "نمی دونم از کجا شروع کنم"], ["اشکالی نداره 🌱 موضوع رو بگو تا با هم قدم‌به‌قدم مرتبش کنیم."]),
    ("simple_question", ["میشه یه سوال بپرسم", "یه سوال دارم", "یک سوال دارم", "یه چیزی بپرسم", "می تونم سوال بپرسم", "میتونم سوال بپرسم", "یه پرسش دارم"], ["حتماً 😊 بپرس.", "حتماً رفیق، سؤال رو بگو 🌱"]),
    ("simple_opinion", ["به نظرت چطوره", "نظرت چیه", "به نظرت خوبه", "فکر میکنی خوبه", "فکر میکنی چطوره", "نظرت راجبش چیه", "نظرت درباره این چیه"], ["بگو دقیقاً درباره چی می‌پرسی تا نظر و اطلاعات مرتبطش رو بر اساس موضوع بگم."]),
    ("encouragement", ["میشه کمکم کنی", "کمکم میکنی", "یه کمکی میخوام", "کمک لازم دارم", "راهنماییم کن", "راهنمایی میخوام", "کمک میخوام"], ["حتماً 😊 موضوع رو بگو تا مرحله‌به‌مرحله جلو بریم."]),
    ("everyday_weather", ["هوا چطوره", "امروز هوا چطوره", "هوا خوبه", "بارون میاد", "امروز بارون میاد", "هوا بارونیه", "هوا سرد شده", "هوا گرمه"], ["اگر شهر رو بگی، می‌تونم درباره وضعیت هوا راهنمایی دقیق‌تری بدم؛ برای وضعیت لحظه‌ای باید دادهٔ هواشناسی همان زمان بررسی شود. 🌦️"]),
    ("everyday_time", ["ساعت چنده", "الان ساعت چنده", "چه ساعتیه", "امروز چندمه", "امروز چه روزیه", "تاریخ امروز چنده"], ["برای ساعت و تاریخ دقیق، بهتره زمان سیستم/منبع لحظه‌ای بررسی بشه؛ اگر خواستی می‌تونم بر اساس زمان فعلی پاسخ بدم."]),
]

# سؤال‌ها و عبارت‌های متنوع درباره کنکور، دانشگاه و پذیرش.
KONKOUR_UNIVERSITY_QA_V58 = [
    ("konkur_general", ["کنکور چیه", "کنکور چیست", "آزمون سراسری چیه", "آزمون سراسری چیست", "کنکور دانشگاه چیه", "برای دانشگاه باید کنکور بدیم", "ورود به دانشگاه چطوریه"], "کنکور سراسری یکی از مسیرهای پذیرش در دانشگاه‌ها و مؤسسات آموزش عالی ایران است. شرایط پذیرش، سهم آزمون، سوابق تحصیلی، زمان ثبت‌نام و جزئیات هر سال ممکن است تغییر کند و باید با سال آزمون بررسی شود."),
    ("konkur_groups", ["گروه های آزمایشی کنکور", "رشته های کنکور", "گروه آزمایشی چیه", "تجربی ریاضی انسانی هنر زبان", "کنکور تجربی", "کنکور ریاضی", "کنکور انسانی", "کنکور هنر", "کنکور زبان"], "گروه‌های آزمایشی اصلی کنکور شامل علوم ریاضی و فنی، علوم تجربی و علوم انسانی است و گروه‌های هنر و زبان‌های خارجی نیز وجود دارند. جزئیات انتخاب گروه و شرایط شرکت باید از دفترچه همان سال بررسی شود."),
    ("konkur_1405_date", ["کنکور ۱۴۰۵ کیه", "کنکور 1405 کیه", "تاریخ کنکور ۱۴۰۵", "تاریخ کنکور 1405", "کنکور ۱۴۰۵ چه روزیه", "کنکور 1405 چه روزیه", "آزمون سراسری ۱۴۰۵ چه زمانی برگزار شد"], "طبق برنامه اعلام‌شده برای سال ۱۴۰۵، آزمون سراسری در روزهای ۱۱ و ۱۲ تیر ۱۴۰۵ برگزار شد. چون زمان‌بندی ممکن است با اطلاعیه جدید تغییر کند، برای هر تغییر باید آخرین اطلاعیه سازمان سنجش بررسی شود."),
    ("konkur_1405_registration", ["ثبت نام کنکور ۱۴۰۵", "ثبت نام کنکور 1405", "ثبت نام کنکور کی بود", "زمان ثبت نام کنکور ۱۴۰۵", "زمان ثبت نام کنکور 1405"], "برای آزمون سراسری ۱۴۰۵، بازه ثبت‌نام اعلام‌شده ۱۸ تا ۲۸ اسفند ۱۴۰۴ بود. شرایط و جزئیات ثبت‌نام باید از دفترچه و اطلاعیه‌های همان سال سازمان سنجش کنترل شود."),
    ("konkur_1405_weight", ["تاثیر معدل در کنکور ۱۴۰۵", "تاثیر معدل ۱۴۰۵", "سوابق تحصیلی کنکور ۱۴۰۵", "معدل چند درصد کنکور ۱۴۰۵", "کنکور ۱۴۰۵ چند درصد معدل", "کنکور 1405 چند درصد معدل"], "برای کنکور ۱۴۰۵ در رشته‌های پرمتقاضی، سهم نمره کل سوابق تحصیلی ۶۰٪ و سهم نمره آزمون سراسری ۴۰٪ اعلام شده است. درباره پایه‌های یازدهم و دوازدهم و نحوه اعمال آن‌ها باید به مصوبه و اطلاعیه همان سال توجه کرد؛ در گزارش‌های منتشرشده، پایه یازدهم برای ۱۴۰۵ به‌صورت مثبت و پایه دوازدهم به‌صورت قطعی توضیح داده شده است."),
    ("konkur_1406_weight", ["تاثیر معدل کنکور ۱۴۰۶", "تاثیر سوابق تحصیلی ۱۴۰۶", "معدل کنکور ۱۴۰۶ چند درصده", "کنکور ۱۴۰۶ چند درصد معدل", "سوابق یازدهم دوازدهم ۱۴۰۶"], "برای پذیرش سال ۱۴۰۶-۱۴۰۷، مصوبات منتشرشده سهم ۶۰٪ سوابق تحصیلی را برای رشته‌های اصلی مطرح می‌کنند؛ جزئیات سهم پایه یازدهم و دوازدهم و گروه‌های هنر و زبان متفاوت است. چون این مقررات قابل تغییرند، پاسخ قطعی باید با آخرین مصوبه و دفترچه همان سال تطبیق داده شود."),
    ("final_exams", ["امتحان نهایی و کنکور", "نهایی روی کنکور تاثیر داره", "نمره نهایی مهمه", "سوابق تحصیلی یعنی چی", "سابقه تحصیلی چیه", "ایجاد سابقه تحصیلی", "ترمیم معدل", "ترمیم نمره"], "سوابق تحصیلی از نمرات آزمون‌های نهایی تشکیل می‌شود و طبق مقررات سال آزمون در نمره کل پذیرش اثر می‌گذارد. ایجاد یا ترمیم سابقه هم مقررات مشخصی دارد و باید با آخرین دستورالعمل آموزش‌وپرورش و سنجش بررسی شود."),
    ("rank", ["رتبه کنکور چیه", "رتبه در کنکور", "رتبه کشوری", "رتبه در سهمیه", "رتبه امسال", "با چه رتبه ای قبول میشم"], "رتبه و نمره کل به‌تنهایی برای پاسخ قطعی درباره قبولی کافی نیست؛ رشته‌محل، سهمیه، نوع دوره، سال پذیرش و ظرفیت‌ها هم مهم‌اند. برای برآورد دقیق باید اطلاعات همان سال و دفترچه انتخاب رشته بررسی شود."),
    ("choice", ["انتخاب رشته چطوریه", "انتخاب رشته کنکور", "انتخاب رشته دانشگاه", "چطور انتخاب رشته کنیم", "دفترچه انتخاب رشته", "رشته محل یعنی چی", "کدرشته محل چیه"], "انتخاب رشته بر اساس رشته‌محل‌های مجاز، رتبه و نمره، سهمیه، نوع دوره و علاقه انجام می‌شود. دفترچه انتخاب رشته همان سال مرجع اصلی شرایط و کدرشته‌محل‌هاست."),
    ("university_types", ["انواع دانشگاه", "دانشگاه دولتی", "روزانه چیه", "نوبت دوم چیه", "شبانه چیه", "پیام نور چیه", "غیرانتفاعی چیه", "آزاد چیه", "دانشگاه فرهنگیان", "پردیس خودگردان"], "در ایران مسیرها و دوره‌های مختلفی مثل روزانه، نوبت دوم، پیام‌نور، غیرانتفاعی، دانشگاه آزاد و برخی دوره‌های خاص وجود دارد. شرایط، شهریه، تعهدات و نحوه پذیرش هرکدام متفاوت است و باید از دفترچه همان سال بررسی شود."),
    ("without_exam", ["بدون کنکور", "پذیرش بدون آزمون", "دانشگاه بدون کنکور", "ثبت نام بدون کنکور", "با سوابق تحصیلی دانشگاه", "دانشگاه با معدل"], "بعضی رشته‌محل‌ها ممکن است بر اساس سوابق تحصیلی پذیرش داشته باشند. فهرست رشته‌محل‌ها و شرایط در دفترچه و اطلاعیه پذیرش همان نوبت منتشر می‌شود؛ بنابراین نمی‌توان یک فهرست ثابت را برای همه سال‌ها معتبر دانست."),
    ("students", ["دانشجو شدن", "ورود به دانشگاه", "انتخاب رشته دانشگاه", "رشته دانشگاهی انتخاب کنم", "چه رشته ای بخونم", "کدوم رشته دانشگاهی", "رشته تحصیلی چی انتخاب کنم"], "برای انتخاب رشته بهتر است علاقه، توانایی درسی، محتوای واقعی رشته، شرایط دانشگاه، مسیر ادامه تحصیل و بازار کار را جداگانه بررسی کنی. اگر رشته‌های مدنظرت را بگویی، می‌توانم اطلاعات آن‌ها را کنار هم توضیح بدهم، بدون اینکه به‌جای خودت تصمیم بگیرم."),
    ("major", ["رشته دانشگاهی چیست", "رشته تحصیلی چیه", "فرق رشته ها", "رشته تجربی دانشگاه", "رشته ریاضی دانشگاه", "رشته انسانی دانشگاه"], "رشته دانشگاهی حوزه تخصصی تحصیل توست و هر رشته درس‌ها، مهارت‌ها، مسیرهای ادامه تحصیل و فرصت‌های شغلی متفاوتی دارد. برای مقایسه باید نام رشته‌ها مشخص باشد."),
    ("quota", ["سهمیه کنکور", "سهمیه مناطق", "سهمیه ایثارگران", "سهمیه ۵ درصد", "سهمیه ۲۵ درصد", "سهمیه در کنکور چیه"], "سهمیه‌های پذیرش قواعد جداگانه‌ای دارند و شرایطشان ممکن است تغییر کند. برای پاسخ دقیق باید سال آزمون و نوع سهمیه مشخص باشد و دفترچه همان سال ملاک قرار گیرد."),
    ("student_teacher", ["دانشجو معلم", "فرهنگیان", "کنکور فرهنگیان", "آزمون فرهنگیان", "دانشگاه فرهنگیان چطوریه"], "پذیرش دانشجو-معلم ضوابط و فرایند جداگانه‌ای دارد و در سال‌های اخیر آزمون اختصاصی دانشجو-معلم نیز در برنامه آزمون‌ها آمده است. شرایط سنی، سوابق، مراحل ارزیابی و تعهدات باید از دفترچه و اطلاعیه همان سال بررسی شود."),
    ("masters", ["کنکور ارشد", "کارشناسی ارشد", "آزمون ارشد", "ثبت نام ارشد", "ارشد دانشگاه چطوریه"], "آزمون کارشناسی ارشد آزمونی جدا از کنکور سراسری کارشناسی است و زمان ثبت‌نام، آزمون و دفترچه آن مستقل اعلام می‌شود. برای پاسخ دقیق باید سال آزمون مشخص باشد."),
    ("phd", ["دکتری", "کنکور دکتری", "آزمون دکتری", "ثبت نام دکتری", "دکتری دانشگاه چطوریه"], "پذیرش دکتری نیز فرایند و دفترچه جداگانه دارد و ممکن است شامل آزمون و مراحل بعدی پذیرش باشد. جزئیات هر سال را باید از سازمان سنجش و دانشگاه‌های مربوط بررسی کرد."),
    ("sources", ["منبع اطلاعات کنکور", "منبع کنکور", "اطلاعات رسمی کنکور", "از کجا کنکور رو پیگیری کنم", "اخبار رسمی کنکور", "اطلاعیه سنجش"], "برای اطلاعات رسمی کنکور، مرجع اصلی سازمان سنجش آموزش کشور و اطلاعیه‌های رسمی آن است. برای سوابق تحصیلی و امتحانات نهایی نیز اطلاعیه‌های آموزش‌وپرورش اهمیت دارند. خبرگزاری‌ها برای اطلاع‌رسانی مفیدند، اما در تعارض، متن اطلاعیه رسمی را ملاک قرار بده."),
    ("study_plan", ["برنامه کنکور", "برنامه ریزی کنکور", "چطور برای کنکور درس بخونم", "چطور کنکور بخونم", "برنامه مطالعه کنکور", "از کجا شروع کنم برای کنکور"], "برای برنامه‌ریزی، اول هدف، گروه آزمایشی، سطح فعلی، زمان باقی‌مانده و وضعیت امتحانات نهایی مشخص شود. بعد می‌شود برنامه روزانه و هفتگی واقع‌بینانه ساخت؛ بهتر است برنامه قابل اجرا باشد نه فقط سنگین."),
    ("exam_strategy", ["روش تست زدن", "تست کنکور", "مرور کنکور", "جمع بندی کنکور", "آزمون آزمایشی", "اشتباهات تستی", "تحلیل آزمون"], "برای آمادگی کنکور معمولاً ترکیب یادگیری، تمرین، تست زمان‌دار، مرور و تحلیل اشتباهات مفید است. نسبت هر بخش باید با سطح و زمان باقی‌مانده تنظیم شود."),
    ("university_terms", ["واحد دانشگاه", "ترم دانشگاه", "مشروطی", "معدل دانشگاه", "انتخاب واحد", "حذف و اضافه", "سنوات دانشگاه", "پیش نیاز دانشگاه", "هم نیاز دانشگاه", "کارآموزی دانشگاه", "پروژه دانشگاه", "پایان نامه"], "این اصطلاحات به مقررات آموزشی دانشگاه مربوط‌اند و جزئیاتشان بین دانشگاه‌ها و مقاطع می‌تواند متفاوت باشد. برای پاسخ دقیق، نام دانشگاه و مقطع را بگو."),
]

# چندین شکل محاوره‌ای و غلط‌نویسی رایج که باید به همان مفهوم هدایت شوند.
SMART_V58_VARIANTS = {
    "کنکور": ["کنکورر", "کنکوررر", "کنکور دانشگاه", "کنکوری", "آزمون دانشگاه", "آزمون سراسری", "ازمون سراسری", "ازمون کنکور", "کنکور سراسری"],
    "دانشگاه": ["دانشگا", "دانشگام", "دانشگاهی", "دانشگاهه", "دانشگاهم", "دانشگاه رفتن"],
    "ثبت نام": ["ثبتنام", "ثبت‌نام", "ثبت نامم", "ثبت نام کنکور"],
    "معدل": ["معدلم", "معدل من", "نمره معدل", "نمرات نهایی", "نمره نهایی"],
    "انتخاب رشته": ["انتخاب‌رشته", "انتخاب رشته کنکوری", "انتخاب رشته دانشگاهی"],
}

SMART_COMMON_QA = [
    ("sky", ["چرا آسمون آبیه", "چرا آسمان آبی است", "علت آبی بودن آسمان"], "آسمان در بیشتر شرایط آبی دیده می‌شود چون نور خورشید در جو پراکنده می‌شود و نور آبی بیشتر در همه جهت‌ها پخش می‌شود. 🌤️"),
    ("boiling", ["آب در چند درجه میجوشه", "آب در چه دمایی میجوشه", "نقطه جوش آب چنده"], "در فشار معمول سطح دریا، آب حدود ۱۰۰ درجهٔ سانتی‌گراد می‌جوشد و با تغییر فشار، نقطهٔ جوش هم تغییر می‌کند. 💧"),
    ("freezing", ["آب در چند درجه یخ میزنه", "آب چه دمایی یخ میزنه", "نقطه انجماد آب چنده"], "آب خالص در فشار معمول، حدود صفر درجهٔ سانتی‌گراد منجمد می‌شود. ❄️"),
    ("dna", ["dna چیه", "دی ان ای چیه", "dna چیست", "دی ان ای چیست"], "DNA مولکولی است که بخش بزرگی از اطلاعات ژنتیکی موجودات زنده را در خود نگه می‌دارد. 🧬"),
    ("rna", ["rna چیه", "آر ان ای چیه", "rna چیست", "آر ان ای چیست"], "RNA یکی از مولکول‌های مهم زیستی است و در فرایندهای مختلف سلولی، از جمله انتقال و استفاده از اطلاعات ژنتیکی، نقش دارد. 🧬"),
    ("cell", ["سلول چیه", "سلول چیست", "یاخته چیست"], "سلول کوچک‌ترین واحد بنیادی ساختاری و عملکردی موجودات زنده است. 🔬"),
    ("photosynthesis", ["فتوسنتز چیه", "فتوسنتز چیست", "گیاه چطور غذا میسازه"], "فتوسنتز فرایندی است که گیاهان با استفاده از نور، آب و دی‌اکسیدکربن مواد آلی می‌سازند و معمولاً اکسیژن آزاد می‌کنند. 🌱"),
    ("gravity", ["جاذبه چیه", "گرانش چیست", "گرانش چیه", "چرا چیزها میفتن"], "گرانش برهم‌کنشی است که باعث جذب اجسام دارای جرم به یکدیگر می‌شود و روی زمین اجسام را به سمت سطح زمین شتاب می‌دهد. 🌍"),
    ("internet", ["اینترنت چیه", "اینترنت چیست", "اینترنت چطور کار میکنه"], "اینترنت شبکه‌ای بزرگ از شبکه‌های به‌هم‌پیوسته است که دستگاه‌ها با پروتکل‌هایی مثل IP و TCP با هم ارتباط برقرار می‌کنند. 🌐"),
    ("python", ["پایتون چیه", "python چیست", "پایتون چیست"], "پایتون یک زبان برنامه‌نویسی عمومی و نسبتاً خواناست که در وب، اتوماسیون، داده و هوش مصنوعی کاربرد دارد. 🐍"),
    ("github", ["گیتهاب چیه", "github چیست", "گیت هاب چیه"], "GitHub سرویسی برای میزبانی و همکاری روی پروژه‌های نرم‌افزاری است و معمولاً همراه Git برای مدیریت نسخه استفاده می‌شود. 💻"),
    ("telegram", ["تلگرام چیه", "تلگرام چیست", "telegram چیست"], "تلگرام یک پیام‌رسان است که برای گفت‌وگو، گروه، کانال، فایل و ربات‌ها استفاده می‌شود. 📱"),
    ("time", ["یک ساعت چند دقیقه است", "هر ساعت چند دقیقه است", "یک دقیقه چند ثانیه است", "یک روز چند ساعت است"], "هر ساعت ۶۰ دقیقه، هر دقیقه ۶۰ ثانیه و یک شبانه‌روز معمولاً ۲۴ ساعت است. ⏱️"),
    ("calendar", ["هفته چند روزه", "یک هفته چند روز است", "سال چند ماهه", "یک سال چند ماه است"], "هفته ۷ روز و سال تقویمی معمولاً ۱۲ ماه دارد. 📅"),
]

# ============================================================
# v57 — Smart Assistant Conversation Expansion
# هدف: مکالمه‌ی روزمره‌ی طبیعی، سؤال درباره‌ی خود ربات، و تشخیص
# جمله‌های معمولی بدون الزام به نوشتن کلمه «ربات».
# این بخش فقط قابلیت اضافه می‌کند و intentهای قبلی را حذف نمی‌کند.
# ============================================================
SMART_CONVERSATION_INTENTS_V57 = [
    ("self_name", ["اسمت چیه", "اسم خودت چیه", "اسم ربات چیه", "اسمتو بگو", "نامت چیه", "چه اسمی داری"],
     ["اسمم «دستیار هوشمند»ه 🤖؛ می‌تونی منو همون دستیار صدا کنی.", "من دستیار هوشمند این گروهم 😊 هر وقت خواستی می‌تونی صدام کنی."]),
    ("self_age", ["چند سالته", "چند سال داری", "سنت چقدره", "سن داری", "کی به دنیا اومدی"],
     ["من مثل آدم‌ها سن و تاریخ تولد ندارم؛ یه ربات نرم‌افزاری‌ام که برای این گروه ساخته و تنظیم شده 🤖."]),
    ("self_location", ["کجایی", "کجا زندگی میکنی", "کجا هستی", "اهل کجایی", "کجایی زندگی میکنی"],
     ["من جای فیزیکی مشخصی مثل یک آدم ندارم؛ روی سرور اجرا می‌شم و از همین‌جا باهات حرف می‌زنم 🌐."]),
    ("self_nature", ["تو آدمی", "آدم هستی", "رباتی", "ربات هستی", "انسانی", "تو انسان هستی", "واقعی هستی"],
     ["نه، انسان نیستم؛ یه ربات نرم‌افزاری‌ام 🤖 ولی می‌تونم باهات گفت‌وگوی متنی داشته باشم."]),
    ("self_memory", ["حافظه داری", "حرفام یادت میمونه", "چیزایی که میگم یادت میمونه", "منو یادت میمونه", "یادت میمونه"],
     ["برای بعضی بخش‌های ربات، اطلاعات کوتاه و غیرحساسِ لازم برای ادامهٔ گفتگو در حافظهٔ موقت نگه داشته می‌شه؛ اما قرار نیست همهٔ حرف‌های کاربران برای همیشه ذخیره بشه. 🧠"]),
    ("self_capability", ["چه کارهایی بلدی", "چه کارایی بلدی", "چه چیزایی بلدی", "چه کار میتونی بکنی", "چه کمکی میتونی بکنی", "بلدی چی کار کنی"],
     ["می‌تونم توی همین گروه در گفتگوهای معمولی جواب بدم، به بعضی سؤال‌های ساده پاسخ بدم، اطلاعاتی مثل ساعت و تاریخ رو بگم، و قابلیت‌های بازی و مدیریت گروه رو اجرا کنم. برای فهرست کامل امکاناتم /start رو بزن. 🤖"]),
    ("self_online", ["به اینترنت وصلی", "اینترنت داری", "آنلاین هستی", "به اینترنت دسترسی داری", "اینترنت داری یا نه"],
     ["بعضی قابلیت‌های ربات برای اطلاعات آنلاین به سرویس بیرونی متکی هستن، ولی موتور گفت‌وگوی معمولی من عمدتاً قانون‌محور و داخلیه. 🌐"]),
    ("self_creator", ["کی ساختت", "چه کسی ساختت", "سازندت کیه", "کی طراحی کردت", "کی نوشتت"],
     ["من برای این ربات و این گروه طراحی و پیکربندی شدم؛ جزئیات سازنده رو بهتره از مالک ربات بپرسی. 🤖"]),
    ("self_status", ["خوبی ربات", "حالت خوبه ربات", "چطوری ربات", "چه خبر ربات", "خوب هستی ربات"],
     ["خوبم 😊 آماده‌ام باهات حرف بزنم. خودت چطوری؟", "من خوبم و اینجام 🌿 تو چه خبر؟"]),
    ("chat_start", ["حرف بزنیم", "گپ بزنیم", "یکم حرف بزنیم", "یه کم حرف بزنیم", "بیا صحبت کنیم", "بیا حرف بزنیم", "حوصله حرف داری", "حوصله گپ داری"],
     ["حتماً 😄 من هستم. دوست داری درباره چی حرف بزنیم؟", "چرا که نه 🌿 یه گفت‌وگوی خودمونی داشته باشیم؛ تو شروع کن."]),
    ("casual_positive", ["امروز خوب بود", "امروز خیلی خوب بود", "روز خوبی بود", "خیلی خوشحالم", "خیلی خوش گذشت", "حال کردم", "خیلی خوب شد", "عالی شد"],
     ["چه خوب 😄 خوشحالم که روز خوبی داشتی. چی باعث شد این‌قدر خوب بشه؟", "عالیه ✨ این حس خوب رو نگه دار؛ دوست داری تعریف کنی چی شد؟"]),
    ("casual_tired", ["خسته ام", "خسته‌ام", "خیلی خسته ام", "خیلی خسته‌ام", "امروز خسته شدم", "دیگه خسته شدم"],
     ["خسته نباشی 🌿 اگه روز شلوغی داشتی، یه استراحت کوتاه می‌تونه کمک کنه. دوست داری یکم گپ بزنیم یا حواست رو پرت کنیم؟", "آره، معلومه روز سختی داشتی. کمی استراحت کن؛ اگر خواستی منم اینجام برای یه گپ کوتاه 😊"]),
    ("casual_bored", ["حوصله ام سر رفته", "حوصله‌ام سر رفته", "حوصلم سر رفته", "حوصله ندارم", "بی حوصله ام", "بی‌حوصله‌ام", "کسل شدم"],
     ["پس یه کاری کنیم حوصله‌ات سر نره 😄 می‌تونیم گپ بزنیم یا یکی از بازی‌های ربات رو امتحان کنیم.", "بیا از این حالت دربیایم 😄 دوست داری حرف بزنیم یا یه سرگرمی انتخاب کنیم؟"]),
    ("casual_confused", ["نمیدونم چیکار کنم", "نمی‌دونم چیکار کنم", "نمیدونم چه کار کنم", "نمی دونم چی کار کنم", "نمیدونم چی بگم"],
     ["اشکالی نداره 😊 لازم نیست همیشه بدونی چی کار کنی. اگه بخوای چند گزینه با هم پیدا می‌کنیم؛ فقط بگو الان بیشتر دنبال سرگرمی، حرف زدن یا حل یه مشکل هستی."]),
    ("casual_agreement", ["باشه", "اوکی", "خب باشه", "باشه فهمیدم", "آها فهمیدم", "متوجه شدم", "فهمیدم"],
     ["آره 😊 بریم ادامه بدیم.", "باشه 🌿 من هستم؛ هر وقت خواستی ادامه بده."]),
    ("casual_thanks", ["ممنون", "مرسی", "خیلی ممنون", "دمت گرم", "دستت درد نکنه", "ممنونم ازت", "لطف کردی"],
     ["خواهش می‌کنم 😊 خوشحالم که تونستم کمک کنم.", "قابلی نداشت 🌿 هر وقت لازم داشتی بگو."]),
    ("casual_apology", ["ببخشید", "ببخش", "معذرت میخوام", "شرمنده", "ببخشید ربات"],
     ["اشکالی نداره 😊 اصلاً نگران نباش.", "خواهش می‌کنم، چیزی نشده 🌿 بگو ادامه بدیم."]),
    ("casual_farewell", ["خداحافظ", "فعلا", "فعلاً", "بای", "میرم", "بعدا میام", "بعداً میام"],
     ["فعلاً 😊 هر وقت برگشتی من اینجام.", "خدانگهدار 🌿 مراقب خودت باش."]),
    ("simple_question", ["یه سوال دارم", "یک سوال دارم", "یه سؤال دارم", "یک سؤال دارم", "میشه یه سوال بپرسم", "می تونم یه سوال بپرسم", "میتونم یه سوال بپرسم"],
     ["حتماً 😊 سوالت رو بپرس.", "آره، بپرس 🌿 ببینیم چی می‌خوای بدونی."]),
    ("simple_help", ["میشه کمکم کنی", "میتونی کمکم کنی", "کمکم میکنی", "یه کمکی میخوام", "کمک لازم دارم"],
     ["حتماً 🌿 بگو دقیقاً توی چی کمک می‌خوای.", "آره، در خدمتم 😊 موضوع رو بگو تا ببینیم چطور می‌شه حلش کرد."]),
    ("simple_explain", ["میشه توضیح بدی", "توضیح میدی", "برام توضیح بده", "این یعنی چی", "منظورش چیه", "یعنی چی"],
     ["حتماً. خود عبارت یا موضوعی که می‌خوای توضیح بدم رو بفرست تا ساده و مرحله‌به‌مرحله توضیحش بدم."]),
    ("simple_opinion", ["به نظرت چطوره", "نظرت چیه", "به نظرت خوبه", "تو چی فکر میکنی", "تو چه فکری میکنی"],
     ["می‌تونم نظرم رو بر اساس اطلاعاتی که دارم بگم 😊 فقط موضوع یا چیزی که درباره‌ش نظر می‌خوای رو بگو."]),
    ("simple_request", ["یه چیزی بگو", "یه حرف بزن", "یه جمله بگو", "یه چیز جالب بگو", "حرفی نداری", "چی بگم"],
     ["باشه 😄 یه موضوع انتخاب کنیم: فیلم و سریال، بازی، تکنولوژی، طبیعت یا هر چیزی که خودت دوست داری.", "یه چیز جالب؟ 🌿 مثلاً می‌تونیم درباره یه واقعیت علمی، بازی یا موضوعی که ذهنت رو مشغول کرده حرف بزنیم."]),
]

SMART_CONVERSATION_INDEX_V57 = [
    (label, [(_smart_normalize(p) or p).split() for p in phrases], replies)
    for label, phrases, replies in SMART_CONVERSATION_INTENTS_V57
]


def _smart_v57_conversation_match(text: str):
    n = _smart_normalize(text)
    if not n:
        return None
    tokens = n.split()
    best = None
    for label, phrases, replies in SMART_CONVERSATION_INDEX_V57:
        for phrase in phrases:
            if not phrase:
                continue
            # عبارت کامل، یا عبارت چندکلمه‌ای درون جمله.
            if len(phrase) == 1:
                if phrase[0] in tokens:
                    score = 80
                else:
                    continue
            elif len(phrase) <= len(tokens):
                found = any(tokens[i:i+len(phrase)] == phrase for i in range(len(tokens)-len(phrase)+1))
                if not found:
                    continue
                score = 100 + len(phrase) * 20
            else:
                continue
            # تطابق کل پیام امتیاز بیشتری دارد.
            if n == " ".join(phrase):
                score += 40
            if best is None or score > best[0]:
                best = (score, label, replies)
    return best


def _smart_is_social_message(text: str) -> bool:
    """تشخیص محافظه‌کارانه برای مکالمه‌ی عادی بدون نیاز به خطاب «ربات»."""
    n = _smart_normalize(text)
    if not n:
        return False
    match = _smart_v57_conversation_match(text)
    if match and match[0] >= 100:
        return True
    # سؤال روشن یا درخواست مستقیم هم ارزش پاسخ دارد.
    return _smart_is_question_or_request(text)



# ============================================================
# V59 — بانک گسترده مکالمه عادی + منابع کمک‌درسی و کنکور
# منابع کتاب‌ها بر اساس بررسی منابع منتشرشده در سال ۱۴۰۵ تنظیم شده‌اند؛
# «بهترین» مطلق در نظر گرفته نمی‌شود و سطح دانش‌آموز/هدف (تست یا تشریحی) مهم است.
# ============================================================
SMART_CONVERSATION_INTENTS_V59 = [
    ("casual_weather", ["هوا چطوره", "امروز هوا چطوره", "هوا چه خبره", "هوا خوبه", "امروز هوا خوبه"],
     ["اگه منظورت هوای یک شهر مشخصه، اسم شهر رو بگو تا درباره همون صحبت کنیم. 🌤️", "اگر شهر رو بگی می‌تونم راهنمایی دقیق‌تری درباره هوا بدم. 🌦️"]),
    ("casual_busy", ["چیکار میکنی", "داری چیکار میکنی", "مشغولی", "الان چیکار میکنی", "چه خبر ازت", "چه خبر"],
     ["اینجام و منتظرم ببینم چه چیزی می‌خوای با هم بررسی کنیم 😄", "فعلاً مشغول جواب دادن به توام 😄 بگو ببینم چه خبره."]),
    ("casual_sleep", ["خوابم میاد", "خیلی خوابم میاد", "خوابم گرفته", "شب خوابم نمیبره", "خوابم نمیبره"],
     ["اگر خوابت میاد، یه استراحت کوتاه شاید بد نباشه 😴 اگر هم خوابت نمی‌بره، می‌تونی بگی ذهنت درگیر چیه.", "گاهی کم‌کردن نور و فاصله گرفتن از گوشی قبل خواب کمک می‌کنه. 🌙"]),
    ("casual_food", ["گرسنه ام", "گرسنه‌ام", "چی بخورم", "حوصله غذا ندارم", "غذا چی درست کنم", "شام چی بخوریم"],
     ["بستگی داره چی دوست داشته باشی 😄 اگر چندتا ماده غذایی که داری رو بگی، می‌تونم چند ایده ساده بدم.", "اگر بگی غذای سبک می‌خوای یا سیرکننده، ایده‌های مناسب‌تری می‌دم 🍽️"]),
    ("casual_music", ["چه آهنگی گوش بدم", "آهنگ پیشنهاد بده", "موزیک چی گوش بدم", "موسیقی دوست داری", "چه سبک موسیقی دوست داری"],
     ["برای پیشنهاد آهنگ، حال‌وهوات مهمه؛ آروم، غمگین، شاد، سنتی، پاپ یا سینمایی؟ 🎧", "اگر سبک مورد علاقه‌ات رو بگی، می‌تونم چند نوع موسیقی مناسب پیشنهاد کنم. 🎵"]),
    ("casual_movie", ["چی ببینم", "فیلم چی ببینم", "سریال چی ببینم", "یه فیلم معرفی کن", "یه سریال معرفی کن", "حوصله فیلم دارم"],
     ["ژانر رو بگو؛ علمی‌تخیلی، فانتزی، معمایی، کمدی، اکشن یا درام؟ 🎬", "اگر بگی فیلم می‌خوای یا سریال و چه حال‌وهوایی، پیشنهادها دقیق‌تر می‌شن. 🍿"]),
    ("casual_game", ["بازی کنیم", "حوصله بازی دارم", "یه بازی بریم", "چه بازی بلدی", "بازی چی داریم"],
     ["داخل ربات بازی‌های فعال خودش مثل گرگینه، UNO و حقیقت یا جرأت وجود داره 🎮", "اگه توی گروه هستیم، می‌تونیم سراغ بازی‌های فعال ربات بریم. 🎮"]),
    ("casual_help", ["کمکم میکنی", "یه کم کمکم کن", "کمک لازم دارم", "میشه کمکم کنی", "میشه راهنماییم کنی", "راهنمایی میخوام"],
     ["حتماً 🌱 موضوعت رو بگو؛ سعی می‌کنم مرحله‌به‌مرحله کمکت کنم.", "بگو چه مشکلی داری؛ لازم نیست رسمی یا دقیق بنویسی، با زبان معمولی هم می‌تونی توضیح بدی. 😊"]),
    ("casual_agree", ["آره", "اره", "درسته", "دقیقا", "دقیقاً", "همینطور", "همینه", "باشه", "اوکی", "اوکیه"],
     ["آره 😊", "باشه، پس بریم سراغش.", "دقیقاً 🌱"]),
    ("casual_disagree", ["نه", "نه بابا", "اینطوری نیست", "اشتباهه", "فکر نکنم", "موافق نیستم"],
     ["باشه، ممکنه برداشت من درست نبوده باشه. اگر منظورت رو بگی، اصلاحش می‌کنم. 🌱", "قبول، بیا دقیق‌تر بررسیش کنیم."]),
    ("casual_confused", ["گیج شدم", "هیچی نفهمیدم", "نفهمیدم", "متوجه نشدم", "سخته برام", "نمیدونم چی میگی"],
     ["اشکالی نداره 😊 می‌تونم خیلی ساده‌تر و مرحله‌به‌مرحله توضیح بدم.", "باشه، از اول و ساده‌تر می‌ریم جلو. فقط بگو کدوم قسمت نامفهوم بود. 🌱"]),
    ("casual_excited", ["خیلی خوشحالم", "ذوق دارم", "هیجان زده ام", "هیجان‌زده‌ام", "چه خوب", "عالیه", "خیلی خوب شد"],
     ["چه خوب! 😄✨ خوشحالم که خوشحالی.", "عالیه 😄✨ تعریف کن ببینم چه اتفاق خوبی افتاده!"]),
    ("casual_sad", ["حالم خوب نیست", "حالم بده", "ناراحتم", "امروز ناراحتم", "دلم گرفته", "حوصله ندارم"],
     ["متأسفم که حالت خوب نیست 🌱 اگر دوست داشتی می‌تونی درباره چیزی که اذیتت کرده حرف بزنی.", "لازم نیست همه‌چیز رو یک‌دفعه توضیح بدی؛ هرقدر راحتی بگو. 🤍"]),
    ("casual_question", ["یه چیزی بپرسم", "یه سوال دارم", "یه سؤال دارم", "میشه یه سوال بپرسم", "یه چیزی میخواستم بپرسم"],
     ["حتماً، بپرس 😊", "آره، بگو ببینم سوالت چیه. 🌱"]),
    ("casual_repeat", ["دوباره بگو", "باز بگو", "تکرار کن", "نفهمیدم دوباره", "یک بار دیگه بگو", "یه بار دیگه"],
     ["حتماً 😊 دوباره می‌گم؛ اگر خواستی حتی ساده‌ترش هم می‌کنم."]),
    ("casual_slow", ["آروم تر بگو", "ساده تر بگو", "ساده‌تر بگو", "خلاصه بگو", "کوتاه بگو", "زیاد توضیح نده"],
     ["حتماً؛ از اینجا به بعد کوتاه و ساده می‌گم. 👍"]),
    ("casual_detail", ["بیشتر توضیح بده", "کامل توضیح بده", "جزئیاتش رو بگو", "با جزئیات بگو", "بیشتر بگو", "ادامه بده"],
     ["حتماً؛ جزئی‌تر توضیح می‌دم و اگر لازم باشه مثال هم می‌زنم. 🌱"]),
    ("casual_mistake", ["اشتباه کردی", "جوابت اشتباه بود", "فکر کنم اشتباه گفتی", "این جواب درست نیست"],
     ["ممکنه حق با تو باشه. متن یا بخش موردنظر رو بفرست تا دوباره بررسیش کنم. 🔎"]),
    ("casual_wait", ["صبر کن", "یه لحظه", "یک لحظه", "صبر داشته باش", "الان نه"],
     ["باشه 😊 هر وقت آماده بودی ادامه می‌دیم."]),
    ("casual_name", ["منو میشناسی", "منو میشناسی؟", "اسم منو میدونی", "اسمم رو میدونی"],
     ["اگر قبلاً در همین گفت‌وگو اطلاعاتی از خودت گفته باشی، ممکنه از همان زمینه استفاده کنم؛ ولی اسم یا اطلاعات شخصی رو حدس نمی‌زنم. 🙂"]),
    ("casual_thought", ["به نظرت", "نظرت چیه", "نظرت راجع به", "تو چی فکر میکنی", "فکرت چیه"],
     ["بگو درباره چه موضوعی؛ می‌تونم جنبه‌های مختلفش رو توضیح بدم و اگر موضوع سلیقه‌ای باشه، انتخاب رو به خودت واگذار می‌کنم. 🌱"]),
    ("casual_goodnight", ["شب بخیر", "شب بخیر ربات", "خواب های خوب ببینی", "خواب‌های خوب ببینی"],
     ["شب بخیر 🌙✨ امیدوارم شب آرومی داشته باشی."]),
    ("casual_goodmorning", ["صبح بخیر", "صبح بخیر ربات", "روز بخیر", "صبح قشنگت بخیر"],
     ["صبح بخیر ☀️ امیدوارم روز خوبی داشته باشی."]),
    ("casual_thanks_more", ["خیلی لطف کردی", "واقعا ممنونم", "دمت گرم واقعا", "مرسی که کمک کردی", "ممنون که جواب دادی"],
     ["خواهش می‌کنم 😊 خوشحالم که مفید بود.", "قربانت 🌱 هر وقت لازم داشتی بپرس."]),
]

# منابع کتابی: نام کتاب‌ها و کاربرد آن‌ها، بدون ادعای «بهترین مطلق».
STUDY_BOOK_QA_V59 = [
    ("bio", ["کتاب زیست چی بخرم", "منبع زیست کنکور", "کتاب تست زیست", "زیست تست", "زیست تشریحی"],
     "برای زیست، منابع تستی شناخته‌شده شامل «زیست‌شناسی جامع تست خیلی سبز» و منابع تستی نشر الگو هستند. برای کار تشریحی و امتحان نهایی، کتاب درسی اولویت دارد و می‌توان از منابع تشریحی مثل فرمول بیست گاج یا ماجراهای من و درسام خیلی سبز برای تمرین استفاده کرد. انتخاب نهایی به سطح و هدف بستگی دارد."),
    ("math", ["کتاب ریاضی چی بخرم", "منبع ریاضی کنکور", "کتاب تست ریاضی", "ریاضی تست", "ریاضی تشریحی"],
     "برای ریاضی، از منابع تستی رایج می‌توان به سری تست نشر الگو و جامع خیلی سبز اشاره کرد. برای یادگیری و کار تشریحی، منابع آموزشی مثل سیر تا پیاز گاج یا آموزش شگفت‌انگیز خیلی سبز هم مطرح‌اند. اگر پایه ضعیف باشد، منبع آموزشیِ قابل‌فهم از منبع صرفاً تستی مناسب‌تر است."),
    ("physics", ["کتاب فیزیک چی بخرم", "منبع فیزیک کنکور", "کتاب تست فیزیک", "فیزیک تست", "فیزیک تشریحی"],
     "برای فیزیک، میکروطبقه‌بندی گاج و سری جامع خیلی سبز از منابع تستی رایج‌اند. برای سطح پایه یا کار تشریحی، سیر تا پیاز گاج و منابع تشریحی مثل فرمول بیست گاج می‌توانند کاربرد داشته باشند."),
    ("chemistry", ["کتاب شیمی چی بخرم", "منبع شیمی کنکور", "کتاب تست شیمی", "شیمی تست", "شیمی تشریحی"],
     "برای شیمی، میکروطبقه‌بندی گاج، منابع جامع نشر الگو و کتاب‌های مبتکران از گزینه‌های شناخته‌شده‌اند. برای تشریحی و نهایی، باید روی کتاب درسی و سوالات تشریحی سال‌های قبل هم تمرکز کرد؛ منابعی مثل فرمول بیست می‌توانند برای تمرین تشریحی استفاده شوند."),
    ("persian", ["کتاب فارسی چی بخرم", "منبع فارسی کنکور", "ادبیات تست", "فارسی تشریحی", "کتاب ادبیات کنکور"],
     "برای فارسی، جامع خیلی سبز و منابع موضوعی نشر الگو از گزینه‌های رایج تستی هستند. برای امتحان نهایی، منابع تشریحی مثل فرمول بیست گاج یا ماجراهای من و درسام خیلی سبز بیشتر با هدف پاسخ‌گویی تشریحی هماهنگ‌اند."),
    ("arabic", ["کتاب عربی چی بخرم", "منبع عربی کنکور", "عربی تست", "عربی تشریحی", "کتاب عربی کنکور"],
     "برای عربی، عربی جامع نشر الگو و جامع خیلی سبز از منابع رایج تستی هستند. برای تشریحی، کتاب درسی و تمرین سوالات نهایی اهمیت زیادی دارد و می‌توان از منابع تشریحی مثل سیر تا پیاز یا فرمول بیست استفاده کرد."),
    ("religion", ["کتاب دینی چی بخرم", "منبع دینی کنکور", "دینی تست", "دینی تشریحی", "کتاب دین و زندگی"],
     "در دین و زندگی، کتاب درسی پایه اصلی مطالعه است. برای تست، منابع جامع خیلی سبز رایج‌اند و برای امتحان نهایی می‌توان از فرمول بیست گاج یا بانک‌های سوال تشریحی استفاده کرد."),
    ("english", ["کتاب زبان چی بخرم", "منبع زبان انگلیسی کنکور", "زبان تست", "زبان تشریحی", "کتاب زبان کنکور"],
     "برای زبان انگلیسی، منابع جامع مبتکران و مجموعه‌های جامع تستی رایج‌اند. برای نهایی، کتاب درسی، واژگان و گرامر کتاب و نمونه‌سوال‌های تشریحی اهمیت بیشتری دارند؛ منابع شب امتحان و ماجراهای من و درسام برای مرور تشریحی کاربرد دارند."),
    ("final_exam", ["برای امتحان نهایی چه کتابی", "کتاب امتحان نهایی", "منبع تشریحی نهایی", "کتاب تشریحی چی بخرم", "برای نهایی چی بخونم"],
     "برای امتحان نهایی، اول کتاب درسی و سپس سوالات نهایی سال‌های قبل را جدی بگیر. برای تمرین تشریحی، مجموعه‌هایی مثل فرمول بیست گاج، شب امتحان خیلی سبز و ماجراهای من و درسام خیلی سبز در بازار آموزشی مطرح‌اند. منبع مناسب به درس و پایه بستگی دارد."),
    ("one_source", ["چند کتاب برای هر درس", "دو تا کتاب تست بخرم", "چند منبع داشته باشم", "یک منبع یا چند منبع", "منبع دوم بخرم"],
     "معمولاً بهتر است اول یک منبع اصلی را کامل و تحلیلی کار کنی و بعد، اگر واقعاً به تست بیشتر نیاز داشتی، منبع دوم بگیری. چند کتاب نیمه‌کاره معمولاً از یک کتاب کامل و تحلیل‌شده مفیدتر نیست."),
    ("weak_student", ["پایه ام ضعیفه چه کتابی", "برای مبتدی چه کتابی", "من ضعیفم چی بخونم", "از صفر چه کتابی", "سطحم پایینه چه کتابی"],
     "اگر پایه ضعیف است، منبعی با درسنامه آموزشی و تست‌های سطح‌بندی‌شده مناسب‌تر است؛ مثلاً سیر تا پیاز گاج یا آموزش شگفت‌انگیز خیلی سبز در بعضی دروس. بعد از ساختن پایه می‌توان سراغ منابع تستی سنگین‌تر رفت."),
    ("advanced", ["برای سطح قوی چه کتابی", "تست سخت چی بخرم", "منبع سطح بالا", "منبع تست سخت", "برای درصد بالا چه کتابی"],
     "برای سطح قوی، بعد از تسلط بر منبع اصلی می‌توان از منابع تستی چالشی‌تر یا بانک‌های تست تکمیلی استفاده کرد. نمونه‌هایی مثل IQ گاج، نشر الگو یا منابع جامع پیشرفته بسته به درس مطرح‌اند؛ لازم نیست برای هر درس چند منبع هم‌زمان تهیه شود."),
]

SMART_GENERAL_QA_V59 = [
    ("time", ["ساعت چنده", "الان ساعت چنده", "امروز چندمه", "امروز چه روزیه"], "برای ساعت و تاریخ دقیق باید زمان فعلی محل موردنظر را بررسی کرد؛ اگر شهر یا منطقه زمانی را بگویی، دقیق‌تر می‌شود."),
    ("meaning", ["یعنی چی", "معنیش چیه", "معنی این چیه", "این یعنی چی", "منظورش چیه"], "حتماً؛ خود کلمه، جمله یا عبارتی که می‌خواهی معنی‌اش را بدانی بفرست."),
    ("translate", ["ترجمه کن", "ترجمه اش کن", "این رو انگلیسی کن", "انگلیسیش چی میشه", "فارسیش چی میشه"], "حتماً؛ متن را بفرست و بگو ترجمه را رسمی، دوستانه یا محاوره‌ای می‌خواهی."),
    ("write", ["برام بنویس", "یه متن بنویس", "متن درست کن", "پیام بنویس", "یه پیام بساز"], "حتماً؛ موضوع، مخاطب و لحن را بگو تا متن مناسبش را بنویسم."),
    ("explain", ["توضیح بده", "ساده توضیح بده", "این رو توضیح بده", "چطوری کار میکنه", "چجوری کار میکنه"], "حتماً؛ موضوع را بفرست و اگر بخواهی می‌توانم از پایه و مرحله‌به‌مرحله توضیحش بدهم."),
    ("calculate", ["حساب کن", "محاسبه کن", "چند میشه", "جمعش چنده", "درصدش چنده"], "حتماً؛ عددها یا صورت سؤال را بفرست تا محاسبه کنم."),
    ("compare", ["مقایسه کن", "فرقشون چیه", "چه فرقی دارن", "کدوم فرق داره", "تفاوتشون چیه"], "حتماً؛ دو یا چند موردی که می‌خواهی مقایسه شوند را بفرست تا تفاوت‌ها را موردبه‌مورد بگویم."),
    ("howto", ["چطور انجامش بدم", "چجوری انجامش بدم", "چطوری انجام بدم", "روش انجامش چیه", "مراحلش چیه"], "بگو دقیقاً چه کاری را می‌خواهی انجام بدهی تا مراحلش را قدم‌به‌قدم بگویم."),
    ("not_understand", ["متوجه نشدم", "نفهمیدم چی شد", "بازم نفهمیدم", "ساده ترش کن", "خیلی سخته"], "اشکالی نداره 😊 می‌تونم همان موضوع را خیلی ساده‌تر، با مثال و مرحله‌به‌مرحله توضیح بدهم."),
    ("thanks", ["ممنون", "مرسی", "دمت گرم", "سپاس", "خیلی ممنون"], "خواهش می‌کنم 😊 خوشحالم که کمک کرد."),
]



# ============================================================
# V60 — بانک گسترده موسیقی و خوانندگان ایرانی/خارجی
# اطلاعات توصیفی و غیررتبه‌بندی؛ بدون درج متن ترانه‌های دارای حق‌نشر.
# ============================================================
MUSIC_ARTISTS_V60 = {
    # ایرانی
    "گوگوش": ("ایرانی", "پاپ و موسیقی کلاسیک پاپ ایران", "گوگوش از خوانندگان شناخته‌شده موسیقی پاپ ایران است و آثارش در دوره‌های مختلف فعالیت هنری‌اش سبک‌های متنوعی داشته‌اند."),
    "داریوش": ("ایرانی", "پاپ و موسیقی اجتماعی", "داریوش از خوانندگان شناخته‌شده موسیقی پاپ ایران است و بخش مهمی از آثارش حال‌وهوای اجتماعی و احساسی دارد."),
    "ابی": ("ایرانی", "پاپ", "ابی از خوانندگان شناخته‌شده موسیقی پاپ فارسی است و فعالیت طولانی در موسیقی فارسی داشته است."),
    "هایده": ("ایرانی", "پاپ و موسیقی سنتی/کلاسیک ایرانی", "هایده از خوانندگان برجسته موسیقی فارسی بود و به‌خاطر صدای قدرتمند و قطعات ماندگارش شناخته می‌شود."),
    "ویگن": ("ایرانی", "پاپ و جَز/موسیقی کافه‌ای", "ویگن از چهره‌های اثرگذار پاپ نوین ایران و از پیشگامان خوانندگی پاپ و جَز در ایران بود."),
    "محمدرضا شجریان": ("ایرانی", "موسیقی سنتی ایرانی و آواز", "محمدرضا شجریان از برجسته‌ترین خوانندگان آواز ایرانی بود و در موسیقی دستگاهی ایران فعالیت گسترده‌ای داشت."),
    "همایون شجریان": ("ایرانی", "موسیقی سنتی ایرانی، تلفیقی و پاپ", "همایون شجریان خواننده ایرانی است که در آواز سنتی و پروژه‌های تلفیقی نیز فعالیت داشته است."),
    "محسن نامجو": ("ایرانی", "تلفیقی، راک و موسیقی تجربی", "محسن نامجو به ترکیب عناصر موسیقی ایرانی با راک، بلوز و موسیقی تجربی شناخته می‌شود."),
    "محسن چاوشی": ("ایرانی", "پاپ، راک و موسیقی تلفیقی", "محسن چاوشی خواننده و آهنگساز ایرانی است و در آثارش عناصر پاپ، راک و موسیقی ایرانی دیده می‌شود."),
    "شادمهر عقیلی": ("ایرانی", "پاپ", "شادمهر عقیلی خواننده، آهنگساز و نوازنده ایرانی است که عمدتاً در موسیقی پاپ فعالیت دارد."),
    "سیروان خسروی": ("ایرانی", "پاپ و الکترونیک", "سیروان خسروی خواننده، آهنگساز و تنظیم‌کننده ایرانی است و در موسیقی پاپ و الکترونیک فعالیت دارد."),
    "فرزاد فرزین": ("ایرانی", "پاپ", "فرزاد فرزین خواننده و بازیگر ایرانی است و فعالیت اصلی موسیقایی او در حوزه پاپ است."),
    "رضا صادقی": ("ایرانی", "پاپ و موسیقی احساسی", "رضا صادقی از خوانندگان موسیقی پاپ ایران است و به قطعات احساسی و صدای خاص خود شناخته می‌شود."),
    "معین": ("ایرانی", "پاپ", "معین از خوانندگان شناخته‌شده موسیقی پاپ فارسی است و آثار متعددی در موسیقی عاشقانه و پاپ دارد."),
    "فریدون آسرایی": ("ایرانی", "پاپ", "فریدون آسرایی خواننده ایرانی در سبک پاپ است."),
    "علیرضا عصار": ("ایرانی", "پاپ و موسیقی تلفیقی", "علیرضا عصار خواننده ایرانی است و در آثارش از موسیقی پاپ و قطعات با فضای ارکسترال استفاده شده است."),
    "رضا یزدانی": ("ایرانی", "راک و پاپ راک", "رضا یزدانی از خوانندگان شناخته‌شده موسیقی راک و پاپ راک ایران است."),
    "محسن یگانه": ("ایرانی", "پاپ", "محسن یگانه خواننده، آهنگساز و ترانه‌سرای ایرانی در حوزه موسیقی پاپ است."),
    "احسان خواجه امیری": ("ایرانی", "پاپ", "احسان خواجه‌امیری خواننده و آهنگساز ایرانی در سبک پاپ است."),
    "حمید هیراد": ("ایرانی", "پاپ و تلفیقی", "حمید هیراد خواننده ایرانی است و در آثارش عناصر پاپ و موسیقی ایرانی دیده می‌شود."),
    "گرشا رضایی": ("ایرانی", "پاپ", "گرشا رضایی خواننده، آهنگساز و تنظیم‌کننده ایرانی در حوزه پاپ است."),
    "مهدی یراحی": ("ایرانی", "پاپ و موسیقی اجتماعی", "مهدی یراحی خواننده و آهنگساز ایرانی است و در آثارش قطعات پاپ و اجتماعی دیده می‌شود."),
    "سالار عقیلی": ("ایرانی", "موسیقی سنتی ایرانی", "سالار عقیلی خواننده ایرانی در زمینه موسیقی سنتی و آواز ایرانی فعالیت دارد."),
    "علیرضا قربانی": ("ایرانی", "موسیقی سنتی، تلفیقی و ارکسترال", "علیرضا قربانی خواننده ایرانی است و در موسیقی سنتی، تلفیقی و پروژه‌های ارکسترال فعالیت داشته است."),
    "پرواز همای": ("ایرانی", "سنتی و تلفیقی", "پرواز همای خواننده و آهنگساز ایرانی است و در موسیقی سنتی و تلفیقی فعالیت می‌کند."),
    # خارجی
    "مایکل جکسون": ("خارجی", "پاپ، فانک و R&B", "Michael Jackson خواننده، ترانه‌پرداز و هنرمند آمریکایی بود و از چهره‌های بسیار اثرگذار موسیقی پاپ به شمار می‌آید."),
    "الویس پریسلی": ("خارجی", "راک اند رول و پاپ", "Elvis Presley خواننده آمریکایی و یکی از چهره‌های مهم تاریخ راک اند رول بود."),
    "ادل": ("خارجی", "پاپ و سول", "Adele خواننده و ترانه‌سرای انگلیسی است و به قطعات پاپ و سول و اجرای آوازی قدرتمند شناخته می‌شود."),
    "تیلور سوئیفت": ("خارجی", "پاپ و کانتری پاپ", "Taylor Swift خواننده و ترانه‌سرای آمریکایی است و در طول فعالیتش از کانتری به پاپ و سبک‌های دیگر حرکت کرده است."),
    "اد شیرن": ("خارجی", "پاپ، فولک پاپ و سافت راک", "Ed Sheeran خواننده و ترانه‌سرای انگلیسی است و در پاپ و فولک پاپ فعالیت دارد."),
    "د ویکند": ("خارجی", "R&B، پاپ و سینث‌پاپ", "The Weeknd خواننده و تهیه‌کننده کانادایی است و موسیقی او عناصری از R&B، پاپ و سینث‌پاپ دارد."),
    "بیلی آیلیش": ("خارجی", "پاپ آلترناتیو و الکترونیک پاپ", "Billie Eilish خواننده و ترانه‌سرای آمریکایی است و به فضای مینیمال و پاپ آلترناتیو شناخته می‌شود."),
    "آریانا گرانده": ("خارجی", "پاپ و R&B", "Ariana Grande خواننده و بازیگر آمریکایی است و در موسیقی پاپ و R&B فعالیت دارد."),
    "برونو مارس": ("خارجی", "پاپ، فانک، سول و R&B", "Bruno Mars خواننده و ترانه‌سرای آمریکایی است و در آثارش پاپ، فانک، سول و R&B ترکیب می‌شوند."),
    "امینم": ("خارجی", "هیپ‌هاپ و رپ", "Eminem رپر و ترانه‌سرای آمریکایی است و از چهره‌های شناخته‌شده هیپ‌هاپ به شمار می‌رود."),
    "ریحانا": ("خارجی", "پاپ، R&B و دنس", "Rihanna خواننده باربادوسی است و در پاپ، R&B و موسیقی دنس فعالیت داشته است."),
    "بیانسه": ("خارجی", "پاپ و R&B", "Beyoncé خواننده، ترانه‌سرا و هنرمند آمریکایی است و در پاپ و R&B فعالیت دارد."),
    "لیدی گاگا": ("خارجی", "پاپ، دنس و جَز", "Lady Gaga خواننده و بازیگر آمریکایی است و علاوه بر پاپ، در موسیقی جَز نیز اجرا داشته است."),
    "جاستین بیبر": ("خارجی", "پاپ و R&B", "Justin Bieber خواننده کانادایی است و عمدتاً در پاپ و R&B فعالیت دارد."),
    "کیتی پری": ("خارجی", "پاپ", "Katy Perry خواننده آمریکایی در سبک پاپ است."),
    "سلنا گومز": ("خارجی", "پاپ و الکتروپاپ", "Selena Gomez خواننده و بازیگر آمریکایی است و در موسیقی پاپ و الکتروپاپ فعالیت دارد."),
    "دوا لیپا": ("خارجی", "پاپ و دنس پاپ", "Dua Lipa خواننده انگلیسی-آلبانیایی است و در پاپ و دنس پاپ فعالیت دارد."),
    "هری استایلز": ("خارجی", "پاپ و راک پاپ", "Harry Styles خواننده و ترانه‌سرای انگلیسی است و موسیقی او ترکیبی از پاپ و عناصر راک و سافت راک دارد."),
    "اولیویا رودریگو": ("خارجی", "پاپ و پاپ راک", "Olivia Rodrigo خواننده و ترانه‌سرای آمریکایی است و در پاپ و پاپ راک فعالیت دارد."),
    "مایلی سایرس": ("خارجی", "پاپ، راک و کانتری پاپ", "Miley Cyrus خواننده و بازیگر آمریکایی است و در دوره‌های مختلف فعالیتش سبک‌های متنوعی را تجربه کرده است."),
    "سلین دیون": ("خارجی", "پاپ و بالاد", "Celine Dion خواننده کانادایی است و به اجرای قطعات پاپ و بالاد شناخته می‌شود."),
    "ویتنی هیوستون": ("خارجی", "پاپ، R&B و سول", "Whitney Houston خواننده آمریکایی بود و به توانایی آوازی و فعالیت در پاپ، R&B و سول شناخته می‌شد."),
    "فردی مرکوری": ("خارجی", "راک", "Freddie Mercury خواننده گروه Queen بود و از چهره‌های برجسته تاریخ موسیقی راک به شمار می‌رود."),
    "کرت کوبین": ("خارجی", "گرنج و راک آلترناتیو", "Kurt Cobain خواننده و گیتاریست گروه Nirvana بود و از چهره‌های مهم موج گرنج دهه ۱۹۹۰ محسوب می‌شود."),
    "کریس مارتین": ("خارجی", "راک آلترناتیو و پاپ راک", "Chris Martin خواننده و ترانه‌سرای گروه Coldplay است و در راک آلترناتیو و پاپ راک فعالیت دارد."),
    "دیوید بویی": ("خارجی", "راک، پاپ و گلم راک", "David Bowie خواننده و هنرمند انگلیسی بود و در طول فعالیتش سبک‌های متعددی را تجربه کرد."),
    "لانا دل ری": ("خارجی", "پاپ آلترناتیو و باروک پاپ", "Lana Del Rey خواننده و ترانه‌سرای آمریکایی است و به فضای سینمایی و پاپ آلترناتیو آثارش شناخته می‌شود."),
}

MUSIC_GROUPS_V60 = {
    "راک": ["Queen", "Nirvana", "Linkin Park", "Coldplay", "Metallica", "The Beatles", "Pink Floyd", "Guns N' Roses"],
    "پاپ": ["Michael Jackson", "Adele", "Taylor Swift", "Bruno Mars", "Ariana Grande", "Dua Lipa", "Rihanna", "Justin Bieber"],
    "رپ": ["Eminem", "Drake", "Kendrick Lamar", "Travis Scott", "Jay-Z"],
    "r&b": ["The Weeknd", "Beyoncé", "Rihanna", "Alicia Keys", "Bruno Mars"],
    "سنتی ایرانی": ["محمدرضا شجریان", "همایون شجریان", "علیرضا قربانی", "سالار عقیلی", "پرواز همای"],
    "پاپ ایرانی": ["گوگوش", "ابی", "داریوش", "معین", "شادمهر عقیلی", "محسن چاوشی", "سیروان خسروی", "محسن یگانه"],
}

MUSIC_ALIASES_V60 = {
    "michael jackson":"مایکل جکسون", "مایکل جکسون":"مایکل جکسون", "adele":"ادل", "ادل":"ادل",
    "taylor swift":"تیلور سوئیفت", "تیلور سویفت":"تیلور سوئیفت", "ed sheeran":"اد شیرن", "the weeknd":"د ویکند",
    "weeknd":"د ویکند", "billie eilish":"بیلی آیلیش", "ariana grande":"آریانا گرانده", "bruno mars":"برونو مارس",
    "eminem":"امینم", "rihanna":"ریحانا", "beyonce":"بیانسه", "lady gaga":"لیدی گاگا",
    "justin bieber":"جاستین بیبر", "dua lipa":"دوا لیپا", "harry styles":"هری استایلز", "freddie mercury":"فردی مرکوری",
    "queen":"فردی مرکوری", "lorde":"لرد", "lana del rey":"لانا دل ری", "coldplay":"کریس مارتین",
}

def _smart_music_answer_v60(text: str):
    n = _smart_normalize(text).lower()
    if not n or not any(k in n for k in ("خواننده", "موزیک", "موسیقی", "آهنگ", " singer", "خوانندگی", "سبک موسیقی")):
        # نام هنرمند به‌تنهایی هم باید قابل تشخیص باشد.
        if not any(_smart_normalize(k).lower() in n for k in MUSIC_ARTISTS_V60):
            return None
    artist = None
    for key, canonical in MUSIC_ALIASES_V60.items():
        if key in n:
            artist = canonical
            break
    if artist is None:
        for key in MUSIC_ARTISTS_V60:
            if _smart_normalize(key).lower() in n:
                artist = key
                break
    if artist:
        country, genre, desc = MUSIC_ARTISTS_V60[artist]
        if any(k in n for k in ("کیه", "کیست", "معرفی", "درباره", "who", "چی میخونه")):
            return f"{artist} ({country}) — {genre}. {desc}"
        if any(k in n for k in ("چه سبکی", "سبکش", "سبک", "ژانر", "genre")):
            return f"سبک‌های شاخص {artist}: {genre}. البته بعضی هنرمندان در دوره‌های مختلف سبک‌های متفاوتی را تجربه کرده‌اند."
        return f"{artist} از خوانندگان {country} است و بیشتر با {genre} شناخته می‌شود. اگر بخواهی می‌توانم درباره دوره‌های کاری، آلبوم‌ها یا سبک موسیقی‌اش هم توضیح بدهم."
    for genre, names in MUSIC_GROUPS_V60.items():
        if genre in n or (genre == "r&b" and "آر اند بی" in n):
            return f"چند خواننده/گروه شناخته‌شده در حوزه {genre}: " + "، ".join(names) + ". اگر بخواهی می‌توانم فهرست را بر اساس ایرانی یا خارجی، دهه یا حال‌وهوای موسیقی هم تفکیک کنم."
    if any(k in n for k in ("خواننده ایرانی", "خواننده های ایرانی", "خواننده‌های ایرانی")):
        return "چند خواننده ایرانی شناخته‌شده: " + "، ".join(["گوگوش", "ابی", "داریوش", "هایده", "محمدرضا شجریان", "همایون شجریان", "محسن چاوشی", "شادمهر عقیلی", "علیرضا قربانی", "سیروان خسروی"]) + "."
    if any(k in n for k in ("خواننده خارجی", "خواننده های خارجی", "خواننده‌های خارجی")):
        return "چند خواننده خارجی شناخته‌شده: " + "، ".join(["Michael Jackson", "Adele", "Taylor Swift", "Ed Sheeran", "The Weeknd", "Billie Eilish", "Bruno Mars", "Rihanna", "Beyoncé", "Eminem"]) + "."
    return None

SMART_V61_WORD_ALIASES = {
    "میخام": "میخوام", "میخای": "میخوای", "میخایم": "میخوایم",
    "میشه": "میشود", "میتونی": "میتوانی", "میتونم": "میتوانم",
    "چجوری": "چطوری", "چجور": "چطور", "چطوریه": "چطور",
    "نمیدونم": "نمی دانم", "نمیدونی": "نمی دانی", "ندارم": "ندارم",
    "راجب": "درباره", "راجع": "درباره", "دربارش": "درباره",
    "درمورد": "درباره", "دربارهش": "درباره", "واسه": "برای",
    "برا": "برای", "میتونی": "میتوانی", "میتوانی": "میتوانی",
    "دانشگا": "دانشگاه", "دانشگام": "دانشگاهم", "کنکورر": "کنکور",
    "ثبتنام": "ثبت نام", "انتخابرشته": "انتخاب رشته",
}

def _smart_v61_normalize(text: str) -> str:
    n = _smart_normalize(text)
    for a, b in SMART_V61_WORD_ALIASES.items():
        n = re.sub(rf"(?<!\w){re.escape(a)}(?!\w)", b, n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

def _smart_v61_phrase_match(text: str, phrase: str) -> float:
    """Return a conservative similarity score for natural Persian variants.
    Exact phrase/subphrase matches win; token overlap handles word-order changes.
    """
    n = _smart_v61_normalize(text)
    p = _smart_v61_normalize(phrase)
    if not n or not p:
        return 0.0
    if p in n:
        return 1.0
    nt, pt = set(n.split()), set(p.split())
    if not pt:
        return 0.0
    overlap = len(nt & pt) / len(pt)
    if len(pt) <= 2:
        return overlap if overlap == 1.0 else 0.0
    return overlap

def _smart_v61_best_answer(text: str, banks):
    best = None
    best_score = 0.0
    for item in banks:
        if len(item) == 3:
            _, phrases, answer = item
            answers = answer if isinstance(answer, list) else [answer]
        else:
            continue
        for phrase in phrases:
            score = _smart_v61_phrase_match(text, phrase)
            if score > best_score:
                best_score = score
                best = random.choice(answers) if answers else None
    return best if best_score >= 0.72 else None


# ============================================================
# v63 — موتور انتخاب منبع درسی بر پایه تحقیق چندمنبعی و شواهد مقایسه‌ای به‌روز
# پاسخ‌ها «بهترین مطلق» اعلام نمی‌کنند؛ یک انتخاب پیش‌فرض برای سؤال‌های
# مبهم ارائه می‌کنند و دلیل انتخاب + دلیل مناسب نبودن گزینه‌های دیگر برای
# همان سناریو را توضیح می‌دهند. سطح، هدف و زمان باقی‌مانده می‌تواند انتخاب را تغییر دهد.
# منابع بررسی‌شده برای طراحی این بانک:
# Alpha School، Rah-e Konkur، IranGaah، Alef Moshaver، Concourino و AkoEdu.
# ============================================================
RESOURCE_RECOMMENDATIONS_V62 = {
    # این بانک بر اساس هم‌پوشانی چند منبع آموزشی مستقل ساخته شده است.
    # «پیش‌فرض» به معنی بهترین مطلق نیست؛ سطح، هدف، زمان و رشته می‌تواند آن را تغییر دهد.
    "ریاضی": {
        "default": "نشر الگو — سری تست/جامع",
        "reason": "چند منبع مستقل، نشر الگو را برای تست‌های چالشی، تحلیل مبحثی و داوطلبان متوسط رو به قوی/قوی مطرح کرده‌اند. برای سؤال خیلی کلیِ «ریاضی چی خوبه؟» بنابراین آن را به‌عنوان پیش‌فرض تستی انتخاب می‌کنم، نه بهترین مطلق.",
        "alternatives": {
            "خیلی سبز": "برای آموزش روان‌تر، شروع از پایه و ترکیب آموزش با تست در چند مقایسه گزینه رایجی است.",
            "گاج میکرو": "برای بانک تست طبقه‌بندی‌شده و آشنایی با تیپ‌های استاندارد گزینه قابل بررسی است.",
            "مهر و ماه": "برای آموزش و تست‌های پله‌ای و بعضی مسیرهای جمع‌بندی گزینه قابل بررسی است.",
            "IQ گاج": "برای مرحله‌ای که پایه تثبیت شده و تست دشوارتر می‌خواهی، بیشتر به‌عنوان منبع تکمیلی مطرح می‌شود.",
        },
        "not_default": "خیلی‌سبز، گاج و مهرومه بد نیستند؛ تفاوت اصلی در سطح، حجم درسنامه، نوع تست و هدف استفاده است. اگر کاربر ضعیف باشد، انتخاب پیش‌فرض باید به سمت منبع آموزشی‌تر تغییر کند.",
        "sources": ["مدرسه ریاضی آلفا (۱۴۰۵)", "ایران‌گاه (۱۴۰۵)", "گروه آموزشی کهن", "دکتر درس"],
        "evidence": "در منابع بررسی‌شده، الگو بیشتر برای تست و تحلیل عمیق/سطح بالاتر، خیلی‌سبز برای آموزش روان و تست متنوع، و گاج برای طبقه‌بندی تست مطرح شده است.",
    },
    "فیزیک": {
        "default": "خیلی سبز — فیزیک جامع کنکور",
        "reason": "در مقایسه تازه راه کنکور، خیلی‌سبز برای پایه ضعیف‌تر و آموزش، گاج برای سطح متوسط و نشر الگو برای تست دشوارتر تفکیک شده‌اند. بنابراین برای سؤال عمومی بدون دانستن سطح، خیلی‌سبز را به‌عنوان نقطه شروع انتخاب می‌کنم.",
        "alternatives": {
            "گاج میکرو": "برای سطح متوسط و ترکیب درسنامه و بانک تست گزینه قابل بررسی است.",
            "نشر الگو": "برای داوطلب قوی‌تر و تمرین تست‌های دشوارتر بیشتر مطرح می‌شود.",
            "نردبام": "بیشتر برای تست‌های سطح بالاتر و به‌عنوان مکمل منبع اصلی مناسب است.",
        },
        "not_default": "الگو کنار گذاشته نشده؛ فقط بدون دانستن سطح کاربر، منبع آموزشی‌تر انتخاب کم‌ریسک‌تری است.",
        "sources": ["راه کنکور (۱۷ سپتامبر ۲۰۲۶)", "گروه آموزشی کهن", "ایران‌کتاب"],
        "evidence": "مقایسه تازه راه کنکور سطح ضعیف/متوسط/قوی را به‌ترتیب با خیلی‌سبز/میکرو گاج/نشر الگو تفکیک کرده است.",
    },
    "شیمی": {
        "default": "مبتکران — شیمی کنکور",
        "reason": "در مقایسه تازه مبتکران و خیلی‌سبز، مبتکران به آموزش عمیق‌تر و جزئیات بیشتر و خیلی‌سبز به بیان خلاصه‌تر و تست استانداردتر نسبت داده شده است. برای کسی که سؤال عمومی می‌پرسد و یک منبع آموزش‌محور می‌خواهد، مبتکران پیش‌فرض مناسبی است.",
        "alternatives": {
            "خیلی سبز": "برای آموزش روان‌تر، حجم کمتر و تمرکز بیشتر بر تست استاندارد گزینه قابل بررسی است.",
            "نشر الگو": "برای تست‌های محاسباتی و سطح بالاتر می‌تواند منبع تکمیلی باشد.",
            "گاج میکرو": "برای ساختار طبقه‌بندی‌شده و بانک تست گزینه دیگری است.",
        },
        "not_default": "خیلی‌سبز، الگو و گاج رد نمی‌شوند؛ تفاوت اصلی در عمق آموزش، حجم، سبک تست و زمان در دسترس است.",
        "sources": ["راه کنکور (۲۶ سپتامبر ۲۰۲۶)", "مشاوران ۱۰۰", "گروه آموزشی کهن"],
        "evidence": "منابع بررسی‌شده مبتکران را آموزش‌محور و عمیق‌تر و خیلی‌سبز را خلاصه‌تر و تست‌محورتر توصیف کرده‌اند.",
    },
    "زیست": {
        "default": "خیلی سبز — زیست‌شناسی جامع تست",
        "reason": "منابع مقایسه‌ای روی پوشش سه پایه، درسنامه مفهومی، تست‌های ترکیبی و پاسخ تشریحی زیست جامع خیلی‌سبز تأکید کرده‌اند. برای سؤال عمومی، این ترکیب آن را گزینه پیش‌فرض مناسبی می‌کند.",
        "alternatives": {
            "IQ گاج": "برای تست‌های سطح بالاتر و تحلیلی‌تر بعد از تثبیت پایه قابل بررسی است.",
            "نشر الگو / موج آزمون": "برای آزمون‌محوری، تست ترکیبی و جمع‌بندی بیشتر کاربرد دارد.",
            "قلم‌چی سه‌سطحی": "برای تمرین سطح‌بندی‌شده و آزمونی گزینه تکمیلی است.",
        },
        "not_default": "گاج و الگو حذف نمی‌شوند؛ برای منبع اول عمومی، پوشش آموزشی و تستی جامع را در اولویت گذاشته‌ام.",
        "sources": ["مدرسه ریاضی آلفا (منابع زیست ۱۴۰۵)", "ایران‌گاه", "دکتر درس"],
        "evidence": "منابع بررسی‌شده زیست جامع خیلی‌سبز را برای پوشش و آموزش، و موج آزمون الگو را برای آزمون‌محوری/جمع‌بندی مطرح کرده‌اند.",
    },
    "فارسی": {
        "default": "خیلی سبز — جامع/تست",
        "reason": "برای فارسی، منبع جامع به‌عنوان گزینه عمومی مناسب است؛ اما برای فارسی بهتر است بر اساس مبحث ضعف، مثل قرابت، آرایه، دستور یا املا، منبع تخصصی هم در نظر گرفته شود.",
        "alternatives": {
            "گاج": "برای بانک تست و دسته‌بندی بیشتر قابل بررسی است.",
            "نشر الگو": "برای بعضی مباحث موضوعی و تست‌محور گزینه تخصصی‌تری است.",
            "مهر و ماه": "برای مرور و جمع‌بندی گزینه قابل بررسی است.",
        },
        "not_default": "در فارسی، انتخاب یک کتاب جامع برای کسی که فقط در یک مبحث ضعف دارد ممکن است باعث خرید اضافه شود؛ اول باید نقطه‌ضعف مشخص شود.",
        "sources": ["مشیرین", "آکو", "منابع مقایسه‌ای امتحان نهایی"],
        "evidence": "منابع آموزشی بین کتاب جامع و منابع موضوعی تفاوت می‌گذارند و برای نهایی، کتاب درسی و تمرین تشریحی را جدا از تست کنکور بررسی می‌کنند.",
    },
    "عربی": {
        "default": "مشاوران آموزش — عربی جامع انسانی (برای رشته انسانی)",
        "reason": "برای عربی انسانی، آکو در ۱۴۰۵ مشاوران آموزش را به‌عنوان منبع تخصصی انسانی و در کنار آن خیلی‌سبز و میکرو گاج معرفی کرده است. چون رشته در این درس مهم است، ربات نباید بدون پرسیدن رشته یک کتاب را برای همه پیشنهاد دهد.",
        "alternatives": {
            "خیلی سبز": "برای درسنامه روان‌تر و مسیر آموزشی‌تر گزینه قابل بررسی است.",
            "گاج میکرو": "برای بانک تست طبقه‌بندی‌شده گزینه قابل بررسی است.",
            "مهر و ماه": "برای منابع خلاصه و جمع‌بندی گزینه تکمیلی است.",
        },
        "not_default": "اگر کاربر انسانی نیست یا هدفش امتحان نهایی است، پیشنهاد باید تغییر کند؛ عربی تخصصی انسانی را نباید با عربی مدرسه یکسان در نظر گرفت.",
        "sources": ["آکو (۱۴۰۵)", "مشیرین", "ایران‌گاه"],
        "evidence": "منابع ۱۴۰۵ بین عربی تخصصی انسانی و منابع عمومی/تشریحی تفکیک کرده‌اند.",
    },
    "دینی": {
        "default": "منبع جامع تستی متناسب با رشته + کتاب درسی",
        "reason": "در دینی، برای پاسخ مسئولانه نمی‌شود یک ناشر را بدون دانستن هدف کاربر به‌عنوان بهترین مطلق معرفی کرد. برای کنکور باید منبع تستی جامع و برای نهایی باید متن کتاب درسی و منبع تشریحی را محور قرار داد.",
        "alternatives": {
            "خیلی سبز": "برای تست و درسنامه جامع گزینه مطرح است.",
            "گاج": "برای بانک تست و منابع تشریحی فرمول بیست گزینه‌های شناخته‌شده‌ای دارد.",
            "خیلی سبز ماجراهای بیست": "برای تمرین تشریحی و امتحان نهایی مطرح است.",
        },
        "not_default": "هدف تستی و تشریحی در این درس تفاوت جدی دارد؛ بنابراین پیشنهاد قطعی بدون مشخص شدن هدف می‌تواند گمراه‌کننده باشد.",
        "sources": ["ایران‌گاه", "دیاوری", "کیمیاگرخونه"],
        "evidence": "منابع نهایی بر کتاب درسی، سؤال‌های نهایی و تمرین تشریحی تأکید دارند و منابع کنکوری مسیر جداگانه‌ای دارند.",
    },
    "زبان انگلیسی": {
        "default": "مبتکران — جامع شهاب اناری (برای زبان تخصصی؛ با توجه به هدف بررسی شود)",
        "reason": "منابع ۱۴۰۵ بین زبان عمومی/سوابق و کنکور تخصصی زبان تفاوت گذاشته‌اند. برای کنکور تخصصی، مبتکران و خیلی‌سبز و قلم‌چی به‌عنوان منابع تخصصی مطرح شده‌اند؛ بنابراین ربات باید اول هدف آزمون را مشخص کند.",
        "alternatives": {
            "خیلی سبز": "برای زبان تخصصی و مسیر آموزشی/تستی گزینه قابل بررسی است.",
            "قلم‌چی": "کتاب آبی زبان تخصصی به‌عنوان منبع ساختاریافته و پیمانه‌ای معرفی شده است.",
            "IQ گاج": "برای زبان عمومی و تست، بسته به آزمون هدف گزینه قابل بررسی است.",
        },
        "not_default": "بدون دانستن اینکه کاربر در گروه اصلی‌اش زبان عمومی می‌خواهد یا کنکور منحصراً زبان، پیشنهاد یک کتاب واحد می‌تواند اشتباه باشد.",
        "sources": ["آکو (۳۰ تیر ۱۴۰۵)", "دانشچی (۱۴۰۵)", "ایران تحصیل (شهریور ۱۴۰۵)", "مشیرین"],
        "evidence": "منابع جدید تأکید می‌کنند انتخاب زبان باید بر اساس نوع آزمون، سطح، زمان و ضعف در واژگان/گرامر/درک مطلب باشد.",
    },
    "اقتصاد": {
        "default": "مهر و ماه — اقتصاد کنکور",
        "reason": "در منابع انسانی، مهر و ماه، خیلی‌سبز و میکرو گاج به‌عنوان گزینه‌های رایج مطرح شده‌اند. برای سؤال عمومی، مهر و ماه را صرفاً به‌عنوان نقطه شروع آموزشی/جمع‌بندی قرار می‌دهم.",
        "alternatives": {
            "خیلی سبز": "برای درسنامه و تست جامع گزینه قابل بررسی است.",
            "گاج میکرو": "برای بانک تست و طبقه‌بندی گزینه قابل بررسی است.",
            "مشاوران آموزش": "در بعضی فهرست‌های منابع انسانی، منابع تخصصی این انتشارات هم مطرح شده‌اند.",
        },
        "not_default": "منابع اقتصاد بسته به سطح و نیاز به آموزش یا تست تفاوت دارند؛ برای کاربر ضعیف باید آموزش در اولویت باشد.",
        "sources": ["مشیرین (منابع کنکور ۱۴۰۵)", "ایران‌گاه", "دکتر درس"],
        "evidence": "منابع انسانی چند ناشر را بسته به سطح و مرحله مطالعه پیشنهاد کرده‌اند و یک انتخاب مطلق ارائه نمی‌کنند.",
    },
    "فلسفه و منطق": {
        "default": "خیلی سبز — جامع",
        "reason": "برای سؤال عمومی فلسفه و منطق، منبع جامع گزینه عملی‌تری است؛ منابع انسانی، خیلی‌سبز و سفیر خرد را با کاربردهای متفاوت مطرح می‌کنند.",
        "alternatives": {
            "سفیر خرد": "برای کسی که آموزش عمیق‌تر و تخصصی‌تر می‌خواهد قابل بررسی است.",
            "گاج": "برای بانک تست و تمرین طبقه‌بندی‌شده گزینه دیگر است.",
            "مهر و ماه": "برای مرور و جمع‌بندی قابل بررسی است.",
        },
        "not_default": "اگر کاربر قوی باشد و فقط تست سخت بخواهد، منبع تکمیلی متفاوت می‌شود.",
        "sources": ["مشیرین", "ایران‌گاه", "منابع انسانی ۱۴۰۵"],
        "evidence": "در منابع انسانی، تفاوت منبع جامع با منبع تخصصی/سطح بالا مورد تأکید است.",
    },
    "هندسه": {
        "default": "خیلی سبز — جامع",
        "reason": "برای کاربر عمومی، منبع جامع که آموزش و تست را کنار هم داشته باشد نقطه شروع مناسبی است؛ برای سطح بالا، الگو و IQ می‌توانند نقش تکمیلی پیدا کنند.",
        "alternatives": {
            "مهر و ماه": "برای آموزش و تمرین مرحله‌ای گزینه قابل بررسی است.",
            "نشر الگو": "برای تست‌های چالشی‌تر و سطح بالاتر می‌تواند مکمل باشد.",
            "IQ گاج": "برای تمرین سطح بالاتر بعد از تثبیت پایه قابل بررسی است.",
        },
        "not_default": "هندسه به سطح حل مسئله وابستگی زیادی دارد؛ بنابراین پیشنهاد قطعی بدون دانستن سطح کاربر دقیق نیست.",
        "sources": ["ایران‌کتاب", "ایران‌گاه", "گروه آموزشی کهن"],
        "evidence": "فهرست‌های منابع، کتاب‌های جامع و تستی را در کنار منابع پیشرفته‌تر برای هندسه قرار داده‌اند.",
    },
}


RESOURCE_ALIASES_V62 = {
    "ریاضی": ["ریاضی", "ریاضی کنکور", "حسابان", "ریاضیات"],
    "فیزیک": ["فیزیک", "فیزیک کنکور"],
    "شیمی": ["شیمی", "شیمی کنکور"],
    "زیست": ["زیست", "زیست شناسی", "زیست‌شناسی"],
    "فارسی": ["فارسی", "ادبیات", "ادبیات فارسی", "زبان و ادبیات فارسی"],
    "عربی": ["عربی", "عربی کنکور", "عربی انسانی"],
    "دینی": ["دینی", "دین و زندگی", "دین زندگی"],
    "زبان انگلیسی": ["زبان", "زبان انگلیسی", "انگلیسی", "english"],
    "اقتصاد": ["اقتصاد", "اقتصاد انسانی"],
    "فلسفه و منطق": ["فلسفه", "منطق", "فلسفه و منطق"],
    "هندسه": ["هندسه", "هندسه کنکور"],
}

def _smart_resource_recommendation_v62(text: str):
    """پیشنهاد منبع بر اساس درس + هدف کاربر؛ با دلیل و گزینه‌های جایگزین."""
    n = _smart_normalize(text)
    if not n:
        return None
    resource_words = ("کتاب", "منبع", "انتشارات", "تست", "تشریحی", "کمک درسی", "کمک‌درسی", "درسنامه", "منابع")
    ask_words = ("چی خوبه", "چی بخرم", "چه کتابی", "کدوم کتاب", "کدوم منبع", "چه منبعی", "چی بخونم", "پیشنهاد", "معرفی", "مناسبه", "خوبه", "بهتره")
    if not (any(x in n for x in resource_words) or any(x in n for x in ask_words)):
        return None
    subject = None
    for key, aliases in RESOURCE_ALIASES_V62.items():
        if any(_smart_normalize(a) in n for a in aliases):
            subject = key
            break
    if not subject:
        return None
    info = RESOURCE_RECOMMENDATIONS_V62[subject]
    # هدف مشخص کاربر را در پاسخ وارد می‌کنیم تا پیشنهاد ثابت و کور نباشد.
    target = []
    if any(x in n for x in ("تشریحی", "نهایی", "امتحان مدرسه", "امتحان")):
        target.append("تشریحی/امتحان نهایی")
    if any(x in n for x in ("تست", "کنکور", "کنکوری")):
        target.append("تست/کنکور")
    level = None
    if any(x in n for x in ("ضعیف", "صفر", "مبتدی", "پایه ندارم")):
        level = "ضعیف"
    elif any(x in n for x in ("قوی", "سخت", "پیشرفته", "سطح بالا")):
        level = "قوی"
    suffix = ""
    if target:
        suffix += f" هدفی که از حرفت می‌فهمم: «{' و '.join(target)}»."
    if level:
        suffix += f" سطحی که گفتی: «{level}»."
    alternatives = " ".join(f"• {k}: {v}" for k, v in info["alternatives"].items())
    sources = "، ".join(info.get("sources", []))
    return (
        f"📚 برای {subject}: {info['default']}\n\n"
        f"چرا این را پیشنهاد می‌کنم؟ {info['reason']}{suffix}\n\n"
        f"🔎 جمع‌بندی تحقیق: {info.get('evidence', '')}\n\n"
        f"چرا گزینه‌های دیگر را نگفتم؟\n{info['not_default']}\n\n"
        f"گزینه‌های جایگزین:\n{alternatives}\n\n"
        f"🌐 منابع بررسی‌شده: {sources}.\n"
        "این پیشنهاد بر اساس مقایسه چند منبع آموزشی است، نه رأی یا تبلیغ یک ناشر؛ مشخصات چاپ و ویرایش را قبل از خرید با نسخه جدید همان سال تطبیق بده.\n\n"
        "اگر پایه/سطح، رشته، هدف (تست یا تشریحی) و مدت‌زمان باقی‌مانده را بگویی، پیشنهاد را دقیق‌تر می‌کنم."
    )


# V64: گسترده‌سازی مکالمه عادی و پرسش‌های روزمره.
# هدف: کاربر مجبور نباشد از عبارت دقیق یا کلیدواژه خاص استفاده کند.
SMART_EVERYDAY_QA_V64 = [
    ("hello_variants", ["سلام", "سلام ربات", "سلام داداش", "سلام دوست من", "سلام خوبی", "هی ربات", "های ربات", "صبح بخیر", "شب بخیر", "درود", "وقت بخیر"],
     ["سلام 😊 خوش اومدی! بگو ببینم امروز چه کمکی ازم می‌خوای؟", "سلام رفیق 🌱 اینجام؛ هرچی خواستی با خیال راحت بپرس."]),
    ("how_are_you_variants", ["خوبی", "خوبی ربات", "ربات خوبی", "حالت خوبه", "چه خبر", "چطوری", "اوضاعت چطوره", "خوب پیش میره", "همه چی خوبه"],
     ["ممنون که پرسیدی 😊 من خوبم و آماده‌ام کمکت کنم. خودت چطوری؟", "اینجام و آماده‌ام 😄 تو بگو حالت چطوره؟"]),
    ("thanks_variants", ["ممنون", "مرسی", "دمت گرم", "خیلی ممنون", "مرسی رفیق", "دستت درد نکنه", "لطف کردی", "خیلی کمکم کردی", "ممنون از کمکت", "تشکر"],
     ["خواهش می‌کنم 🌱 خوشحالم که به دردت خورد.", "قربانت 😊 هر وقت چیزی خواستی بپرس."]),
    ("apology_variants", ["ببخشید", "ببخش", "معذرت میخوام", "ببخش که پرسیدم", "شرمنده", "اشتباه کردم", "ببخشید ربات", "معذرت"],
     ["اشکالی نداره 😊 راحت باش.", "نه بابا، مشکلی نیست 🌱 ادامه بده."]),
    ("farewell_variants", ["فعلا", "فعلاً", "خداحافظ", "خدانگهدار", "بعدا میام", "بعدا میبینمت", "شب بخیر", "من برم", "دیگه برم", "تا بعد"],
     ["فعلاً رفیق 👋 هر وقت برگشتی من اینجام.", "خداحافظ 🌙 مراقب خودت باش."]),
    ("bored_variants", ["حوصلم سر رفته", "حوصله ندارم", "کسل شدم", "بی حوصله ام", "بیحوصله ام", "حوصله‌ام سر رفته", "نمیدونم چیکار کنم", "کلافه شدم"],
     ["اگه حوصله‌ات سر رفته، می‌تونیم یه بازی متنی، سؤال‌جواب یا یه موضوع جالب برای حرف زدن پیدا کنیم 😄", "می‌خوای یه موضوع جالب باز کنیم و یکم گپ بزنیم؟ 🌱"]),
    ("tired_variants", ["خسته ام", "خیلی خسته ام", "خسته شدم", "امروز خسته بودم", "انرژی ندارم", "جون ندارم", "خیلی کوفتم", "از خستگی مردم"],
     ["اگه خسته‌ای، یکم استراحت می‌تونه کمک‌کننده باشه 🌱 اگر هم خواستی می‌تونیم خیلی ساده گپ بزنیم.", "امروز به خودت یکم فرصت استراحت بده 😊"]),
    ("happy_variants", ["خوشحالم", "خیلی خوشحالم", "امروز خوبم", "حالم خوبه", "خیلی حس خوبی دارم", "امروز عالیه", "ذوق دارم", "خیلی راضی ام"],
     ["چه خوب 😊 امیدوارم همین حس خوب ادامه داشته باشه!", "عالیه 🌟 از شنیدنش خوشحال شدم."]),
    ("sad_variants", ["ناراحتم", "حالم بده", "حالم خوب نیست", "خیلی ناراحتم", "امروز حالم خوب نیست", "دلم گرفته", "حوصله ندارم حرف بزنم", "روز بدی بود"],
     ["متأسفم که حالت خوب نیست 🌱 اگر دوست داشتی می‌تونی درباره چیزی که اذیتت کرده حرف بزنی.", "لازم نیست همه‌چیز رو یک‌دفعه توضیح بدی؛ اگر خواستی از همون چیزی که بیشتر ذهنت رو درگیر کرده شروع کن."]),
    ("chat_start", ["بیا حرف بزنیم", "یکم حرف بزنیم", "یه کم گپ بزنیم", "حرف داری", "گپ بزنیم", "با من حرف بزن", "حوصله حرف زدن دارم", "یه موضوع بگو"],
     ["حتماً 😄 می‌تونیم درباره فیلم، موسیقی، بازی، دانشگاه، درس یا هر موضوع معمولی دیگه‌ای حرف بزنیم.", "حتماً 🌱 یه موضوع انتخاب کنیم و از همون شروع کنیم."]),
    ("question_permission", ["یه سوال دارم", "یه سؤال دارم", "میشه سوال بپرسم", "میتونم سوال بپرسم", "یه چیزی بپرسم", "یه سوال ازت بپرسم", "میخواستم یه چیزی بپرسم"],
     ["حتماً 😊 بپرس.", "آره حتماً، راحت باش و سؤالت رو بگو."]),
    ("repeat_explain", ["نفهمیدم", "متوجه نشدم", "دوباره بگو", "یه بار دیگه بگو", "ساده تر بگو", "ساده‌تر توضیح بده", "واضح تر توضیح بده", "یعنی چی دقیقا", "بیشتر توضیح بده", "جزئی تر بگو"],
     ["حتماً 😊 اگر بگی کدوم قسمت برات نامفهوم بود، همون بخش رو ساده‌تر و مرحله‌به‌مرحله توضیح می‌دم.", "حتماً؛ می‌تونم همون موضوع رو خیلی ساده‌تر و با مثال توضیح بدم."]),
    ("confirmation", ["درسته", "مطمئنی", "واقعا", "یعنی مطمئنی", "صد درصد", "اطمینان داری", "پس همینطوره", "درست فهمیدم"],
     ["اگر منظورت همون نکته قبلیه، بله؛ ولی اگر موضوع دقیق رو بگی می‌تونم همون مورد رو دقیق‌تر بررسی کنم.", "برای اطمینان بیشتر، خود سؤال یا موضوع دقیق رو بفرست تا روی همون مورد جواب بدم."]),
    ("confused", ["گیج شدم", "نمیدونم", "نمیفهمم", "اصلا نمیفهمم", "قاتی کردم", "سر در نمیارم", "برام گنگه", "نمیدونم چی کار کنم", "نمیدونم از کجا شروع کنم"],
     ["اشکالی نداره 🌱 از اول و خیلی ساده شروع می‌کنیم.", "نگران نباش؛ موضوع رو به چند قدم کوچیک تقسیم می‌کنیم تا واضح بشه."]),
    ("help_request", ["کمکم میکنی", "میشه کمکم کنی", "یه کمکی میخوام", "کمک لازم دارم", "میتونی کمکم کنی", "کمکم کن", "راهنماییم کن", "راهنمایی میخوام"],
     ["حتماً 😊 بگو دقیقاً در چه چیزی کمک می‌خوای.", "آره، بگو چه مشکلی داری تا مرحله‌به‌مرحله بررسیش کنیم."]),
    ("opinion_request", ["نظرت چیه", "به نظرت چطوره", "تو چی فکر میکنی", "نظر تو چیه", "تو نظرت چیه", "فکر میکنی خوبه", "به نظرت خوبه"],
     ["می‌تونم نظرم رو بر اساس اطلاعاتی که داریم بگم؛ فقط موضوع یا گزینه‌ها رو بفرست 😊", "حتماً؛ موضوع رو بگو تا نکات مثبت و منفی رو با هم بررسی کنیم."]),
    ("comparison_request", ["کدوم بهتره", "این بهتره یا اون", "مقایسه کن", "فرقشون چیه", "چه فرقی دارن", "کدومو انتخاب کنم", "بین این دوتا کدوم", "تفاوت اینا چیه"],
     ["حتماً. دو گزینه رو بفرست؛ تفاوت‌ها، مزایا و محدودیت‌های هرکدوم رو کنار هم می‌گم.", "بفرستشون 😊 می‌تونم مقایسه رو بر اساس قیمت، کیفیت، کاربرد یا هر معیار دیگه‌ای انجام بدم."]),
    ("thanks_after_help", ["خیلی خوب بود", "عالی توضیح دادی", "فهمیدم", "الان فهمیدم", "مشکلم حل شد", "درست شد", "جوابمو گرفتم", "خیلی کمک کرد"],
     ["عالیه 😊 خوشحالم که روشن شد.", "چه خوب 🌱 اگر دوباره چیزی خواستی، بپرس."]),
    ("waiting", ["صبر کن", "یه لحظه", "یکم صبر کن", "الان میام", "بعدا جواب میدم", "صبر داشته باش", "یه دقیقه"],
     ["باشه 😊 عجله‌ای نیست.", "حتماً، هر وقت آماده بودی ادامه می‌دیم."]),
    ("name_question", ["اسم منو میدونی", "اسمم چیه", "منو میشناسی", "منو میشناسی ربات", "من کیم"],
     ["اگر قبلاً اسمت رو در همین گفتگو/پروفایل ثبت کرده باشم می‌تونم از همون استفاده کنم؛ وگرنه خودت بگو دوست داری با چه اسمی صدات کنم. 😊"]),
    ("capabilities", ["چه کارایی بلدی", "چه کارهایی بلدی", "چه کمکی میتونی بکنی", "چه چیزایی بلدی", "چیکار میتونی بکنی", "چه قابلیت هایی داری", "قابلیت هات چیه", "چه کار میکنی"],
     ["می‌تونم درباره موضوعات مختلف جواب بدم، در درس و دانشگاه کمک کنم، درباره منابع کنکور راهنمایی کنم، متن و ترجمه آماده کنم و داخل گروه هم در بخش‌های مختلف کمکتون کنم 🤖."]),
    ("good_bad", ["خوبه", "خیلی خوبه", "بد نیست", "عالیه", "باحاله", "چه خوب", "بد شد", "خوب نیست", "افتضاحه", "بد بود"],
     ["آره 😊 اگر منظورت یک موضوع مشخصه، بگو تا دقیق‌تر درباره همون صحبت کنیم.", "می‌فهمم 😄 اگر دوست داری بگو چه چیزی مدنظرت بوده."]),
    ("short_ack", ["اوکی", "باشه", "باش", "آها", "اوهو", "هوم", "خب", "اوکیه", "قبوله", "درسته خب"],
     ["باشه 😊", "حتماً 🌱", "آره، متوجه شدم."]),
    ("what_doing", ["چیکار میکنی", "داری چیکار میکنی", "مشغولی", "الان کجایی", "چه خبر ازت", "مشغول چی هستی"],
     ["فعلاً مشغول جواب دادن به توام 😄 بگو ببینم چی توی ذهنت هست."]),
    ("food_chat", ["گرسنمه", "گرسنه ام", "چی بخورم", "حوصله غذا ندارم", "شام چی بخوریم", "ناهار چی بخورم", "غذا چی درست کنم"],
     ["اگر چندتا چیز که دم دستت هست رو بگی، می‌تونم چند پیشنهاد ساده بدم 🍽️.", "بستگی داره چی دوست داشته باشی و چه چیزهایی داشته باشی؛ مواد اولیه رو بگو تا پیشنهاد بدم."]),
    ("sleep_chat", ["خوابم میاد", "خیلی خوابم میاد", "خوابم نمیبره", "نمیتونم بخوابم", "باید بخوابم", "شب شده", "صبح زوده"],
     ["اگر خوابت میاد، شاید یکم استراحت برات بهتر باشه 🌙.", "اگر منظورت مشکل خوابیدنه، می‌تونی بگی دقیقاً چه مشکلی داری تا چند راهکار عمومی بگم."]),
    ("weather_generic", ["هوا چطوره", "هوا خوبه", "هوا چجوریه", "امروز هوا چطوره", "امروز هوا خوبه", "هوا چه خبره"],
     ["اگر شهر رو بگی، می‌تونم درباره هوای همونجا راهنمایی دقیق‌تری بدم 🌤️."]),
    ("music_chat", ["موسیقی دوست داری", "چه آهنگی خوبه", "آهنگ معرفی کن", "چی گوش بدم", "یه آهنگ خوب بگو", "خواننده معرفی کن", "موزیک چی گوش بدم"],
     ["حتماً 🎵 اگر بگی چه سبکی دوست داری، مثلاً پاپ، راک، رپ، سنتی یا K-pop، پیشنهادها دقیق‌تر می‌شن."]),
    ("movie_chat", ["فیلم چی ببینم", "سریال چی ببینم", "یه فیلم خوب بگو", "فیلم معرفی کن", "سریال معرفی کن", "چی نگاه کنم", "حوصله فیلم دارم"],
     ["حتماً 🎬 ژانرت رو بگو؛ مثلاً علمی‌تخیلی، فانتزی، معمایی، اکشن، کمدی یا درام."]),
    ("game_chat", ["بازی کنیم", "یه بازی بریم", "حوصله بازی دارم", "بازی بلدی", "چه بازی هایی داری", "یه بازی پیشنهاد بده", "بریم بازی"],
     ["حتماً 🎮 داخل ربات چند بازی گروهی داریم؛ از بخش بازی‌ها می‌تونی انتخاب کنی."]),
    ("thanks_emoji", ["❤️", "❤", "🙏", "😊", "😂", "😄", "🌹", "دمت گرم ❤️", "مرسی ❤️"],
     ["😊❤️", "قربانت 🌱"]),
    ("direct_address", ["ربات", "هی ربات", "ربات جان", "ربات عزیز", "دستیار", "دستیار جان"],
     ["جانم؟ 😊 بگو ببینم چی لازم داری.", "در خدمتم 🌱 بگو چه کمکی می‌خوای."]),
]


def _smart_everyday_answer_v64(text: str):
    """Match broad everyday Persian conversation before the older, narrower banks."""
    try:
        return _smart_v61_best_answer(text, SMART_EVERYDAY_QA_V64)
    except Exception:
        return None


# ============================================================
# V66 — تشخیص معنایی‌تر جمله‌های محاوره‌ای
# هدف: یک مفهوم واحد با جمله‌بندی، ترتیب واژه‌ها و غلط‌های رایج متفاوت
# همچنان به همان intent هدایت شود. این بخش بدون سرویس خارجی کار می‌کند.
# ============================================================
SMART_V66_ALIASES = {
    "میخواهم":"میخوام", "میخوام":"میخوام", "میخواستم":"میخواستم",
    "می توانم":"میتونم", "میتوانم":"میتونم", "میتونی":"میتونی", "میتوانی":"میتونی",
    "میشود":"میشه", "می شود":"میشه", "میشه":"میشه",
    "نمیدانم":"نمیدونم", "نمی دانم":"نمیدونم", "نمیدونم":"نمیدونم",
    "چگونه":"چطور", "چجوری":"چطور", "چجور":"چطور", "چطوری":"چطور",
    "درباره":"راجع", "درمورد":"راجع", "راجب":"راجع", "راجع به":"راجع",
    "برای":"برا", "واسه":"برا", "میخواهم":"میخوام", "می خوام":"میخوام",
    "سوال":"سوال", "سؤال":"سوال", "مسئله":"سوال",
    "دانشگاه":"دانشگاه", "دانشگا":"دانشگاه", "کنکورر":"کنکور", "کنکوررر":"کنکور",
    "ثبتنام":"ثبت نام", "ثبت‌نام":"ثبت نام", "انتخابرشته":"انتخاب رشته",
}

def _smart_v66_normalize(text: str) -> str:
    n = _smart_normalize(text)
    for a, b in SMART_V66_ALIASES.items():
        n = n.replace(_smart_normalize(a), _smart_normalize(b))
    # حذف کلمات پرکننده‌ای که در معنای سؤال نقش کمی دارند.
    n = re.sub(r'\b(لطفا|لطفاً|خواهشا|خواهشاً|خب|آخه|یعنی|مثلا|مثلاً|راستی|یه|یک|هم|دیگه)\b', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()

SMART_V66_EVERYDAY_INTENTS = [
    ("greeting", ["سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر"],
     ["سلام 😊 خوش اومدی! بگو ببینم چه کاری از دستم برمیاد؟", "سلام رفیق 🌱 بگو، گوشم با توئه."]),
    ("thanks", ["ممنون", "مرسی", "دمت گرم", "دستت درد نکنه", "لطف کردی", "تشکر"],
     ["خواهش می‌کنم 😊 خوشحالم که کمکت کردم.", "قربانت 🌱 هر وقت خواستی دوباره بپرس."]),
    ("confusion", ["نفهمیدم", "متوجه نشدم", "گنگه", "برام واضح نیست", "دوباره بگو", "ساده تر بگو", "بیشتر توضیح بده"],
     ["حتماً؛ ساده‌تر و مرحله‌به‌مرحله توضیحش می‌دم. فقط همون موضوع رو بگو تا از اول بازش کنم."]),
    ("opinion", ["نظرت چیه", "چه نظری داری", "به نظرت", "تو چی فکر میکنی", "کدوم بهتره"],
     ["حتماً. موضوع یا گزینه‌هایی که بینشان مرددی را بگو تا مزایا و معایب هرکدام را با هم مقایسه کنیم."]),
    ("help", ["کمکم کن", "کمک لازم دارم", "راهنمایی میخوام", "میشه راهنماییم کنی", "نمیدونم چیکار کنم"],
     ["حتماً 🌱 بگو دقیقاً در چه چیزی گیر کردی؛ سعی می‌کنم قدم‌به‌قدم پیش بریم."]),
    ("question", ["یه سوال دارم", "یه چیزی بپرسم", "میتونم بپرسم", "سوال بپرسم"],
     ["حتماً 😊 سؤالت رو بپرس."]),
    ("chat", ["حرف بزنیم", "گپ بزنیم", "یکم صحبت کنیم", "حوصله حرف زدن دارم"],
     ["حتماً 😄 درباره هر موضوع معمولی که دوست داری می‌تونیم گپ بزنیم؛ موسیقی، فیلم، بازی، درس یا دانشگاه."]),
    ("unknown", ["چی کار کنم", "از کجا شروع کنم", "گیر کردم", "نمیدونم از کجا شروع کنم"],
     ["اشکالی نداره؛ اول بگو موضوعت چیه و الان دقیقاً کجاش برات سخت شده تا قدم اول رو با هم مشخص کنیم."]),
]

def _smart_v66_token_score(text: str, phrase: str) -> float:
    n, p = _smart_v66_normalize(text), _smart_v66_normalize(phrase)
    if not n or not p: return 0.0
    if n == p or p in n: return 1.0
    nt, pt = set(n.split()), set(p.split())
    if not pt: return 0.0
    overlap = len(nt & pt) / len(pt)
    # بخشی از سؤال که بعد از حذف کلمات پرکننده باقی می‌ماند باید معنا را حمل کند.
    containment = len(nt & pt) / max(1, len(nt))
    return 0.72 * overlap + 0.28 * containment

def _smart_v66_everyday_match(text: str):
    best = (0.0, None)
    for _, phrases, answers in SMART_V66_EVERYDAY_INTENTS:
        for phrase in phrases:
            score = _smart_v66_token_score(text, phrase)
            if score > best[0]:
                best = (score, answers)
    return random.choice(best[1]) if best[1] and best[0] >= 0.68 else None

def _smart_v66_domain_rephrase(text: str):
    """تشخیص سؤال‌های بازنویسی‌شده درباره کنکور/درس/منابع بدون وابستگی به عبارت دقیق."""
    n = _smart_v66_normalize(text)
    if not n: return None
    study = any(x in n for x in ("ریاضی","فیزیک","شیمی","زیست","فارسی","عربی","دینی","زبان","هندسه","گسسته","اقتصاد","فلسفه","منطق"))
    exam = any(x in n for x in ("کنکور","آزمون سراسری","سوابق تحصیلی","امتحان نهایی","انتخاب رشته","رتبه","تراز","سهمیه"))
    resource = any(x in n for x in ("کتاب","منبع","انتشارات","تست","تشریحی","درسنامه","بخرم","بخونم","منابع"))
    if study and resource:
        # موتور منابع موجود، پس از نرمال‌سازی گسترده دوباره امتحان می‌شود.
        ans = _smart_resource_recommendation_v62(n)
        if ans: return ans
    if exam:
        ans = _smart_v58_domain_answer(n)
        if ans: return ans
    return None

SMART_NORMAL_VARIANTS_V67 = [
    ("ask_simple", ["یه سوال", "یک سوال", "یه چیزی بپرسم", "یه چیز بپرسم", "میشه بپرسم", "می تونم بپرسم", "میتونم بپرسم"], [
        "حتماً، بپرس 😊", "آره، بگو ببینم چی می‌خوای بدونی 🌱", "حتماً رفیق، سوالت رو بگو."
    ]),
    ("explain_more", ["نفهمیدم", "متوجه نشدم", "درک نکردم", "گنگه", "ساده تر بگو", "سادهتر بگو", "دوباره توضیح بده", "بیشتر توضیح بده", "یه جور دیگه بگو", "واضح تر بگو"], [
        "حتماً؛ ساده‌ترش می‌کنم و مرحله‌به‌مرحله توضیح می‌دم. 🌱", "باشه، از یه زاویه ساده‌تر توضیحش می‌دم تا راحت‌تر جا بیفته."
    ]),
    ("thanks", ["ممنون", "مرسی", "دمت گرم", "خیلی ممنون", "متشکرم", "مرسی رفیق", "دستت درد نکنه"], [
        "خواهش می‌کنم 😊", "قربانت، خوشحالم که به کارت اومد 🌿", "خواهش می‌کنم رفیق ✨"
    ]),
    ("agreement", ["باشه", "اوکی", "اوکیه", "قبوله", "درسته", "آره دقیقا", "دقیقاً"], [
        "باشه 😊", "آره، پس بریم سراغش.", "اوکیه 👍"
    ]),
    ("confused", ["نمیدونم", "نمی دونم", "نمی‌دونم", "گیج شدم", "نمیدونم چیکار کنم", "نمی دونم چیکار کنم"], [
        "اشکالی نداره؛ از قدم اول شروع کنیم. بگو موضوعت چیه تا با هم مرتبش کنیم. 🌱", "طبیعیه؛ لازم نیست از اول همه‌چیز رو بدونی. موضوع رو بگو تا قدم‌به‌قدم پیش بریم."
    ]),
    ("casual_chat", ["چیکار میکنی", "چکار میکنی", "چه خبر", "خب چه خبر", "چطوری", "خوبی", "حالت چطوره", "چه کارا میکنی"], [
        "اینجام و آماده‌ام کمک کنم 😊 تو چه خبر؟", "خوبم رفیق 😄 بگو ببینم امروز درباره چی حرف بزنیم؟"
    ]),
    ("direct_help", ["کمکم کن", "کمک میخوام", "راهنماییم کن", "یه کمکی میخوام", "میشه کمکم کنی"], [
        "حتماً 🌱 موضوعت رو بگو تا با هم قدم‌به‌قدم حلش کنیم.", "آره، بگو دقیقاً توی چی کمک می‌خوای."
    ]),
]

def _smart_v67_everyday_answer(text):
    n=_smart_normalize(text)
    if not n: return None
    for _, phrases, answers in SMART_NORMAL_VARIANTS_V67:
        if any(_smart_normalize(p) in n for p in phrases):
            return random.choice(answers)
    return None

def _smart_common_answer(text: str):
    # V67: مکالمه‌های معمولیِ بازنویسی‌شده را قبل از بانک‌های تخصصی بررسی کن.
    everyday_v67 = _smart_v67_everyday_answer(text)
    if everyday_v67:
        return everyday_v67
    # V66: ابتدا بازنویسی معناییِ جمله‌های عادی و سپس حوزه‌های درس/کنکور.
    v66 = _smart_v66_everyday_match(text)
    if v66:
        return v66
    v66_domain = _smart_v66_domain_rephrase(text)
    if v66_domain:
        return v66_domain
    n = _smart_v61_normalize(text)
    # V64: مکالمه روزمره و جمله‌های محاوره‌ای قبل از بانک‌های قدیمی.
    everyday_answer = _smart_everyday_answer_v64(text)
    if everyday_answer:
        return everyday_answer
    if not n:
        return None
    # V62: سؤال منبع درسی قبل از بانک‌های عمومی تا پاسخ دقیق و همراه با دلیل بدهد.
    resource_answer = _smart_resource_recommendation_v62(text)
    if resource_answer:
        return resource_answer
    # V61: تشخیص محاوره‌ای و تغییر ترتیب کلمات قبل از بانک‌های قبلی.
    music_answer = _smart_music_answer_v60(text)
    if music_answer:
        return music_answer
    fuzzy = _smart_v61_best_answer(text, [
        *SMART_CONVERSATION_INTENTS_V59,
        *STUDY_BOOK_QA_V59,
        *SMART_GENERAL_QA_V59,
        *SMART_CONVERSATION_INTENTS_V58,
        *KONKOUR_UNIVERSITY_QA_V58,
    ])
    if fuzzy:
        return fuzzy
    # V59: بانک مکالمه گسترده‌تر، سپس کتاب‌های کمک‌درسی، کنکور/دانشگاه و بانک عمومی.
    for _, phrases, answers in SMART_CONVERSATION_INTENTS_V59:
        if any(_smart_normalize(p) in n for p in phrases):
            return random.choice(answers)
    for _, phrases, answer in STUDY_BOOK_QA_V59:
        if any(_smart_normalize(p) in n for p in phrases):
            return answer
    for _, phrases, answer in SMART_GENERAL_QA_V59:
        if any(_smart_normalize(p) in n for p in phrases):
            return answer
    for _, phrases, answers in SMART_CONVERSATION_INTENTS_V58:
        if any(_smart_normalize(p) in n for p in phrases):
            return random.choice(answers)
    for _, phrases, answer in KONKOUR_UNIVERSITY_QA_V58:
        if any(_smart_normalize(p) in n for p in phrases):
            return answer
    conv = _smart_v57_conversation_match(text)
    if conv and conv[0] >= 100:
        return random.choice(conv[2])
    for _, phrases, answer in SMART_COMMON_QA:
        if any(_smart_normalize(p) in n for p in phrases):
            return answer
    return None

def _smart_is_question_or_request(text: str) -> bool:
    n = _smart_normalize(text)
    if not n:
        return False
    words = set(n.split())
    if words.intersection(set(_QUESTION_WORDS)):
        return True
    return any(x in n for x in ("میشه", "میتونی", "میتوانی", "کمک کن", "بگو", "توضیح بده", "راهنمایی کن", "انجام بده", "میخوام بدونم"))

def _smart_v58_domain_answer(text: str):
    """Match common natural-language variants without requiring exact canned sentences."""
    n = _smart_normalize(text)
    if not n:
        return None
    # Normalize common colloquial spellings and route to the relevant knowledge bank.
    replacements = {
        "کنکوری": "کنکور", "کنکورر": "کنکور", "کنکوررر": "کنکور",
        "دانشگا": "دانشگاه", "دانشگام": "دانشگاه", "دانشگاهی": "دانشگاه",
        "ثبتنام": "ثبت نام", "ثبت‌نام": "ثبت نام", "انتخاب‌رشته": "انتخاب رشته",
        "معدلم": "معدل", "نمرات نهایی": "معدل", "نمره نهایی": "معدل",
    }
    for a,b in replacements.items():
        n=n.replace(a,b)
    if any(k in n for k in ("کنکور", "آزمون سراسری", "دانشگاه", "سوابق تحصیلی", "ترمیم معدل", "انتخاب رشته", "رتبه کنکور")):
        # Retry the detailed bank after normalization.
        for _, phrases, answer in KONKOUR_UNIVERSITY_QA_V58:
            if any(_smart_normalize(p) in n for p in phrases):
                return answer
        if "کنکور" in n and any(k in n for k in ("زمان", "تاریخ", "کی", "چه روز", "برگزار")):
            return "اگر منظورت کنکور ۱۴۰۵ است، تاریخ اعلام‌شده ۱۱ و ۱۲ تیر ۱۴۰۵ بود. اگر منظورت سال دیگری است، سال را بگو چون تقویم هر سال جداگانه اعلام می‌شود."
        if "معدل" in n or "سوابق" in n or "نهایی" in n:
            return "اثر سوابق تحصیلی به سال پذیرش و گروه آزمایشی بستگی دارد و باید طبق مصوبه و دفترچه همان سال بررسی شود. اگر سال کنکور را بگویی، دقیق‌تر پاسخ می‌دهم."
        if "دانشگاه" in n and any(k in n for k in ("چطور", "چجوری", "چطوری", "چطور", "قبول", "ورود")):
            return "برای ورود به دانشگاه مسیرهای مختلفی وجود دارد؛ کنکور، پذیرش بر اساس سوابق تحصیلی و بعضی مسیرهای اختصاصی. شرایط هر مسیر به سال و نوع دانشگاه بستگی دارد."
    return None

def _smart_general_fallback(text: str, name: str):
    answer = _smart_common_answer(text)
    if answer:
        return answer
    answer = _smart_v58_domain_answer(text)
    if answer:
        return answer
    if _smart_is_question_or_request(text):
        return random.choice([
            f"حتماً {name} 🌿 سوالت رو دیدم. اگر منظورت مشخصه، همون موضوع رو بگو تا مستقیم جواب بدم؛ اگر هم پیچیده باشه، مرحله‌به‌مرحله با هم بازش می‌کنیم.",
            f"بله {name} 😊 بپرس. اگر پاسخ دقیقش رو داشته باشم مستقیم می‌گم؛ اگر اطلاعات بیشتری لازم باشه، فقط همون بخش لازم رو ازت می‌پرسم.",
            f"در خدمتم {name} 🌱 سؤال رو کامل بفرست؛ لازم نیست از عبارت‌های خاص استفاده کنی، با زبان معمولی هم می‌تونی صحبت کنی.",
        ])
    return random.choice([
        f"آره {name} 😊 اینجام. بگو دوست داری درباره چی صحبت کنیم؟",
        f"در خدمتم {name} 🌿 هر چیزی خواستی بگو؛ اگر بلد باشم مستقیم جواب می‌دم و اگر نباشه صادقانه می‌گم.",
    ])

async def handle_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user = update.effective_user
    chat = update.effective_chat

    if user.is_bot:
        return

    # پاسخ خصوصی جرأت/حقیقت: محتوا فقط موقتاً برای همین نوبت بررسی می‌شود.
    # متن پاسخ نه در JSON و نه در SQLite ذخیره نمی‌شود؛ پس از بررسی، پیام کاربر و پیام تکلیف پاک می‌شوند.
    if chat.type == "private":
        task_key, task = td_find_private_task(user.id)
        if task:
            game_guard = TD_GAMES.get(task.get("chat_id"))
            current_guard = td_current_player(game_guard) if game_guard else None
            if (not game_guard or not game_guard.get("started") or not current_guard or
                    current_guard.get("id") != user.id or
                    task.get("turn_index") != int(game_guard.get("turn_index", -1)) or
                    task.get("round") != int(game_guard.get("round", -1))):
                TD_PRIVATE_TASKS.pop(task_key, None)
                try:
                    await td_delete_private_message(context.bot, user.id, update.message.message_id)
                except Exception:
                    pass
                return
            if not await td_claim_processing(task):
                await td_delete_private_message(context.bot, user.id, update.message.message_id)
                return
            created = task.get("created", 0)
            if datetime.now().timestamp() - created > TD_TASK_TIMEOUT_MINUTES * 60:
                TD_PRIVATE_TASKS.pop(task_key, None)
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=update.message.message_id)
                except TelegramError:
                    pass
                await update.message.reply_text("⌛ این نوبت منقضی شده؛ اگر بازی هنوز ادامه دارد، نوبت جدیدت را انتخاب کن.")
                await td_release_processing(task)
                return

            answer = update.message.text or ""
            task["attempts"] = int(task.get("attempts", 0)) + 1
            task["answer_message_id"] = update.message.message_id
            if task.get("kind") == "truth":
                valid, reason = td_validate_truth(task.get("task", ""), answer)
            else:
                valid, reason = td_validate_dare(task.get("task", ""), answer)

            # پاسخ کاربر را حتی در حالت نامعتبر هم بعد از بررسی نگه نمی‌داریم.
            delete_ok = await td_delete_private_message(context.bot, user.id, update.message.message_id)

            if not valid:
                if task.get("feedback_message_id"):
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=task["feedback_message_id"])
                    except TelegramError:
                        pass
                if task.get("attempts", 0) >= TD_MAX_VALIDATION_ATTEMPTS:
                    task_key = task_key
                    target_chat = task.get("chat_id")
                    TD_PRIVATE_TASKS.pop(task_key, None)
                    game = TD_GAMES.get(target_chat)
                    if game:
                        game["active_task"] = None
                        td_add_failed_turn(game, user.id)
                    await update.message.reply_text("🛑 این نوبت بعد از چند پاسخ نامعتبر بسته شد. پیام پاسخ برای حذف به Telegram سپرده شد؛ متن پاسخ ذخیره نشد و نوبت بازی به بازیکن بعدی می‌رسد.")
                    if game and game.get("started"):
                        td_advance(game)
                        await td_announce_turn(context.bot, game, context)
                    return
                feedback = await update.message.reply_text(
                    f"⚠️ این پاسخ هنوز قابل تأیید نیست.\n\n{reason}\n\n"
                    "پاسخ قبلی نگه‌داری نشد. دوباره فقط نتیجه‌ی همین چالش را بفرست."
                )
                task["feedback_message_id"] = feedback.message_id
                task["answer_message_id"] = None
                return

            task["verified"] = True
            target_chat = task.get("chat_id")
            kind = task.get("kind")
            game = TD_GAMES.get(target_chat)
            current = td_current_player(game) if game else None
            if not game or not game.get("started") or not current or current.get("id") != user.id:
                TD_PRIVATE_TASKS.pop(task_key, None)
                await update.message.reply_text("⚠️ بازی یا نوبت دیگر فعال نیست؛ این پاسخ وارد بازی نشد و ذخیره هم نشد.")
                return

            # پیام تکلیف ربات نیز پس از تأیید پاک می‌شود.
            task_message_id = task.get("task_message_id")
            if task_message_id:
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=task_message_id)
                except TelegramError as e:
                    logger.warning("TD private task deletion failed for %s: %s", user.id, e)
            feedback_message_id = task.get("feedback_message_id")
            if feedback_message_id:
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=feedback_message_id)
                except TelegramError:
                    pass

            points = td_add_score(game, user.id, kind, task.get("attempts", 0))
            TD_PRIVATE_TASKS.pop(task_key, None)
            game["active_task"] = None
            name = td_clean_name(current.get("name"))
            label = "حقیقت" if kind == "truth" else "جرأت"
            delete_line = (
                "🧹 پیام پاسخ با موفقیت از چت Private حذف شد." if delete_ok
                else "⚠️ Telegram حذف پیام را تأیید نکرد؛ ربات پاسخ را ذخیره نکرد و دیگر به آن دسترسی ندارد."
            )
            await context.bot.send_message(
                target_chat,
                f"✅ <b>{name}</b> نوبت {label} را با موفقیت انجام داد. <b>+{points}⭐</b>\n"
                "🔒 پاسخ/جزئیات پاسخ در گروه گفته نمی‌شود.\n"
                f"{delete_line}\n🚫 متن پاسخ برای استفاده‌ی بعدی ذخیره نشد.",
                parse_mode="HTML",
            )
            await td_send_media(context.bot, target_chat, "success")
            td_advance(game)
            await td_announce_turn(context.bot, game, context)
            return

    # --- اولویت اول: آیا این ادمین الان توی «حالت افزودن کلمه نامناسب»ه؟ ---
    # این چک قبل از هر پردازش دیگه‌ای انجام می‌شه تا با فیلتر ناسزا یا ترجمه تداخل نکنه،
    # چون خودِ کلمه‌ی جدید ممکنه یه ناسزا باشه و نباید به‌عنوان پیام عادی پردازش بشه.
    pending_key = f"{chat.id}:{user.id}"
    pending_chat = pending_badword_add.get(pending_key)
    if pending_chat is not None and pending_chat == chat.id:
        word = text.strip().lower()
        del pending_badword_add[pending_key]
        if not word:
            await update.message.reply_text("⚠️ متن خالی بود، دوباره از پنل مدیریت امتحان کن.")
            return
        await add_custom_bad_word(chat.id, word)
        await update.message.reply_text(
            f"✅ کلمه «{word}» به لیست الفاظ نامناسب این گروه اضافه شد.\n"
            f"از این به بعد اگه کسی این کلمه رو بگه، بهش اخطار داده می‌شه."
        )
        return

    # --- ضد اسپم (flood control) ---
    # اعضای عادی در صورت Flood محدود می‌شوند؛ ادمین‌ها محدود/میوت نمی‌شوند و فقط اخطار می‌گیرند.
    # این رفتار عمداً جدا از فیلتر ناسزا است تا قانون «ادمین اسپم کرد = فقط اخطار» حفظ شود.
    admin_user = await is_admin(update, context)
    now = time.time()
    times = user_message_times[f"{chat.id}:{user.id}"]
    times.append(now)
    if len(times) == FLOOD_LIMIT and (now - times[0]) < FLOOD_WINDOW:
        if admin_user:
            last = admin_spam_last_warn.get(f"{chat.id}:{user.id}", 0)
            if now - last >= ADMIN_SPAM_WARN_COOLDOWN:
                admin_spam_last_warn[f"{chat.id}:{user.id}"] = now
                await apply_warn(update, context, user, reason="اسپم و ارسال پیام‌های پی‌درپی توسط ادمین", exempt_auto_action=True)
            return
        try:
            until = datetime.now() + timedelta(minutes=5)
            await context.bot.restrict_chat_member(
                chat.id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await update.message.reply_text(
                f"🚫 {user.first_name} به دلیل ارسال پیام زیاد و پشت‌سرهم، ۵ دقیقه سکوت شد."
            )
        except TelegramError as e:
            logger.warning(f"خطای ضد اسپم: {e}")
        return

    # --- فیلتر ناسزا (شامل کلمات پیش‌فرض + کلمات سفارشی همین گروه) ---
    if contains_bad_word(text, chat_id=chat.id):
        mention = mention_html(user)
        try:
            await update.message.reply_text(
                f"⚠️ {mention} لطفاً از الفاظ نامناسب استفاده نکن. این پیام گزارش شد.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"خطای اخطار: {e}")

        try:
            admins = await context.bot.get_chat_administrators(chat.id)
            admin_mentions = [mention_html(a.user) for a in admins if not a.user.is_bot]
            if admin_mentions:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"🚨 توجه ادمین‌ها {' '.join(admin_mentions)}:\nکاربر {mention} از الفاظ نامناسب استفاده کرد.",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.warning(f"خطای اطلاع به ادمین: {e}")

        await apply_warn(update, context, user, reason="استفاده از الفاظ نامناسب")
        return

    # --- Gemini AI مستقل (v71) ---
    # فقط وقتی کاربر/گروه Gemini را روشن کرده باشد وارد این مسیر می‌شویم.
    # در حالت خاموش، هیچ درخواست شبکه‌ای به Gemini ارسال نمی‌شود و منطق قبلی دست‌نخورده می‌ماند.
    if gemini_enabled(chat.id) and not gemini_blocked_by_game(chat):
        handled_by_gemini = await gemini_answer_message(update, context)
        if handled_by_gemini:
            _remember_user_turn(chat.id, user.id, text, "[gemini]", "gemini")
            return

    # --- Smart Assistant عادی و همیشه آماده است ---
    # v55: احوالپرسی و خطاب مستقیم به ربات مسیر سریع و مستقل دارند؛
    # بنابراین امتیازدهی intent یا ترتیب کلمات نمی‌تواند پاسخ را بی‌دلیل متوقف کند.
    is_reply_to_bot = bool(
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )
    norm_for_trigger = _smart_normalize(text)
    fast_social = _smart_social_fast_key(text)
    addressed_to_bot = "ربات" in set(norm_for_trigger.split()) or "دستیار" in set(norm_for_trigger.split())

    if owner_feature_enabled("assistant") and fast_social:
        await update.message.reply_text(random.choice(SMART_FAST_SOCIAL_REPLIES[fast_social]))
        # پاسخ سریع عمداً بدون عبور از مسیر سنگین intent انجام می‌شود.
        _remember_user_turn(chat.id, user.id, text, "[smart-social]", "social")
        return

    # پیام‌هایی که صریحاً ربات را خطاب می‌کنند همیشه باید حداقل یک پاسخ داشته باشند.
    # اگر intent دقیق پیدا نشد، fallback دوستانه می‌دهیم تا ربات «گیر کرده» به نظر نرسد.
    direct_match = _best_intent_match(norm_for_trigger)
    # v57: مکالمه‌ی طبیعی فقط به خطاب «ربات» وابسته نیست.
    # پیام اجتماعی شناخته‌شده، سؤال روشن، یا ادامه‌ی گفت‌وگوی همین کاربر وارد Smart می‌شود؛
    # چت کاملاً بی‌ربط و بدون نشانه‌ی سؤال همچنان نادیده گرفته می‌شود.
    social_message = _smart_is_social_message(text)
    should_process_smart = is_reply_to_bot or addressed_to_bot or direct_match is not None or social_message
    if should_process_smart and owner_feature_enabled("assistant"):
        key = _memory_key(chat.id, user.id)
        now_ctx = time.time()
        history = conversation_context.get(key, [])
        history = [item for item in history if now_ctx - item[0] <= CONVERSATION_TTL][-CONVERSATION_MAX:]
        rich_memory = _get_user_memory(chat.id, user.id)

        explicit_topic = _extract_topic(text)
        current_topic = _current_topic(chat.id, user.id)
        effective_text = text
        requested_old_topic = _find_topic_in_memory(chat.id, user.id, text) if _is_topic_switch_request(text) else None
        if requested_old_topic:
            explicit_topic = requested_old_topic
        if explicit_topic:
            _remember_topic(chat.id, user.id, explicit_topic, text)
            current_topic = explicit_topic
        elif _is_followup_message(text) and current_topic:
            n_text = _smart_normalize(text)
            if any(x in n_text for x in ("همون قبلی", "قبلی", "موضوع قبلی", "برگردیم")) and _previous_topic(chat.id, user.id):
                current_topic = _previous_topic(chat.id, user.id)
            topic_phrase = _topic_context_phrase(chat.id, user.id, current_topic)
            if topic_phrase:
                effective_text = f"{topic_phrase} {text}"
        elif rich_memory and _is_followup_message(text):
            last_topic = _last_user_context_phrase(chat.id, user.id)
            if last_topic:
                effective_text = f"{last_topic} {text}"
        elif history and len(_smart_normalize(text).split()) <= 4 and _is_followup_message(text):
            last_topic = history[-1][1]
            if last_topic:
                effective_text = f"{last_topic} {text}"

        reply = await smart_rule_based_reply(
            effective_text, user.first_name or "دوست عزیز", context, chat, username=user.username, user_id=user.id
        )

        if not reply and (addressed_to_bot or social_message or is_reply_to_bot):
            reply = random.choice([
                f"بله {user.first_name or 'دوست'} 😊 اینجام؛ لازم نیست جمله‌ات رو خاص بنویسی، معمولی بگو چه چیزی می‌خوای.",
                "آره، حواسم هست 🌿 موضوعت رو با همون زبان خودت بگو تا از همون‌جا ادامه بدیم.",
                "در خدمتم ✨ اگر سؤال یا درخواستی داری مستقیم بنویس؛ اگر چیزی مبهم باشه فقط همون بخش رو می‌پرسم.",
            ])

        if reply:
            await update.message.reply_text(reply)
            topic_tokens = _smart_normalize(effective_text).split()[:10]
            topic = _extract_topic(effective_text) or current_topic or " ".join(topic_tokens) or "general"
            history.append((now_ctx, topic))
            _remember_topic(chat.id, user.id, topic, effective_text)
            conversation_context[key] = history[-CONVERSATION_MAX:]
            _remember_user_turn(chat.id, user.id, text, reply, topic)
        elif history:
            conversation_context[key] = history
        return

# ============================================================
# گزارش به ادمین‌ها (/report روی یه پیام)
# ============================================================
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("روی پیامی که می‌خوای گزارش بدی ریپلای بزن و بنویس /report")
        return
    reporter = update.effective_user
    reported_msg = update.message.reply_to_message
    chat = update.effective_chat
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_mentions = [mention_html(a.user) for a in admins if not a.user.is_bot]
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                f"🚨 گزارش جدید از طرف {mention_html(reporter)}:\n"
                f"پیام گزارش‌شده از: {mention_html(reported_msg.from_user)}\n\n"
                f"{' '.join(admin_mentions)}"
            ),
            parse_mode="HTML",
            reply_to_message_id=reported_msg.message_id,
        )
        await update.message.reply_text("✅ گزارش به ادمین‌ها ارسال شد.")
    except Exception as e:
        logger.warning(f"خطای گزارش: {e}")
        await update.message.reply_text("⚠️ گزارش ارسال نشد، دوباره امتحان کن.")


# ============================================================
# خوش‌آمدگویی و بدرقه اعضا
# ============================================================
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_feature_enabled("welcome"):
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        text = (
            f"👋 سلام {member.first_name} عزیز، به گروه خوش اومدی!\n\n"
            f"لطفاً قوانین گروه رو با /rules ببین، و برای دیدن امکانات دستیار هوشمند /start رو بزن. خوش بگذره! 🎉"
        )
        await update.message.reply_text(text)


async def member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member and not member.is_bot:
        await update.message.reply_text(f"👋 {member.first_name} از گروه رفت. به امید دیدار دوباره!")


# ============================================================
# آمار گروه
# ============================================================
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    try:
        count = await context.bot.get_chat_member_count(chat.id)
        admins = await context.bot.get_chat_administrators(chat.id)
        custom_count = len(get_custom_words_for_chat(chat.id))
        text = (
            f"📊 آمار گروه «{chat.title}»:\n\n"
            f"👥 تعداد اعضا: {count}\n"
            f"👑 تعداد ادمین‌ها: {len(admins)}\n"
            f"📋 تعداد کلمات فیلترشده (پیش‌فرض): {len(BAD_WORDS_FA) + len(BAD_WORDS_EN)}\n"
            f"📋 تعداد کلمات سفارشیِ همین گروه: {custom_count}\n"
            f"⏰ یادآور خودکار: {'🟢 روشن' if reminder_enabled.get(str(chat.id), False) else '🔴 خاموش'}"
        )
    except Exception as e:
        text = f"⚠️ نشد آمار رو بگیرم: {e}"
    await update.message.reply_text(text)


# ============================================================
# ⏰ یادآور زمان‌بندی‌شده (JobQueue)
# این دو تا کاملاً باهم فرق دارن، هر کدوم فقط سرِ یه لحظه‌ی مشخص فعال می‌شن:
#   • «وقت پاچیدن چاهه» → فقط توی ساعت‌های زوج، دقیقه‌ی ۳۰ (مثلاً ۸:۳۰، ۱۰:۳۰، ۱۲:۳۰...)
#   • «شام ننه‌جون سرد شد» → فقط توی ساعت‌های فرد، دقیقه‌ی ۰۰ یعنی سرِ ساعت (مثلاً ۹:۰۰، ۱۱:۰۰...)
# هر ۶۰ ثانیه یه بار چک می‌کنه؛ برای هر گروه فقط یه بار در همون اسلات مشخص می‌فرسته
# (با کلید last-sent، ترکیب تاریخ+ساعت+دقیقه) تا تکراری نشه.
# ============================================================
async def reminder_check_job(context: ContextTypes.DEFAULT_TYPE):
    if not owner_feature_enabled("reminders"):
        return
    now = datetime.now()

    text = None
    # نکته‌ی مهم که عمداً دوباره تأیید شده: ساعتِ زوج + دقیقه‌ی ۳۰ = پیام «چاه»،
    # ساعتِ فرد + سرِ ساعت (دقیقه‌ی ۰) = پیام «شام ننه‌جون». این دو هیچ‌وقت با
    # هم قاطی نمی‌شن چون شرط‌هاشون کاملاً مانع‌الجمعن (هم زوج/فرد هم دقیقه فرق داره).
    if now.hour % 2 == 0 and now.minute == 30:
        text = REMINDER_EVEN_TEXT
    elif now.hour % 2 == 1 and now.minute == 0:
        text = REMINDER_ODD_TEXT
    elif now.hour == 0 and now.minute == 12:
        text = GOODNIGHT_TEXT
    else:
        return  # الان زمان هیچ‌کدوم از یادآورها نیست

    current_slot = (now.date().isoformat(), now.hour, now.minute)
    for chat_id_str, enabled in list(reminder_enabled.items()):
        if not enabled:
            continue
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            continue
        last_slot = reminder_last_sent_hour.get(chat_id_str)
        if last_slot == current_slot:
            continue  # همین لحظه‌ی مشخص قبلاً فرستاده شده
        try:
            await context.bot.send_message(chat_id, text)
            # فقط بعد از ارسال موفق، این اسلات را ثبت می‌کنیم؛ اگر ارسال شکست خورد،
            # اجرای بعدی JobQueue در همان دقیقه فرصت تلاش دوباره دارد.
            reminder_last_sent_hour[chat_id_str] = current_slot
        except TelegramError as e:
            logger.warning(f"خطای ارسال یادآور به {chat_id}: {e}")


# ============================================================
# بازی گروهی گرگینه (روستا در خطر)
# ============================================================
WW_MIN_PLAYERS = 3
WW_MAX_PLAYERS = 16
WW_JOIN_SECONDS = 45
WW_NIGHT_SECONDS = 40
WW_DAY_DISCUSSION_SECONDS = 45
WW_VOTE_SECONDS = 30

WW_ROLE_FA = {
    "wolf": "🐺 گرگ",
    "seer": "🔮 پیشگو",
    "doctor": "💉 دکتر",
    "mayor": "👑 شهردار",
    "villager": "👤 روستایی",
}
WW_ROLE_DESC = {
    "wolf": "هر شب همراه بقیه‌ی گرگ‌ها یه نفر رو انتخاب می‌کنی که کشته بشه. اگه تعداد گرگ‌ها به روستایی‌ها برسه، گرگ‌ها می‌برن. 🐺",
    "seer": "هر شب می‌تونی یه نفر رو چک کنی و بفهمی گرگه یا نه. کمک کن روستایی‌ها گرگ‌ها رو پیدا کنن. 🔮",
    "doctor": "هر شب می‌تونی یه نفر (حتی خودت) رو از کشته‌شدن نجات بدی. 💉",
    "mayor": "از ۴ بازیکن به بالا شهردار می‌تواند در رأی‌گیری روز با رأی ۲ امتیازی سرنوشت رأی را تغییر دهد. هویتش مخفی است و باید با دقت از قدرتش استفاده کند. 👑",
    "villager": "قدرت خاصی نداری، ولی رأیت روزها مهمه؛ سعی کن با بحث گرگ‌ها رو لو بدی. 👤",
}

ww_games = {}
ww_player_game = {}


class WWPlayer:
    def __init__(self, user):
        self.id = user.id
        self.name = user.first_name or "بازیکن"
        self.role = None
        self.alive = True


class WWGame:
    def __init__(self, chat_id, host_id):
        self.chat_id = chat_id
        self.host_id = host_id
        self.state = "lobby"
        self.players = {}
        self.round_no = 0
        self.night_kill_votes = {}
        self.seer_acted = False
        self.doctor_save = None
        self.last_victim_id = None
        self.last_saved = False
        self.day_votes = {}
        self.phase_id = 0
        self.mayor_vote_used = False
        self.created_at = time.time()

    def alive_players(self):
        return [p for p in self.players.values() if p.alive]


def ww_assign_roles(player_ids):
    n=len(player_ids)
    wolves_count=max(1,n//4)
    roles=["wolf"]*wolves_count
    remaining=n-wolves_count
    if remaining>=1 and n>=5:
        roles.append("seer"); remaining-=1
    if remaining>=1 and n>=6:
        roles.append("doctor"); remaining-=1
    if remaining>=1 and n>=4:
        roles.append("mayor"); remaining-=1
    roles += ["villager"]*remaining
    random.shuffle(roles)
    return dict(zip(player_ids,roles))


def ww_check_win(game: "WWGame"):
    alive = game.alive_players()
    wolves = [p for p in alive if p.role == "wolf"]
    others = [p for p in alive if p.role != "wolf"]
    if len(wolves) == 0:
        return "village"
    if len(wolves) >= len(others):
        return "wolves"
    return None


def ww_cleanup_game(chat_id):
    game = ww_games.pop(chat_id, None)
    if game:
        for uid in list(game.players.keys()):
            if ww_player_game.get(uid) == chat_id:
                ww_player_game.pop(uid, None)


def spawn_background_task(application, coro, name="background"):
    """Create a supervised background task so exceptions never become unhandled task errors.
    The task itself is still cancelled normally when the application shuts down.
    """
    task = application.create_task(coro, update=None, name=name)
    def _done(t):
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("%s task inspection failed: %s", name, e)
            return
        if exc:
            logger.error("Background task %s failed: %s", name, exc, exc_info=exc)
    try:
        task.add_done_callback(_done)
    except Exception:
        pass
    return task


async def ww_start_lobby(chat_id, host_id, context: ContextTypes.DEFAULT_TYPE):
    busy, game_name = group_game_is_busy(chat_id, "werewolf")
    if busy:
        await context.bot.send_message(chat_id, f"⚠️ الان بازی {game_name} در این گروه در جریانه. اول اون بازی رو تموم کنید.")
        return
    if chat_id in ww_games and ww_games[chat_id].state != "ended":
        await context.bot.send_message(chat_id, "🐺 یه بازی از قبل توی این گروه در جریانه یا لابیش بازه.")
        return
    game = WWGame(chat_id, host_id)
    ww_games[chat_id] = game
    kb = [[InlineKeyboardButton("🐺 پیوستن به بازی", callback_data="ww_join")]]
    await send_game_animation(chat_id, context, "werewolf", "lobby")
    await context.bot.send_message(
        chat_id,
        (
            game_scene("werewolf", "lobby") + "\n\n🐺 روستا در خطره!\n"
            f"حداقل {WW_MIN_PLAYERS} و حداکثر {WW_MAX_PLAYERS} نفر می‌تونن بازی کنن.\n"
            f"برای پیوستن دکمه‌ی زیر رو بزن، {WW_JOIN_SECONDS} ثانیه وقت داری.\n\n"
            "⚠️ حتماً قبلش یه‌بار توی خصوصی به من پیام بده (/start)، وگرنه نمی‌تونم نقشتو برات بفرستم.\n"
            "ادمین می‌تونه با /startgame زودتر شروع کنه یا با /endgame لغوش کنه."
        ),
        reply_markup=InlineKeyboardMarkup(kb),
    )
    spawn_background_task(context.application, ww_lobby_countdown(chat_id, context), name=f"ww-lobby:{chat_id}")


async def ww_lobby_countdown(chat_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(WW_JOIN_SECONDS)
    game = ww_games.get(chat_id)
    if game and game.state == "lobby":
        await ww_try_start_game(chat_id, context)


async def ww_try_start_game(chat_id, context: ContextTypes.DEFAULT_TYPE):
    game = ww_games.get(chat_id)
    if not game or game.state != "lobby":
        return
    if len(game.players) < WW_MIN_PLAYERS:
        await context.bot.send_message(chat_id, f"❌ تعداد بازیکن‌ها کافی نبود (حداقل {WW_MIN_PLAYERS} نفر لازمه). بازی لغو شد.")
        ww_cleanup_game(chat_id)
        return

    # پیش‌بررسی Private قبل از پخش نقش‌ها: اگر بازیکنی ربات را Start نکرده باشد،
    # او را از این دور کنار می‌گذاریم تا نقش مخفی نصفه‌نیمه پخش نشود و بازی در میانه گیر نکند.
    ready_ids = []
    blocked = []
    for uid, p in list(game.players.items()):
        try:
            probe = await context.bot.send_message(uid, "🐺 آماده‌ای؟ نقش مخفی بازی بعد از شروع برایت ارسال می‌شود. این پیام فقط برای بررسی دسترسی Private است.")
            ready_ids.append(uid)
            try:
                await context.bot.delete_message(chat_id=uid, message_id=probe.message_id)
            except TelegramError:
                pass
        except (Forbidden, TelegramError):
            blocked.append(uid)
    for uid in blocked:
        p = game.players.pop(uid, None)
        if p:
            ww_player_game.pop(uid, None)
            await context.bot.send_message(chat_id, f"⚠️ {p.name} چون Private ربات را فعال نکرده بود، از این دور گرگینه کنار گذاشته شد. برای بازی بعد ابتدا /start را در Private بزند.")

    if len(game.players) < WW_MIN_PLAYERS:
        await context.bot.send_message(chat_id, f"❌ بعد از بررسی Private، تعداد بازیکنان کافی نماند (حداقل {WW_MIN_PLAYERS} نفر). این دور لغو شد.")
        ww_cleanup_game(chat_id)
        return

    roles = ww_assign_roles(list(game.players.keys()))
    for uid, role in roles.items():
        game.players[uid].role = role

    lines = ["🎭 نقش‌ها پخش شد! هر کس نقشش رو توی خصوصی می‌بینه.\n\n👥 بازیکنان:"]
    for p in game.players.values():
        lines.append(f"• {p.name}")
    await context.bot.send_message(chat_id, "\n".join(lines))

    for p in game.players.values():
        try:
            await context.bot.send_message(
                p.id, f"🎭 نقش تو توی این بازی: {WW_ROLE_FA[p.role]}\n\n{WW_ROLE_DESC[p.role]}"
            )
        except Forbidden:
            await context.bot.send_message(
                chat_id,
                f"⚠️ {p.name} عزیز، نتونستم نقشتو خصوصی بفرستم؛ اول به من پیام بده (/start) و دفعه بعد دوباره بازی کن.",
            )

    game.state = "night"
    spawn_background_task(context.application, ww_game_loop(chat_id, context), name=f"ww-game:{chat_id}")


async def ww_game_loop(chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        while True:
            # اگر بازی دستی لغو شده یا پاکسازی شده، حلقه نباید دوباره آن را لمس کند.
            game = ww_games.get(chat_id)
            if not game:
                return
            await ww_run_night(chat_id, context)
            game = ww_games.get(chat_id)
            if not game:
                return
            winner = ww_check_win(game)
            if winner:
                await ww_announce_winner(chat_id, context, winner)
                break
            winner = await ww_run_day(chat_id, context)
            game = ww_games.get(chat_id)
            if not game:
                return
            if winner:
                await ww_announce_winner(chat_id, context, winner)
                break
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"خطا توی حلقه بازی گرگینه: {e}", exc_info=True)
        # فقط اگر بازی هنوز وجود دارد، پیام خطا بفرست.
        if chat_id in ww_games:
            try:
                await context.bot.send_message(chat_id, "⚠️ یه مشکل غیرمنتظره پیش اومد؛ بازی متوقف شد.")
            except Exception:
                pass
    finally:
        ww_cleanup_game(chat_id)


async def ww_run_night(chat_id, context: ContextTypes.DEFAULT_TYPE):
    game = ww_games[chat_id]
    game.state = "night"
    game.round_no += 1
    game.phase_id += 1
    game.night_kill_votes = {}
    game.seer_acted = False
    game.doctor_save = None

    await send_game_animation(chat_id, context, "werewolf", "night")
    await send_game_animation(chat_id, context, "werewolf", "wolf")
    await context.bot.send_message(chat_id, f"{game_scene("werewolf", "night")}\n\n🌙 شب {game.round_no} فرا رسید.\n🤫 روستا ساکت می‌شود... نقش‌های خاص به خصوصی من مراجعه کنند.")

    alive = game.alive_players()
    wolves = [p for p in alive if p.role == "wolf"]
    wolf_targets = [p for p in alive if p.role != "wolf"]

    for w in wolves:
        kb = [[InlineKeyboardButton(p.name, callback_data=f"ww_kill_{chat_id}_{game.round_no}_{game.phase_id}_{p.id}")] for p in wolf_targets]
        try:
            await context.bot.send_message(w.id, "🐺 امشب کی رو می‌کشید؟", reply_markup=InlineKeyboardMarkup(kb))
        except Forbidden:
            await context.bot.send_message(chat_id, f"⚠️ نتونستم به {w.name} پیام خصوصی بدم.")

    seer = next((p for p in alive if p.role == "seer"), None)
    if seer:
        targets = [p for p in alive if p.id != seer.id]
        kb = [[InlineKeyboardButton(p.name, callback_data=f"ww_seer_{chat_id}_{game.round_no}_{game.phase_id}_{p.id}")] for p in targets]
        try:
            await context.bot.send_message(seer.id, "🔮 کی رو می‌خوای چک کنی؟", reply_markup=InlineKeyboardMarkup(kb))
        except Forbidden:
            await context.bot.send_message(chat_id, f"⚠️ نتونستم به {seer.name} پیام خصوصی بدم.")

    doctor = next((p for p in alive if p.role == "doctor"), None)
    if doctor:
        kb = [[InlineKeyboardButton(p.name, callback_data=f"ww_save_{chat_id}_{game.round_no}_{game.phase_id}_{p.id}")] for p in alive]
        try:
            await context.bot.send_message(doctor.id, "💉 امشب کی رو نجات می‌دی؟", reply_markup=InlineKeyboardMarkup(kb))
        except Forbidden:
            await context.bot.send_message(chat_id, f"⚠️ نتونستم به {doctor.name} پیام خصوصی بدم.")

    # اگر نقش ویژه‌ای نتوانسته پیام خصوصی بگیرد، بازی متوقف نمی‌شود؛
    # اما وضعیت به بازیکن اعلام شده و زمان شب همچنان محدود می‌ماند.
    await context.bot.send_message(
        chat_id,
        "🌙 اکشن‌های شبانه فعال شدند. هر بازیکن فقط یک انتخاب معتبر در نقش خودش دارد و دکمه‌های قدیمی قابل استفاده نیستند."
    )

    waited = 0
    while waited < WW_NIGHT_SECONDS:
        await asyncio.sleep(2)
        waited += 2
        wolves_done = all(w.id in game.night_kill_votes for w in wolves) if wolves else True
        seer_done = (seer is None) or game.seer_acted
        doctor_done = (doctor is None) or (game.doctor_save is not None)
        if wolves_done and seer_done and doctor_done:
            break

    ww_resolve_night(game)


def ww_resolve_night(game: "WWGame"):
    votes = list(game.night_kill_votes.values())
    victim_id = None
    if votes:
        tally = {}
        for v in votes:
            if v in game.players and game.players[v].alive and game.players[v].role != "wolf":
                tally[v] = tally.get(v, 0) + 1
        if tally:
            top_count = max(tally.values())
            top = [k for k, c in tally.items() if c == top_count]
            # در تساوی، گرگ‌ها قربانی تصادفی ندارند؛ حمله ناموفق است.
            if len(top) == 1:
                victim_id = top[0]
    game.last_victim_id = victim_id
    game.last_saved = victim_id is not None and victim_id == game.doctor_save


async def ww_run_day(chat_id, context: ContextTypes.DEFAULT_TYPE):
    game = ww_games[chat_id]
    game.state = "day_discuss"

    victim_id = game.last_victim_id
    await send_game_animation(chat_id, context, "werewolf", "morning")
    if victim_id and not game.last_saved:
        victim = game.players[victim_id]
        victim.alive = False
        await context.bot.send_message(
            chat_id, f"{game_scene("werewolf", "day")}\n\n☀️ صبح شد... متأسفانه {victim.name} ({WW_ROLE_FA[victim.role]}) دیشب از بازی خارج شد. 💀"
        )
    elif victim_id and game.last_saved:
        await context.bot.send_message(chat_id, f"{game_scene("werewolf", "day")}\n\n🩺 دیشب یک نفر هدف گرگ‌ها بود، اما دکتر نجاتش داد! 🎉")
    else:
        await context.bot.send_message(chat_id, f"{game_scene("werewolf", "day")}\n\n🌤️ صبح شد... دیشب اتفاق مشکوکی نیفتاد.")

    winner = ww_check_win(game)
    if winner:
        return winner

    await context.bot.send_message(chat_id, f"💬 حالا نوبت بحث روستاست.\n⏳ {WW_DAY_DISCUSSION_SECONDS} ثانیه وقت دارید سرنخ‌ها رو کنار هم بذارید و گرگ‌ها رو پیدا کنید...")
    await asyncio.sleep(WW_DAY_DISCUSSION_SECONDS)

    game.state = "day_vote"
    game.phase_id += 1
    game.day_votes = {}
    alive = game.alive_players()
    kb = [[InlineKeyboardButton(p.name, callback_data=f"ww_vote_{chat_id}_{game.round_no}_{game.phase_id}_{p.id}")] for p in alive]
    await context.bot.send_message(chat_id, "╭──────── 🗳️ رأی‌گیری ────────╮\nسرنوشت روستا دست شماست...\n╰──────────────────────────────╯\n\nچه کسی مشکوک‌تره؟\n\n🔒 فقط رأیِ بازیکنان زنده و فقط دکمه‌های همین مرحله معتبرند.", reply_markup=InlineKeyboardMarkup(kb))

    waited = 0
    while waited < WW_VOTE_SECONDS:
        await asyncio.sleep(2)
        waited += 2
        if len(game.day_votes) >= len(alive):
            break

    text = ww_resolve_vote(game)
    await context.bot.send_message(chat_id, text)
    return ww_check_win(game)


def ww_resolve_vote(game: "WWGame") -> str:
    # فقط رأی‌های معتبرِ بازیکنان زنده و هدف‌های زنده محاسبه شوند.
    valid_votes = {
        voter_id: target_id
        for voter_id, target_id in game.day_votes.items()
        if voter_id in game.players
        and target_id in game.players
        and game.players[voter_id].alive
        and game.players[target_id].alive
        and voter_id != target_id
    }
    if not valid_votes:
        return "🤷 رأی معتبر کافی ثبت نشد؛ امروز کسی اعدام نشد.\n🛡️ هیچ رأی ناقص یا نامعتبر در نتیجه حساب نشد."
    tally = {}
    for voter_id, target_id in valid_votes.items():
        voter = game.players[voter_id]
        weight = 1
        if voter.role == "mayor" and not game.mayor_vote_used:
            weight = 2
            game.mayor_vote_used = True
        tally[target_id] = tally.get(target_id, 0) + weight
    top_count = max(tally.values())
    top = [k for k, c in tally.items() if c == top_count]
    if len(top) > 1:
        return "⚖️ رأی‌ها مساوی شد، امروز کسی اعدام نشد."
    target_id = top[0]
    target = game.players[target_id]
    target.alive = False
    return f"⚖️ رأی گروه: {target.name} اعدام شد. نقشش {WW_ROLE_FA[target.role]} بود!"


async def ww_announce_winner(chat_id, context: ContextTypes.DEFAULT_TYPE, winner: str):
    game = ww_games[chat_id]
    for _p in game.players.values():
        _won = (_p.role == "wolf" and winner == "wolves") or (_p.role != "wolf" and winner == "village")
        record_game_result(chat_id, _p.id, _p.name, "werewolf", _won, role=winner)
    reveal = "\n".join(f"• {p.name}: {WW_ROLE_FA[p.role]} {'💀' if not p.alive else '🟢'}" for p in game.players.values())
    text = "🎉 روستایی‌ها بردن و همه‌ی گرگ‌ها رو پیدا کردن!" if winner == "village" else "🐺 گرگ‌ها بردن و روستا رو تصرف کردن!"
    await send_game_animation(chat_id, context, "werewolf", "win")
    await context.bot.send_message(chat_id, f"╭──────── 🏆 پایان بازی ────────╮\n{text}\n╰───────────────────────────────╯\n\n🎭 نقش همه:\n{reveal}\n\n✨ بازی تموم شد؛ ممنون که بازی کردید!")


async def gorgineh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بازی‌ها فعلاً توسط مالک ربات غیرفعال شده‌اند.")
        return
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("🐺 این بازی فقط توی گروه قابل اجراست.")
        return
    busy, game_name = group_game_is_busy(chat.id, "werewolf")
    if busy:
        await update.message.reply_text(f"⚠️ الان بازی {game_name} در این گروه در جریانه. اول همون بازی رو تموم کنید.")
        return
    await ww_start_lobby(chat.id, update.effective_user.id, context)


async def startgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین می‌تونه زودتر بازی رو شروع کنه.")
        return
    chat_id = update.effective_chat.id
    game = ww_games.get(chat_id)
    if not game or game.state != "lobby":
        await update.message.reply_text("لابی‌ای برای شروع نیست. اول با /gorgineh یکی بساز.")
        return
    await ww_try_start_game(chat_id, context)


async def endgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ فقط ادمین می‌تونه بازی رو لغو کنه.")
        return
    chat_id = update.effective_chat.id
    if chat_id in ww_games:
        ww_cleanup_game(chat_id)
        await update.message.reply_text("🛑 بازی گرگینه لغو شد.")
    else:
        await update.message.reply_text("بازی‌ای در جریان نیست.")


async def players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = ww_games.get(chat_id)
    if not game:
        await update.message.reply_text("بازی‌ای در جریان نیست.")
        return
    lines = [f"👥 بازیکنان ({len(game.players)} نفر):"]
    for p in game.players.values():
        lines.append(f"{'🟢' if p.alive else '💀'} {p.name}")
    await update.message.reply_text("\n".join(lines))


@_callback_ack_guard
async def ww_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not owner_feature_enabled("gaming"):
        await _cb_answer(query, "🎮 بازی‌ها فعلاً توسط مالک ربات غیرفعال شده‌اند.", show_alert=True)
        return
    data = query.data or ""
    user = query.from_user

    if data == "ww_join":
        chat_id = query.message.chat_id
        game = ww_games.get(chat_id)
        if not game or game.state != "lobby":
            await query.message.reply_text("لابی‌ای برای پیوستن نیست.")
            return
        if user.id in game.players:
            await query.message.reply_text(f"{user.first_name} جان، تو از قبل عضو بازی هستی!")
            return
        existing_chat = ww_player_game.get(user.id)
        if existing_chat is not None and existing_chat != chat_id:
            existing_game = ww_games.get(existing_chat)
            if existing_game and existing_game.state != "ended":
                await query.message.reply_text("⚠️ تو همین الان در یک بازی گرگینه‌ی دیگر هستی. اول آن بازی تمام یا لغو شود، بعد می‌توانی وارد این یکی شوی.")
                return
            ww_player_game.pop(user.id, None)
        if len(game.players) >= WW_MAX_PLAYERS:
            await query.message.reply_text("ظرفیت بازی پره!")
            return
        game.players[user.id] = WWPlayer(user)
        ww_player_game[user.id] = chat_id
        await context.bot.send_message(chat_id, f"✅ {user.first_name} به بازی پیوست. ({len(game.players)} نفر)")
        return

    # نکته‌ی مهم (رفع باگ): برای اکشن‌های شبانه/رأی‌گیری، chat_id مستقیماً از خودِ
    # callback_data خونده می‌شه (نه از یه دیکشنری سراسری بر اساس آخرین بازیِ کاربر).
    # این‌جوری اگه یه کاربر همزمان عضو دو بازی توی دو گروه مختلف باشه، اکشن‌هاش
    # هیچ‌وقت با هم قاطی نمی‌شن.
    try:
        parts = data.split("_")
        action = parts[1]  # kill / seer / save / vote
        chat_id = int(parts[2])
        callback_round = int(parts[3])
        callback_phase = int(parts[4])
        target_id = int(parts[5])
    except (IndexError, ValueError):
        await query.message.reply_text("⚠️ این دکمه دیگه معتبر نیست.")
        return

    game = ww_games.get(chat_id)
    if not game:
        await query.message.reply_text("این بازی دیگه فعال نیست.")
        return
    if callback_round != game.round_no or callback_phase != game.phase_id:
        await query.message.reply_text("⚠️ این دکمه مربوط به مرحله قبلی بازیه و دیگه معتبر نیست.")
        return
    if user.id not in game.players:
        await query.message.reply_text("تو عضو این بازی نیستی.")
        return
    if target_id not in game.players:
        await query.message.reply_text("⚠️ این بازیکن دیگه توی بازی نیست.")
        return

    # دکمه ممکن است قدیمی باشد؛ وضعیت فعلی هدف را دوباره از خود بازی بررسی می‌کنیم.
    target = game.players[target_id]
    if not target.alive:
        await query.message.reply_text("⚠️ این بازیکن دیگر در بازی زنده نیست.")
        return

    player = game.players[user.id]
    if not player.alive:
        await query.message.reply_text("تو دیگه توی این دور بازی نیستی (مرده‌ای)! 💀")
        return

    try:
        if action == "kill":
            if player.role != "wolf" or game.state != "night":
                await query.message.reply_text("⚠️ الان نوبت اکشن تو نیست.")
                return
            if target.role == "wolf":
                await query.message.reply_text("🐺 گرگ‌ها نمی‌تونن یکی از اعضای گله رو هدف بگیرن.")
                return
            game.night_kill_votes[user.id] = target_id
            await query.message.reply_text(f"✅ انتخاب شبانه ثبت شد: {target.name}")
        elif action == "seer":
            if player.role != "seer" or game.state != "night" or game.seer_acted:
                await query.message.reply_text("⚠️ الان نوبت اکشن تو نیست یا قبلاً انتخابت رو انجام دادی.")
                return
            if target_id == user.id:
                await query.message.reply_text("🔮 بهتره یک بازیکن دیگر را بررسی کنی.")
                return
            game.seer_acted = True
            await query.message.reply_text(f"🔮 نتیجه: {target.name} {'گرگه! 🐺' if target.role == 'wolf' else 'گرگ نیست. ✅'}")
        elif action == "save":
            if player.role != "doctor" or game.state != "night":
                await query.message.reply_text("⚠️ الان نوبت اکشن تو نیست.")
                return
            game.doctor_save = target_id
            await query.message.reply_text(f"💉 انتخاب ثبت شد: امشب {target.name} رو نجات می‌دی.")
        elif action == "vote":
            if game.state != "day_vote":
                await query.message.reply_text("⚠️ الان زمان رأی‌گیری نیست.")
                return
            if target_id == user.id:
                await query.message.reply_text("🗳️ نمی‌تونی به خودت رأی بدی.")
                return
            game.day_votes[user.id] = target_id
            await query.message.reply_text(f"🗳️ رأیت ثبت شد: {target.name}")
        else:
            await query.message.reply_text("⚠️ دکمه‌ی نامعتبر.")
    except (KeyError, IndexError, ValueError) as e:
        logger.warning(f"خطای دکمه گرگینه: {e}")
        await query.message.reply_text("⚠️ یه مشکل موقتی پیش اومد.")


# ============================================================
# مدیریت خطای کلی (تا ربات هیچ‌وقت کرش نکنه)
# ============================================================
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("خطای پیش‌بینی‌نشده:\n" + "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__)))


# ============================================================
# v24 — پایداری و ضدتداخل گرگینه
# شهردار از ۴ بازیکن به بالا در ترکیب قرار می‌گیرد.
# اعتبارسنجی اکشن‌ها همیشه بر اساس وضعیت فعلی بازی انجام می‌شود.
# ============================================================

# ============================================================
# v17 — رسانه‌ی بازی حرفه‌ای و مقاوم
# ============================================================
GAME_MEDIA_EVENTS = {
    "werewolf": {"lobby":"🐺🌙", "night":"🌙🐺", "morning":"☀️🌲", "wolf":"🐺🌙", "win":"🏆🐺"},
    "uno": {"start":"🃏✨", "deal":"🎴✨", "special":"🌈🃏", "uno":"🚨🃏", "win":"🏆🃏"},
}

async def safe_game_animation(chat_id, context, game_name, event, caption=None):
    try:
        return await send_game_animation(chat_id, context, game_name, event, caption=caption)
    except Exception as exc:
        logger.warning("media fallback %s/%s: %s", game_name, event, exc)
        return False


# ============================================================
# v18 — XP / Level / Ranking / Achievement
# ============================================================
GAME_STATS_FILE = DATA_DIR / "game_stats.json"
GAME_STATS = load_json_safe(GAME_STATS_FILE, {})

ACHIEVEMENTS = {
    "first_game": ("🎮 اولین بازی", "اولین بازی گروهی را انجام دادی."),
    "first_win": ("🏆 اولین برد", "اولین بردت را ثبت کردی."),
    "uno_master": ("🃏 UNO Master", "۱۰ برد UNO ثبت کردی."),
    "wolf_hunter": ("🐺 شکارچی گرگ", "۵ برد روستا در گرگینه."),
    "wolf_pack": ("🌙 عضو گله", "۵ برد به عنوان گرگ."),
    "streak_5": ("🔥 پنج‌تایی", "۵ برد پشت‌سرهم."),
}

def _gs_key(chat_id, user_id): return f"{chat_id}:{user_id}"
def _get_gs(chat_id, user_id):
    k=_gs_key(chat_id,user_id)
    d=GAME_STATS.setdefault(k,{"name":"دوست","games":0,"wins":0,"losses":0,"xp":0,"streak":0,"best_streak":0,"by_game":{},"achievements":[]})
    return d

def save_game_stats(): save_json_safe(GAME_STATS_FILE, GAME_STATS)

def xp_level(xp): return max(1, int(xp)//100 + 1)

def record_game_result(chat_id, user_id, name, game_name, won=False, role=None):
    d=_get_gs(chat_id,user_id); d["name"]=name or d.get("name") or "دوست"; d["games"]+=1
    d["xp"] += 50 if won else 15
    if won: d["wins"]+=1; d["streak"]+=1; d["best_streak"]=max(d["best_streak"],d["streak"])
    else: d["losses"]+=1; d["streak"]=0
    g=d["by_game"].setdefault(game_name,{"games":0,"wins":0}); g["games"]+=1; g["wins"]+=int(won)
    ach=set(d.get("achievements",[]))
    if d["games"]>=1: ach.add("first_game")
    if d["wins"]>=1: ach.add("first_win")
    if g.get("wins",0)>=10 and game_name=="uno": ach.add("uno_master")
    if g.get("wins",0)>=5 and game_name=="werewolf" and role=="village": ach.add("wolf_hunter")
    if g.get("wins",0)>=5 and game_name=="werewolf" and role=="wolves": ach.add("wolf_pack")
    if d["best_streak"]>=5: ach.add("streak_5")
    d["achievements"]=sorted(ach); save_game_stats()
    try: db_record_result(chat_id,user_id,game_name,won)
    except Exception as exc: logger.warning("SQLite game result failed: %s", exc)

async def my_stats_cmd(update, context):
    d=_get_gs(update.effective_chat.id,update.effective_user.id)
    await update.message.reply_text(f"🏆 آمار {d['name']}\n\n⭐ Level: {xp_level(d['xp'])}\n✨ XP: {d['xp']}\n🎮 بازی: {d['games']}\n🏆 برد: {d['wins']}\n🔥 رکورد برد پیاپی: {d['best_streak']}\n🎖️ دستاوردها: {len(d['achievements'])}")

async def leaderboard_cmd(update, context):
    chat_id=update.effective_chat.id
    rows=[d for k,d in GAME_STATS.items() if k.startswith(str(chat_id)+":")]
    rows=sorted(rows,key=lambda x:(x.get("xp",0),x.get("wins",0)),reverse=True)[:10]
    if not rows: return await update.message.reply_text("🏆 هنوز آماری برای این گروه ثبت نشده.")
    text="🏆 رتبه‌بندی گروه\n\n"+"\n".join(f"{i}. {d.get('name','دوست')} — Level {xp_level(d.get('xp',0))} | {d.get('xp',0)} XP" for i,d in enumerate(rows,1))
    await update.message.reply_text(text)

async def achievements_cmd(update, context):
    d=_get_gs(update.effective_chat.id,update.effective_user.id); ids=d.get("achievements",[])
    if not ids: return await update.message.reply_text("🎖️ هنوز دستاوردی نگرفتی؛ اولین بازیت رو شروع کن!")
    await update.message.reply_text("🎖️ دستاوردهای تو:\n\n"+"\n".join(f"• {ACHIEVEMENTS[i][0]} — {ACHIEVEMENTS[i][1]}" for i in ids if i in ACHIEVEMENTS))


# ============================================================
# v19 — پروفایل کاربر و تنظیمات شخصی غیرحساس
# ============================================================
PROFILE_PREFS_FILE = DATA_DIR / "profile_preferences.json"
PROFILE_PREFS = load_json_safe(PROFILE_PREFS_FILE, {})

def profile_key(chat_id,user_id): return f"{chat_id}:{user_id}"
def get_profile_pref(chat_id,user_id):
    return PROFILE_PREFS.setdefault(profile_key(chat_id,user_id),{"tone":"normal","nickname":"","games":True})

def save_profile_prefs(): save_json_safe(PROFILE_PREFS_FILE, PROFILE_PREFS)

def profile_cmd_text(d):
    tone={"normal":"معمولی","friendly":"صمیمی","fun":"شوخ و دوستانه"}.get(d.get("tone"),"معمولی")
    return f"👤 پروفایل گفت‌وگویی\n\n🏷️ نام نمایشی: {d.get('nickname') or 'همان نام تلگرام'}\n💬 لحن: {tone}\n🎮 پاسخ‌های بازی: {'روشن' if d.get('games',True) else 'خاموش'}"

async def profile_cmd(update, context):
    d=get_profile_pref(update.effective_chat.id,update.effective_user.id)
    await update.message.reply_text(profile_cmd_text(d)+"\n\nبرای تغییر: /setprofile tone friendly یا /setprofile nickname نام")

async def setprofile_cmd(update, context):
    if len(context.args)<2: return await update.message.reply_text("استفاده: /setprofile tone normal|friendly|fun یا /setprofile nickname نام")
    d=get_profile_pref(update.effective_chat.id,update.effective_user.id); field=context.args[0].lower(); value=" ".join(context.args[1:]).strip()
    if field=="tone" and value in {"normal","friendly","fun"}: d["tone"]=value
    elif field=="nickname" and len(value)<=40: d["nickname"]=value
    else: return await update.message.reply_text("⚠️ مقدار یا گزینه معتبر نیست.")
    save_profile_prefs(); await update.message.reply_text("✅ پروفایل به‌روزرسانی شد.")

async def group_game_profile_cmd(update, context):
    d=get_profile_pref(update.effective_chat.id,update.effective_user.id); d["games"]=not d.get("games",True); save_profile_prefs()
    await update.message.reply_text("🎮 پاسخ‌های مرتبط با بازی برای پروفایل تو " + ("روشن شد." if d["games"] else "خاموش شد."))


# ============================================================
# v20 — SQLite storage layer (بدون حذف فایل‌های قدیمی)
# ============================================================
import sqlite3
DB_FILE = DATA_DIR / "bot_data.sqlite3"
_db_lock = asyncio.Lock()

def db_conn():
    c=sqlite3.connect(DB_FILE)
    c.execute("PRAGMA journal_mode=WAL")
    return c

def db_init():
    c=db_conn(); c.executescript("""
    CREATE TABLE IF NOT EXISTS user_stats(chat_id INTEGER,user_id INTEGER,name TEXT,games INTEGER DEFAULT 0,wins INTEGER DEFAULT 0,losses INTEGER DEFAULT 0,xp INTEGER DEFAULT 0,streak INTEGER DEFAULT 0,best_streak INTEGER DEFAULT 0,achievements TEXT DEFAULT '[]',PRIMARY KEY(chat_id,user_id));
    CREATE TABLE IF NOT EXISTS user_profiles(chat_id INTEGER,user_id INTEGER,nickname TEXT DEFAULT '',tone TEXT DEFAULT 'normal',games_enabled INTEGER DEFAULT 1,PRIMARY KEY(chat_id,user_id));
    CREATE TABLE IF NOT EXISTS group_settings(chat_id INTEGER PRIMARY KEY,created_at TEXT);
    CREATE TABLE IF NOT EXISTS game_results(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,user_id INTEGER,game TEXT,won INTEGER,created_at TEXT);
    """); c.commit(); c.close()

def db_sync_stats_from_json():
    c=db_conn()
    for key,d in GAME_STATS.items():
        try: chat_id,user_id=map(int,key.split(":",1))
        except (ValueError, TypeError): continue
        c.execute("INSERT OR REPLACE INTO user_stats(chat_id,user_id,name,games,wins,losses,xp,streak,best_streak,achievements) VALUES(?,?,?,?,?,?,?,?,?,?)",(chat_id,user_id,d.get('name','دوست'),d.get('games',0),d.get('wins',0),d.get('losses',0),d.get('xp',0),d.get('streak',0),d.get('best_streak',0),json.dumps(d.get('achievements',[]),ensure_ascii=False)))
    c.commit(); c.close()

def db_record_result(chat_id,user_id,game,won):
    c=db_conn(); c.execute("INSERT INTO game_results(chat_id,user_id,game,won,created_at) VALUES(?,?,?,?,datetime('now'))",(chat_id,user_id,game,int(won))); c.commit(); c.close()

# v20 keeps the JSON files as a compatibility/fallback layer. SQLite is the authoritative analytics store.


# ============================================================
# v21 — Gaming Center 2.0
# ============================================================
async def gamestats_cmd(update, context):
    chat_id=update.effective_chat.id
    totals={}
    for key,d in GAME_STATS.items():
        if key.startswith(str(chat_id)+":"):
            for g,gd in d.get("by_game",{}).items():
                t=totals.setdefault(g,{"games":0,"wins":0}); t["games"]+=gd.get("games",0); t["wins"]+=gd.get("wins",0)
    if not totals: return await update.message.reply_text("🎮 هنوز آماری برای بازی‌های این گروه ثبت نشده.")
    names={"uno":"🃏 UNO","werewolf":"🐺 گرگینه","truth_or_dare":"🕵️ جرأت یا حقیقت"}
    await update.message.reply_text("🎮 آمار بازی‌های گروه\n\n"+"\n".join(f"{names.get(g,g)}: {d['games']} بازی | {d['wins']} برد" for g,d in totals.items()))

async def dailygame_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    today=datetime.now().strftime("%Y-%m-%d")
    seed=f"{update.effective_chat.id}:{today}"
    rng=random.Random(seed); choices=["🃏 امروز یک دور UNO سه‌نفره بازی کنید.","🐺 امشب یک دور گرگینه با نقش‌های متنوع برگزار کنید.","🎭 یک دور جرأت یا حقیقت با جمع دوستانه برگزار کنید."]
    await update.message.reply_text("🎯 چالش امروز گروه:\n\n"+rng.choice(choices)+"\n\nبا امتیازهای معمول Gaming Center ثبت می‌شود.")

async def gamingcenter_cmd(update, context):
    if not owner_feature_enabled("gaming"):
        await update.effective_message.reply_text("🎮 بخش بازی‌ها فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    await update.message.reply_text("🎮 Gaming Center 2.0\n\n🃏 /uno\n🐺 /gorgineh\n🏆 /leaderboard\n🎖️ /achievements\n📊 /gamestats\n🎯 /dailygame\n\nبازی‌ها مستقل‌اند و در یک گروه هم‌زمان با هم تداخل نمی‌کنند.")


# ============================================================
# v22 — Smart Assistant 2.0
# ============================================================
ASSISTANT_MODES = {"normal":"متعادل", "friendly":"صمیمی", "fun":"شوخ و دوستانه"}

def assistant_profile_context(chat_id,user_id):
    d=get_profile_pref(chat_id,user_id); return f"لحن فعلی: {ASSISTANT_MODES.get(d.get('tone'),'متعادل')}"

async def assistant_cmd(update, context):
    if not owner_feature_enabled("assistant"):
        await update.effective_message.reply_text("🧠 Smart Assistant فعلاً توسط مالک ربات غیرفعال شده است.")
        return
    chat=update.effective_chat; user=update.effective_user; d=get_profile_pref(chat.id,user.id)
    topics=[]
    mem=_get_user_memory(chat.id,user.id)
    if mem:
        topics=[x.get("topic") for x in mem[-5:] if isinstance(x,dict) and x.get("topic")]
    topic_text="، ".join(dict.fromkeys(topics)) if topics else "هنوز موضوعی ثبت نشده"
    await update.message.reply_text(
        "🧠 Smart Assistant 2.0\n\n"
        f"👤 {d.get('nickname') or user.first_name or 'دوست'}\n"
        f"💬 {assistant_profile_context(chat.id,user.id)}\n"
        f"🗂️ موضوعات اخیر: {topic_text}\n\n"
        "من سعی می‌کنم فقط وقتی مطمئنم به موضوع قبلی اشاره کنم و بین کاربران/گروه‌ها حافظه را قاطی نکنم. ✨"
    )

async def assistant_clear_cmd(update, context):
    key=_memory_key(update.effective_chat.id,update.effective_user.id)
    user_short_memory.pop(key,None); conversation_context.pop(key,None); conversation_topic_memory.pop(key,None); SMART_DIALOGUE_STATE.pop(key,None)
    await update.message.reply_text("🧹 حافظه گفت‌وگویی موقت همین گفت‌وگو پاک شد.")


def main():
    if not BOT_TOKEN:
        raise SystemExit("متغیر محیطی BOT_TOKEN تنظیم نشده. با export BOT_TOKEN=... مقداردهیش کن.")
    db_init()
    try: db_sync_stats_from_json()
    except Exception as exc: logger.warning("SQLite sync failed: %s", exc)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fal", fal_cmd))
    app.add_handler(CommandHandler("tarot", tarot_cmd))
    app.add_handler(CommandHandler("hafez", hafez_cmd))
    app.add_handler(CommandHandler("shans", shans_cmd))
    app.add_handler(CommandHandler("eightball", eightball_cmd))
    app.add_handler(CommandHandler("wheel", wheel_cmd))
    app.add_handler(CommandHandler("td", td_cmd))
    app.add_handler(CommandHandler("rules", rules_cmd))
    app.add_handler(CommandHandler("dollar", dollar_cmd))
    app.add_handler(CommandHandler("bitcoin", bitcoin_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("mystats", my_stats_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("achievements", achievements_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("setprofile", setprofile_cmd))
    app.add_handler(CommandHandler("gameprofile", group_game_profile_cmd))
    app.add_handler(CommandHandler("gamestats", gamestats_cmd))
    app.add_handler(CommandHandler("dailygame", dailygame_cmd))
    app.add_handler(CommandHandler("gaming", gamingcenter_cmd))
    app.add_handler(CommandHandler("assistant", assistant_cmd))
    app.add_handler(CommandHandler("assistant_clear", assistant_clear_cmd))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CommandHandler("botstatus", botstatus_cmd))
    app.add_handler(CommandHandler("adminpanel", adminpanel_cmd))

    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("quote", quote_cmd))
    app.add_handler(CommandHandler("compliment", compliment_cmd))
    app.add_handler(CommandHandler("roast", roast_cmd))
    app.add_handler(CommandHandler("love", love_cmd))

    app.add_handler(CommandHandler("uno", uno_start_cmd))
    app.add_handler(CommandHandler("uno_join", uno_join_cmd))
    app.add_handler(CommandHandler("uno_startgame", uno_startgame_cmd))
    app.add_handler(CommandHandler("uno_leave", uno_leave_cmd))
    app.add_handler(CommandHandler("uno_stop", uno_stop_cmd))
    app.add_handler(CallbackQueryHandler(uno_button_handler, pattern=r"^uno_"))

    app.add_handler(CommandHandler("gorgineh", gorgineh_cmd))
    app.add_handler(CommandHandler("startgame", startgame_cmd))
    app.add_handler(CommandHandler("endgame", endgame_cmd))
    app.add_handler(CommandHandler("players", players_cmd))
    app.add_handler(CallbackQueryHandler(ww_button_handler, pattern=r"^ww_"))
    app.add_handler(CommandHandler("ownerpanel", owner_panel_cmd))
    app.add_handler(CommandHandler("ownerhealth", owner_health_cmd))
    app.add_handler(CallbackQueryHandler(_callback_ack_guard(owner_callback_handler), pattern=r"^owner_"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^tdg_"))

    app.add_handler(CommandHandler("addbad", addbad_cmd))
    app.add_handler(CommandHandler("removebad", removebad_cmd))
    app.add_handler(CommandHandler("listbad", listbad_cmd))

    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("warns", warns_cmd))
    app.add_handler(CommandHandler("unwarn", unwarn_cmd))
    app.add_handler(CommandHandler("pin", pin_cmd))
    app.add_handler(CommandHandler("unpin", unpin_cmd))
    app.add_handler(CommandHandler("purge", purge_cmd))

    # نکته: هندلر بدون pattern (button_handler) باید بعد از هندلر ww_ ثبت بشه که با
    # pattern محدود شده، تا هیچ تداخلی توی دکمه‌های بازی گرگینه پیش نیاد.
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, member_left))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_text))
    # پاسخ‌های غیرمتنی Private جرأت/حقیقت: عکس، فایل متنی، استیکر، صدا، ویدئو و سایر رسانه‌ها
    # فقط در صورت داشتن نوبت فعال بررسی می‌شوند؛ پیام ورودی بلافاصله پس از استخراج موقت حذف می‌شود.
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND & (
            filters.PHOTO | filters.Document.ALL | filters.Sticker.ALL | filters.VOICE |
            filters.VIDEO | filters.ANIMATION | filters.AUDIO
        ),
        handle_td_private_media,
    ))

    app.add_error_handler(error_handler)
    app.post_init = set_commands

    # فعال‌سازی جاب زمان‌بندی‌شده‌ی یادآور - هر ۶۰ ثانیه چک می‌کنه
    if app.job_queue is not None:
        app.job_queue.run_repeating(reminder_check_job, interval=60, first=5)
        # Gemini فقط ۲ دقیقه پس از آخرین سؤال فعال می‌ماند؛ بعد خودکار خاموش می‌شود.
        app.job_queue.run_repeating(gemini_idle_timeout_job, interval=15, first=15)
        # v13: پاکسازی حافظه‌های موقت هر ۱۰ دقیقه؛ قابلیت‌ها و داده‌های ماندگار دست‌نخورده می‌مانند.
        app.job_queue.run_repeating(memory_cleanup_job, interval=600, first=600)
        app.job_queue.run_repeating(td_cleanup_job, interval=TD_CLEANUP_INTERVAL_SECONDS, first=TD_CLEANUP_INTERVAL_SECONDS)
    else:
        logger.warning(
            "JobQueue در دسترس نیست - برای فعال شدن قابلیت یادآور خودکار، پکیج رو با "
            "'pip install \"python-telegram-bot[job-queue]\"' نصب کن."
        )

    print(f"✅ دستیار هوشمند نسخه {BOT_VERSION} روشن شد و در حال اجراست...")
    app.run_polling(drop_pending_updates=True)


async def set_commands(app):
    global BOT_USERNAME
    try:
        me = await app.bot.get_me()
        BOT_USERNAME = (me.username or "").strip()
    except Exception as exc:
        BOT_USERNAME = ""
        logger.warning("Could not cache bot username for TD deep-links: %s", exc)
    commands = [
        BotCommand("start", "منوی اصلی"),
        BotCommand("fal", "فال روزانه"),
        BotCommand("tarot", "کارت تاروت"),
        BotCommand("hafez", "فال حافظ"),
        BotCommand("shans", "درصد شانس امروز"),
        BotCommand("eightball", "توپ جادویی هشت"),
        BotCommand("wheel", "چرخ شانس"),
        BotCommand("td", "جرأت یا حقیقت"),
        BotCommand("joke", "یه جوک بامزه"),
        BotCommand("quote", "یه ضرب‌المثل"),
        BotCommand("compliment", "تعریف بامزه از یه نفر (ریپلای کن)"),
        BotCommand("roast", "متلک بامزه و دوستانه (ریپلای کن)"),
        BotCommand("love", "عشق‌سنج شوخی"),
        BotCommand("uno", "ساخت بازی اونو گروهی") ,
        BotCommand("uno_join", "پیوستن به اونو") ,
        BotCommand("uno_startgame", "شروع اونو") ,
        BotCommand("uno_leave", "خروج از اونو") ,
        BotCommand("uno_stop", "توقف اونو") ,
        BotCommand("gorgineh", "شروع بازی گروهی گرگینه"),
        BotCommand("startgame", "شروع زودهنگام گرگینه - فقط ادمین"),
        BotCommand("endgame", "لغو بازی گرگینه - فقط ادمین"),
        BotCommand("players", "لیست بازیکنان گرگینه"),
        BotCommand("dollar", "قیمت دلار"),
        BotCommand("bitcoin", "قیمت بیت‌کوین"),
        BotCommand("price", "قیمت دلار و بیت‌کوین"),
        BotCommand("rules", "قوانین گروه"),
        BotCommand("stats", "آمار گروه"),
        BotCommand("botstatus", "وضعیت و دسترسی‌های ربات توی گروه"),
        BotCommand("adminpanel", "پنل مدیریت شیشه‌ای (الفاظ + یادآور خودکار) - فقط ادمین"),
        BotCommand("report", "گزارش پیام به ادمین (ریپلای کن)"),
        BotCommand("id", "دیدن آیدی عددی"),
        BotCommand("owner", "شناخت مالک گروه"),
        BotCommand("ownerpanel", "پنل خصوصی مالک ربات"),
        BotCommand("ownerhealth", "وضعیت فنی خصوصی مالک"),
        BotCommand("mute", "سکوت عضو - فقط ادمین (ریپلای کن)"),
        BotCommand("unmute", "باز کردن سکوت - فقط ادمین (ریپلای کن)"),
        BotCommand("kick", "اخراج عضو - فقط ادمین (ریپلای کن)"),
        BotCommand("ban", "بن عضو - فقط ادمین (ریپلای کن)"),
        BotCommand("warn", "اخطار به عضو - فقط ادمین (ریپلای کن)"),
        BotCommand("pin", "پین کردن پیام - فقط ادمین (ریپلای کن)"),
        BotCommand("unpin", "برداشتن پین - فقط ادمین"),
        BotCommand("purge", "پاک کردن N پیام اخیر - فقط ادمین"),
        BotCommand("addbad", "افزودن کلمه فیلتر - فقط ادمین"),
        BotCommand("removebad", "حذف کلمه فیلتر - فقط ادمین"),
        BotCommand("listbad", "تعداد کلمات فیلترشده - فقط ادمین"),
    ]
    await app.bot.set_my_commands(commands)



# ============================================================
# v41 — Curated Premium Truth & Dare
# بانک‌های قبلی حفظ شده‌اند، اما انتخاب خودکار بازی از این بانک
# باکیفیت و دسته‌بندی‌شده انجام می‌شود تا سؤال‌های مکانیکی/کم‌ارزش
# وارد تجربه اصلی نشوند.
# ============================================================
V41_TRUTH_QUESTIONS = [
    # شناخت عمیق و شخصیت
    "چه چیزی در رفتار یک آدم باعث می‌شود احساس کنی می‌توانی واقعاً به او اعتماد کنی؟",
    "اگر بخواهی یک ویژگی از شخصیتت را که کمتر دیده می‌شود برای بقیه توضیح بدهی، چه ویژگی‌ای است؟",
    "کدام بخش شخصیتت را در طول زمان بیشتر از همه تغییر داده‌ای و چه چیزی باعث این تغییر شد؟",
    "چه چیزی هست که دیگران معمولاً درباره تو اشتباه حدس می‌زنند؟",
    "در چه موقعیتی بیشتر از همیشه خود واقعی‌ات هستی؟",
    "اگر قرار باشد یک اصل شخصی را هیچ‌وقت در زندگی کنار نگذاری، آن اصل چیست؟",
    "چه چیزی باعث می‌شود از یک آدم معمولی به یک آدم قابل‌احترام برایت تبدیل شود؟",
    "کدام ویژگی خوب را در دیگران می‌بینی و آرزو می‌کنی خودت هم بیشتر داشته باشی؟",
    "چه چیزی برایت مهم است که دیگران بدون اینکه مجبور باشی توضیحش بدهی، درباره‌ات بفهمند؟",
    "اگر بخواهی خودت را با سه ویژگی توصیف کنی، کدام سه ویژگی واقعاً به تو نزدیک‌ترند و چرا؟",
    # دوستی و رابطه اجتماعی
    "به نظرت یک دوستی خوب بیشتر با شباهت ساخته می‌شود یا با تفاوت؟ چرا؟",
    "کدام رفتار کوچک می‌تواند به تو نشان دهد که یک دوست واقعاً حواسش به تو هست؟",
    "اگر دوستی بین دو نفر به خاطر یک سوءتفاهم خراب شود، به نظرت چه چیزی برای درست‌شدنش لازم است؟",
    "چه چیزی باعث می‌شود بعد از مدت‌ها هنوز یک دوستی برایت ارزشمند بماند؟",
    "اگر دوستت در تصمیم مهمی با تو مخالف باشد، ترجیح می‌دهی فقط حمایتت کند یا صادقانه مخالفتش را بگوید؟ چرا؟",
    "چه چیزی برایت سخت‌تر است: عذرخواهی‌کردن یا پذیرفتن عذرخواهی؟ چرا؟",
    "به نظرت آدم‌ها بیشتر با حرف‌هایشان شناخته می‌شوند یا با رفتاری که وقتی کسی نگاهشان نمی‌کند دارند؟",
    "چه نوع گفت‌وگویی می‌تواند باعث شود با کسی که تازه شناخته‌ای احساس نزدیکی بیشتری کنی؟",
    # خاطره و گذشته
    "کدام خاطره ساده را هیچ‌وقت فکر نمی‌کردی مهم شود، اما امروز برایت ارزشمند است؟",
    "اگر بتوانی یک روز معمولی از گذشته را دقیقاً دوباره تجربه کنی، کدام روز را انتخاب می‌کنی؟",
    "کدام اتفاق کوچک در گذشته باعث شد بعداً بفهمی چقدر روی تو اثر گذاشته است؟",
    "چه چیزی از دوران کودکی یا مدرسه هنوز بخشی از شخصیت امروزت است؟",
    "کدام خاطره با یک آهنگ، بو، فصل یا مکان خاص فوراً برایت زنده می‌شود؟",
    "اگر بتوانی به خودت در یک دوره سخت از گذشته فقط یک جمله بگویی، چه می‌گویی؟",
    "کدام اشتباه گذشته را امروز بیشتر به چشم یک درس می‌بینی تا یک شکست؟",
    # انتخاب و دیدگاه
    "اگر مجبور باشی بین زندگی کاملاً قابل‌پیش‌بینی و زندگی پر از تجربه‌های تازه یکی را انتخاب کنی، کدام را انتخاب می‌کنی و چرا؟",
    "اگر پول و زمان محدود نباشند، چه تجربه‌ای را دوست داری حداقل یک‌بار در زندگی امتحان کنی؟",
    "اگر بتوانی فقط یک تصمیم مهم آینده‌ات را از قبل مطمئن شوی، دوست داری درباره چه چیزی باشد؟",
    "در یک تصمیم سخت، چه زمانی ترجیح می‌دهی به منطق اعتماد کنی و چه زمانی به حس درونی؟",
    "اگر مجبور باشی بین موفقیت بزرگ و آرامش بیشتر یکی را انتخاب کنی، چه چیزی انتخابت را تعیین می‌کند؟",
    "چه چیزی می‌تواند باعث شود نظرت درباره یک موضوع کاملاً تغییر کند؟",
    "کدام ارزش را حتی اگر برایت سخت باشد، حاضر نیستی به خاطر منفعت کوتاه‌مدت کنار بگذاری؟",
    # آینده و آرزو
    "اگر پنج سال بعد از زندگی‌ات فقط یک صحنه را ببینی، دوست داری آن صحنه چه چیزی را نشان دهد؟",
    "کدام آرزو را هنوز جدی دنبال نکرده‌ای اما واقعاً دوست داری روزی امتحانش کنی؟",
    "اگر بتوانی یک مهارت را بدون سال‌ها تمرین یاد بگیری، کدام مهارت را انتخاب می‌کنی و چرا؟",
    "چه چیزی را دوست داری در آینده درباره نسخه امروزی خودت با افتخار به یاد بیاوری؟",
    "اگر یک سال کامل فرصت داشته باشی فقط روی یک چیز مهم زندگی‌ات تمرکز کنی، چه چیزی را انتخاب می‌کنی؟",
    # سرگرمی و رسانه با ارزش گفتگو
    "کدام فیلم، سریال، انیمه، کتاب یا بازی باعث شد بعد از تمام‌شدنش هنوز درباره یک ایده یا شخصیت آن فکر کنی؟ چرا؟",
    "اگر قرار باشد یک اثر هنری یا بازی را به کسی که تو را نمی‌شناسد معرفی کنی تا کمی با سلیقه‌ات آشنا شود، چه چیزی را انتخاب می‌کنی؟",
    "کدام شخصیت داستانی را به خاطر یک ویژگی‌اش تحسین می‌کنی، حتی اگر با همه تصمیم‌هایش موافق نباشی؟",
    "چه نوع داستانی بیشتر تو را درگیر می‌کند: داستانی که امید می‌دهد، غافلگیر می‌کند یا وادارت می‌کند فکر کنی؟ چرا؟",
    "اگر بتوانی با یک شخصیت خیالی یک گفت‌وگوی واقعی داشته باشی، چه سؤالی از او می‌پرسی؟",
    # خلاق و فرضی
    "اگر زندگی یک بازی بود، فکر می‌کنی الان در کدام مرحله آن هستی و مرحله بعدی برایت چه چالشی دارد؟",
    "اگر بتوانی یک قانون جدید برای دنیا تعیین کنی که همه فقط یک روز مجبور به رعایتش باشند، چه قانونی می‌گذاری و چرا؟",
    "اگر فردا همه آدم‌ها فقط یک ویژگی تو را به خاطر بسپارند، دوست داری آن ویژگی چه باشد؟",
    "اگر بتوانی یک روز کامل را با نسخه‌ای از خودت که ده سال دیگر است بگذرانی، درباره چه چیزی با او حرف می‌زنی؟",
    "اگر قرار باشد یک جمله روی جلد داستان زندگی تو نوشته شود، چه جمله‌ای انتخاب می‌کنی و چرا؟",
    "اگر بتوانی یک سؤال از تمام اعضای این جمع بپرسی که واقعاً جواب‌های متفاوتی ایجاد کند، سؤال تو چیست؟",
    # خودشناسی و ارزش
    "چه چیزی بیشتر از آنچه انتظار داشتی روی حال خوبت اثر می‌گذارد؟",
    "وقتی از یک دوره سخت عبور می‌کنی، معمولاً چه چیزی کمک می‌کند دوباره خودت را پیدا کنی؟",
    "کدام عادت یا طرزفکر را دوست داری در آینده تغییر بدهی، نه به خاطر دیگران بلکه برای خودت؟",
    "چه چیزی برای تو معنای «یک زندگی خوب» را می‌سازد؟",
    "اگر بخواهی یک ویژگی را در خودت بیشتر تقویت کنی، کدام را انتخاب می‌کنی و چرا؟",
    "چه چیزی باعث می‌شود احساس کنی زمانی که برای یک نفر گذاشته‌ای واقعاً ارزش داشته است؟",
    "کدام حقیقت درباره بزرگ‌شدن را دیرتر از چیزی که انتظار داشتی فهمیدی؟",
    "اگر بخواهی یک درس مهمی که زندگی تا امروز به تو داده را در یک جمله بگویی، چه می‌گویی؟",
]

V41_DARE_ACTIONS = [
    "یک خاطره واقعی و بی‌خطر تعریف کن که در آن یک اتفاق کوچک، روزت را بهتر کرد؛ حداقل ۳ جمله و بگو چرا هنوز یادت مانده است.",
    "یک داستان کوتاه سه‌جمله‌ای بساز که شروع، یک اتفاق غیرمنتظره و پایان مشخص داشته باشد.",
    "یک فیلم، سریال، انیمه یا بازی را بدون گفتن نامش با چهار سرنخ منصفانه توصیف کن و بگو چرا پیشنهادش می‌کنی.",
    "یک سؤال عمیق طراحی کن که جوابش نیاز به فکرکردن داشته باشد؛ خودت هم جواب بده و توضیح بده چرا این سؤال را انتخاب کردی.",
    "برای خودِ پنج سال بعدت یک پیام بنویس؛ حداقل ۴ جمله و شامل یک امید، یک هدف و یک چیزی که دوست داری هیچ‌وقت فراموش نکنی.",
    "یک شخصیت خیالی بساز و در حداقل ۵ جمله معرفی‌اش کن: هدف، ویژگی خوب، ضعف، یک ترس بی‌خطر و یک تصمیم مهم.",
    "یک سفر خیالی برای جمع طراحی کن: مقصد، زمان تقریبی، یک فعالیت اصلی و دلیل انتخاب هرکدام را توضیح بده.",
    "یک ایده واقعی و قابل‌اجرا برای بهترشدن فضای همین گروه پیشنهاد بده و حداقل دو دلیل برای مفیدبودنش بنویس.",
    "یک پایان متفاوت برای یک داستان خیالی بساز؛ حداقل ۴ جمله بنویس و توضیح بده چرا این پایان را انتخاب کردی.",
    "سه ویژگی یک دوست قابل‌اعتماد را بنویس و سپس با یک مثال کوتاه توضیح بده کدام ویژگی برای خودت مهم‌تر است.",
    "یک معمای کوتاه و منصفانه برای گروه طراحی کن؛ حداقل ۴ جمله و بدون نوشتن جواب معما.",
    "یک تصویر خیالی را فقط با کلمات توصیف کن؛ رنگ، نور، صدا، فضا و یک جزئیات غیرمنتظره را در حداقل ۵ جمله بیاور.",
    "چیزی را که واقعاً بلد هستی در قالب یک آموزش سه‌مرحله‌ای برای بقیه توضیح بده؛ هر مرحله باید یک نکته مشخص داشته باشد.",
    "یک هدف کوچک و واقعی برای یک ماه آینده تعریف کن و سه قدم مشخص و قابل‌انجام برای رسیدن به آن بنویس.",
    "دو برنامه کاملاً متفاوت برای یک روز آزاد طراحی کن؛ یکی آرام و یکی پرتحرک، سپس یکی را با دلیل انتخاب کن.",
    "یک صحنه خیالی چهار تا پنج جمله‌ای بنویس که دو شخصیت در آن یک سوءتفاهم بامزه را حل می‌کنند.",
    "یک پیام کوتاه و صادقانه برای تشکر از یک رفتار خوب بنویس؛ درباره یک رفتار مشخص باشد، نه تعریف کلی.",
    "یک باور یا نظر شخصی درباره یک موضوع روزمره بنویس و حداقل دو دلیل یا تجربه برایش بیاور.",
    "یک بازی کوتاه برای همین جمع طراحی کن که قوانینش در چهار جمله روشن باشد و همه بتوانند بدون ابزار خاص اجراش کنند.",
    "یک شهر یا کشور را انتخاب کن و سه تجربه‌ای را که واقعاً دوست داری آنجا داشته باشی توضیح بده؛ دلیل انتخاب مقصد را هم بگو.",
    "یک خاطره را بدون نام افراد و بدون اطلاعات خصوصی تعریف کن و فقط روی حس، فضا و اتفاق اصلی تمرکز کن؛ حداقل ۴ جمله.",
    "یک موضوع کاملاً معمولی انتخاب کن و درباره‌اش یک سخنرانی چهار جمله‌ای کاملاً جدی اما خلاقانه بنویس.",
    "بین دو ارزش متفاوت یک انتخاب سخت طراحی کن، یکی را انتخاب کن و حداقل دو دلیل برای انتخابت ارائه بده.",
    "یک روز ایده‌آل خودت را از صبح تا شب در حداقل پنج بخش بنویس و بگو کدام بخش برایت از همه مهم‌تر است.",
    "یک صحنه را که دوست داشتی از آن عکس بگیری بدون فرستادن عکس توصیف کن؛ حداقل پنج جزئیات قابل‌تصور بده.",
    "یک سؤال جالب از یکی از بازیکنان بپرس که درباره علاقه یا دیدگاهش باشد و بعد توضیح بده چرا آن سؤال را انتخاب کردی.",
    "یک توصیه‌ای که واقعاً به آن باور داری بنویس و با یک تجربه یا دلیل توضیح بده چرا به آن باور داری.",
    "یک اتفاق معمولی از امروز یا این هفته را طوری تعریف کن که انگار صحنه‌ای از یک فیلم است؛ حداقل ۴ جمله.",
    "سه چیز کوچک را که معمولاً روزت را بهتر می‌کنند بنویس و توضیح بده حذف کدام‌یک بیشتر برایت محسوس خواهد بود.",
    "یک قانون جادویی برای یک روز زندگی تعریف کن و در حداقل چهار جمله توضیح بده چه پیامدهای جالبی ایجاد می‌کند.",
    "یک شخصیت داستانی را انتخاب کن و بدون گفتن نامش، چهار ویژگی رفتاری او را توصیف کن تا گروه بتواند حدس بزند.",
    "یک خاطره یا تجربه را در قالب سه پرده کوتاه تعریف کن: قبل از اتفاق، خود اتفاق و چیزی که بعدش فهمیدی.",
    "یک سؤال دوگزینه‌ای واقعاً سخت برای گروه طراحی کن که هر دو گزینه دلیل داشته باشند؛ سپس انتخاب خودت را توضیح بده.",
    "یک مکان خیالی بساز که بعد از یک روز شلوغ دوست داری به آن بروی و حداقل پنج ویژگی آن را توصیف کن.",
    "یک مهارت یا موضوعی را که دوست داری بهتر یاد بگیری انتخاب کن و یک برنامه سه‌مرحله‌ای ساده برای شروعش بنویس.",
    "یک داستان کوتاه بساز که سه کلمه «باران»، «چراغ» و «پنجره» در آن طبیعی استفاده شده باشند؛ حداقل ۴ جمله.",
    "یک پیام دوستانه برای تشویق یکی از بازیکنان بنویس که مشخص و محترمانه باشد و حداقل دو جمله داشته باشد.",
    "یک انتخاب فرضی بین «تجربه بیشتر» و «امنیت بیشتر» بساز، خودت انتخاب کن و توضیح بده چه چیزی تصمیم تو را تعیین می‌کند.",
]

# این بانک عمداً جایگزین بانک انتخاب خودکار می‌شود؛ بانک‌های قبلی در فایل باقی هستند
# و برای سازگاری با سایر بخش‌ها حذف نشده‌اند.
TRUTH_QUESTIONS = list(V41_TRUTH_QUESTIONS)
DARE_ACTIONS = list(V41_DARE_ACTIONS)

# دسته‌بندی دقیق‌تر برای جلوگیری از پشت‌سرهم آمدن سؤال‌های هم‌جنس.
V41_CATEGORY_RULES = {
    "self": ("خودت", "شخصیت", "ویژگی", "عادت", "خود واقعی", "خودشناسی"),
    "friendship": ("دوست", "دوستی", "اعتماد", "عذرخواهی", "گروه", "بازیکن"),
    "memory": ("خاطره", "گذشته", "کودکی", "مدرسه", "سال", "روز معمولی"),
    "future": ("آینده", "پنج سال", "هدف", "مهارت", "ماه آینده", "سال کامل"),
    "values": ("ارزش", "اصل شخصی", "منطقی", "حس درونی", "موفقیت", "زندگی خوب"),
    "media": ("فیلم", "سریال", "انیمه", "بازی", "کتاب", "شخصیت داستانی", "موسیقی"),
    "creative": ("خیالی", "داستان", "معما", "قانون جادویی", "شخصیت", "سؤال دوگزینه‌ای"),
    "daily": ("روز", "صبح", "شب", "آرام", "معمولی"),
}


def v41_content_category(text):
    t = td_norm_text(text)
    for name, markers in V41_CATEGORY_RULES.items():
        if any(m in t for m in markers):
            return name
    return "other"


def v41_pick(game, kind):
    pool = TRUTH_QUESTIONS if kind == "truth" else DARE_ACTIONS
    used_key = "used_truth" if kind == "truth" else "used_dare"
    last_key = "last_truth_category" if kind == "truth" else "last_dare_category"
    used = game.setdefault(used_key, set())
    available = [i for i in range(len(pool)) if i not in used]
    if not available:
        used.clear()
        available = list(range(len(pool)))
    last = game.get(last_key)
    preferred = [i for i in available if v41_content_category(pool[i]) != last]
    # اگر هنوز انتخاب‌ها محدود باشند، یک دسته‌ای را که در چند نوبت اخیر دیده نشده ترجیح بده.
    recent_key = "truth_recent_categories" if kind == "truth" else "dare_recent_categories"
    recent = game.setdefault(recent_key, [])
    candidates = [i for i in preferred if v41_content_category(pool[i]) not in recent[-2:]] or preferred or available
    idx = random.choice(candidates)
    used.add(idx)
    cat = v41_content_category(pool[idx])
    game[last_key] = cat
    recent.append(cat)
    del recent[:-3]
    return pool[idx]

# جایگزینی امن انتخاب محتوا: سایر فراخوانی‌های قدیمی td_pick همچنان کار می‌کنند.
td_pick = v41_pick

# سخت‌گیری بیشتر برای پاسخ‌های جرأت v41: هر چالش باید حداقل ساختار محتوایی خود را داشته باشد.
V41_DARE_RULES = {
    "خاطره واقعی و بی‌خطر": (3, 15),
    "داستان کوتاه سه‌جمله‌ای": (3, 12),
    "فیلم، سریال، انیمه یا بازی": (4, 16),
    "سؤال عمیق طراحی کن": (3, 12),
    "خودِ پنج سال بعدت": (4, 15),
    "شخصیت خیالی بساز": (5, 18),
    "یک سفر خیالی برای جمع": (3, 14),
    "ایده واقعی و قابل‌اجرا": (2, 10),
    "پایان متفاوت برای یک داستان خیالی": (4, 14),
    "سه ویژگی یک دوست قابل‌اعتماد": (3, 10),
    "معمای کوتاه و منصفانه": (4, 14),
    "تصویر خیالی را فقط با کلمات": (5, 16),
    "آموزش سه‌مرحله‌ای": (3, 12),
    "هدف کوچک و واقعی برای یک ماه": (3, 12),
    "دو برنامه کاملاً متفاوت": (3, 12),
    "صحنه خیالی چهار تا پنج جمله‌ای": (4, 14),
    "پیام کوتاه و صادقانه برای تشکر": (2, 8),
    "باور یا نظر شخصی": (2, 10),
    "بازی کوتاه برای همین جمع": (4, 14),
    "شهر یا کشور را انتخاب کن": (3, 12),
    "خاطره را بدون نام افراد": (4, 14),
    "سخنرانی چهار جمله‌ای": (4, 14),
    "انتخاب سخت طراحی کن": (3, 12),
    "روز ایده‌آل خودت": (5, 15),
    "صحنه را که دوست داشتی از آن عکس بگیری": (3, 14),
    "سؤال جالب از یکی از بازیکنان": (2, 10),
    "توصیه‌ای که واقعاً به آن باور داری": (2, 10),
    "اتفاق معمولی از امروز یا این هفته": (4, 14),
    "سه چیز کوچک را": (3, 10),
    "قانون جادویی برای یک روز": (4, 14),
    "شخصیت داستانی را انتخاب کن": (4, 12),
    "سه پرده کوتاه": (3, 14),
    "سؤال دوگزینه‌ای واقعاً سخت": (3, 12),
    "مکان خیالی بساز": (4, 14),
    "مهارت یا موضوعی را که دوست داری": (3, 12),
    "باران، چراغ و پنجره": (4, 12),
    "پیام دوستانه برای تشویق": (2, 8),
    "تجربه بیشتر و امنیت بیشتر": (3, 12),
}

# لایه نهایی verifier جرأت v42: قواعد نسخه‌های قبلی حفظ می‌شوند، اما قبل از تأیید
# یک بررسی معنایی/کیفی هم انجام می‌شود تا پاسخ کوتاه، کپی‌شده یا بی‌ربط قبول نشود.
# در این نسخه تابع پایه از قبل با نام _td_base_validate_dare تعریف شده است؛
# هرگز نباید قبل از تعریف td_validate_dare به خودش alias شود.

def td_validate_dare(task, answer):
    task_text = str(task or '').strip()
    raw = str(answer or '').strip()
    a = td_norm_text(raw)
    if td_is_filler(raw):
        return False, 'این پاسخ شبیه پیام آزمایشی یا طفره‌رفتن است؛ خودِ جرأت را کامل انجام بده.'
    if len(raw) > 700:
        return False, 'پاسخ خیلی طولانی است؛ فقط نتیجه واقعی همان چالش را بفرست.'

    # اگر جرأت ساختار مشخصی دارد، قواعد دقیق v41 اولویت دارند.
    marker = next((m for m in V41_DARE_RULES if m in task_text), None)
    if marker:
        words = td_words(raw)
        sentences = [x.strip() for x in re.split(r'[.!؟?]+', raw) if x.strip()]
        min_sentences, min_words = V41_DARE_RULES[marker]
        if len(sentences) < min_sentences or len(words) < min_words:
            return False, f'پاسخ هنوز شرایط این چالش را ندارد؛ حداقل {min_sentences} جمله و {min_words} کلمه لازم است.'
        meaningful = [w for w in words if len(w) > 2 and w not in TD_STOPWORDS]
        if len(set(meaningful)) < max(3, min_words // 4):
            return False, 'پاسخ بیش از حد تکراری یا بی‌محتواست؛ نتیجه واقعی چالش را بنویس.'
        sim = SequenceMatcher(None, td_norm_text(task_text), a).ratio()
        if sim > 0.82:
            return False, 'پاسخ بیشتر شبیه تکرار متن جرأت است؛ نتیجه واقعی انجام چالش را بفرست.'
        return True, 'پاسخ از نظر ساختار، استقلال و محتوای لازم برای این چالش تأیید شد.'

    # برای قواعد قدیمی‌تر، verifier دقیق قبلی اجرا می‌شود؛ اگر قبول نکرد، رد می‌شود.
    ok, msg = _td_base_validate_dare(task_text, raw)
    if not ok:
        return False, msg

    # حتی در قواعد قدیمی، پاسخ بسیار شبیه متن خود چالش یا کاملاً تکراری نباشد.
    sim = SequenceMatcher(None, td_norm_text(task_text), a).ratio()
    words = td_words(raw)
    if sim > 0.84:
        return False, 'پاسخ بیشتر شبیه کپی‌کردن متن جرأت است؛ نتیجه واقعی را بفرست.'
    if len(words) >= 6 and len(set(words)) <= max(2, len(words) // 4):
        return False, 'پاسخ بیش از حد تکراری است و به‌عنوان انجام واقعی چالش تأیید نمی‌شود.'
    return True, msg


# v49 Final Resource Manager: multi-source health/backoff, allowlist, cache-first, GIF-only download validation.


if __name__ == "__main__":
    main()
