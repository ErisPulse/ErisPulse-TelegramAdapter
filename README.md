# ErisPulse Telegram Adapter

[English](#english) | [中文](#中文)

---

<a id="english"></a>

## English

A Telegram Bot API adapter for the [ErisPulse](https://github.com/ErisPulse/ErisPulse/) framework, supporting multi-account, multiple message types for sending/receiving, and platform-specific event handling.

### Installation

```bash
epsdk install TelegramAdapter
```

### Configuration

Add to `config/config.toml`:

```toml
[Telegram_Adapter.accounts.default]
token = "YOUR_BOT_TOKEN"
enabled = true

# Multi-account example
[Telegram_Adapter.accounts.bot2]
token = "ANOTHER_BOT_TOKEN"
enabled = true
```

#### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | Yes | Telegram Bot Token |
| `bot_id` | string | No | Automatically extracted from the Token; no need to fill in manually |
| `enabled` | bool | No | Whether to enable (default true) |

#### Legacy Configuration Compatibility

The legacy single-token format is still supported:

```toml
[Telegram_Adapter]
token = "YOUR_BOT_TOKEN"
```

Migrating to the new format is recommended to support multi-account.

#### Proxy

If you need to connect to the Telegram API through a proxy, set system-level proxy environment variables (such as `ALL_PROXY`, `HTTPS_PROXY`).

### Quick Start

```python
from ErisPulse import sdk
from ErisPulse.Core.Event import command, message

@command("hello")
async def hello_handler(event):
    await event.reply("Hello from Telegram!")

async def main():
    await sdk.run(keep_running=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Sending Messages

All send methods are invoked via the chained DSL:

```python
telegram = sdk.adapter.get("telegram")

# Text message
await telegram.Send.To("user", "123456789").Text("Hello World!")

# Markdown / HTML formats
await telegram.Send.To("group", "-1001234567890").Markdown("*bold*")
await telegram.Send.To("user", "123456789").Html("<b>bold</b>")

# Media messages (supports URL, file_id, bytes)
await telegram.Send.To("user", "123456789").Image("https://example.com/photo.jpg")
await telegram.Send.To("user", "123456789").Image(image_bytes, caption="Image caption")

# Sticker
await telegram.Send.To("user", "123456789").Sticker("CAACAgIAAxkBAA...")

# Location
await telegram.Send.To("user", "123456789").Location(39.9042, 116.4074)
```

#### Chained Modifiers

```python
# @user (implemented via Telegram entities)
await telegram.Send.To("group", "-1001234567890").At("6117725680").Text("Hello!")

# Reply to message
await telegram.Send.To("group", "-1001234567890").Reply("12345").Text("Reply content")

# Inline keyboard
keyboard = [[{"text": "Button 1", "callback_data": "btn1"}]]
await telegram.Send.To("group", "-1001234567890").Keyboard(keyboard).Text("Please choose:")

# Protect content + silent send
await telegram.Send.To("group", "-1001234567890").ProtectContent().Silent().Text("Confidential message")
```

#### Message Operations

```python
# Edit message
await telegram.Send.To("user", "123456789").Edit(123, "New content")

# Recall message
await telegram.Send.To("user", "123456789").Recall(123)

# Forward message
await telegram.Send.To("user", "123456789").Forward(from_chat_id="-1001234567890", message_id=456)

# Copy message (without source)
await telegram.Send.To("user", "123456789").CopyMessage(from_chat_id="-1001234567890", message_id=456)

# Answer callback query
await telegram.Send.AnswerCallback("callback_query_id", text="Processed")
```

### Event Types

Telegram event conversion follows the OneBot12 standard, with platform extensions using the `telegram_` prefix.

#### Message Events

| Telegram Type | OB12 detail_type | Description |
|---------------|------------------|-------------|
| `message` / `edited_message` | `private` / `group` / `channel` | Private / group / channel message |
| `channel_post` / `edited_channel_post` | `channel` | Channel message |

#### Notice Events

| detail_type | Description |
|-------------|-------------|
| `telegram_callback_query` | Callback query (button click) |
| `telegram_poll` | Poll event |
| `telegram_poll_answer` | Poll answer |
| `telegram_my_chat_member` | Bot's own member status change |
| `telegram_chat_member` | Chat member change |

#### Request Events

| detail_type | Description |
|-------------|-------------|
| `telegram_inline_query` | Inline query |
| `telegram_chat_join_request` | Join chat request |
| `telegram_shipping_query` | Shipping query |
| `telegram_pre_checkout_query` | Pre-checkout query |

#### Message Segment Types

| Type | Description |
|------|-------------|
| `text` | Plain text |
| `mention` | @user (`user_id`, `user_name`) |
| `reply` | Reply reference |
| `image` | Image |
| `video` | Video |
| `voice` | Voice |
| `audio` | Audio |
| `file` | File |
| `location` | Location |
| `telegram_sticker` | Sticker (extension) |
| `telegram_animation` | GIF animation (extension) |
| `telegram_contact` | Contact (extension) |
| `telegram_inline_keyboard` | Inline keyboard (extension) |

### Event Mixin Methods

The adapter registers the following platform-specific methods (available when `platform == "telegram"`):

```python
from ErisPulse.Core.Event import message

@message.on_message()
async def handle(event):
    if event.get("platform") != "telegram":
        return

    # Message attributes
    event.is_bot_message()        # Whether from a bot
    event.is_edited_message()     # Whether an edited message
    event.is_topic_message()      # Whether a topic message

    # Chat info
    event.get_chat_title()        # Chat title
    event.get_chat_username()     # Chat username
    event.get_forward_from()      # Forward source
    event.get_topic_id()          # Topic ID

    # Callback query
    event.get_callback_data()     # callback_data
    event.get_callback_id()       # callback_query_id

    # Message segment data
    event.get_sticker_info()      # Sticker info
    event.get_contact_info()      # Contact info
    event.get_location()          # Location info
    event.get_inline_keyboard()   # Inline keyboard
```

### Run Mode

Only **Polling (long polling)** mode is supported. Each account polls independently, supporting parallel multi-Bot operation.

### Notes

- Media content supports three input methods: URL, file_id, and bytes
- HTML-format messages automatically sanitize unsupported tags
- All send methods return `asyncio.Task` objects; awaiting is optional
- Session type mapping: `private` → use `user` when sending, `group`/`supergroup` → `group`, `channel` → `channel`

### References

- [ErisPulse Main Repository](https://github.com/ErisPulse/ErisPulse/)
- [Telegram Bot API Official Documentation](https://core.telegram.org/bots/api)

---

<a id="中文"></a>

## 中文

基于 [ErisPulse](https://github.com/ErisPulse/ErisPulse/) 框架的 Telegram Bot API 适配器，支持多账号、多种消息类型收发和平台特有事件处理。

## 安装

```bash
epsdk install TelegramAdapter
```

## 配置

在 `config/config.toml` 中添加：

```toml
[Telegram_Adapter.accounts.default]
token = "YOUR_BOT_TOKEN"
enabled = true

# 多账号示例
[Telegram_Adapter.accounts.bot2]
token = "ANOTHER_BOT_TOKEN"
enabled = true
```

### 配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | 是 | Telegram Bot Token |
| `bot_id` | string | 否 | 自动从 Token 提取，无需手动填写 |
| `enabled` | bool | 否 | 是否启用（默认 true） |

### 旧版配置兼容

旧版单 token 格式仍可使用：

```toml
[Telegram_Adapter]
token = "YOUR_BOT_TOKEN"
```

建议迁移到新格式以支持多账号。

### 代理

如需通过代理连接 Telegram API，请设置系统级代理环境变量（如 `ALL_PROXY`、`HTTPS_PROXY`）。

## 快速开始

```python
from ErisPulse import sdk
from ErisPulse.Core.Event import command, message

@command("hello")
async def hello_handler(event):
    await event.reply("Hello from Telegram!")

async def main():
    await sdk.run(keep_running=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 消息发送

所有发送方法通过链式 DSL 调用：

```python
telegram = sdk.adapter.get("telegram")

# 文本消息
await telegram.Send.To("user", "123456789").Text("Hello World!")

# Markdown / HTML 格式
await telegram.Send.To("group", "-1001234567890").Markdown("*粗体*")
await telegram.Send.To("user", "123456789").Html("<b>粗体</b>")

# 媒体消息（支持 URL、file_id、bytes）
await telegram.Send.To("user", "123456789").Image("https://example.com/photo.jpg")
await telegram.Send.To("user", "123456789").Image(image_bytes, caption="图片说明")

# 贴纸
await telegram.Send.To("user", "123456789").Sticker("CAACAgIAAxkBAA...")

# 位置
await telegram.Send.To("user", "123456789").Location(39.9042, 116.4074)
```

### 链式修饰

```python
# @用户（通过 Telegram entities 实现）
await telegram.Send.To("group", "-1001234567890").At("6117725680").Text("你好！")

# 回复消息
await telegram.Send.To("group", "-1001234567890").Reply("12345").Text("回复内容")

# 内联键盘
keyboard = [[{"text": "按钮1", "callback_data": "btn1"}]]
await telegram.Send.To("group", "-1001234567890").Keyboard(keyboard).Text("请选择：")

# 保护内容 + 静默发送
await telegram.Send.To("group", "-1001234567890").ProtectContent().Silent().Text("机密消息")
```

### 消息操作

```python
# 编辑消息
await telegram.Send.To("user", "123456789").Edit(123, "新内容")

# 撤回消息
await telegram.Send.To("user", "123456789").Recall(123)

# 转发消息
await telegram.Send.To("user", "123456789").Forward(from_chat_id="-1001234567890", message_id=456)

# 复制消息（不带来源）
await telegram.Send.To("user", "123456789").CopyMessage(from_chat_id="-1001234567890", message_id=456)

# 应答回调查询
await telegram.Send.AnswerCallback("callback_query_id", text="已处理")
```

## 事件类型

Telegram 事件转换遵循 OneBot12 标准，平台扩展使用 `telegram_` 前缀。

### 消息事件

| Telegram 类型 | OB12 detail_type | 说明 |
|---|---|---|
| `message` / `edited_message` | `private` / `group` / `channel` | 私聊/群聊/频道消息 |
| `channel_post` / `edited_channel_post` | `channel` | 频道消息 |

### 通知事件

| detail_type | 说明 |
|---|---|
| `telegram_callback_query` | 回调查询（按钮点击） |
| `telegram_poll` | 投票事件 |
| `telegram_poll_answer` | 投票答案 |
| `telegram_my_chat_member` | Bot 自身成员状态变更 |
| `telegram_chat_member` | 聊天成员变更 |

### 请求事件

| detail_type | 说明 |
|---|---|
| `telegram_inline_query` | 内联查询 |
| `telegram_chat_join_request` | 加入聊天请求 |
| `telegram_shipping_query` | 运费查询 |
| `telegram_pre_checkout_query` | 预付款查询 |

### 消息段类型

| 类型 | 说明 |
|---|---|
| `text` | 纯文本 |
| `mention` | @用户（`user_id`, `user_name`） |
| `reply` | 回复引用 |
| `image` | 图片 |
| `video` | 视频 |
| `voice` | 语音 |
| `audio` | 音频 |
| `file` | 文件 |
| `location` | 位置 |
| `telegram_sticker` | 贴纸（扩展） |
| `telegram_animation` | GIF 动画（扩展） |
| `telegram_contact` | 联系人（扩展） |
| `telegram_inline_keyboard` | 内联键盘（扩展） |

## Event Mixin 方法

适配器注册了以下平台专有方法（`platform == "telegram"` 时可用）：

```python
from ErisPulse.Core.Event import message

@message.on_message()
async def handle(event):
    if event.get("platform") != "telegram":
        return

    # 消息属性
    event.is_bot_message()        # 是否来自机器人
    event.is_edited_message()     # 是否编辑过的消息
    event.is_topic_message()      # 是否话题消息

    # 聊天信息
    event.get_chat_title()        # 聊天标题
    event.get_chat_username()     # 聊天用户名
    event.get_forward_from()      # 转发来源
    event.get_topic_id()          # 话题 ID

    # 回调查询
    event.get_callback_data()     # callback_data
    event.get_callback_id()       # callback_query_id

    # 消息段数据
    event.get_sticker_info()      # 贴纸信息
    event.get_contact_info()      # 联系人信息
    event.get_location()          # 位置信息
    event.get_inline_keyboard()   # 内联键盘
```

## 运行模式

仅支持 **Polling（长轮询）** 模式。每个账号独立轮询，支持多 Bot 并行运行。

## 注意事项

- 媒体内容支持 URL、file_id、bytes 三种输入方式
- HTML 格式消息会自动清洗不支持的标签
- 所有发送方法返回 `asyncio.Task` 对象，可选择是否 `await`
- 会话类型映射：`private` → 发送时用 `user`，`group`/`supergroup` → `group`，`channel` → `channel`

## 参考链接

- [ErisPulse 主库](https://github.com/ErisPulse/ErisPulse/)
- [Telegram Bot API 官方文档](https://core.telegram.org/bots/api)
