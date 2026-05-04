import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from ErisPulse import sdk


@dataclass
class TestConfig:
    """测试配置类"""
    # 适配器配置
    adapter_name: str = "telegram"  # 要测试的适配器名称
    
    # 基础配置
    group_id: str = "-1002850921906"  # 测试群号
    test_user_id: str = "6117725680"  # 测试用户ID
    test_user_id_2: str = "1725385676"  # 第二个测试用户ID
    
    # 文件路径配置
    test_files_dir: str = "test_files"
    video_file: str = "test.mp4"
    image_file: str = "test.jpg"
    doc_file  : str = "test.docx"
    voice_file: Optional[str] = "M5000017K7gL4WYnw2.mp3"
    
    # 消息发送间隔（秒）
    send_interval: float = 3.0
    
    # 启用/禁用特定测试
    enable_basic_tests: bool = False  # 基础测试（1-5）
    enable_media_tests: bool = False  # 媒体测试（6-11）
    enable_advanced_tests: bool = False  # 高级功能测试（12-16）
    enable_format_tests: bool = True  # 格式化消息测试（17-19）
    enable_chain_tests: bool = True  # 链式调用测试（20-24）
    enable_mention_tests: bool = True  # @功能测试（25-26）
    enable_keyboard_tests: bool = True  # 内联键盘测试（27-29）
    enable_special_tests: bool = True  # 特殊消息测试（30-34）
    enable_message_mgmt_tests: bool = True  # 消息管理测试（35-38）
    enable_modifier_tests: bool = True  # 修饰符测试（39-41）
    
    # 单独启用的测试（列表形式）
    # 例如：[1, 6, 7] 表示只运行测试1、6和7
    # 如果为空列表，则根据上面的 bool 配置运行
    specific_tests: List[int] = field(default_factory=list)
    
    # URL 配置
    image_url: str = "https://http.cat/200"
    voice_url: str = "https://download.samplelib.com/mp3/sample-12s.mp3"
    video_url: str = "https://www.w3school.com.cn/example/html5/mov_bbb.mp4"
    file_url: str = "https://www.w3school.com.cn/example/html5/mov_bbb.mp4"


@dataclass
class TestResult:
    """单个测试结果"""
    test_num: int
    test_name: str
    status: str  # "success", "failed", "error", "skipped"
    response: Optional[dict] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class TestCase:
    """测试用例类"""
    name: str
    enabled: bool = True
    async_func: Optional[callable] = None
    description: str = ""


