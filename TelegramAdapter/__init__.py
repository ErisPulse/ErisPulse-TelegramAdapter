moduleInfo = {
    "meta": {
        "name": "TelegramAdapter",
        "version": "1.1.5",
        "description": "Telegram 协议适配器",
        "author": "wsu2059q",
        "license": "MIT"
    },
    "dependencies": {
        "requires": [],
        "optional": [],
        "pip": ["aiohttp", "aiohttp-socks", "certifi"]
    }
}

from .Core import Main

from .Core import TelegramAdapter

adapterInfo = {
    "telegram": TelegramAdapter,
    "Telegram": TelegramAdapter,
    "tg":  TelegramAdapter,
}
# build_hash="8ff363312135c1e0b24000ed4af84262e07a2d408c8e62737a19e182e2cff3a7"

# build_hash="67db1234ad959d5a4efd1fe6a4c2fedd0c7a281a0e8102a9dbb0a6b649a179af"

# build_hash="256737657f441faa45b075283ac631a4d0255f107e835da2faeaca01c2a44cce"

# build_hash="28ad36cd9b3d0c8f97280ed4723c4a5286e771a5b4572ad58f876476c2df209c"

# build_hash="876452e307721fecfb65cc3b607d93cd74e5d621d5b323da26957aeebb3cf283"
