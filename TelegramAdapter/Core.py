import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from ErisPulse import sdk

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
                    "/sendPhoto",
                    field_name="photo",
                    file=file,
                    endpoint="sendPhoto",
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Document(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "/sendDocument",
                    field_name="document",
                    file=file,
                    endpoint="sendDocument",
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Video(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "/sendVideo",
                    field_name="video",
                    file=file,
                    endpoint="sendVideo",
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def Audio(self, file: bytes, caption: str = "", parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._upload_file_and_call_api(
                    "/sendAudio",
                    field_name="audio",
                    file=file,
                    endpoint="sendAudio",
                    chat_id=self._target_id,
                    caption=caption,
                    parse_mode=parse_mode
                )
            )

        def EditMessageText(self, message_id: int, text: str, parse_mode: str = "markdown"):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="editMessageText",
                    chat_id=self._target_id,
                    message_id=message_id,
                    text=text,
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

        def DeleteMessage(self, message_id: int):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="deleteMessage",
                    chat_id=self._target_id,
                    message_id=message_id
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

        def GetChat(self):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="getChat",
                    chat_id=self._target_id
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

        async def _upload_file_and_call_api(self, upload_endpoint, field_name, file, endpoint, **kwargs):
            url = f"{self._adapter.base_url}/{endpoint.lstrip('/')}"
            sdk.logger.info(f"Uploading file to {url}")
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
                result = await response.json()

            return result

    def __init__(self, sdk):
        super().__init__()
        self.sdk = sdk
        self.logger = sdk.logger
        self.config = self._load_config()
        self.token = self.config.get("token", "")
        self.session = None
        self.server = None
        self.poll_task = None
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.proxy_info = self.config.get("proxy")
        self._setup_event_mapping()

    def _load_config(self):
        config = self.sdk.env.getConfig("Telegram_Adapter")
        if not config:
            default_config = {
                # 必填：Telegram Bot Token
                "token": "YOUR_BOT_TOKEN",
                # Webhook 模式下的服务配置（如使用 webhook）
                "server": {
                    "host": "127.0.0.1",            # 推荐监听本地，防止外网直连
                    "port": 8443,                   # 监听端口
                    "path": "/telegram/webhook"     # Webhook 路径
                },
                "webhook": {
                    "host": "example.com",          # Telegram API 监听地址（外部地址）
                    "port": 8443,                   # 监听端口
                    "path": "/telegram/webhook"     # Webhook 路径
                },
                # 启动模式: webhook 或 polling
                "mode": "polling",
                # 可选：代理配置（用于连接 Telegram API）
                "proxy": {
                    "host": "127.0.0.1",
                    "port": 1080,
                    "type": "socks5"  # 支持 socks4 / socks5
                }
            }
            try:
                sdk.logger.warning("电报(Telegram)适配器配置不存在，已自动创建默认配置")
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

    async def call_api(self, endpoint: str, **params):
        url = f"{self.base_url}/{endpoint}"
        async with self.session.post(url, json=params) as response:
            result = await response.json()
        return result

    async def set_webhook(self):
        server_config = self.config.get("server", {})
        webhook_config = self.config.get("webhook", {})

        # 构造 Webhook URL（对外地址），优先使用 webhook 配置
        if webhook_config:
            webhook_url = f"https://{webhook_config.get('host')}:{webhook_config.get('port', 443)}{webhook_config.get('path', '/telegram/webhook')}"
        else:
            webhook_url = f"https://{server_config.get('host', 'localhost')}:{server_config.get('port', 443)}{server_config.get('path', '/telegram/webhook')}"

        self.logger.info(f"正在设置 Webhook 地址: {webhook_url}")

        # 构造基础参数
        params = {
            "url": webhook_url,
            "drop_pending_updates": True
        }

        cert_data = None
        cert_source = None

        # 优先使用 cert_content（字符串形式）
        if "cert_content" in self.config:
            try:
                cert_data = self.config["cert_content"].encode("utf-8")
                cert_source = "cert_content (inline)"
            except Exception as e:
                self.logger.error(f"解析内联证书失败: {e}")

        # 其次尝试 cert_path（文件路径）
        elif "cert_path" in self.config:
            cert_path = self.config["cert_path"]
            try:
                with open(cert_path, "rb") as f:
                    cert_data = f.read()
                cert_source = f"cert_path ({cert_path})"
            except Exception as e:
                self.logger.error(f"读取证书文件失败: {e}")

        else:
            self.logger.warning("未配置 SSL 证书，请确认 Webhook URL 使用 HTTPS 并由反向代理处理 SSL")

        # 构造请求数据
        if cert_data:
            data = aiohttp.FormData()
            data.add_field("url", webhook_url)
            data.add_field("drop_pending_updates", "true")
            data.add_field("certificate", cert_data, filename="cert.pem", content_type="application/x-pem-file")
            self.logger.info(f"使用 {cert_source} 设置 Webhook 并上传证书")
        else:
            data = params
            self.logger.info("未上传证书，Telegram 将验证域名证书")

        url = f"{self.base_url}/setWebhook"

        async with self.session.post(url, data=data) as response:
            result = await response.json()
            self.logger.info(f"SetWebhook 返回结果: {result}")

        return result

    async def delete_webhook(self):
        return await self.call_api("deleteWebhook")

    async def get_webhook_info(self):
        return await self.call_api("getWebhookInfo")

    async def _handle_webhook(self, request):
        try:
            data = await request.json()
            update_id = data.get("update_id")
            self.logger.debug(f"处理Webhook: {data}")
            for event_type in self.event_map:
                if event_type in data:
                    mapped_type = self.event_map[event_type]
                    self.logger.debug(f"处理Webhook事件: {mapped_type}")
                    await self.emit(mapped_type, data)
                    break

            return aiohttp.web.Response(text="OK", status=200)

        except Exception as e:
            self.logger.error(f"Webhook处理错误: {str(e)}")
            return aiohttp.web.Response(text=f"ERROR: {str(e)}", status=500)

    async def start_server(self):
        if not self.config.get("server"):
            self.logger.warning("Webhook服务器未配置，将不会启动")
            return

        server_config = self.config["server"]
        app = aiohttp.web.Application()
        app.router.add_post(
            server_config.get("path", "/"),
            self._handle_webhook
        )

        self.server = aiohttp.web.AppRunner(app)
        await self.server.setup()

        site = aiohttp.web.TCPSite(
            self.server,
            server_config.get("host", "127.0.0.1"),
            server_config.get("port", 8080)
        )

        await site.start()
        self.logger.info(f"Webhook服务器已启动: {site.name}")

    async def stop_server(self):
        if self.server:
            await self.server.cleanup()
            self.server = None
            self.logger.info("Webhook服务器已停止")

    async def _poll_updates(self):
        offset = 0
        while True:
            try:
                updates = await self.call_api("getUpdates", offset=offset, timeout=60)
                self.logger.debug(f"轮询更新: {updates}")
                if "result" in updates and len(updates["result"]) > 0:
                    for update in updates["result"]:
                        update_id = update["update_id"]
                        if update_id >= offset:
                            offset = update_id + 1
                        for event_type in self.event_map:
                            if event_type in update:
                                mapped_type = self.event_map[event_type]
                                self.logger.debug(f"处理轮询事件: {mapped_type}")
                                await self.emit(mapped_type, update)
                                break
            except Exception as e:
                self.logger.error(f"轮询更新失败: {e}")
                await asyncio.sleep(5)

    async def start(self):
        import ssl
        import certifi
        from aiohttp_socks import ProxyType, ProxyConnector

        proxy = self.proxy_info
        connector = None

        if proxy and proxy.get("host") and proxy.get("port"):
            proxy_type = proxy.get("type")
            host = proxy["host"]
            port = proxy["port"]
            if proxy_type in ["socks5", "socks4"]:
                proxy_type_enum = ProxyType.SOCKS5 if proxy_type == "socks5" else ProxyType.SOCKS4
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                connector = ProxyConnector(
                    proxy_type=proxy_type_enum,
                    host=host,
                    port=port,
                    ssl=ssl_context
                )
            else:
                self.logger.warning(f"不支持的代理类型: {proxy_type}")

        self.session = aiohttp.ClientSession(connector=connector) if connector else aiohttp.ClientSession()

        webhook_info = await self.get_webhook_info()
        if webhook_info.get("url"):
            self.logger.info("检测到已有 Webhook，正在删除...")
            await self.delete_webhook()

        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass
            self.poll_task = None

        if self.config.get("mode") == "webhook":
            await self.set_webhook()
            await self.start_server()
        elif self.config.get("mode") == "polling":
            self.poll_task = asyncio.create_task(self._poll_updates())
        else:
            self.logger.warning("未配置启动模式，请设置 mode 为 webhook 或 polling")


    async def shutdown(self):
        await self.stop_server()

        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass
            self.poll_task = None

        if self.config.get("mode") == "webhook":
            self.logger.info("正在删除 Webhook 配置...")
            await self.delete_webhook()

        if self.session:
            await self.session.close()
            self.session = None

        self.logger.info("Telegram适配器已关闭")