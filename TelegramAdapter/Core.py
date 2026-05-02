import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Any, Union
from ErisPulse import sdk
from ErisPulse.Core import router
from .Converter import TelegramConverter
from ErisPulse.Core.Event import register_event_mixin, unregister_platform_event_methods


class TelegramEventMixin:
    """Telegram 平台 Event 扩展方法"""

    def is_bot_message(self) -> bool:
        """判断消息是否来自机器人"""
        from_user = self.get("telegram_raw", {}).get("message", {}).get("from", {})
        if not from_user:
            from_user = (
                self.get("telegram_raw", {}).get("edited_message", {}).get("from", {})
            )
        return from_user.get("is_bot", False)

    def get_update_id(self) -> int:
        """获取 Telegram update ID"""
        return self.get("telegram_raw", {}).get("update_id", 0)

    def get_chat_title(self) -> str:
        """获取聊天标题"""
        chat = self.get("telegram_chat", {})
        return chat.get("title", "") if chat else ""

    def get_chat_username(self) -> str:
        """获取聊天用户名"""
        chat = self.get("telegram_chat", {})
        return chat.get("username", "") if chat else ""

    def is_edited_message(self) -> bool:
        """判断是否为编辑过的消息"""
        return "telegram_edit_time" in self

    def get_callback_data(self) -> str:
        """获取回调查询的 callback_data"""
        return self.get("telegram_callback_data")

    def get_callback_id(self) -> str:
        """获取回调查询 ID（用于应答）"""
        return self.get("telegram_callback_id", "")

    def get_inline_keyboard(self):
        """获取消息中的内联键盘"""
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_inline_keyboard":
                return seg.get("data", {}).get("inline_keyboard")
        return None

    def get_sticker_info(self) -> dict:
        """获取贴纸信息"""
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_sticker":
                return seg.get("data", {})
        return None

    def get_contact_info(self) -> dict:
        """获取联系人信息"""
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_contact":
                return seg.get("data", {})
        return None

    def get_location(self) -> dict:
        """获取位置信息"""
        for seg in self.get("message", []):
            if seg.get("type") == "location":
                return seg.get("data", {})
        return None

    def get_forward_from(self) -> dict:
        """获取转发来源信息"""
        raw = self.get("telegram_raw", {})
        msg = raw.get("message") or raw.get("edited_message") or raw.get("channel_post") or {}
        forward = msg.get("forward_from") or msg.get("forward_from_chat")
        return forward

    def is_topic_message(self) -> bool:
        """判断是否为话题/Topic 消息"""
        return "thread_id" in self

    def get_topic_id(self) -> str:
        """获取话题 ID"""
        return self.get("thread_id")


register_event_mixin("telegram", TelegramEventMixin)


