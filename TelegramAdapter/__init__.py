moduleInfo = {
    "meta": {
        "name": "TelegramAdapter",
        "version": "1.1.6",
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

# build_hash="59540fc2a833df13e97c39bd916f002f17672d103d1b7348ca1cd6866a1aaa06"
