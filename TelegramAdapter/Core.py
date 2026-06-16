import asyncio
import io
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union

from ErisPulse.Core import client
from ErisPulse.Core.Bases.adapter import BaseAdapter
from ErisPulse.runtime.config_schema import BotAccountConfig
from ErisPulse.Core.Event import register_event_mixin, unregister_platform_event_methods
from .Converter import TelegramConverter


@dataclass
class TelegramAccountConfig(BotAccountConfig):
    token: str = field(
        default="",
        metadata={
            "description": "Telegram Bot Token",
            "required": True,
            "secret": True,
            "webui": {"widget": "password", "group": "basic", "order": 2},
        },
    )


class TelegramEventMixin:

    def is_bot_message(self) -> bool:
        from_user = self.get("telegram_raw", {}).get("message", {}).get("from", {})
        if not from_user:
            from_user = (
                self.get("telegram_raw", {}).get("edited_message", {}).get("from", {})
            )
        return from_user.get("is_bot", False)

    def get_update_id(self) -> int:
        return self.get("telegram_raw", {}).get("update_id", 0)

    def get_chat_title(self) -> str:
        chat = self.get("telegram_chat", {})
        return chat.get("title", "") if chat else ""

    def get_chat_username(self) -> str:
        chat = self.get("telegram_chat", {})
        return chat.get("username", "") if chat else ""

    def is_edited_message(self) -> bool:
        return "telegram_edit_time" in self

    def get_callback_data(self) -> str:
        return self.get("telegram_callback_data")

    def get_callback_id(self) -> str:
        return self.get("telegram_callback_id", "")

    def get_inline_keyboard(self):
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_inline_keyboard":
                return seg.get("data", {}).get("inline_keyboard")
        return None

    def get_sticker_info(self) -> dict:
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_sticker":
                return seg.get("data", {})
        return None

    def get_contact_info(self) -> dict:
        for seg in self.get("message", []):
            if seg.get("type") == "telegram_contact":
                return seg.get("data", {})
        return None

    def get_location(self) -> dict:
        for seg in self.get("message", []):
            if seg.get("type") == "location":
                return seg.get("data", {})
        return None

    def get_forward_from(self) -> dict:
        raw = self.get("telegram_raw", {})
        msg = raw.get("message") or raw.get("edited_message") or raw.get("channel_post") or {}
        forward = msg.get("forward_from") or msg.get("forward_from_chat")
        return forward

    def is_topic_message(self) -> bool:
        return "thread_id" in self

    def get_topic_id(self) -> str:
        return self.get("thread_id")


register_event_mixin("telegram", TelegramEventMixin)


