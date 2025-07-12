import time
from typing import Dict, Optional, List, Any

class TelegramConverter:
    def __init__(self, token: str):
        self.token = token
        self._setup_event_mapping()
    
    def _setup_event_mapping(self):
        """初始化事件类型映射"""
        self.event_map = {
            "message": "message",
            "edited_message": "message_edit",
            "channel_post": "channel_message",
            "edited_channel_post": "channel_message_edit",
            "inline_query": "inline_query",
            "chosen_inline_result": "chosen_inline_result",
            "callback_query": "callback_query",
            "shipping_query": "shipping_query",
            "pre_checkout_query": "pre_checkout_query",
            "poll": "poll",
            "poll_answer": "poll_answer"
        }

    def convert(self, raw_event: Dict) -> Optional[Dict]:
        """
        将Telegram事件转换为OneBot12格式
        
        :param raw_event: 原始Telegram事件数据
        :return: 转换后的OneBot12事件，None表示不支持的事件类型
        """
        if not isinstance(raw_event, dict):
            raise ValueError("事件数据必须是字典类型")

        update_id = raw_event.get("update_id")
        if update_id is None:
            raise ValueError("无效的Telegram事件格式")

        # 基础事件结构
        onebot_event = {
            "id": str(update_id),
            "time": int(time.time()),
            "platform": "telegram",
            "self": {
                "platform": "telegram",
                "user_id": ""  # 由具体事件填充
            },
            "telegram_raw": raw_event  # 保留原始数据
        }

        # 分派到具体事件处理器
        for tg_type, mapped_type in self.event_map.items():
            if tg_type in raw_event:
                handler = getattr(self, f"_handle_{mapped_type}", None)
                if handler:
                    return handler(raw_event[tg_type], onebot_event)
        
        return None

    def _handle_message(self, message: Dict, base_event: Dict) -> Dict:
        """
        处理消息事件
        """
        # 确定消息类型
        chat_type = message["chat"]["type"]
        detail_type = "private" if chat_type == "private" else "group"
        
        # 处理消息内容
        message_segments = self._parse_message_content(message)
        alt_message = self._generate_alt_message(message_segments)
        
        # 构建最终事件
        base_event.update({
            "type": "message",
            "detail_type": detail_type,
            "message_id": str(message["message_id"]),
            "message": message_segments,
            "alt_message": alt_message,
            "user_id": str(message["from"]["id"]),
            "telegram_chat": message["chat"]
        })

        if detail_type == "group":
            base_event["group_id"] = str(message["chat"]["id"])
        
        # 设置self.user_id为机器人ID（如果可用）
        if "bot" in message.get("from", {}):
            base_event["self"]["user_id"] = str(message["from"]["id"])
        
        return base_event

    def _parse_message_content(self, message: Dict) -> List[Dict]:
        """解析消息内容为OneBot12消息段"""
        segments = []
        
        # 文本内容
        if "text" in message:
            segments.append({
                "type": "text",
                "data": {"text": message["text"]}
            })
        elif "caption" in message:
            segments.append({
                "type": "text",
                "data": {"text": message["caption"]}
            })
        
        # 处理实体（如粗体、链接等）
        if "entities" in message:
            for entity in message["entities"]:
                if entity["type"] == "bold":
                    segments.append({
                        "type": "text",
                        "data": {"text": message["text"][entity["offset"]:entity["offset"]+entity["length"]]}
                    })
        
        # 处理附件
        if "photo" in message:
            photo = message["photo"][-1]  # 获取最高分辨率图片
            segments.append({
                "type": "image",
                "data": {
                    "file_id": photo["file_id"],
                    "url": f"https://api.telegram.org/file/bot{self.token}/{photo.get('file_path', '')}",
                    "telegram_file": photo
                }
            })
        
        if "video" in message:
            video = message["video"]
            segments.append({
                "type": "video",
                "data": {
                    "file_id": video["file_id"],
                    "url": f"https://api.telegram.org/file/bot{self.token}/{video.get('file_path', '')}",
                    "duration": video.get("duration", 0),
                    "width": video.get("width", 0),
                    "height": video.get("height", 0)
                }
            })
        
        if "document" in message:
            doc = message["document"]
            segments.append({
                "type": "file",
                "data": {
                    "file_id": doc["file_id"],
                    "file_name": doc.get("file_name", ""),
                    "file_size": doc.get("file_size", 0),
                    "mime_type": doc.get("mime_type", "")
                }
            })
        
        # 处理回复消息
        if "reply_to_message" in message:
            segments.append({
                "type": "telegram_reply",
                "data": {
                    "message_id": str(message["reply_to_message"]["message_id"]),
                    "user_id": str(message["reply_to_message"]["from"]["id"])
                }
            })
        
        return segments

    def _generate_alt_message(self, segments: List[Dict]) -> str:
        """生成替代文本消息"""
        parts = []
        for seg in segments:
            if seg["type"] == "text":
                parts.append(seg["data"]["text"])
            elif seg["type"] == "image":
                parts.append("[图片]")
            elif seg["type"] == "video":
                parts.append("[视频]")
            elif seg["type"] == "file":
                parts.append(f"[文件:{seg['data'].get('file_name', '')}]")
        return " ".join(parts)

    def _handle_message_edit(self, message: Dict, base_event: Dict) -> Dict:
        """处理消息编辑事件"""
        event = self._handle_message(message, base_event)
        event["sub_type"] = "edit"
        return event

    def _handle_channel_message(self, message: Dict, base_event: Dict) -> Dict:
        """处理频道消息事件"""
        event = self._handle_message(message, base_event)
        event["detail_type"] = "channel"
        return event

    def _handle_channel_message_edit(self, message: Dict, base_event: Dict) -> Dict:
        """处理频道消息编辑事件"""
        event = self._handle_message(message, base_event)
        event["detail_type"] = "channel"
        event["sub_type"] = "edit"
        return event

    def _handle_callback_query(self, callback: Dict, base_event: Dict) -> Dict:
        """处理回调查询事件"""
        base_event.update({
            "type": "notice",
            "detail_type": "telegram_callback_query",
            "user_id": str(callback["from"]["id"]),
            "telegram_callback_data": {
                "id": callback["id"],
                "data": callback.get("data"),
                "message": callback.get("message"),
                "inline_message_id": callback.get("inline_message_id")
            }
        })
        
        if "message" in callback:
            base_event["message_id"] = str(callback["message"]["message_id"])
            if "chat" in callback["message"]:
                base_event["group_id"] = str(callback["message"]["chat"]["id"])
        
        return base_event

    def _handle_inline_query(self, inline_query: Dict, base_event: Dict) -> Dict:
        """处理内联查询事件"""
        base_event.update({
            "type": "notice",
            "detail_type": "telegram_inline_query",
            "user_id": str(inline_query["from"]["id"]),
            "telegram_inline_query": {
                "id": inline_query["id"],
                "query": inline_query["query"],
                "offset": inline_query["offset"]
            }
        })
        return base_event

    def _handle_chosen_inline_result(self, result: Dict, base_event: Dict) -> Dict:
        """处理选择的内联结果事件"""
        base_event.update({
            "type": "notice",
            "detail_type": "telegram_chosen_inline_result",
            "user_id": str(result["from"]["id"]),
            "telegram_inline_result": {
                "result_id": result["result_id"],
                "query": result["query"],
                "inline_message_id": result.get("inline_message_id")
            }
        })
        return base_event

    def _handle_poll(self, poll: Dict, base_event: Dict) -> Dict:
        """处理投票事件"""
        base_event.update({
            "type": "notice",
            "detail_type": "telegram_poll",
            "telegram_poll": {
                "id": poll["id"],
                "question": poll["question"],
                "options": poll["options"],
                "total_voter_count": poll.get("total_voter_count", 0),
                "is_closed": poll.get("is_closed", False),
                "is_anonymous": poll.get("is_anonymous", True)
            }
        })
        return base_event

    def _handle_poll_answer(self, answer: Dict, base_event: Dict) -> Dict:
        """处理投票答案事件"""
        base_event.update({
            "type": "notice",
            "detail_type": "telegram_poll_answer",
            "user_id": str(answer["user"]["id"]),
            "telegram_poll_answer": {
                "poll_id": answer["poll_id"],
                "option_ids": answer["option_ids"]
            }
        })
        return base_event