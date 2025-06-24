moduleInfo = {
    "meta": {
        "name": "TelegramAdapter",
        "version": "1.2.1",
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

# build_hash="2d58aa34acbbd99767ba2616ba5b5b7b3757a229083f6ee6059f447bc9f2eaba"
