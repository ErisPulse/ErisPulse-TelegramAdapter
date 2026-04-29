import time
from typing import Dict, Optional, List
import uuid


class TelegramConverter:
    """
    Telegram 事件转换器

    严格遵循 ErisPulse 适配器标准化转换规范：
    - standards/event-conversion.md

    核心原则：
    1. 严格兼容：所有标准字段必须完全遵循 OneBot12 规范
    2. 明确扩展：平台特有功能必须添加 telegram_ 前缀
    3. 数据完整：原始事件数据必须保留在 telegram_raw 字段中
    4. 时间统一：所有时间戳必须转换为 10 位 Unix 时间戳（秒级）
    """

    def __init__(self, token: str):
        self.token = token
        self.bot_id = token.split(":")[0] if token and ":" in token else ""
        self._event_type_map = {
            "message": "message",
            "edited_message": "message",
            "channel_post": "message",
            "edited_channel_post": "message",
            "inline_query": "request",
            "chosen_inline_result": "notice",
            "callback_query": "notice",
            "shipping_query": "request",
            "pre_checkout_query": "request",
            "poll": "notice",
            "poll_answer": "notice",
            "my_chat_member": "notice",
            "chat_member": "notice",
            "chat_join_request": "request",
        }

    def convert(self, raw_event: Dict) -> Optional[Dict]:
        """
        将 Telegram 原始事件转换为 OneBot12 标准格式

        :param raw_event: 原始 Telegram update 对象
        :return: OneBot12 标准格式事件，不支持的事件返回 None
        """
        if not isinstance(raw_event, dict):
            return None

        update_id = raw_event.get("update_id")
        if update_id is None:
            return None

        event_type, raw_type = self._detect_event_type(raw_event)

        if event_type is None:
            return self._create_unknown_event(raw_event, update_id)

        onebot_event = self._create_base_event(
            raw_event, update_id, event_type, raw_type
        )

        event_handler = getattr(self, f"_handle_{event_type}", None)
        if event_handler:
            return event_handler(raw_event, onebot_event)

        return onebot_event

    # ==================== 基础事件构建 ====================

    def _create_base_event(
        self, raw_event: Dict, update_id: int, event_type: str, raw_type: str
    ) -> Dict:
        """创建基础事件结构"""
        return {
            "id": str(update_id),
            "time": int(time.time()),
            "type": event_type,
            "detail_type": "",
            "platform": "telegram",
            "self": {
                "platform": "telegram",
                "user_id": self.bot_id,
            },
            "telegram_raw": raw_event,
            "telegram_raw_type": raw_type,
        }

    def _create_unknown_event(self, raw_event: Dict, update_id: int) -> Dict:
        """创建未知事件"""
        unknown_type = "unknown"
        for key in raw_event.keys():
            if key != "update_id":
                unknown_type = key
                break

        return {
            "id": str(update_id),
            "time": int(time.time()),
            "type": "unknown",
            "platform": "telegram",
            "self": {"platform": "telegram", "user_id": ""},
            "telegram_raw": raw_event,
            "telegram_raw_type": unknown_type,
            "warning": f"Unsupported event type: {unknown_type}",
            "alt_message": "This event type is not supported by this system.",
        }

    def _detect_event_type(self, raw_event: Dict) -> tuple:
        """检测事件类型"""
        for tg_type, ob_type in self._event_type_map.items():
            if tg_type in raw_event:
                return ob_type, tg_type
        return None, "unknown"

    # ==================== 事件处理器 ====================

    def _handle_message(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理消息事件"""
        if "message" in raw_event:
            message = raw_event["message"]
            is_edited = False
        elif "edited_message" in raw_event:
            message = raw_event["edited_message"]
            is_edited = True
        elif "channel_post" in raw_event:
            message = raw_event["channel_post"]
            is_edited = False
        elif "edited_channel_post" in raw_event:
            message = raw_event["edited_channel_post"]
            is_edited = True
        else:
            return base_event

        # 确定 detail_type (OB12 标准: private/group/channel)
        chat = message.get("chat", {})
        chat_type = chat.get("type", "")

        if chat_type == "private":
            detail_type = "private"
        elif chat_type in ["group", "supergroup"]:
            detail_type = "group"
        elif chat_type == "channel":
            detail_type = "channel"
        else:
            detail_type = chat_type

        base_event["detail_type"] = detail_type

        # 解析消息内容（实体感知分段）
        message_segments = self._parse_message_content(message)
        alt_message = self._generate_alt_message(message_segments)

        base_event["message_id"] = str(message.get("message_id", ""))
        base_event["message"] = message_segments
        base_event["alt_message"] = alt_message

        # 用户信息
        if "from" in message:
            from_user = message["from"]
            base_event["user_id"] = str(from_user.get("id", ""))
            base_event["user_nickname"] = self._get_user_name(from_user)

        if is_edited:
            base_event["telegram_edit_time"] = int(time.time())

        base_event["telegram_chat"] = chat

        if detail_type == "group":
            base_event["group_id"] = str(chat.get("id", ""))
        elif detail_type == "channel":
            base_event["channel_id"] = str(chat.get("id", ""))

        # 话题/Topic 支持
        if "message_thread_id" in message:
            base_event["thread_id"] = str(message["message_thread_id"])

        return base_event

    def _handle_notice(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理通知事件"""
        raw_type = base_event["telegram_raw_type"]

        if raw_type == "callback_query":
            return self._handle_callback_query(raw_event, base_event)
        elif raw_type == "poll":
            return self._handle_poll(raw_event, base_event)
        elif raw_type == "poll_answer":
            return self._handle_poll_answer(raw_event, base_event)
        elif raw_type == "chosen_inline_result":
            return self._handle_chosen_inline_result(raw_event, base_event)
        elif raw_type in ["my_chat_member", "chat_member"]:
            return self._handle_chat_member(raw_event, base_event)

        return base_event

    def _handle_request(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理请求事件"""
        raw_type = base_event["telegram_raw_type"]

        if raw_type == "inline_query":
            return self._handle_inline_query(raw_event, base_event)
        elif raw_type == "shipping_query":
            return self._handle_shipping_query(raw_event, base_event)
        elif raw_type == "pre_checkout_query":
            return self._handle_pre_checkout_query(raw_event, base_event)
        elif raw_type == "chat_join_request":
            return self._handle_chat_join_request(raw_event, base_event)

        return base_event

    # ==================== 具体 Notice 处理器 ====================

    def _handle_callback_query(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理回调查询"""
        callback = raw_event["callback_query"]
        from_user = callback.get("from", {})

        base_event["detail_type"] = "telegram_callback_query"
        base_event["user_id"] = str(from_user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(from_user)

        base_event["telegram_callback_id"] = callback.get("id", "")
        base_event["telegram_callback_data"] = callback.get("data")
        base_event["telegram_inline_message_id"] = callback.get("inline_message_id")
        base_event["telegram_chat_instance"] = callback.get("chat_instance", "")

        if "message" in callback:
            msg = callback["message"]
            base_event["message_id"] = str(msg.get("message_id", ""))
            if "chat" in msg:
                chat = msg["chat"]
                if chat.get("type") == "channel":
                    base_event["channel_id"] = str(chat.get("id", ""))
                else:
                    base_event["group_id"] = str(chat.get("id", ""))

        return base_event

    def _handle_poll(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理投票"""
        poll = raw_event["poll"]

        base_event["detail_type"] = "telegram_poll"
        base_event["telegram_poll_id"] = poll.get("id", "")
        base_event["telegram_poll_question"] = poll.get("question", "")
        base_event["telegram_poll_options"] = poll.get("options", [])
        base_event["telegram_poll_total_voter_count"] = poll.get("total_voter_count", 0)
        base_event["telegram_poll_is_closed"] = poll.get("is_closed", False)
        base_event["telegram_poll_is_anonymous"] = poll.get("is_anonymous", True)
        base_event["telegram_poll_type"] = poll.get("type", "regular")
        base_event["telegram_poll_allows_multiple_answers"] = poll.get(
            "allows_multiple_answers", False
        )
        base_event["telegram_poll_correct_option_id"] = poll.get("correct_option_id")
        base_event["telegram_poll_explanation"] = poll.get("explanation")
        base_event["telegram_poll_open_period"] = poll.get("open_period")
        base_event["telegram_poll_close_date"] = poll.get("close_date")

        return base_event

    def _handle_poll_answer(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理投票答案"""
        answer = raw_event["poll_answer"]
        user = answer.get("user", {})

        base_event["detail_type"] = "telegram_poll_answer"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)

        base_event["telegram_poll_id"] = answer.get("poll_id", "")
        base_event["telegram_poll_option_ids"] = answer.get("option_ids", [])
        base_event["telegram_voter_chat"] = answer.get("voter_chat")

        return base_event

    def _handle_chosen_inline_result(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理选择的内联结果"""
        result = raw_event["chosen_inline_result"]
        user = result.get("from", {})

        base_event["detail_type"] = "telegram_chosen_inline_result"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)

        base_event["telegram_result_id"] = result.get("result_id", "")
        base_event["telegram_query"] = result.get("query", "")
        base_event["telegram_inline_message_id"] = result.get("inline_message_id")

        return base_event

    def _handle_chat_member(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理聊天成员变更"""
        if "my_chat_member" in raw_event:
            member_update = raw_event["my_chat_member"]
            base_event["detail_type"] = "telegram_my_chat_member"
        else:
            member_update = raw_event["chat_member"]
            base_event["detail_type"] = "telegram_chat_member"

        from_user = member_update.get("from", {})
        old_member = member_update.get("old_chat_member", {})
        new_member = member_update.get("new_chat_member", {})
        chat = member_update.get("chat", {})

        base_event["user_id"] = str(from_user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(from_user)

        base_event["telegram_old_member"] = old_member
        base_event["telegram_new_member"] = new_member
        base_event["telegram_chat"] = chat

        if chat.get("type") == "channel":
            base_event["channel_id"] = str(chat.get("id", ""))
        else:
            base_event["group_id"] = str(chat.get("id", ""))

        return base_event

    # ==================== 具体 Request 处理器 ====================

    def _handle_inline_query(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理内联查询"""
        query = raw_event["inline_query"]
        user = query.get("from", {})

        base_event["detail_type"] = "telegram_inline_query"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)

        base_event["telegram_query_id"] = query.get("id", "")
        base_event["telegram_query_text"] = query.get("query", "")
        base_event["telegram_query_offset"] = query.get("offset", "")
        base_event["telegram_query_chat_type"] = query.get("chat_type")

        return base_event

    def _handle_shipping_query(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理运费查询"""
        shipping = raw_event["shipping_query"]
        user = shipping.get("from", {})

        base_event["detail_type"] = "telegram_shipping_query"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)

        base_event["telegram_shipping_query_id"] = shipping.get("id", "")
        base_event["telegram_invoice_payload"] = shipping.get("invoice_payload", "")
        base_event["telegram_shipping_address"] = shipping.get("shipping_address")

        return base_event

    def _handle_pre_checkout_query(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理预付款查询"""
        checkout = raw_event["pre_checkout_query"]
        user = checkout.get("from", {})

        base_event["detail_type"] = "telegram_pre_checkout_query"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)

        base_event["telegram_checkout_id"] = checkout.get("id", "")
        base_event["telegram_invoice_payload"] = checkout.get("invoice_payload", "")
        base_event["telegram_currency"] = checkout.get("currency", "")
        base_event["telegram_total_amount"] = checkout.get("total_amount", 0)
        base_event["telegram_shipping_option_id"] = checkout.get("shipping_option_id")
        base_event["telegram_order_info"] = checkout.get("order_info")

        return base_event

    def _handle_chat_join_request(self, raw_event: Dict, base_event: Dict) -> Dict:
        """处理聊天加入请求"""
        request = raw_event["chat_join_request"]
        user = request.get("from", {})
        chat = request.get("chat", {})

        base_event["detail_type"] = "telegram_chat_join_request"
        base_event["user_id"] = str(user.get("id", ""))
        base_event["user_nickname"] = self._get_user_name(user)
        base_event["comment"] = request.get("invite_link", {}).get("name", "")

        base_event["telegram_chat_join_request_id"] = request.get(
            "chat_join_request_id", ""
        )
        base_event["telegram_date"] = request.get("date", 0)
        base_event["telegram_user_chat_id"] = request.get("user_chat_id")
        base_event["telegram_chat"] = chat

        if chat.get("type") == "channel":
            base_event["channel_id"] = str(chat.get("id", ""))
        else:
            base_event["group_id"] = str(chat.get("id", ""))

        return base_event

    # ==================== 消息内容解析 ====================

    def _parse_message_content(self, message: Dict) -> List[Dict]:
        """
        解析消息内容为 OneBot12 消息段

        核心逻辑：
        - 使用实体感知分段，确保文本中不包含 @用户名
        - mention 使用标准 OB12 格式: {"type": "mention", "data": {"user_id": "...", "user_name": "..."}}
        - 贴纸、联系人、位置、动画等使用 telegram_ 前缀扩展消息段
        - 内联键盘使用 telegram_inline_keyboard 扩展消息段
        """
        segments = []

        # 1. 回复消息（标准 reply 段）
        if "reply_to_message" in message:
            reply_msg = message["reply_to_message"]
            segments.append({
                "type": "reply",
                "data": {
                    "message_id": str(reply_msg["message_id"]),
                    "user_id": str(reply_msg.get("from", {}).get("id", "")),
                },
            })

        # 2. 贴纸 → telegram_sticker 扩展消息段
        if "sticker" in message:
            sticker = message["sticker"]
            segments.append({
                "type": "telegram_sticker",
                "data": {
                    "file_id": sticker["file_id"],
                    "emoji": sticker.get("emoji", ""),
                    "sticker_type": sticker.get("type", ""),
                    "url": self._build_file_url(sticker.get("file_path")),
                    "telegram_file": sticker,
                },
            })
            return segments

        # 3. 联系人 → telegram_contact 扩展消息段
        if "contact" in message:
            contact = message["contact"]
            segments.append({
                "type": "telegram_contact",
                "data": {
                    "phone_number": contact.get("phone_number", ""),
                    "first_name": contact.get("first_name", ""),
                    "last_name": contact.get("last_name", ""),
                    "user_id": str(contact.get("user_id", "")),
                },
            })
            return segments

        # 4. 位置 → 标准 location 消息段
        if "location" in message:
            location = message["location"]
            segments.append({
                "type": "location",
                "data": {
                    "latitude": location.get("latitude", 0.0),
                    "longitude": location.get("longitude", 0.0),
                },
            })
            return segments

        # 5. 地点
        if "venue" in message:
            venue = message["venue"]
            segments.append({
                "type": "location",
                "data": {
                    "latitude": venue.get("location", {}).get("latitude", 0.0),
                    "longitude": venue.get("location", {}).get("longitude", 0.0),
                    "title": venue.get("title", ""),
                    "address": venue.get("address", ""),
                },
            })
            return segments

        # 6. GIF 动画 → telegram_animation 扩展消息段
        if "animation" in message:
            anim = message["animation"]
            caption = message.get("caption", "")
            segments.append({
                "type": "telegram_animation",
                "data": {
                    "file_id": anim["file_id"],
                    "url": self._build_file_url(anim.get("file_path")),
                    "width": anim.get("width", 0),
                    "height": anim.get("height", 0),
                    "duration": anim.get("duration", 0),
                    "caption": caption,
                    "telegram_file": anim,
                },
            })
            # 动画也有图片消息段作为降级
            segments.append({
                "type": "image",
                "data": {
                    "file_id": anim["file_id"],
                    "url": self._build_file_url(anim.get("file_path")),
                },
            })
            if caption:
                self._add_text_and_mentions(message, segments, caption)
            return segments

        # 7. 图片
        if "photo" in message:
            photo = message["photo"][-1]
            caption = message.get("caption", "")
            segments.append({
                "type": "image",
                "data": {
                    "file_id": photo["file_id"],
                    "url": self._build_file_url(photo.get("file_path")),
                    "telegram_file": photo,
                },
            })
            # caption + mentions
            if caption:
                self._add_text_and_mentions(message, segments, caption)
            else:
                self._add_text_and_mentions(message, segments)
            return segments

        # 8. 视频
        if "video" in message:
            video = message["video"]
            caption = message.get("caption", "")
            segments.append({
                "type": "video",
                "data": {
                    "file_id": video["file_id"],
                    "url": self._build_file_url(video.get("file_path")),
                    "duration": video.get("duration", 0),
                    "width": video.get("width", 0),
                    "height": video.get("height", 0),
                },
            })
            if caption:
                self._add_text_and_mentions(message, segments, caption)
            else:
                self._add_text_and_mentions(message, segments)
            return segments

        # 9. 语音
        if "voice" in message:
            voice = message["voice"]
            segments.append({
                "type": "voice",
                "data": {
                    "file_id": voice["file_id"],
                    "url": self._build_file_url(voice.get("file_path")),
                    "duration": voice.get("duration", 0),
                },
            })
            return segments

        # 10. 音频
        if "audio" in message:
            audio = message["audio"]
            segments.append({
                "type": "audio",
                "data": {
                    "file_id": audio["file_id"],
                    "url": self._build_file_url(audio.get("file_path")),
                    "duration": audio.get("duration", 0),
                    "title": audio.get("title", ""),
                    "performer": audio.get("performer", ""),
                },
            })
            return segments

        # 11. 文件
        if "document" in message:
            doc = message["document"]
            caption = message.get("caption", "")
            segments.append({
                "type": "file",
                "data": {
                    "file_id": doc["file_id"],
                    "url": self._build_file_url(doc.get("file_path")),
                    "file_name": doc.get("file_name", ""),
                    "file_size": doc.get("file_size", 0),
                    "mime_type": doc.get("mime_type", ""),
                },
            })
            if caption:
                self._add_text_and_mentions(message, segments, caption)
            else:
                self._add_text_and_mentions(message, segments)
            return segments

        # 12. 纯文本消息（无媒体）
        self._add_text_and_mentions(message, segments)

        # 13. 内联键盘 → telegram_inline_keyboard 扩展消息段
        if "reply_markup" in message:
            reply_markup = message["reply_markup"]
            if isinstance(reply_markup, dict) and "inline_keyboard" in reply_markup:
                segments.append({
                    "type": "telegram_inline_keyboard",
                    "data": {
                        "inline_keyboard": reply_markup["inline_keyboard"],
                    },
                })

        return segments

    def _add_text_and_mentions(self, message: Dict, segments: list, text_override: str = None):
        """
        实体感知的文本分段，将 mention 从文本中分离

        核心逻辑：
        - 按 entities 将文本拆分为纯文本段和 mention 段
        - mention 段使用 OB12 标准: {"type": "mention", "data": {"user_id": "...", "user_name": "..."}}
        - 纯文本段中不包含 @用户名
        """
        text = text_override if text_override is not None else (message.get("text") or "")
        if not text:
            return

        entities = message.get("entities", [])
        if not entities:
            # 无实体，整段为纯文本
            segments.append({"type": "text", "data": {"text": text}})
            return

        # 过滤出 mention 相关实体并按 offset 排序
        mention_entities = []
        for entity in entities:
            etype = entity.get("type", "")
            if etype in ("mention", "text_mention"):
                mention_entities.append(entity)

        if not mention_entities:
            # 无 mention 实体，整段为纯文本
            segments.append({"type": "text", "data": {"text": text}})
            return

        # 按 offset 排序
        mention_entities.sort(key=lambda e: e["offset"])

        # 分段处理
        current_pos = 0
        for entity in mention_entities:
            offset = entity["offset"]
            length = entity["length"]
            etype = entity["type"]

            # offset 前的纯文本
            if current_pos < offset:
                plain_text = text[current_pos:offset]
                if plain_text:
                    segments.append({"type": "text", "data": {"text": plain_text}})

            # mention 段
            mention_text = text[offset:offset + length]
            if etype == "text_mention":
                user = entity.get("user", {})
                segments.append({
                    "type": "mention",
                    "data": {
                        "user_id": str(user.get("id", "")),
                        "user_name": self._get_user_name(user),
                    },
                })
            elif etype == "mention":
                # mention 格式: @username，无法获取 user_id
                segments.append({
                    "type": "mention",
                    "data": {
                        "user_id": "",
                        "user_name": mention_text,
                    },
                })

            current_pos = offset + length

        # 最后一段纯文本
        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining:
                segments.append({"type": "text", "data": {"text": remaining}})

    def _build_file_url(self, file_path: Optional[str]) -> Optional[str]:
        """构建文件 URL"""
        if not file_path:
            return None
        return f"https://api.telegram.org/file/bot{self.token}/{file_path}"

    # ==================== 辅助方法 ====================

    def _get_user_name(self, user: Dict) -> str:
        """获取用户显示名称"""
        username = user.get("username", "")
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")

        if username:
            return username

        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else str(user.get("id", ""))

    def _generate_alt_message(self, segments: List[Dict]) -> str:
        """生成替代文本消息"""
        parts = []
        for seg in segments:
            seg_type = seg["type"]
            data = seg["data"]

            if seg_type == "text":
                parts.append(data.get("text", ""))
            elif seg_type == "mention":
                parts.append(data.get("user_name", ""))
            elif seg_type == "reply":
                parts.append("[回复]")
            elif seg_type == "image":
                parts.append("[图片]")
            elif seg_type == "video":
                parts.append("[视频]")
            elif seg_type == "voice":
                parts.append("[语音]")
            elif seg_type == "audio":
                parts.append("[音频]")
            elif seg_type == "file":
                file_name = data.get("file_name", "")
                parts.append(f"[文件:{file_name}]" if file_name else "[文件]")
            elif seg_type == "telegram_sticker":
                emoji = data.get("emoji", "")
                parts.append(f"[贴纸{emoji}]" if emoji else "[贴纸]")
            elif seg_type == "telegram_contact":
                name = data.get("first_name", "")
                parts.append(f"[联系人:{name}]" if name else "[联系人]")
            elif seg_type == "location":
                parts.append("[位置]")
            elif seg_type == "telegram_animation":
                parts.append("[动画]")
            elif seg_type == "telegram_inline_keyboard":
                pass  # 键盘不影响 alt_message

        return " ".join(parts).strip()