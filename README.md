# Telegram 适配器模块

## 简介
TelegramAdapter 是基于 [ErisPulse](https://github.com/ErisPulse/ErisPulse/) 架构的 Telegram 协议适配器，提供统一的事件处理和消息操作接口。整合了所有 Telegram 功能模块，支持文本、图片、视频、文件等多种类型消息的收发。

## 使用示例

### 初始化与事件处理
```python
from ErisPulse import sdk

async def main():
    # 初始化 SDK
    sdk.init()
    
    # 启动适配器
    await sdk.adapter.startup()
    
    # 获取适配器实例
    telegram = sdk.adapter.get("telegram")
    
    # 注册事件处理器
    @telegram.on("message")
    async def handle_message(data):
        print(f"收到消息: {data}")
        await telegram.Send.To("user", data["message"]["from"]["id"]).Text("已收到您的消息！")

    @telegram.on("callback_query")
    async def handle_callback_query(data):
        print(f"收到回调查询: {data}")
        await telegram.answer_callback_query(data["id"], "处理完成")

    # 保持程序运行
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 消息发送示例
```python
# 发送纯文本消息
await telegram.Send.To("user", "123456789").Text("Hello World!")

# 发送Markdown格式消息
await telegram.Send.To("user", "123456789").Markdown("*粗体文本*")

# 发送HTML格式消息
await telegram.Send.To("user", "123456789").Html("<b>粗体文本</b>")

# 发送图片（需先读取为 bytes）
with open("image.jpg", "rb") as f:
    await telegram.Send.To("user", "123456789").Image(f.read(), caption="图片描述")

# 发送带格式说明的图片
with open("image.jpg", "rb") as f:
    await telegram.Send.To("user", "123456789").Image(f.read(), caption="*图片说明*", content_type="Markdown")

# 发送视频
with open("video.mp4", "rb") as f:
    await telegram.Send.To("group", "987654321").Video(f.read(), caption="这是个视频")

# 发送文件
with open("document.docx", "rb") as f:
    await telegram.Send.To("user", "123456789").Document(f.read(), caption="附件文件")

# 编辑消息
await telegram.Send.To("user", "123456789").Edit(123456, "修改后的内容")

# 撤回消息
await telegram.Send.To("user", "123456789").Recall(123456)

# 检查消息是否存在
exists = await telegram.Send.To("user", "123456789").CheckExist(123456)
```

## 配置说明

首次运行会生成配置，内容及解释如下：

```toml
# config.toml
[Telegram_Adapter]
token = "your_bot_token"
proxy_enabled = false
mode = "webhook"  # 或 "polling"

[Telegram_Adapter.proxy]
host = "127.0.0.1"
port = 1080
type = "socks5"  # 支持 socks4/socks5

[Telegram_Adapter.webhook]
path = "/telegram/webhook"
domain = "yourdomain.com"  # 外部可访问域名
```

## 事件类型
TelegramAdapter 支持以下事件类型的监听与处理：

| 事件类型                     | 映射名称       | 说明                  |
|------------------------------|----------------|-----------------------|
| `message`                    | `message`      | 普通消息              |
| `edited_message`             | `message_edit` | 消息被编辑            |
| `channel_post`               | `channel_post` | 频道发布消息           |
| `edited_channel_post`        | `channel_post_edit` | 频道消息被编辑     |
| `inline_query`               | `inline_query` | 内联查询              |
| `chosen_inline_result`       | `chosen_inline_result` | 内联结果被选择   |
| `callback_query`             | `callback_query` | 回调查询（按钮点击） |
| `shipping_query`             | `shipping_query` | 配送信息查询         |
| `pre_checkout_query`         | `pre_checkout_query` | 支付预检查询       |
| `poll`                       | `poll`         | 投票创建              |
| `poll_answer`                | `poll_answer`  | 投票响应              |

## 通讯模式
TelegramAdapter 支持两种通讯模式：
- **Webhook**：使用 Telegram API 的 Webhook 机制，将消息推送到指定 URL。
- **Polling**：使用 Telegram API 的 Polling 模式，通过轮询方式获取消息。

> 如果你使用 Webhook 模式，请确保配置中包含以下字段：
>   ```toml
>   [Telegram_Adapter.webhook]
>   path = "/telegram/webhook"
>   domain = "yourdomain.com"
>   ```

> 如果你使用 Polling 模式，只需要填写 token 字段即可


你可以选择性配置证书内容或路径：
- 通过反向代理（如 Nginx/Caddy）处理 HTTPS

## 代理设置（可选）

如果需要通过代理连接 Telegram API，可在配置中添加：

```toml
[Telegram_Adapter]
proxy_enabled = true

[Telegram_Adapter.proxy]
host = "127.0.0.1"
port = 1080
type = "socks5"  # 支持 socks4/socks5
```

## 注意事项
- 二进制内容（如图片、视频等）应以 `bytes` 形式传入；
- 推荐使用反向代理处理 HTTPS 请求，避免手动管理 SSL 证书；
- 所有格式化消息方法支持 `content_type` 参数，可选 "Markdown" 或 "HTML"；
- 所有发送方法返回 `asyncio.Task` 对象，可以选择是否等待结果。

---

## 参考链接

- [ErisPulse 主库](https://github.com/ErisPulse/ErisPulse/)
- [Telegram Bot API 官方文档](https://core.telegram.org/bots/api)
- [ErisPulse 模块开发指南](https://github.com/ErisPulse/ErisPulse/tree/main/docs/DEVELOPMENT.md)
