import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from ErisPulse import sdk
from ErisPulse.Core import adapter_server
from .Converter import TelegramConverter

class TelegramAdapter(sdk.BaseAdapter):
    class Send(sdk.BaseAdapter.Send):
        def Text(self, text: str, parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendMessage",
                    chat_id=self._target_id,
                    text=text,
                    parse_mode=parse_mode
                )
            )

        def Image(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "sendPhoto",
                    field_name="photo",
                    file=file,
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Document(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "sendDocument",
                    field_name="document",
                    file=file,
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Video(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "sendVideo",
                    field_name="video",
                    file=file,
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Audio(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "sendAudio",
                    field_name="audio",
                    file=file,
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Edit(self, message_id: int, text: str, parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="editMessageText",
                    chat_id=self._target_id,
                    message_id=message_id,
                    text=text,
                    parse_mode=parse_mode
                )
            )

        def Recall(self, message_id: int):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="deleteMessage",
                    chat_id=self._target_id,
                    message_id=message_id
                )
            )

        async def CheckExist(self, message_id: int):
            try:
                result = await self._adapter.call_api(
                    "forwardMessage",
                    chat_id=self._target_id,
                    from_chat_id=self._target_id,
                    message_id=message_id
                )
                return bool(result)
            except Exception as e:
                if "message to forward not found" in str(e):
                    return False
                raise

        async def _upload_file_and_call_api(self, endpoint, field_name, file, **kwargs):
            url = f"{self._adapter.base_url}/{endpoint}"
            data = aiohttp.FormData()
            data.add_field(
                field_name,
                file,
                filename=f"file.{field_name}",
                content_type="application/octet-stream"
            )

            for key, value in kwargs.items():
                if isinstance(value, (dict, list)):
                    data.add_field(key, json.dumps(value))
                else:
                    data.add_field(key, str(value))

            async with self._adapter.session.post(url, data=data) as response:
                return await response.json()

    def __init__(self, sdk):
        super().__init__()
        self.sdk = sdk
        self.logger = sdk.logger
        self.config = self._load_config()
        self.token = self.config.get("token", "")
        self.session = None
        self.poll_task = None
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self._setup_event_mapping()
        self._proxy_enabled = self.config.get("proxy_enabled", False)
        self._proxy_config = self.config.get("proxy", {}) if self._proxy_enabled else None
        self.convert = TelegramConverter().convert  # 初始化转换器

    def _load_config(self):
        config = self.sdk.env.getConfig("Telegram_Adapter")
        if not config:
            default_config = {
                "token": "YOUR_BOT_TOKEN",
                "proxy_enabled": False,
                "proxy": {
                    "host": "127.0.0.1",
                    "port": 1080,
                    "type": "socks5"
                },
                "mode": "webhook",
                "webhook": {
                    "path": "/telegram/webhook",
                    "domain": None  # 新增域名配置项
                }
            }
            try:
                sdk.logger.warning("Telegram适配器配置不存在，已自动创建默认配置")
                self.sdk.env.setConfig("Telegram_Adapter", default_config)
                return default_config
            except Exception as e:
                self.logger.error(f"保存默认配置失败: {str(e)}")
                return default_config
        return config

    def _setup_event_mapping(self):
        self.event_map = {
            "message": "message",
            "edited_message": "message_edit",
            "channel_post": "channel_post",
            "edited_channel_post": "channel_post_edit",
            "inline_query": "inline_query",
            "chosen_inline_result": "chosen_inline_result",
            "callback_query": "callback_query",
            "shipping_query": "shipping_query",
            "pre_checkout_query": "pre_checkout_query",
            "poll": "poll",
            "poll_answer": "poll_answer"
        }

    async def _process_webhook_event(self, data: Dict):
        try:
            if not isinstance(data, dict):
                raise ValueError("事件数据必须是字典类型")

            update_id = data.get("update_id")
            if update_id is None:
                raise ValueError("无效的Telegram事件数据")

            # 找到匹配的事件类型
            for event_type in self.event_map:
                if event_type in data:
                    mapped_type = self.event_map[event_type]
                    self.logger.debug(f"Telegram事件 {event_type} -> {mapped_type}")
                    
                    # 触发原生事件
                    await self.emit(mapped_type, data)
                    
                    # 转换为OneBot12事件并提交
                    if hasattr(self.adapter, "emit"):
                        onebot_event = self.convert(data)
                        self.logger.debug(f"OneBot12事件数据: {json.dumps(onebot_event, ensure_ascii=False)}")
                        if onebot_event:
                            await self.adapter.emit(onebot_event)
                    
                    break

        except Exception as e:
            self.logger.error(f"处理Telegram事件错误: {str(e)}")
            self.logger.debug(f"原始事件数据: {json.dumps(data, ensure_ascii=False)}")

    async def register_webhook(self):
        if not self.config.get("webhook"):
            self.logger.warning("Webhook配置不存在，将不会注册")
            return

        webhook_config = self.config["webhook"]
        path = webhook_config.get("path", "/telegram/webhook")

        # 注册到统一服务器系统
        adapter_server.register_webhook(
            "telegram",
            path,
            self._process_webhook_event,
            methods=["POST"]
        )

    async def set_webhook(self):
        webhook_config = self.config.get("webhook", {})
        path = webhook_config.get("path", "/telegram/webhook")
        
        # 获取服务器配置
        server_config = self.sdk.env.getConfig("Server", {})
        
        # 优先使用webhook配置中的域名，其次使用server配置中的host
        domain = webhook_config.get("domain") or server_config.get("host", "localhost")
        port = server_config.get("port", 443)
        
        # 构造webhook URL
        webhook_url = f"https://{domain}:{port}/telegram{path}"
        self.logger.info(f"设置Telegram Webhook地址: {webhook_url}")

        return await self.call_api(
            "setWebhook",
            url=webhook_url,
            drop_pending_updates=True
        )

    async def delete_webhook(self):
        return await self.call_api("deleteWebhook")

    async def get_webhook_info(self):
        return await self.call_api("getWebhookInfo")

    async def _poll_updates(self):
        offset = 0
        while True:
            try:
                updates = await self.call_api(
                    "getUpdates",
                    offset=offset,
                    timeout=60
                )
                
                if updates.get("result"):
                    for update in updates["result"]:
                        update_id = update["update_id"]
                        if update_id >= offset:
                            offset = update_id + 1
                        
                        for event_type in self.event_map:
                            if event_type in update:
                                mapped_type = self.event_map[event_type]
                                
                                # 触发原生事件
                                await self.emit(mapped_type, update)
                                
                                # 转换为OneBot12事件并提交
                                if hasattr(self.adapter, "emit"):
                                    onebot_event = self.convert(update)
                                    self.logger.debug(f"OneBot12事件数据: {json.dumps(onebot_event, ensure_ascii=False)}")
                                    if onebot_event:
                                        await self.adapter.emit(onebot_event)
                                
                                break
            except Exception as e:
                self.logger.error(f"轮询更新失败: {e}")
                await asyncio.sleep(5)

    async def call_api(self, endpoint: str, **params):
        url = f"{self.base_url}/{endpoint}"
        async with self.session.post(url, json=params) as response:
            return await response.json()

    async def start(self):
        import ssl
        import certifi
        from aiohttp_socks import ProxyType, ProxyConnector

        # 初始化会话
        if self._proxy_enabled and self._proxy_config:
            proxy_type = self._proxy_config.get("type")
            if proxy_type in ["socks5", "socks4"]:
                proxy_type_enum = ProxyType.SOCKS5 if proxy_type == "socks5" else ProxyType.SOCKS4
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                connector = ProxyConnector(
                    proxy_type=proxy_type_enum,
                    host=self._proxy_config["host"],
                    port=self._proxy_config["port"],
                    ssl=ssl_context
                )
                self.session = aiohttp.ClientSession(connector=connector)
                self.logger.info(f"已启用{proxy_type.upper()}代理: {self._proxy_config['host']}:{self._proxy_config['port']}")
            else:
                self.logger.warning(f"不支持的代理类型: {proxy_type}, 将不使用代理")
                self.session = aiohttp.ClientSession()
        else:
            self.session = aiohttp.ClientSession()
            if self._proxy_enabled:
                self.logger.warning("代理已启用但未配置，将不使用代理")

        # 注册webhook路由
        await self.register_webhook()

        # 根据模式启动
        if self.config.get("mode") == "webhook":
            await self.set_webhook()
        elif self.config.get("mode") == "polling":
            self.poll_task = asyncio.create_task(self._poll_updates())
        else:
            self.logger.warning("未配置启动模式，请设置 mode 为 webhook 或 polling")

    async def shutdown(self):
        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass
            self.poll_task = None

        if self.config.get("mode") == "webhook":
            await self.delete_webhook()

        if self.session:
            await self.session.close()
            self.session = None

        self.logger.info("Telegram适配器已关闭")