class TelegramAdapter(BaseAdapter):

    AccountConfigClass = TelegramAccountConfig

    class Send(BaseAdapter.Send):

        def __init__(self, adapter, target_type=None, target_id=None, account_id=None):
            super().__init__(adapter, target_type, target_id, account_id)
            self._at_user_ids = []
            self._reply_message_id = None
            self._at_all = False
            self._inline_keyboard = None
            self._protect_content = False
            self._silent = False

        def Text(self, text: str):
            return self.Raw_ob12([{"type": "text", "data": {"text": text}}])

        def Image(self, file, caption: str = "", content_type: str = None):
            return self.Raw_ob12(
                [{"type": "image", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Video(self, file, caption: str = "", content_type: str = None):
            return self.Raw_ob12(
                [{"type": "video", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Voice(self, file, caption: str = ""):
            return self.Raw_ob12(
                [{"type": "voice", "data": {"file": file, "caption": caption}}]
            )

        def Audio(self, file, caption: str = "", content_type: str = None):
            return self.Raw_ob12(
                [{"type": "audio", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def File(self, file, caption: str = ""):
            return self.Raw_ob12(
                [{"type": "file", "data": {"file": file, "caption": caption}}]
            )

        def Document(self, file, caption: str = "", content_type: str = None):
            return self.Raw_ob12(
                [{"type": "file", "data": {"file": file, "caption": caption, "content_type": content_type}}]
            )

        def Sticker(self, file):
            if isinstance(file, bytes):
                return asyncio.create_task(self._send_sticker_bytes(file))
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="sendSticker", chat_id=ctx["target_id"], sticker=file,
                )
            )

        def Location(self, latitude: float, longitude: float):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="sendLocation", chat_id=ctx["target_id"],
                    latitude=latitude, longitude=longitude,
                )
            )

        def Venue(self, latitude: float, longitude: float, title: str, address: str):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="sendVenue", chat_id=ctx["target_id"],
                    latitude=latitude, longitude=longitude, title=title, address=address,
                )
            )

        def Contact(self, phone_number: str, first_name: str, last_name: str = ""):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="sendContact", chat_id=ctx["target_id"],
                    phone_number=phone_number, first_name=first_name, last_name=last_name,
                )
            )

        def Face(self, emoji: str):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="sendDice", chat_id=ctx["target_id"], emoji=emoji,
                )
            )

        def Markdown(self, text: str, content_type: str = "Markdown"):
            params = {"chat_id": self.send_context["target_id"], "text": text, "parse_mode": content_type}
            self._apply_common_params(params)
            self._reset_modifiers()
            return asyncio.create_task(
                self._adapter.call_api(_account_id=self.send_context.get("account_id"), endpoint="sendMessage", **params)
            )

        def Html(self, text: str):
            params = {
                "chat_id": self.send_context["target_id"],
                "text": self._sanitize_html_for_tg(text),
                "parse_mode": "HTML",
            }
            self._apply_common_params(params)
            self._reset_modifiers()
            return asyncio.create_task(
                self._adapter.call_api(_account_id=self.send_context.get("account_id"), endpoint="sendMessage", **params)
            )

        def Edit(self, message_id: int, text: str, content_type: str = None):
            ctx = self.send_context
            params = {"chat_id": ctx["target_id"], "message_id": message_id, "text": text}
            if content_type:
                params["parse_mode"] = content_type
            return asyncio.create_task(
                self._adapter.call_api(_account_id=ctx.get("account_id"), endpoint="editMessageText", **params)
            )

        def Recall(self, message_id: int):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="deleteMessage", chat_id=ctx["target_id"], message_id=message_id,
                )
            )

        def Forward(self, from_chat_id: str, message_id: int):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="forwardMessage", chat_id=ctx["target_id"],
                    from_chat_id=from_chat_id, message_id=message_id,
                )
            )

        def CopyMessage(self, from_chat_id: str, message_id: int):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    _account_id=ctx.get("account_id"),
                    endpoint="copyMessage", chat_id=ctx["target_id"],
                    from_chat_id=from_chat_id, message_id=message_id,
                )
            )

        def AnswerCallback(self, callback_query_id: str, text: str = "", show_alert: bool = False):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="answerCallbackQuery",
                    callback_query_id=callback_query_id, text=text, show_alert=show_alert,
                )
            )

        def Raw_ob12(self, message: list, **kwargs):

            async def _send():
                converted = await self._convert_ob12_to_telegram(message, **kwargs)
                if isinstance(converted, dict):
                    return await self._do_send(converted)
                elif isinstance(converted, list):
                    results = []
                    for call in converted:
                        results.append(await self._do_send(call))
                    self._reset_modifiers()
                    return results[-1] if results else None

            return asyncio.create_task(_send())

        def Raw_json(self, json_str: str):
            data = json.loads(json_str)

            async def _send():
                endpoint = data.pop("endpoint", "sendMessage")
                return await self._adapter.call_api(endpoint=endpoint, **data)

            return asyncio.create_task(_send())

        def At(self, user_id: str):
            self._at_user_ids.append(user_id)
            return self

        def AtAll(self):
            self._at_all = True
            return self

        def Reply(self, message_id: str):
            self._reply_message_id = message_id
            return self

        def Keyboard(self, inline_keyboard: list):
            self._inline_keyboard = inline_keyboard
            return self

        def ProtectContent(self, protect: bool = True):
            self._protect_content = protect
            return self

        def Silent(self, silent: bool = True):
            self._silent = silent
            return self

        @staticmethod
        def _escape_markdown_v2(text: str) -> str:
            return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

        @staticmethod
        def _escape_html(text: str) -> str:
            return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        @staticmethod
        def _sanitize_html_for_tg(text: str) -> str:
            text = re.sub(r'<h[1-6][^>]*>', '<b>', text, flags=re.IGNORECASE)
            text = re.sub(r'</h[1-6]>', '</b>\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
            text = re.sub(r'<hr\s*/?>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<li[^>]*>', '\u2022 ', text, flags=re.IGNORECASE)
            text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)

            supported = {
                'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del',
                'code', 'pre', 'a', 'tg-spoiler', 'blockquote', 'tg-emoji',
            }

            def _strip_tag(m):
                tag_match = re.match(r'</?(\w+[\w-]*)', m.group(0))
                if tag_match:
                    return m.group(0) if tag_match.group(1).lower() in supported else ''
                return m.group(0)

            text = re.sub(r'</?[\w][\w-]*(?:\s[^>]*)?/?>', _strip_tag, text)
            text = re.sub(r'\s+style=["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

            lines = [re.sub(r'[ \t]+', ' ', line.strip()) for line in text.split('\n')]
            text = '\n'.join(lines)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()

        def _reset_modifiers(self):
            self._at_user_ids = []
            self._reply_message_id = None
            self._at_all = False
            self._inline_keyboard = None
            self._protect_content = False
            self._silent = False

        def _apply_common_params(self, params: dict):
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
                params["reply_markup"] = {"inline_keyboard": self._inline_keyboard}

        def _add_mention_entity(self, entities: list, text_parts: list, user_id: str, name: str):
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

        async def _send_sticker_bytes(self, file_data: bytes):
            import aiohttp

            ctx = self.send_context
            bot_name, bot = self._adapter._resolve_account(ctx.get("account_id"))
            url = f"https://api.telegram.org/bot{bot.token}/sendSticker"

            data = aiohttp.FormData()
            data.add_field("sticker", io.BytesIO(file_data), filename="sticker.webp", content_type="image/webp")
            data.add_field("chat_id", str(ctx["target_id"]))

            if self._reply_message_id:
                try:
                    data.add_field("reply_to_message_id", str(int(self._reply_message_id)))
                except (ValueError, TypeError):
                    pass
            if self._protect_content:
                data.add_field("protect_content", "true")
            if self._silent:
                data.add_field("disable_notification", "true")

            try:
                resp = await client.post(url, data=data)
                raw_response = await resp.json()
                self._reset_modifiers()
                return self._adapter._format_telegram_response(raw_response)
            except Exception as e:
                self._reset_modifiers()
                return self._adapter.make_error(message=str(e), raw=None)

        async def _do_send(self, call: Dict) -> Dict:
            endpoint = call["endpoint"]
            params = call["params"]
            ctx = self.send_context

            file_data = params.pop("_media_file_data", None)
            if file_data is not None:
                return await self._upload_file_and_call_api(
                    endpoint, params.pop("_field_name"), file_data,
                    _account_id=ctx.get("account_id"), **params
                )

            self._reset_modifiers()
            return await self._adapter.call_api(
                _account_id=ctx.get("account_id"), endpoint=endpoint, **params
            )

        async def _upload_file_and_call_api(self, endpoint, field_name, file, **kwargs):
            import aiohttp

            account_id = kwargs.pop("_account_id", None)
            bot_name, bot = self._adapter._resolve_account(account_id)

            if "content_type" in kwargs:
                ct = kwargs.pop("content_type")
                if ct is not None:
                    kwargs["parse_mode"] = ct

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

            url = f"https://api.telegram.org/bot{bot.token}/{endpoint}"
            data = aiohttp.FormData()
            data.add_field(field_name, io.BytesIO(file) if isinstance(file, bytes) else file,
                           filename=f"file.{field_name}", content_type="application/octet-stream")

            for key, value in kwargs.items():
                data.add_field(key, json.dumps(value) if isinstance(value, (dict, list)) else str(value))

            try:
                resp = await client.post(url, data=data, timeout=300)
                raw_response = await resp.json()
                self._reset_modifiers()
                return self._adapter._format_telegram_response(raw_response)
            except Exception as e:
                self._reset_modifiers()
                return self._adapter.make_error(message=str(e), raw=None)

        async def _convert_ob12_to_telegram(self, message_segments: list, **kwargs) -> Dict:
            text_parts = []
            entities = []
            media_segment = None
            reply_message_id = None
            parse_mode = None
            rich_text = False

            for segment in message_segments:
                seg_type = segment.get("type")
                data = segment.get("data", {})

                if seg_type == "text":
                    text_parts.append(data.get("text", ""))

                elif seg_type in ("image", "video", "voice", "file", "audio"):
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
                    parse_mode = data.get("content_type", "Markdown")
                    rich_text = True

                elif seg_type == "html":
                    text_parts.append(self._sanitize_html_for_tg(data.get("html", "")))
                    parse_mode = "HTML"
                    rich_text = True

                elif seg_type == "telegram_sticker":
                    file_data = data.get("file_id") or data.get("file", "")
                    if isinstance(file_data, bytes):
                        media_segment = {"type": "sticker", "data": data}
                    else:
                        text_parts.append(data.get("emoji", ""))

                elif seg_type == "telegram_inline_keyboard":
                    self._inline_keyboard = data.get("inline_keyboard", [])

            for user_id in self._at_user_ids:
                self._add_mention_entity(entities, text_parts, user_id, f"@{user_id}")

            full_text = "".join(text_parts)
            if self._at_all:
                full_text = "@All " + full_text

            ctx = self.send_context
            params = {"chat_id": ctx["target_id"]}
            self._apply_common_params(params)

            final_reply_id = reply_message_id or self._reply_message_id
            if final_reply_id and "reply_to_message_id" not in params:
                try:
                    params["reply_to_message_id"] = int(final_reply_id)
                except (ValueError, TypeError):
                    pass

            if media_segment and media_segment["type"] == "sticker":
                sticker_file = media_segment["data"].get("file_id") or media_segment["data"].get("file", b"")
                if isinstance(sticker_file, bytes):
                    return {
                        "endpoint": "sendSticker",
                        "params": {**params, "_field_name": "sticker", "_media_file_data": sticker_file},
                    }
                params["sticker"] = sticker_file
                return {"endpoint": "sendSticker", "params": params}

            if media_segment:
                return self._build_media_params(params, media_segment, full_text, parse_mode, rich_text)

            return self._build_text_params(params, full_text, parse_mode, rich_text, entities)

        def _build_media_params(self, params: dict, media_segment: dict, caption: str, parse_mode: str, rich_text: bool) -> dict:
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
            caption = caption or data.get("caption", "")

            effective_parse = data.get("content_type") or parse_mode

            if isinstance(media_file, bytes):
                if effective_parse:
                    params["parse_mode"] = effective_parse
                    if not rich_text:
                        caption = self._escape_text_by_parse_mode(caption, effective_parse)
                params["caption"] = caption
                return {
                    "endpoint": endpoint,
                    "params": {**params, "_field_name": field_name, "_media_file_data": media_file},
                }

            params[field_name] = media_file
            if effective_parse:
                params["parse_mode"] = effective_parse
                if not rich_text:
                    caption = self._escape_text_by_parse_mode(caption, effective_parse)
            params["caption"] = caption
            return {"endpoint": endpoint, "params": params}

        def _build_text_params(self, params: dict, text: str, parse_mode: str, rich_text: bool, entities: list) -> dict:
            text = text or " "

            if parse_mode:
                params["parse_mode"] = parse_mode
                if not rich_text:
                    text = self._escape_text_by_parse_mode(text, parse_mode)

            params["text"] = text

            if parse_mode and entities:
                entities = []

            if entities:
                params["entities"] = entities

            return {"endpoint": "sendMessage", "params": params}

        def _escape_text_by_parse_mode(self, text: str, mode: str) -> str:
            if mode == "MarkdownV2":
                return self._escape_markdown_v2(text)
            if mode == "HTML":
                return self._escape_html(text)
            return text

    def __init__(self, sdk_ref=None):
        super().__init__(sdk_ref)
        self._poll_tasks: Dict[str, asyncio.Task] = {}
        self._converters: Dict[str, TelegramConverter] = {}
        self._running = False
        self._register_event_methods()

    def _get_config_key(self) -> str:
        return "Telegram_Adapter"

    def _load_accounts(self) -> dict:
        from ErisPulse.runtime.config_schema import dict_to_dataclass
        from ErisPulse.Core.config import config as config_mgr

        key = "Telegram_Adapter.accounts"
        data = config_mgr.getConfig(key)

        if not data:
            old_config = config_mgr.getConfig("Telegram_Adapter")
            if old_config and "token" in old_config:
                self.logger.warning("检测到旧格式配置，建议迁移到新格式")
                self.logger.warning(
                    "迁移方法：将现有配置移动到 Telegram_Adapter.accounts.default 下"
                )
                data = {
                    "default": {
                        "token": old_config.get("token", ""),
                        "enabled": True,
                    }
                }
                self.logger.warning(
                    "已临时加载旧配置为默认bot，请尽快迁移到新格式"
                )
            else:
                self.logger.info("未找到配置文件，创建默认bot配置")
                data = {
                    "default": {
                        "token": "",
                        "enabled": True,
                    }
                }
                try:
                    config_mgr.setConfig(key, data)
                except Exception as e:
                    self.logger.error(f"保存默认bot配置失败: {str(e)}")

        accounts = {}
        for name, account_data in data.items():
            if not isinstance(account_data, dict):
                continue
            if "token" not in account_data or not account_data["token"]:
                self.logger.error(f"Bot {name} 缺少token配置，已跳过")
                continue

            instance = dict_to_dataclass(TelegramAccountConfig, account_data)
            instance.name = name

            if not instance.bot_id and instance.token and ":" in instance.token:
                instance.bot_id = instance.token.split(":")[0]

            accounts[name] = instance

        self.logger.info(f"Telegram适配器初始化完成，共加载 {len(accounts)} 个机器人")
        return accounts

    def _register_event_methods(self):
        try:
            pass
        except Exception as e:
            self.logger.warning(f"注册Telegram事件扩展方法失败: {e}")

    def _format_telegram_response(self, raw_response: dict) -> dict:
        if not isinstance(raw_response, dict):
            return self.make_error(
                retcode=34000,
                message=f"API 返回了意外格式: {type(raw_response)}",
                raw=raw_response,
            )

        result = raw_response.get("result")
        is_ok = raw_response.get("ok", False)
        message_id = str(result.get("message_id", "")) if isinstance(result, dict) else ""

        resp = self.make_response(
            status="ok" if is_ok else "failed",
            retcode=0 if is_ok else 34000,
            data=result,
            message_id=message_id,
            message="" if is_ok else raw_response.get("description", "Unknown error"),
            raw=raw_response,
        )
        resp["telegram_raw"] = raw_response
        return resp

    async def call_api(self, endpoint: str, _account_id: str = None, **params):
        account_name, account = self._resolve_account(_account_id)
        url = f"https://api.telegram.org/bot{account.token}/{endpoint}"
        echo = params.pop("echo", None)

        try:
            resp = await client.post(url, json=params)
            raw_response = await resp.json()

            self.logger.debug(f"Telegram API请求: {url}")
            self.logger.debug(f"Telegram API响应: {raw_response}")

            if not isinstance(raw_response, dict):
                error_resp = self.make_error(
                    retcode=34000,
                    message=f"API 返回了意外格式: {type(raw_response)}",
                    raw=raw_response,
                )
                if echo:
                    error_resp["echo"] = echo
                return error_resp

            response = self._format_telegram_response(raw_response)
            if echo:
                response["echo"] = echo
            return response

        except Exception as e:
            self.logger.error(f"调用Telegram API失败: {str(e)}")
            error_resp = self.make_error(
                retcode=33001,
                message=f"API调用失败: {str(e)}",
                raw=None,
            )
            if echo:
                error_resp["echo"] = echo
            return error_resp

    async def _poll_updates(self, account_name: str):
        account = self.accounts.get(account_name)
        converter = self._converters.get(account_name)
        if not account or not converter:
            return

        offset = 0

        while self._running:
            try:
                response = await self.call_api("getUpdates", _account_id=account_name, offset=offset, timeout=60)

                if response.get("status") != "ok":
                    self.logger.error(f"Bot {account_name} 获取更新失败: {response.get('message')}")
                    await asyncio.sleep(5)
                    continue

                updates = response.get("data")
                if updates:
                    for update in updates:
                        update_id = update["update_id"]
                        if update_id >= offset:
                            offset = update_id + 1

                        onebot_event = converter.convert(update)
                        if onebot_event:
                            from ErisPulse.Core import adapter as adapter_mgr
                            await adapter_mgr.emit(onebot_event)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.logger.error(f"Bot {account_name} 轮询更新失败: {e}")
                await asyncio.sleep(5)

    async def start(self):
        self._running = True

        for account_name, account in self.enabled_accounts.items():
            converter = TelegramConverter(account.token)
            self._converters[account_name] = converter

            try:
                me = await self.call_api("getMe", _account_id=account_name)
                if me.get("status") == "ok" and isinstance(me.get("data"), dict):
                    converter._bot_username = me["data"].get("username", "")
            except Exception:
                pass

            await self.emit_meta("connect", account.bot_id)
            self._poll_tasks[account_name] = asyncio.create_task(
                self._poll_updates(account_name)
            )
            self.logger.info(
                f"Bot {account_name} (bot_id: {account.bot_id}) 已启动（polling模式）"
            )

        self.logger.info(f"Telegram适配器启动完成，共 {len(self.enabled_accounts)} 个机器人")

    async def shutdown(self):
        self._running = False

        for task in self._poll_tasks.values():
            if not task.done():
                task.cancel()
        if self._poll_tasks:
            await asyncio.gather(*self._poll_tasks.values(), return_exceptions=True)
        self._poll_tasks.clear()

        for account_name, account in self.enabled_accounts.items():
            try:
                await self.emit_meta("disconnect", account.bot_id)
            except Exception:
                pass

        try:
            unregister_platform_event_methods("telegram")
        except Exception:
            pass

        self.logger.info("Telegram适配器已关闭")