class TestRunner:
    """测试运行器"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.adapter = None
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []
        self.reply_message_id = ""  # 用于存储回复测试的 message_id
        self.recall_message_id = ""  # 用于存储撤回测试的 message_id
        
    def setup(self):
        """初始化"""
        self.adapter = getattr(sdk.adapter, self.config.adapter_name).Send
        self._register_test_cases()
        
    def _read_file(self, filename: str) -> Optional[bytes]:
        """读取文件内容"""
        file_path = Path(self.config.test_files_dir) / filename
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def _register_test_cases(self):
        """注册所有测试用例"""
        # 基础测试
        self._add_basic_tests()
        # 媒体测试
        self._add_media_tests()
        # 高级功能测试
        self._add_advanced_tests()
        # 格式化消息测试
        self._add_format_tests()
        # 链式调用测试
        self._add_chain_tests()
        # @功能测试
        self._add_mention_tests()
        # 内联键盘测试
        self._add_keyboard_tests()
        # 特殊消息测试
        self._add_special_tests()
        # 消息管理测试
        self._add_message_mgmt_tests()
        # 修饰符测试
        self._add_modifier_tests()
    
    def _add_basic_tests(self):
        """添加基础测试用例"""
        self.test_cases.extend([
            TestCase("发送文本消息", self.config.enable_basic_tests, None),
            TestCase("发送@用户消息", self.config.enable_basic_tests, None),
            TestCase("发送表情（emoji）", self.config.enable_basic_tests, None),
            TestCase("发送Markdown消息", self.config.enable_basic_tests, None),
            TestCase("发送Html消息", self.config.enable_basic_tests, None),
        ])
    
    def _add_media_tests(self):
        """添加媒体测试用例"""
        self.test_cases.extend([
            TestCase("发送图片（本地文件）", self.config.enable_media_tests, None),
            TestCase("发送图片（URL）", self.config.enable_media_tests, None),
            TestCase("发送视频（本地文件）", self.config.enable_media_tests, None),
            TestCase("发送视频（URL）", self.config.enable_media_tests, None),
            TestCase("发送语音（本地文件）", self.config.enable_media_tests, None),
            TestCase("发送语音（URL）", self.config.enable_media_tests, None),
        ])
    
    def _add_advanced_tests(self):
        """添加高级功能测试用例"""
        self.test_cases.extend([
            TestCase("发送文件（本地）", self.config.enable_advanced_tests, None),
            TestCase("发送文件（URL）", self.config.enable_advanced_tests, None),
            TestCase("发送回复消息", self.config.enable_advanced_tests, None),
            TestCase("发送组合消息", self.config.enable_advanced_tests, None),
            TestCase("撤回消息", self.config.enable_advanced_tests, None),
        ])
    
    def _add_format_tests(self):
        """添加格式化消息测试用例"""
        self.test_cases.extend([
            TestCase("发送格式化消息（Raw_ob12）", self.config.enable_format_tests, None),
            TestCase("发送文本消息段", self.config.enable_format_tests, None),
            TestCase("发送组合消息段", self.config.enable_format_tests, None),
        ])
    
    def _add_chain_tests(self):
        """添加链式调用测试用例"""
        self.test_cases.extend([
            TestCase("多次@用户（链式调用）", self.config.enable_chain_tests, None),
            TestCase("链式调用 - 回复+@用户", self.config.enable_chain_tests, None),
            TestCase("链式调用 - 组合修饰符", self.config.enable_chain_tests, None),
            TestCase("格式化消息 + 链式@", self.config.enable_chain_tests, None),
            TestCase("复杂组合消息", self.config.enable_chain_tests, None),
        ])
    
    def _add_mention_tests(self):
        """添加@功能测试用例"""
        self.test_cases.extend([
            TestCase("@全体成员", self.config.enable_mention_tests, None),
            TestCase("@全体 + @用户组合", self.config.enable_mention_tests, None),
        ])
    
    def _add_keyboard_tests(self):
        """添加内联键盘测试用例"""
        self.test_cases.extend([
            TestCase("发送内联键盘消息", self.config.enable_keyboard_tests, None),
            TestCase("内联键盘 + 回复", self.config.enable_keyboard_tests, None),
            TestCase("复杂内联键盘", self.config.enable_keyboard_tests, None),
        ])
    
    def _add_special_tests(self):
        """添加特殊消息测试用例"""
        self.test_cases.extend([
            TestCase("发送贴纸（file_id）", self.config.enable_special_tests, None),
            TestCase("发送位置", self.config.enable_special_tests, None),
            TestCase("发送地点（Venue）", self.config.enable_special_tests, None),
            TestCase("发送联系人", self.config.enable_special_tests, None),
            TestCase("发送 Raw_json", self.config.enable_special_tests, None),
        ])
    
    def _add_message_mgmt_tests(self):
        """添加消息管理测试用例"""
        self.test_cases.extend([
            TestCase("编辑消息", self.config.enable_message_mgmt_tests, None),
            TestCase("转发消息", self.config.enable_message_mgmt_tests, None),
            TestCase("复制消息", self.config.enable_message_mgmt_tests, None),
            TestCase("AnswerCallback 应答", self.config.enable_message_mgmt_tests, None),
        ])
    
    def _add_modifier_tests(self):
        """添加修饰符测试用例"""
        self.test_cases.extend([
            TestCase("ProtectContent 保护内容", self.config.enable_modifier_tests, None),
            TestCase("Silent 静默发送", self.config.enable_modifier_tests, None),
            TestCase("全修饰符组合", self.config.enable_modifier_tests, None),
        ])
    
    def _check_response(self, response: Any) -> tuple[bool, Optional[dict]]:
        """检查响应是否成功"""
        if response is None:
            return False, None
        
        # 如果是 Task 对象，获取结果
        if hasattr(response, '__await__'):
            # 这是一个协程，已经被 await 了
            if isinstance(response, dict):
                resp = response
            else:
                return False, None
        elif isinstance(response, dict):
            resp = response
        else:
            return False, None
        
        # 检查响应格式是否符合标准
        if isinstance(resp, dict):
            status = resp.get("status")
            retcode = resp.get("retcode", -1)
            
            if status == "ok" and retcode == 0:
                return True, resp
        
        return False, resp
    
    async def run_test(self, test_num: int):
        """运行单个测试"""
        if test_num > len(self.test_cases) or test_num < 1:
            return
        
        test_case = self.test_cases[test_num - 1]
        print(f"{test_num}. {test_case.name}")
        
        result = TestResult(
            test_num=test_num,
            test_name=test_case.name,
            status="skipped"
        )
        
        start_time = time.time()
        
        try:
            # 执行测试
            response = await self._execute_test(test_num)
            
            # 检查结果
            success, resp_dict = self._check_response(response)
            
            result.execution_time = time.time() - start_time
            result.response = resp_dict
            
            if success:
                result.status = "success"
                print(f"  成功 - {result.execution_time:.2f}s")
            else:
                result.status = "failed"
                if resp_dict:
                    retcode = resp_dict.get("retcode", -1)
                    message = resp_dict.get("message", "")
                    print(f"  失败 - retcode: {retcode}, message: {message}")
                else:
                    print(f"  失败 - 无效响应")
                    
        except Exception as e:
            result.execution_time = time.time() - start_time
            result.status = "error"
            result.error_message = str(e)
            print(f"  错误 - {type(e).__name__}: {str(e)}")
        
        self.results.append(result)
        await asyncio.sleep(self.config.send_interval)
    
    async def _execute_test(self, test_num: int) -> Optional[Any]:
        """执行具体的测试逻辑"""
        group_id = self.config.group_id
        test_user_id = self.config.test_user_id
        
        # 1. 发送文本消息
        if test_num == 1:
            return await self.adapter.To("group", group_id).Text("Hello, 这是一条测试消息！")
        
        # 2. 发送@用户消息
        elif test_num == 2:
            return await self.adapter.To("group", group_id).At(test_user_id).Text("@某位成员")
        
        # 3. 发送表情
        elif test_num == 3:
            return await self.adapter.To("group", group_id).Face("1")
        
        # 4. 发送Markdown消息
        elif test_num == 4:
            markdown_text = "**粗体** 和 *斜体* 文本测试"
            return await self.adapter.To("group", group_id).Markdown(markdown_text)
        
        # 5. 发送Html消息
        elif test_num == 5:
            html_text = "<b>粗体</b> 和 <i>斜体</i> 文本测试"
            return await self.adapter.To("group", group_id).Html(html_text)
        
        # 6. 发送图片（本地文件）
        elif test_num == 6:
            image_data = self._read_file(self.config.image_file)
            if image_data:
                return await self.adapter.To("group", group_id).Image(image_data)
            # 回退到 URL 方式
            return await self.adapter.To("group", group_id).Image(self.config.image_url)
        
        # 7. 发送图片（URL）
        elif test_num == 7:
            return await self.adapter.To("group", group_id).Image(self.config.image_url)
        
        # 8. 发送视频（本地文件）
        elif test_num == 8:
            video_data = self._read_file(self.config.video_file)
            if video_data:
                return await self.adapter.To("group", group_id).Video(video_data)
            # 回退到 URL 方式
            return await self.adapter.To("group", group_id).Video(self.config.video_url)
        
        # 9. 发送视频（URL）
        elif test_num == 9:
            return await self.adapter.To("group", group_id).Video(self.config.video_url)
        
        # 10. 发送语音（本地文件）
        elif test_num == 10:
            if self.config.voice_file:
                voice_data = self._read_file(self.config.voice_file)
                if voice_data:
                    return await self.adapter.To("group", group_id).Voice(voice_data)
            # 回退到 URL 方式
            return await self.adapter.To("group", group_id).Voice(self.config.voice_url)
        
        # 11. 发送语音（URL）
        elif test_num == 11:
            return await self.adapter.To("group", group_id).Voice(self.config.voice_url)
        
        # 12. 发送文件（本地）
        elif test_num == 12:
            file_data = self._read_file(self.config.doc_file)
            if file_data:
                return await self.adapter.To("group", group_id).File(file_data, self.config.doc_file)
            return await self.adapter.To("group", group_id).File(self.config.file_url)
        
        # 13. 发送文件（URL）
        elif test_num == 13:
            return await self.adapter.To("group", group_id).File(self.config.file_url)
        
        # 14. 发送回复消息
        elif test_num == 14:
            test_message = "这是一条测试消息，用于后续回复功能测试"
            result = await self.adapter.To("group", group_id).Text(test_message)
            
            # 尝试获取 message_id
            if isinstance(result, dict) and result.get("data", {}).get("message_id"):
                self.reply_message_id = result["data"]["message_id"]
            else:
                self.reply_message_id = "temp_msg_id_" + str(int(time.time()))
            
            return result
        
        # 15. 发送组合消息
        elif test_num == 15:
            ob12_message = [
                {"type": "text", "data": {"text": "组合消息测试："}},
                {"type": "mention", "data": {"user_id": test_user_id}}
            ]
            return await self.adapter.To("group", group_id).Raw_ob12(ob12_message)
        
        # 16. 撤回消息
        elif test_num == 16:
            # 先发送一条消息
            test_message = "这条消息将被撤回"
            result = await self.adapter.To("group", group_id).Text(test_message)
            # 获取 message_id
            self.recall_message_id = result.get("data", {}).get("message_id")
            
            # 等待一下再撤回
            await asyncio.sleep(2)
            # 撤回消息
            return await self.adapter.To("group", group_id).Recall(self.recall_message_id)
        
        # 17. 发送格式化消息（Raw_ob12）
        elif test_num == 17:
            ob12_message = [
                {"type": "text", "data": {"text": "这是格式化消息 "}},
                {"type": "text", "data": {"text": "使用 Raw_ob12 发送"}}
            ]
            return await self.adapter.To("group", group_id).Raw_ob12(ob12_message)
        
        # 18. 发送文本消息段
        elif test_num == 18:
            ob12_message = [
                {"type": "text", "data": {"text": "第一条文本消息段"}},
                {"type": "text", "data": {"text": "第二条文本消息段"}}
            ]
            return await self.adapter.To("group", group_id).Raw_ob12(ob12_message)
        
        # 19. 发送组合消息段
        elif test_num == 19:
            ob12_message = [
                {"type": "text", "data": {"text": "文本 + 图片："}},
                {"type": "image", "data": {"file": self.config.image_url}}
            ]
            return await self.adapter.To("group", group_id).Raw_ob12(ob12_message)
        
        # 20. 多次@用户（链式调用）
        elif test_num == 20:
            return await self.adapter.To("group", group_id).At(test_user_id).At(self.config.test_user_id_2).Text(" @多个用户")
        
        # 21. 链式调用 - 回复+@用户
        elif test_num == 21:
            return await self.adapter.To("group", group_id).Reply(self.reply_message_id).At(test_user_id).Text("回复并@用户")
        
        # 22. 链式调用 - 组合修饰符
        elif test_num == 22:
            return await self.adapter.To("group", group_id).At(test_user_id).Reply(self.reply_message_id).Text("@用户并回复")
        
        # 23. 格式化消息 + 链式@
        elif test_num == 23:
            ob12_message = [{"type": "text", "data": {"text": "格式化消息 + 链式@"}}]
            return await self.adapter.To("group", group_id).At(test_user_id).Raw_ob12(ob12_message)
        
        # 24. 复杂组合消息
        elif test_num == 24:
            ob12_message = [
                {"type": "text", "data": {"text": "复杂组合消息："}},
                {"type": "mention", "data": {"user_id": test_user_id}},
                {"type": "reply", "data": {"message_id": self.reply_message_id}}
            ]
            return await self.adapter.To("group", group_id).Raw_ob12(ob12_message)
        
        # 25. @全体成员
        elif test_num == 25:
            return await self.adapter.To("group", group_id).AtAll().Text("这是全体成员消息")
        
        # 26. @全体 + @用户组合
        elif test_num == 26:
            return await self.adapter.To("group", group_id).AtAll().At(test_user_id).Text("全体 + 单个@")
        
        # ========== 27-29: 内联键盘测试 ==========
        
        # 27. 发送内联键盘消息
        elif test_num == 27:
            keyboard = [
                [
                    {"text": "按钮1", "callback_data": "btn1"},
                    {"text": "按钮2", "callback_data": "btn2"},
                ]
            ]
            return await self.adapter.To("group", group_id).Keyboard(keyboard).Text("请选择一个选项：")
        
        # 28. 内联键盘 + 回复
        elif test_num == 28:
            keyboard = [
                [
                    {"text": "确认", "callback_data": "confirm"},
                    {"text": "取消", "callback_data": "cancel"},
                ]
            ]
            return await self.adapter.To("group", group_id).Keyboard(keyboard).Reply(self.reply_message_id).Text("确认操作？")
        
        # 29. 复杂内联键盘
        elif test_num == 29:
            keyboard = [
                [
                    {"text": "🔗 访问网站", "url": "https://example.com"},
                    {"text": "📋 复制内容", "callback_data": "copy"},
                ],
                [
                    {"text": "✅ 确认", "callback_data": "yes"},
                    {"text": "❌ 取消", "callback_data": "no"},
                ],
                [
                    {"text": "🔍 内联搜索", "switch_inline_query_current_chat": "search "},
                ],
            ]
            return await self.adapter.To("group", group_id).Keyboard(keyboard).Text("复杂内联键盘演示：")
        
        # ========== 30-34: 特殊消息测试 ==========
        
        # 30. 发送贴纸（使用 file_id 或 URL）
        elif test_num == 30:
            # 使用一个公开贴纸的 file_id（如果不可用则回退到文本）
            try:
                return await self.adapter.To("group", group_id).Sticker(self.config.image_url)
            except Exception:
                return await self.adapter.To("group", group_id).Text("[贴纸发送测试] 需要有效的 sticker file_id")
        
        # 31. 发送位置
        elif test_num == 31:
            return await self.adapter.To("group", group_id).Location(39.9042, 116.4074)
        
        # 32. 发送地点（Venue）
        elif test_num == 32:
            return await self.adapter.To("group", group_id).Venue(39.9042, 116.4074, "天安门广场", "北京市东城区")
        
        # 33. 发送联系人
        elif test_num == 33:
            return await self.adapter.To("group", group_id).Contact("8613800138000", "测试", "联系人")
        
        # 34. 发送 Raw_json
        elif test_num == 34:
            raw_json = '{"endpoint": "sendMessage", "chat_id": "' + group_id + '", "text": "Raw_json 发送测试"}'
            return await self.adapter.To("group", group_id).Raw_json(raw_json)
        
        # ========== 35-38: 消息管理测试 ==========
        
        # 35. 编辑消息
        elif test_num == 35:
            # 先发送一条消息
            result = await self.adapter.To("group", group_id).Text("这条消息将被编辑...")
            msg_id = result.get("data", {}).get("message_id")
            if msg_id:
                await asyncio.sleep(2)
                return await self.adapter.To("group", group_id).Edit(msg_id, "✅ 消息已编辑！")
            return result
        
        # 36. 转发消息
        elif test_num == 36:
            # 先发一条消息再转发
            result = await self.adapter.To("group", group_id).Text("需要转发的消息")
            msg_id = result.get("data", {}).get("message_id")
            if msg_id:
                await asyncio.sleep(2)
                return await self.adapter.To("group", group_id).Forward(group_id, msg_id)
            return result
        
        # 37. 复制消息
        elif test_num == 37:
            # 先发一条消息再复制
            result = await self.adapter.To("group", group_id).Text("需要复制的消息")
            msg_id = result.get("data", {}).get("message_id")
            if msg_id:
                await asyncio.sleep(2)
                return await self.adapter.To("group", group_id).CopyMessage(group_id, msg_id)
            return result
        
        # 38. AnswerCallback 应答（需要有效的 callback_query_id，此处仅展示调用方式）
        elif test_num == 38:
            # 先发送带按钮的消息
            keyboard = [[{"text": "点击我", "callback_data": "test_callback"}]]
            result = await self.adapter.To("group", group_id).Keyboard(keyboard).Text("AnswerCallback 测试 - 请点击按钮触发回调")
            self.reply_message_id = result.get("data", {}).get("message_id", "")
            return result
        
        # ========== 39-41: 修饰符测试 ==========
        
        # 39. ProtectContent 保护内容
        elif test_num == 39:
            return await self.adapter.To("group", group_id).ProtectContent(True).Text("🔒 这条消息受保护，无法转发")
        
        # 40. Silent 静默发送
        elif test_num == 40:
            return await self.adapter.To("group", group_id).Silent(True).Text("🔇 这是一条静默消息")
        
        # 41. 全修饰符组合
        elif test_num == 41:
            keyboard = [[{"text": "组合按钮", "callback_data": "combo"}]]
            return await (
                self.adapter.To("group", group_id)
                .ProtectContent(True)
                .Silent(True)
                .At(test_user_id)
                .Keyboard(keyboard)
                .Text("🔒🔇 全修饰符组合测试")
            )
        
        return None
    
    def _print_summary(self):
        """打印测试结果汇总"""
        success_count = sum(1 for r in self.results if r.status == "success")
        failed_count = sum(1 for r in self.results if r.status == "failed")
        error_count = sum(1 for r in self.results if r.status == "error")
        total_time = sum(r.execution_time for r in self.results)
        
        print("\n___")
        print("测试结果")
        print("    总结")
        print(f"         成功：{success_count}个")
        print(f"         失败：{failed_count}个")
        print(f"         错误：{error_count}个")
        
        if failed_count > 0:
            print("\n    失败详情")
            for r in self.results:
                if r.status == "failed":
                    if r.response:
                        retcode = r.response.get("retcode", -1)
                        message = r.response.get("message", "")
                        print(f"         [{r.test_num}] {r.test_name} - retcode: {retcode}, message: {message}")
                    else:
                        print(f"         [{r.test_num}] {r.test_name} - 无响应")
        
        if error_count > 0:
            print("\n    错误详情")
            for r in self.results:
                if r.status == "error":
                    print(f"         [{r.test_num}] {r.test_name} - {r.error_message}")
        
        print(f"\n    执行时间：{total_time:.2f} 秒")
        print("___")
    
    async def run_all(self):
        """运行所有启用的测试"""
        enabled_tests = []
        
        # 如果指定了特定测试，只运行这些测试
        if self.config.specific_tests:
            for test_num in self.config.specific_tests:
                if 1 <= test_num <= len(self.test_cases):
                    enabled_tests.append(test_num)
                else:
                    print(f"[警告] 无效的测试编号: {test_num}")
        else:
            # 否则根据配置运行所有启用的测试
            for i, test_case in enumerate(self.test_cases, 1):
                if test_case.enabled:
                    enabled_tests.append(i)
        
        print(f"准备运行 {len(enabled_tests)} 个测试用例")
        print("=" * 50)
        
        for test_num in enabled_tests:
            await self.run_test(test_num)
        
        print("=" * 50)
        self._print_summary()


async def main():
    try:
        isInit = await sdk.init_task()
        
        if not isInit:
            sdk.logger.error("ErisPulse 初始化失败，请检查日志")
            return
        
        await sdk.adapter.startup()

        # 等待适配器完全启动
        await asyncio.sleep(3)
        
        # 创建测试配置
        config = TestConfig()
        
        # 配置示例：
        # 1. 指定适配器
        # config.adapter_name = "onebot12"
        # config.adapter_name = "red"
        
        # 2. 只运行特定测试
        # config.specific_tests = [6, 7, 8, 9, 10, 11]  # 只运行媒体测试
        
        # 3. 禁用某些测试类别
        # config.enable_media_tests = False  # 禁用媒体测试
        # config.enable_chain_tests = False   # 禁用链式调用测试
        
        # 4. 配置文件路径
        # config.video_file = "my_video.mp4"
        # config.voice_file = "my_voice.amr"
        # config.test_files_dir = "custom/files"
        
        # 配置发送间隔（秒）
        # config.send_interval = 1.0
        
        print(f"测试适配器: {config.adapter_name}")
        print(f"测试目标: 群号 {config.group_id}")
        print("=" * 50)
        
        # 创建并运行测试
        runner = TestRunner(config)
        runner.setup()
        await runner.run_all()
        
        # 保持程序运行(不建议修改)
        await asyncio.Event().wait()
    except Exception as e:
        sdk.logger.error(f"发生错误: {e}", exc_info=True)
    except KeyboardInterrupt:
        sdk.logger.info("正在停止程序")
    finally:
        await sdk.adapter.shutdown()


if __name__ == "__main__":
    asyncio.run(main())