moduleInfo = {
    "meta": {
        "name": "TelegramAdapter",
        "version": "1.2.0",
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
    "tg":  TelegramAdapter,
}
