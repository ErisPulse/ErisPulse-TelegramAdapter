import asyncio
import aiohttp
import json
from typing import Dict, List, Any
from ErisPulse import sdk
from ErisPulse.Core import router
from .Converter import TelegramConverter

class TelegramAdapter(sdk.BaseAdapter):
    class Send(sdk.BaseAdapter.Send):
        """消息发送DSL实现"""

        # 方法名映射表（全小写 -> 实际方法名）
        _METHOD_MAP = {
            # 消息发送方法
            "text": "Text",
            "image": "Image",
            "voice": "Voice",
            "video": "Video",
            "face": "Face",
            "file": "File",
            "document": "Document",
            "audio": "Audio",
            "markdown": "Markdown",
            "html": "HTML",
            
            # 批量和其他方法
            "recall": "Recall",
            "edit": "Edit",
            
            # 原始消息和转换
            "raw_ob12": "Raw_ob12",
            "raw_json": "Raw_json",
            
            # 链式修饰方法
            "at": "At",
            "atall": "AtAll",
            "reply": "Reply",
        }

        def __init__(self, adapter, target_type=None, target_id=None, account_id=None):
            super().__init__(adapter, target_type, target_id, account_id)
            self._at_user_ids = []       # @的用户列表
            self._reply_message_id = None # 回复的消息ID
            self._at_all = False         # 是否@全体

        def __getattr__(self, name):
            """
            处理未定义的发送方法（支持大小写不敏感）
            
            当调用不存在的消息类型方法时：
            1. 通过映射表查找对应的方法
            2. 如果找到则调用该方法
            3. 如果找不到，则发送文本提示不支持
            """
            name_lower = name.lower()
            
            # 查找映射
            if name_lower in self._METHOD_MAP:
                actual_method_name = self._METHOD_MAP[name_lower]
                return getattr(self, actual_method_name)
            
            # 方法不存在，返回文本提示
            def unsupported_method(*args, **kwargs):
                # 格式化参数信息
                params_info = []
                for i, arg in enumerate(args):
                    if isinstance(arg, bytes):
                        params_info.append(f"args[{i}]: <bytes: {len(arg)} bytes>")
                    else:
                        params_info.append(f"args[{i}]: {repr(arg)[:100]}")
                
                for k, v in kwargs.items():
                    if isinstance(v, bytes):
                        params_info.append(f"{k}: <bytes: {len(v)} bytes>")
                    else:
                        params_info.append(f"{k}: {repr(v)[:100]}")
                
                params_str = ", ".join(params_info)
                error_msg = f"[不支持的发送类型] 方法名: {name}, 参数: [{params_str}]"
                
                return self.Text(error_msg)
            
            return unsupported_method

        # ============ 消息发送方法 ============

        def Text(self, text: str):
            """发送文本消息"""
            params = {
                "chat_id": self._target_id,
                "text": text
            }
            
            # 处理@用户
            entities = []
            if self._at_user_ids:
                mention_text = " ".join([f"@{uid}" for uid in self._at_user_ids])
                params["text"] = f"{mention_text} {text}"
                offset = 0
                for user_id in self._at_user_ids:
                    # 检查是否是用户名（包含@）还是纯数字ID
                    if str(user_id).isdigit():
                        # 用户ID模式：使用 text_mention 实体（需要 user 对象）
                        entities.append({
                            "type": "text_mention",
                            "offset": offset,
                            "length": len(f"@{user_id}"),
                            "user": {
                                "id": int(user_id)
                            }
                        })
                    else:
                        # 用户名模式：使用 mention 实体
                        entities.append({
                            "type": "mention",
                            "offset": offset,
                            "length": len(f"@{user_id}")
                        })
                    offset += len(f"@{user_id}") + 1
            
            # 处理@全体
            if self._at_all:
                params["text"] = f"@All {params['text']}"
            
            if entities:
                params["entities"] = entities
            
            # 处理回复（将字符串转换为整数）
            if self._reply_message_id:
                try:
                    params["reply_to_message_id"] = int(self._reply_message_id)
                except (ValueError, TypeError):
                    pass
            
            return asyncio.create_task(self._adapter.call_api(endpoint="sendMessage", **params))

        def Image(self, file: bytes | str, caption: str = "", content_type: str = None):
            """发送图片消息（支持 bytes 和 URL）"""
            # 判断是 URL 还是文件数据
            if isinstance(file, str):
                # URL 模式
                params = {
                    "photo": file,
                    "caption": caption,
                    "chat_id": self._target_id
                }
                if content_type is not None:
                    params["parse_mode"] = content_type
                if self._reply_message_id:
                    try:
                        params["reply_to_message_id"] = int(self._reply_message_id)
                    except (ValueError, TypeError):
                        pass
                return asyncio.create_task(self._adapter.call_api(endpoint="sendPhoto", **params))
            else:
                # 文件上传模式
                return asyncio.create_task(
                    self._upload_file_and_call_api(
                        "sendPhoto",
                        field_name="photo",
                        file=file,
                        chat_id=self._target_id,
                        caption=caption,
                        parse_mode=content_type
                    )
                )

        def Voice(self, file: bytes | str, caption: str = ""):
            """发送语音消息（支持 bytes 和 URL）"""
            # 判断是 URL 还是文件数据
            if isinstance(file, str):
                # URL 模式
                params = {
                    "voice": file,
                    "caption": caption,
                    "chat_id": self._target_id
                }
                if self._reply_message_id:
                    try:
                        params["reply_to_message_id"] = int(self._reply_message_id)
                    except (ValueError, TypeError):
                        pass
                return asyncio.create_task(self._adapter.call_api(endpoint="sendVoice", **params))
            else:
                # 文件上传模式
                return asyncio.create_task(
                    self._upload_file_and_call_api(
                        "sendVoice",
                        field_name="voice",
                        file=file,
                        chat_id=self._target_id,
                        caption=caption
                    )
                )

        def Video(self, file: bytes | str, caption: str = "", content_type: str = None):
            """发送视频消息（支持 bytes 和 URL）"""
            # 判断是 URL 还是文件数据
            if isinstance(file, str):
                # URL 模式
                params = {
                    "video": file,
                    "caption": caption,
                    "chat_id": self._target_id
                }
                if content_type is not None:
                    params["parse_mode"] = content_type
                if self._reply_message_id:
                    try:
                        params["reply_to_message_id"] = int(self._reply_message_id)
                    except (ValueError, TypeError):
                        pass
                return asyncio.create_task(self._adapter.call_api(endpoint="sendVideo", **params))
            else:
                # 文件上传模式
                return asyncio.create_task(
                    self._upload_file_and_call_api(
                        "sendVideo",
                        field_name="video",
                        file=file,
                        chat_id=self._target_id,
                        caption=caption,
                        parse_mode=content_type
                    )
                )

        def File(self, file: bytes | str, caption: str = ""):
            """发送文件消息（通用方法，支持 bytes 和 URL）"""
            # 判断是 URL 还是文件数据
            if isinstance(file, str):
                # URL 模式
                params = {
                    "document": file,
                    "caption": caption,
                    "chat_id": self._target_id
                }
                if self._reply_message_id:
                    try:
                        params["reply_to_message_id"] = int(self._reply_message_id)
                    except (ValueError, TypeError):
                        pass
                return asyncio.create_task(self._adapter.call_api(endpoint="sendDocument", **params))
            else:
                # 文件上传模式
                return asyncio.create_task(
                    self._upload_file_and_call_api(
                        "sendDocument",
                        field_name="document",
                        file=file,
                        chat_id=self._target_id,
                        caption=caption
                    )
                )

        def Document(self, file: bytes | str, caption: str = "", content_type: str = None):
            """发送文档消息（File 的别名）"""
            return self.File(file, caption)

        def Audio(self, file: bytes | str, caption: str = "", content_type: str = None):
            """发送音频消息（支持 bytes 和 URL）"""
            # 判断是 URL 还是文件数据
            if isinstance(file, str):
                # URL 模式
                params = {
                    "audio": file,
                    "caption": caption,
                    "chat_id": self._target_id
                }
                if content_type is not None:
                    params["parse_mode"] = content_type
                if self._reply_message_id:
                    try:
                        params["reply_to_message_id"] = int(self._reply_message_id)
                    except (ValueError, TypeError):
                        pass
                return asyncio.create_task(self._adapter.call_api(endpoint="sendAudio", **params))
            else:
                # 文件上传模式
                return asyncio.create_task(
                    self._upload_file_and_call_api(
                        "sendAudio",
                        field_name="audio",
                        file=file,
                        chat_id=self._target_id,
                        caption=caption,
                        parse_mode=content_type
                    )
                )

        def Face(self, emoji: str):
            """发送表情消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendMessage",
                    chat_id=self._target_id,
                    text=emoji
                )
            )

        def Markdown(self, text: str, content_type: str = "MarkdownV2"):
            """发送 Markdown 格式消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendMessage",
                    chat_id=self._target_id,
                    text=text,
                    parse_mode=content_type
                )
            )

        def HTML(self, text: str):
            """发送 HTML 格式消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="sendMessage",
                    chat_id=self._target_id,
                    text=text,
                    parse_mode="HTML"
                )
            )

        def Edit(self, message_id: int, text: str, content_type: str = None):
            """编辑消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="editMessageText",
                    chat_id=self._target_id,
                    message_id=message_id,
                    text=text,
                    parse_mode=content_type
                )
            )

        def Recall(self, message_id: int):
            """撤回消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="deleteMessage",
                    chat_id=self._target_id,
                    message_id=message_id
                )
            )

        # ============ 原始消息发送方法 ============

        def Raw_ob12(self, message: List[Dict], **kwargs):
            """
            发送原始 OneBot12 格式的消息
            
            :param message: OneBot12 格式的消息段数组
            :param kwargs: 额外参数
            :return: asyncio.Task 对象
            """
            import asyncio
            
            async def _send_raw_ob12():
                # 将 OneBot12 消息段转换为 Telegram API 格式
                converted = await self._convert_ob12_to_telegram(message, **kwargs)
                
                if isinstance(converted, dict):
                    # 单个 API 调用
                    return await self._adapter.call_api(
                        endpoint=converted["endpoint"],
                        **converted["params"]
                    )
                elif isinstance(converted, list):
                    # 多个 API 调用（按顺序执行）
                    results = []
                    for call in converted:
                        result = await self._adapter.call_api(
                            endpoint=call["endpoint"],
                            **call["params"]
                        )
                        results.append(result)
                    return results[-1] if results else None
            
            return asyncio.create_task(_send_raw_ob12())

        def Raw_json(self, json_str: str):
            """
            发送原始 JSON 格式的消息
            
            :param json_str: JSON 格式的字符串
            :return: asyncio.Task 对象
            """
            import asyncio
            data = json.loads(json_str)
            
            async def _send_raw_json():
                endpoint = data.pop("endpoint", "sendMessage")
                return await self._adapter.call_api(endpoint=endpoint, **data)
            
            return asyncio.create_task(_send_raw_json())

        # ============ 链式修饰方法 ============

        def At(self, user_id: str) -> 'Send':
            """@用户（可多次调用）"""
            self._at_user_ids.append(user_id)
            return self

        def AtAll(self) -> 'Send':
            """@全体成员"""
            self._at_all = True
            return self

        def Reply(self, message_id: str) -> 'Send':
            """回复消息"""
            self._reply_message_id = message_id
            return self

        # ============ 辅助方法 ============

        async def _convert_ob12_to_telegram(self, message_segments: List[Dict], **kwargs) -> Dict:
            """
            将 OneBot12 消息段转换为 Telegram API 格式
            
            :param message_segments: OneBot12 消息段数组
            :param kwargs: 额外参数
            :return: Telegram API 调用格式
            """
            # 第一遍扫描：确定消息类型和收集文本
            text_parts = []
            entities = []
            media_segment = None  # 存储媒体消息段（如果有）
            reply_message_id = None
            at_all = False
            
            for segment in message_segments:
                seg_type = segment.get("type")
                data = segment.get("data", {})
                
                if seg_type == "text":
                    text_parts.append(data.get("text", ""))
                
                elif seg_type in ["image", "video", "voice", "file", "audio"]:
                    # 媒体消息段：只保留第一个媒体段
                    if not media_segment:
                        media_segment = {"type": seg_type, "data": data}
                
                elif seg_type == "at":
                    user_id = data.get("user_id", "")
                    mention_text = data.get("name", f"@{user_id}")
                    start_pos = len("".join(text_parts))
                    text_parts.append(mention_text)
                    
                    # 检查是用户ID还是用户名
                    if str(user_id).isdigit():
                        # 用户ID模式：使用 text_mention 实体
                        entities.append({
                            "type": "text_mention",
                            "offset": start_pos,
                            "length": len(mention_text),
                            "user": {"id": int(user_id)}
                        })
                    else:
                        # 用户名模式：使用 mention 实体
                        entities.append({
                            "type": "mention",
                            "offset": start_pos,
                            "length": len(mention_text)
                        })
                
                elif seg_type == "mention":
                    # OneBot12 标准的 mention 类型
                    user_id = data.get("user_id", "")
                    name = data.get("name", f"@{user_id}")
                    start_pos = len("".join(text_parts))
                    text_parts.append(name)
                    
                    # 检查是用户ID还是用户名
                    if str(user_id).isdigit():
                        entities.append({
                            "type": "text_mention",
                            "offset": start_pos,
                            "length": len(name),
                            "user": {"id": int(user_id)}
                        })
                    else:
                        entities.append({
                            "type": "mention",
                            "offset": start_pos,
                            "length": len(name)
                        })
                
                elif seg_type == "reply":
                    # 回复消息
                    msg_id = data.get("message_id")
                    if msg_id:
                        try:
                            reply_message_id = int(msg_id)
                        except (ValueError, TypeError):
                            pass
            
            # 构建 API 调用参数
            params = {
                "chat_id": self._target_id
            }
            
            # 处理回复消息（优先级：消息段中的 > 链式修饰符）
            final_reply_id = reply_message_id or self._reply_message_id
            if final_reply_id:
                try:
                    params["reply_to_message_id"] = int(final_reply_id)
                except (ValueError, TypeError):
                    pass
            
            # 处理@全体（优先级：消息段中的 > 链式修饰符）
            final_at_all = at_all or self._at_all
            
            # 添加手动设置的@用户
            for user_id in self._at_user_ids:
                mention_text = f"@{user_id}"
                start_pos = len("".join(text_parts))
                text_parts.append(" " + mention_text)
                
                if str(user_id).isdigit():
                    entities.append({
                        "type": "text_mention",
                        "offset": start_pos,
                        "length": len(mention_text),
                        "user": {"id": int(user_id)}
                    })
                else:
                    entities.append({
                        "type": "mention",
                        "offset": start_pos,
                        "length": len(mention_text)
                    })
            
            # 构建最终文本
            full_text = "".join(text_parts)
            if final_at_all:
                full_text = "@All " + full_text
            
            # 根据是否有媒体消息段决定 API 调用类型
            if media_segment:
                # 媒体消息
                seg_type = media_segment["type"]
                data = media_segment["data"]
                
                # 根据类型确定 endpoint 和字段名
                if seg_type == "image":
                    endpoint = "sendPhoto"
                    field_name = "photo"
                elif seg_type == "video":
                    endpoint = "sendVideo"
                    field_name = "video"
                elif seg_type == "voice":
                    endpoint = "sendVoice"
                    field_name = "voice"
                elif seg_type == "audio":
                    endpoint = "sendAudio"
                    field_name = "audio"
                else:  # file
                    endpoint = "sendDocument"
                    field_name = "document"
                
                # 媒体文件路径
                media_file = data.get("file_id") or data.get("url") or data.get("file", "")
                
                # 构建参数
                params[field_name] = media_file
                params["caption"] = full_text or data.get("caption", "")
                
                return {
                    "endpoint": endpoint,
                    "params": params
                }
            else:
                # 纯文本消息
                params["text"] = full_text or " "
                
                if entities:
                    params["entities"] = entities
                
                return {
                    "endpoint": "sendMessage",
                    "params": params
                }

        async def _upload_file_and_call_api(self, endpoint, field_name, file, **kwargs):
            """上传文件并调用 Telegram API"""
            # 将content_type转换为parse_mode以符合Telegram API
            if 'content_type' in kwargs:
                content_type = kwargs.pop('content_type')
                # 只有当 content_type 不为 None 时才设置 parse_mode
                if content_type is not None:
                    kwargs['parse_mode'] = content_type
                
            # 添加链式修饰参数（将字符串转换为整数）
            if self._reply_message_id:
                try:
                    kwargs['reply_to_message_id'] = int(self._reply_message_id)
                except (ValueError, TypeError):
                    pass
            
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
                raw_response = await response.json()
                
                # 标准化响应
                return {
                    "status": "ok" if raw_response.get("ok") else "failed",
                    "retcode": 0 if raw_response.get("ok") else 34000,
                    "data": raw_response.get("result"),
                    "message_id": str(raw_response.get("result", {}).get("message_id", "")) if isinstance(raw_response.get("result"), dict) else "",
                    "message": "" if raw_response.get("ok") else raw_response.get("description", "Unknown error"),
                    "telegram_raw": raw_response
                }

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
        self._proxy_config = self.config.get("proxy", {}) if self._proxy_enabled else None
        self.convert = TelegramConverter(self.token).convert

    def _load_config(self):
        config = self.sdk.config.getConfig("Telegram_Adapter")
        if not config:
            # 新配置（无 mode 和 webhook）
            default_config = {
                "token": "YOUR_BOT_TOKEN",
                "proxy_enabled": False,
                "proxy": {
                    "host": "127.0.0.1",
                    "port": 1080,
                    "type": "socks5"
                }
            }
            try:
                sdk.logger.warning("Telegram适配器配置不存在，已自动创建默认配置")
                self.sdk.config.setConfig("Telegram_Adapter", default_config)
                return default_config
            except Exception as e:
                self.logger.error(f"保存默认配置失败: {str(e)}")
                return default_config
        
        # 兼容旧版配置：检查是否有 mode 和 webhook 配置
        has_mode = "mode" in config
        has_webhook = "webhook" in config
        
        if has_mode or has_webhook:
            mode = config.get("mode", "polling")
            
            # 如果旧版配置是 webhook 模式，发出 Error 日志
            if mode == "webhook":
                self.logger.error("Telegram 适配器不再支持 Webhook 模式！请切换到 Polling 模式。将自动使用 Polling 模式启动。")
            elif has_webhook:
                self.logger.warning("检测到旧版 Webhook 配置，已自动忽略。Telegram 适配器将使用 Polling 模式。")
            else:
                self.logger.info("检测到旧版配置，已自动兼容。当前使用 Polling 模式。")
        
        return config

    async def _poll_updates(self):
        """轮询获取 Telegram 更新"""
        offset = 0
        while True:
            try:
                response = await self.call_api(
                    "getUpdates",
                    offset=offset,
                    timeout=60
                )
                
                # 检查API调用是否成功
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
                            self.logger.debug(f"OneBot12事件数据: {json.dumps(onebot_event, ensure_ascii=False)}")
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
                
                # 检查响应是否为预期的字典格式
                if not isinstance(raw_response, dict):
                    self.logger.error(f"Telegram API 返回了意外的响应格式: {type(raw_response)}, 内容: {raw_response}")
                    return {
                        "status": "failed",
                        "retcode": 34000,
                        "data": None,
                        "message_id": "",
                        "message": f"API 返回了意外格式: {type(raw_response)}",
                        "telegram_raw": raw_response,
                        "echo": params.get("echo", "")
                    }
                
                # 构建标准化响应
                response_data = {
                    "status": "ok" if raw_response.get("ok") else "failed",
                    "retcode": 0 if raw_response.get("ok") else 34000,  # 34xxx 平台错误
                    "data": raw_response.get("result"),
                    "message_id": str(raw_response.get("result", {}).get("message_id", "")) if isinstance(raw_response.get("result"), dict) else "",
                    "message": "" if raw_response.get("ok") else raw_response.get("description", "Unknown Telegram API error"),
                    "telegram_raw": raw_response
                }
                
                # 处理echo字段
                if "echo" in params:
                    response_data["echo"] = params["echo"]
                    
                return response_data
                
        except Exception as e:
            self.logger.error(f"调用Telegram API失败: {str(e)}")
            return {
                "status": "failed",
                "retcode": 33001,  # 网络错误
                "data": None,
                "message_id": "",
                "message": f"API调用失败: {str(e)}",
                "telegram_raw": None,
                "echo": params.get("echo", "")
            }
        
    async def start(self):
        """启动适配器（仅支持 polling 模式）"""
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

        # 启动轮询模式
        self.poll_task = asyncio.create_task(self._poll_updates())
        self.logger.info("Telegram适配器已启动（polling 模式）")

    async def shutdown(self):
        """关闭适配器"""
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

        self.logger.info("Telegram适配器已关闭")