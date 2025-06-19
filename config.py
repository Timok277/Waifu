# -*- coding: utf-8 -*-

# --- РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РЎРµСЂРІРµСЂР° ---
SERVER_URL = "http://26.186.125.19:8000"
STATUS_ENDPOINT = f"{SERVER_URL}/status"
ERROR_ENDPOINT = f"{SERVER_URL}/error"
LOG_ENDPOINT = f"{SERVER_URL}/log"

# --- Р¦РµР»РµРІС‹Рµ РћРєРЅР° ---
# РСЃРїРѕР»СЊР·СѓСЋС‚СЃСЏ РґР»СЏ РѕРїСЂРµРґРµР»РµРЅРёСЏ, РіРґРµ РїРµСЂСЃРѕРЅР°Р¶ Р±СѓРґРµС‚ "СЃРёРґРµС‚СЊ"
TARGET_WINDOW_TITLES = ["Visual Studio Code", "Visual Studio"]
TARGET_WINDOW_PROCESSES = ["Code.exe", "devenv.exe"]

# --- РџСѓС‚Рё Рє РЎРїСЂР°Р№С‚Р°Рј ---
SPRITE_PATHS = {
    "idle": "assets/anime_waifu_idle_pose_transparent_background_index_3.png",
    "walk1": "assets/anime_girl_walking_animation_frame_index_0.png",
    "walk2": "assets/anime_girl_walking_animation_frame_index_1.png",
    "sit": "assets/anime_girl_waifu_sitting_transparent_background_index_2.png",
}

# --- РџР°СЂР°РјРµС‚СЂС‹ РџРµСЂСЃРѕРЅР°Р¶Р° ---
SPRITE_WIDTH, SPRITE_HEIGHT = 150, 200

# --- РќР°СЃС‚СЂРѕР№РєРё Pygame ---
FPS = 60

# --- РРЅС‚РµСЂРІР°Р»С‹ (РІ РјРёР»Р»РёСЃРµРєСѓРЅРґР°С…) ---
ANIMATION_INTERVAL = 150
PHYSICS_INTERVAL = 50 
CURSOR_CHECK_INTERVAL = 200 
STATUS_SEND_INTERVAL = 5000 

# --- Р¤РёР·РёС‡РµСЃРєРёРµ РљРѕРЅСЃС‚Р°РЅС‚С‹ ---
WALK_SPEED = 2
JUMP_POWER = 12
GRAVITY = 0.98
TERMINAL_VELOCITY = 10
CURSOR_EVADE_DISTANCE = 50

# --- РќРѕРІС‹Рµ РїР°СЂР°РјРµС‚СЂС‹ РґР»СЏ СѓРїСЂР°РІР»СЏРµРјРѕРіРѕ РїСЂС‹Р¶РєР° ---
JUMP_HEIGHT = 1100
TIME_TO_JUMP_APEX = 0.7

# --- РџРѕРІРµРґРµРЅРёРµ AI ---
AI_UPDATE_INTERVAL = 3.0       # РљР°Рє С‡Р°СЃС‚Рѕ AI РїСЂРёРЅРёРјР°РµС‚ СЂРµС€РµРЅРёСЏ (РІ СЃРµРєСѓРЅРґР°С…)
PLATFORM_UPDATE_INTERVAL = 2.0 # РљР°Рє С‡Р°СЃС‚Рѕ СЃРєР°РЅРёСЂРѕРІР°С‚СЊ РѕРєРЅР° РЅР° СЂР°Р±РѕС‡РµРј СЃС‚РѕР»Рµ

# --- РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РћР±РЅРѕРІР»РµРЅРёР№ ---
CURRENT_VERSION = "2.1.3.8.1" # РўРµРєСѓС‰Р°СЏ РІРµСЂСЃРёСЏ РїСЂРёР»РѕР¶РµРЅРёСЏ
GITHUB_REPO = "Timok277/Waifu" # РџСѓС‚СЊ Рє СЂРµРїРѕР·РёС‚РѕСЂРёСЋ

# --- РћС‚Р»Р°РґРєР° ---
DEBUG_LOGGING = False # Р’РєР»СЋС‡РёС‚СЊ РґР»СЏ РІС‹РІРѕРґР° РїРѕРґСЂРѕР±РЅС‹С… Р»РѕРіРѕРІ СЃРѕСЃС‚РѕСЏРЅРёСЏ РІ РєРѕРЅСЃРѕР»СЊ 

# --- Р¤РёР·РёРєР° Рё РґРІРёР¶РµРЅРёРµ ---
MAX_FALL_SPEED = 25 
MAX_HORIZONTAL_SPEED = 25 # РћРіСЂР°РЅРёС‡РёРІР°РµРј РјР°РєСЃРёРјР°Р»СЊРЅСѓСЋ СЃРєРѕСЂРѕСЃС‚СЊ РїРѕ РіРѕСЂРёР·РѕРЅС‚Р°Р»Рё 