class TelegramAdapter(sdk.BaseAdapter):
    class Send(sdk.BaseAdapter.Send):
        """消息发送 DSL 实现"""

        def __init__(self, adapter, target_type=None, target_id=None, account_id=None):
            super().__init__(adapter, target_type, target_id, account_id)
            self._at_user_ids = []
            self._reply_message_id = None
            self._at_all = False
            self._inline_keyboard = None
            self._protect_content = False
            self._silent = False

        # ============ 消息发送方法 ============

        def Text(self, text: str):
            """发送纯文本消息"""
            return self.Raw_ob12([{"type": "text", "data": {"text": text}}])

        def Image(self, file, caption: str = "", content_type: str = None):
            """发送图片消息"""
            return self.Raw_ob12(
                [{"type": "image", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Video(self, file, caption: str = "", content_type: str = None):
            """发送视频消息"""
            return self.Raw_ob12(
                [{"type": "video", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Voice(self, file, caption: str = ""):
            """发送语音消息"""
            return self.Raw_ob12(
                [{"type": "voice", "data": {"file": file, "caption": caption}}]
            )

        def Audio(self, file, caption: str = "", content_type: str = None):
            """发送音频消息"""
            return self.Raw_ob12(
                [{"type": "audio", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def File(self, file, caption: str = ""):
            """发送文件消息"""
            return self.Raw_ob12(
                [{"type": "file", "data": {"file": file, "caption": caption}}]
            )

        def Document(self, file, caption: str = "", content_type: str = None):
            """发送文档消息（File 的别名）"""
            return self.Raw_ob12(
                [{"type": "file", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Sticker(self, file):
            """发送贴纸"""
            if isinstance(file, bytes):
                return asyncio.create_task(self._send_sticker_bytes(file))
            else:
                return asyncio.create_task(
                    self._adapter.call_api(
                        endpoint="sendSticker",
                        chat_id=self._target_id,
                        sticker=file,
                    )
                )

        def Location(self, latitude: float, longitude: float):
            """发送位置"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendLocation",
                    chat_id=self._target_id,
                    latitude=latitude,
                    longitude=longitude,
                )
            )

        def Venue(self, latitude: float, longitude: float, title: str, address: str):
            """发送地点"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendVenue",
                    chat_id=self._target_id,
                    latitude=latitude,
                    longitude=longitude,
                    title=title,
                    address=address,
                )
            )

        def Contact(self, phone_number: str, first_name: str, last_name: str = ""):
            """发送联系人"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendContact",
                    chat_id=self._target_id,
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                )
            )

        def Face(self, emoji: str):
            """发送表情消息（使用 Telegram Dice API）"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendDice",
                    chat_id=self._target_id,
                    emoji=emoji,
                )
            )

        def Markdown(self, text: str, content_type: str = "MarkdownV2"):
            """发送 Markdown 格式消息"""
            return self.Raw_ob12(
                [{"type": "markdown", "data": {"markdown": text, "content_type": content_type}}]
            )

        def HTML(self, text: str):
            """发送 HTML 格式消息"""
            return self.Raw_ob12(
                [{"type": "html", "data": {"html": text, "content_type": "HTML"}}]
            )

        def Edit(self, message_id: int, text: str, content_type: str = None):
            """编辑已有消息"""
            params = {
                "chat_id": self._target_id,
                "message_id": message_id,
                "text": text,
            }
            if content_type:
                params["parse_mode"] = content_type
            return asyncio.create_task(
                self._adapter.call_api(endpoint="editMessageText", **params)
            )

        def Recall(self, message_id: int):
            """删除指定消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="deleteMessage",
                    chat_id=self._target_id,
                    message_id=message_id,
                )
            )

        def Forward(self, from_chat_id: str, message_id: int):
            """转发消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="forwardMessage",
                    chat_id=self._target_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
            )

        def CopyMessage(self, from_chat_id: str, message_id: int):
            """复制消息（不带转发来源）"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="copyMessage",
                    chat_id=self._target_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
            )

        def AnswerCallback(self, callback_query_id: str, text: str = "", show_alert: bool = False):
            """应答回调查询"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="answerCallbackQuery",
                    callback_query_id=callback_query_id,
                    text=text,
                    show_alert=show_alert,
                )
            )

        # ============ 原始消息发送方法 ============

        def Raw_ob12(self, message: list, **kwargs):
            """发送 OneBot12 标准格式消息"""

            async def _send_raw_ob12():
                converted = await self._convert_ob12_to_telegram(message, **kwargs)

                if isinstance(converted, dict):
                    return await self._do_send(converted)
                elif isinstance(converted, list):
                    results = []
                    for call in converted:
                        result = await self._do_send(call)
                        results.append(result)
                    self._reset_modifiers()
                    return results[-1] if results else None

            return asyncio.create_task(_send_raw_ob12())

        def Raw_json(self, json_str: str):
            """发送原始 JSON 格式消息"""
            data = json.loads(json_str)

            async def _send_raw_json():
                endpoint = data.pop("endpoint", "sendMessage")
                return await self._adapter.call_api(endpoint=endpoint, **data)

            return asyncio.create_task(_send_raw_json())

        # ============ 链式修饰方法 ============

        def At(self, user_id: str) -> "Send":
            """@指定用户（通过 Telegram entities 实现）"""
            self._at_user_ids.append(user_id)
            return self

        def AtAll(self) -> "Send":
            """@全体成员"""
            self._at_all = True
            return self

        def Reply(self, message_id: str) -> "Send":
            """回复指定消息"""
            self._reply_message_id = message_id
            return self

        def Keyboard(self, inline_keyboard: list) -> "Send":
            """设置内联键盘"""
            self._inline_keyboard = inline_keyboard
            return self

        def ProtectContent(self, protect: bool = True) -> "Send":
            """保护内容（防止转发和保存）"""
            self._protect_content = protect
            return self

        def Silent(self, silent: bool = True) -> "Send":
            """静默发送（不通知用户）"""
            self._silent = silent
            return self

        # ============ 辅助方法 ============

        @staticmethod
        def _escape_markdown_v2(text: str) -> str:
            return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

        @staticmethod
        def _escape_html(text: str) -> str:
            return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        def _escape_text_by_parse_mode(self, text: str, mode: str) -> str:
            if mode == "MarkdownV2":
                return self._escape_markdown_v2(text)
            if mode == "HTML":
                return self._escape_html(text)
            return text

        def _reset_modifiers(self):
            """重置所有修饰状态"""
            self._at_user_ids = []
            self._reply_message_id = None
            self._at_all = False
            self._inline_keyboard = None
            self._protect_content = False
            self._silent = False

        async def _send_sticker_bytes(self, file_data: bytes):
            """上传并发送贴纸文件"""
            url = f"{self._adapter.base_url}/sendSticker"
            data = aiohttp.FormData()
            data.add_field("sticker", file_data, filename="sticker.webp", content_type="image/webp")
            data.add_field("chat_id", str(self._target_id))

            if self._reply_message_id:
                try:
                    data.add_field("reply_to_message_id", str(int(self._reply_message_id)))
                except (ValueError, TypeError):
                    pass

            if self._protect_content:
                data.add_field("protect_content", "true")
            if self._silent:
                data.add_field("disable_notification", "true")

            async with self._adapter.session.post(url, data=data) as response:
                raw_response = await response.json()
                self._reset_modifiers()
                return self._adapter._format_response(raw_response)

        async def _do_send(self, call: Dict) -> Dict:
            """执行发送调用"""
            endpoint = call["endpoint"]
            params = call["params"]

            media_file_data = params.pop("_media_file_data", None)
            if media_file_data is not None:
                return await self._upload_file_and_call_api(
                    endpoint, params.pop("_field_name"), media_file_data, **params
                )

            self._reset_modifiers()
            return await self._adapter.call_api(endpoint=endpoint, **params)

        def _add_mention_entity(self, entities: list, text_parts: list, user_id, name: str):
            """添加 Telegram mention entity"""
            start_pos = len("".join(text_parts))
            text_parts.append(name)
            if str(user_id).isdigit():
                entities.append({
                    "type": "text_mention",
                    "offset": start_pos,
                    "length": len(name),
                    "user": {"id": int(user_id)},
                })
            else:
                entities.append({
                    "type": "mention",
                    "offset": start_pos,
                    "length": len(name),
                })

        def _apply_common_params(self, params: dict):
            """应用通用修饰参数"""
            if self._reply_message_id:
                try:
                    params["reply_to_message_id"] = int(self._reply_message_id)
                except (ValueError, TypeError):
                    pass

            if self._protect_content:
                params["protect_content"] = True
            if self._silent:
                params["disable_notification"] = True

            if self._inline_keyboard:
                params["reply_markup"] = json.dumps({"inline_keyboard": self._inline_keyboard})

        async def _convert_ob12_to_telegram(self, message_segments: list, **kwargs) -> Dict:
            """将 OneBot12 消息段转换为 Telegram API 调用"""
            text_parts = []
            entities = []
            media_segment = None
            reply_message_id = None
            at_all = False
            parse_mode = None

            for segment in message_segments:
                seg_type = segment.get("type")
                data = segment.get("data", {})

                if seg_type == "text":
                    text_parts.append(data.get("text", ""))

                elif seg_type in ["image", "video", "voice", "file", "audio"]:
                    if not media_segment:
                        media_segment = {"type": seg_type, "data": data}

                elif seg_type == "mention":
                    user_id = data.get("user_id", "")
                    user_name = data.get("user_name", f"@{user_id}" if user_id else "")
                    self._add_mention_entity(entities, text_parts, user_id, user_name)

                elif seg_type == "reply":
                    msg_id = data.get("message_id")
                    if msg_id:
                        try:
                            reply_message_id = int(msg_id)
                        except (ValueError, TypeError):
                            pass

                elif seg_type == "markdown":
                    text_parts.append(data.get("markdown", ""))
                    parse_mode = data.get("content_type", "MarkdownV2")

                elif seg_type == "html":
                    text_parts.append(data.get("html", ""))
                    parse_mode = data.get("content_type", "HTML")

                elif seg_type == "telegram_sticker":
                    file_data = data.get("file_id") or data.get("file", "")
                    if isinstance(file_data, bytes):
                        # bytes 贴纸需要单独上传，合并到媒体段
                        media_segment = {"type": "sticker", "data": data}
                    else:
                        text_parts.append(data.get("emoji", ""))

                elif seg_type == "telegram_inline_keyboard":
                    self._inline_keyboard = data.get("inline_keyboard", [])

            # 链式修饰中的 At 用户
            for user_id in self._at_user_ids:
                self._add_mention_entity(entities, text_parts, user_id, f"@{user_id}")

            final_reply_id = reply_message_id or self._reply_message_id
            final_at_all = at_all or self._at_all

            full_text = "".join(text_parts)
            if final_at_all:
                full_text = "@All " + full_text

            params = {"chat_id": self._target_id}
            self._apply_common_params(params)

            if final_reply_id and "reply_to_message_id" not in params:
                try:
                    params["reply_to_message_id"] = int(final_reply_id)
                except (ValueError, TypeError):
                    pass

            # 贴纸发送（bytes 上传）
            if media_segment and media_segment["type"] == "sticker":
                sticker_data = media_segment["data"].get("file_id") or media_segment["data"].get("file", b"")
                if isinstance(sticker_data, bytes):
                    return {
                        "endpoint": "sendSticker",
                        "params": {
                            **params,
                            "_field_name": "sticker",
                            "_media_file_data": sticker_data,
                        },
                    }
                else:
                    params["sticker"] = sticker_data
                    return {"endpoint": "sendSticker", "params": params}

            if media_segment:
                seg_type = media_segment["type"]
                data = media_segment["data"]

                endpoint_map = {
                    "image": ("sendPhoto", "photo"),
                    "video": ("sendVideo", "video"),
                    "voice": ("sendVoice", "voice"),
                    "audio": ("sendAudio", "audio"),
                    "file": ("sendDocument", "document"),
                }
                endpoint, field_name = endpoint_map.get(seg_type, ("sendDocument", "document"))

                media_file = data.get("file_id") or data.get("url") or data.get("file", "")
                caption = full_text or data.get("caption", "")

                if isinstance(media_file, bytes):
                    ct = data.get("content_type")
                    caption_to_send = self._escape_text_by_parse_mode(caption, ct) if ct else caption
                    params["caption"] = caption_to_send
                    if ct is not None:
                        params["parse_mode"] = ct
                    return {
                        "endpoint": endpoint,
                        "params": {
                            **params,
                            "_field_name": field_name,
                            "_media_file_data": media_file,
                        },
                    }

                params[field_name] = media_file
                ct = data.get("content_type")
                effective_parse = ct or parse_mode
                caption_to_send = self._escape_text_by_parse_mode(caption, effective_parse) if effective_parse else caption
                params["caption"] = caption_to_send
                if ct is not None:
                    params["parse_mode"] = ct
                if parse_mode and not ct:
                    params["parse_mode"] = parse_mode
                return {"endpoint": endpoint, "params": params}
            else:
                text_to_send = full_text or " "
                if parse_mode:
                    text_to_send = self._escape_text_by_parse_mode(text_to_send, parse_mode)
                params["text"] = text_to_send
                if entities:
                    params["entities"] = entities
                if parse_mode:
                    params["parse_mode"] = parse_mode
                return {"endpoint": "sendMessage", "params": params}

        async def _upload_file_and_call_api(self, endpoint, field_name, file, **kwargs):
            """上传文件并调用 API"""
            if "content_type" in kwargs:
                content_type = kwargs.pop("content_type")
                if content_type is not None:
                    kwargs["parse_mode"] = content_type
                    if "caption" in kwargs:
                        kwargs["caption"] = self._escape_text_by_parse_mode(kwargs["caption"], content_type)

            if self._reply_message_id and "reply_to_message_id" not in kwargs:
                try:
                    kwargs["reply_to_message_id"] = int(self._reply_message_id)
                except (ValueError, TypeError):
                    pass

            if self._protect_content:
                kwargs["protect_content"] = "true"
            if self._silent:
                kwargs["disable_notification"] = "true"

            if self._inline_keyboard:
                kwargs["reply_markup"] = json.dumps({"inline_keyboard": self._inline_keyboard})

            url = f"{self._adapter.base_url}/{endpoint}"
            data = aiohttp.FormData()
            data.add_field(
                field_name, file,
                filename=f"file.{field_name}",
                content_type="application/octet-stream",
            )

            for key, value in kwargs.items():
                if isinstance(value, (dict, list)):
                    data.add_field(key, json.dumps(value))
                else:
                    data.add_field(key, str(value))

            async with self._adapter.session.post(url, data=data) as response:
                raw_response = await response.json()
                self._reset_modifiers()
                return self._adapter._format_response(raw_response)

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
        self._proxy_enabled = self.config.get("proxy_enabled", False)
        self._proxy_config = (
            self.config.get("proxy", {}) if self._proxy_enabled else None
        )
        converter = TelegramConverter(self.token)
        self._converter = converter
        self.convert = converter.convert
        self.bot_id = converter.bot_id

    def _format_response(self, raw_response: dict) -> dict:
        """格式化 Telegram API 响应为标准格式"""
        if not isinstance(raw_response, dict):
            return {
                "status": "failed",
                "retcode": 34000,
                "data": None,
                "message_id": "",
                "message": f"API 返回了意外格式: {type(raw_response)}",
                "telegram_raw": raw_response,
            }

        result = raw_response.get("result")
        return {
            "status": "ok" if raw_response.get("ok") else "failed",
            "retcode": 0 if raw_response.get("ok") else 34000,
            "data": result,
            "message_id": str(result.get("message_id", "")) if isinstance(result, dict) else "",
            "message": "" if raw_response.get("ok") else raw_response.get("description", "Unknown error"),
            "telegram_raw": raw_response,
        }

    def _load_config(self):
        """加载配置"""
        config = self.sdk.config.getConfig("Telegram_Adapter")
        if not config:
            default_config = {
                "token": "YOUR_BOT_TOKEN",
                "proxy_enabled": False,
                "proxy": {"host": "127.0.0.1", "port": 1080, "type": "socks5"},
            }
            try:
                sdk.logger.warning("Telegram适配器配置不存在，已自动创建默认配置")
                self.sdk.config.setConfig("Telegram_Adapter", default_config)
                return default_config
            except Exception as e:
                self.logger.error(f"保存默认配置失败: {str(e)}")
                return default_config

        has_mode = "mode" in config
        has_webhook = "webhook" in config

        if has_mode or has_webhook:
            mode = config.get("mode", "polling")
            if mode == "webhook":
                self.logger.error(
                    "Telegram 适配器不再支持 Webhook 模式！请切换到 Polling 模式。将自动使用 Polling 模式启动。"
                )
            elif has_webhook:
                self.logger.warning(
                    "检测到旧版 Webhook 配置，已自动忽略。Telegram 适配器将使用 Polling 模式。"
                )
            else:
                self.logger.info("检测到旧版配置，已自动兼容。当前使用 Polling 模式。")

        return config

    async def _poll_updates(self):
        """轮询获取 Telegram 更新"""
        offset = 0
        while True:
            try:
                response = await self.call_api("getUpdates", offset=offset, timeout=60)

                if response.get("status") != "ok":
                    self.logger.error(f"获取更新失败: {response.get('message')}")
                    await asyncio.sleep(5)
                    continue

                updates = response.get("data")

                if updates:
                    for update in updates:
                        update_id = update["update_id"]
                        if update_id >= offset:
                            offset = update_id + 1

                        if hasattr(self.sdk, "adapter"):
                            onebot_event = self.convert(update)
                            if onebot_event:
                                await self.sdk.adapter.emit(onebot_event)
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"轮询更新失败: {e}")
                await asyncio.sleep(5)

    async def call_api(self, endpoint: str, **params):
        """调用 Telegram Bot API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with self.session.post(url, json=params) as response:
                raw_response = await response.json()

                self.logger.debug(f"Telegram API请求: {url}")
                self.logger.debug(f"Telegram API响应: {raw_response}")

                if not isinstance(raw_response, dict):
                    self.logger.error(
                        f"Telegram API 返回了意外的响应格式: {type(raw_response)}, 内容: {raw_response}"
                    )
                    return {
                        "status": "failed",
                        "retcode": 34000,
                        "data": None,
                        "message_id": "",
                        "message": f"API 返回了意外格式: {type(raw_response)}",
                        "telegram_raw": raw_response,
                        "echo": params.get("echo", ""),
                    }

                response_data = self._format_response(raw_response)

                if "echo" in params:
                    response_data["echo"] = params["echo"]

                return response_data

        except Exception as e:
            self.logger.error(f"调用Telegram API失败: {str(e)}")
            return {
                "status": "failed",
                "retcode": 33001,
                "data": None,
                "message_id": "",
                "message": f"API调用失败: {str(e)}",
                "telegram_raw": None,
                "echo": params.get("echo", ""),
            }

    async def start(self):
        """启动适配器（仅支持 polling 模式）"""
        import ssl
        import certifi
        from aiohttp_socks import ProxyType, ProxyConnector

        if self._proxy_enabled and self._proxy_config:
            proxy_type = self._proxy_config.get("type")
            if proxy_type in ["socks5", "socks4"]:
                proxy_type_enum = (
                    ProxyType.SOCKS5 if proxy_type == "socks5" else ProxyType.SOCKS4
                )
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                connector = ProxyConnector(
                    proxy_type=proxy_type_enum,
                    host=self._proxy_config["host"],
                    port=self._proxy_config["port"],
                    ssl=ssl_context,
                )
                self.session = aiohttp.ClientSession(connector=connector)
                self.logger.info(
                    f"已启用{proxy_type.upper()}代理: {self._proxy_config['host']}:{self._proxy_config['port']}"
                )
            else:
                self.logger.warning(f"不支持的代理类型: {proxy_type}, 将不使用代理")
                self.session = aiohttp.ClientSession()
        else:
            self.session = aiohttp.ClientSession()
            if self._proxy_enabled:
                self.logger.warning("代理已启用但未配置，将不使用代理")

        self.poll_task = asyncio.create_task(self._poll_updates())

        try:
            me = await self.call_api("getMe")
            if me.get("status") == "ok" and isinstance(me.get("data"), dict):
                self._converter._bot_username = me["data"].get("username", "")
        except Exception:
            pass

        self.logger.info("Telegram适配器已启动（polling 模式）")

        await self.sdk.adapter.emit(
            {
                "type": "meta",
                "detail_type": "connect",
                "platform": "telegram",
                "self": {"platform": "telegram", "user_id": self.bot_id},
            }
        )

    async def shutdown(self):
        """关闭适配器"""
        await self.sdk.adapter.emit(
            {
                "type": "meta",
                "detail_type": "disconnect",
                "platform": "telegram",
                "self": {"platform": "telegram", "user_id": self.bot_id},
            }
        )

        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass
            self.poll_task = None

        if self.session:
            await self.session.close()
            self.session = None

        unregister_platform_event_methods("telegram")
        self.logger.info("Telegram适配器已关闭")