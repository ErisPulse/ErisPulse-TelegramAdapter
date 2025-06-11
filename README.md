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

    # 获取适配器实例
    telegram = sdk.adapter.telegram

    # 注册事件处理器
    @telegram.on("message")
    async def handle_message(data):
        print(f"收到消息: {data}")
        await telegram.Send.To("user", data["message"]["from"]["id"]).Text("已收到您的消息！")

    @telegram.on("callback_query")
    async def handle_callback_query(data):
        print(f"收到回调查询: {data}")
        await telegram.answer_callback_query(data["id"], "处理完成")

    # 启动适配器
    await sdk.adapter.startup()

    # 保持程序运行
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 消息发送示例
```python
# 发送文本消息
await telegram.Send.To("user", "123456789").Text("Hello World!")

# 发送图片（需先读取为 bytes）
with open("image.jpg", "rb") as f:
    await telegram.Send.To("user", "123456789").Image(f.read())

# 发送视频
with open("video.mp4", "rb") as f:
    await telegram.Send.To("group", "987654321").Video(f.read())

# 发送文件
with open("document.docx", "rb") as f:
    await telegram.Send.To("user", "123456789").Document(f.read())
```

## 配置说明
在 `env.py` 中进行如下配置：

```python
sdk.env.set("TelegramAdapter", {
    "token": "your_bot_token",
    "mode": "webhook",  # 或 "polling"
    "server": {
        "host": "127.0.0.1",  # Webhook 监听地址
        "port": 8443,         # Webhook 监听端口
        "path": "/telegram/webhook"  # Webhook 路径
    },
    "webhook": {
        "host": "yourdomain.com",  # 外部可访问域名
        "port": 443,               # 对外 HTTPS 端口
        "path": "/telegram/webhook"  # 必须与 server.path 一致
    },
    "proxy": {
        "host": "127.0.0.1",      # 可选：代理服务器地址
        "port": 1080,             # 可选：代理端口
        "type": "socks5"          # 支持 socks4/socks5
    }
})
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

## 链式发送方法

TelegramAdapter 提供链式语法用于清晰地发送各类消息：

### 文本消息
```python
await telegram.Send.To("user", user_id).Text("这是一条文本消息", parse_mode="markdown")
```

### 图片消息
```python
with open("image.jpg", "rb") as f:
    await telegram.Send.To("user", user_id).Image(f.read(), caption="图片描述", parse_mode="markdown")
```

### 视频消息
```python
with open("video.mp4", "rb") as f:
    await telegram.Send.To("group", group_id).Video(f.read(), caption="这是个视频", parse_mode="markdown")
```

### 文件消息
```python
with open("document.pdf", "rb") as f:
    await telegram.Send.To("user", user_id).Document(f.read(), caption="附件文件", parse_mode="markdown")
```

### 编辑消息
```python
await telegram.Send.To("user", user_id).EditMessageText(message_id, "这是修改后的消息", parse_mode="markdown")
```

### 删除消息
```python
await telegram.Send.To("user", user_id).DeleteMessage(message_id)
```

### 获取聊天信息
```python
chat_info = await telegram.Send.To("user", user_id).GetChat()
print(chat_info)
```

## Webhook 设置

如果你使用 Webhook 模式，请确保配置中包含以下字段：

```python
"webhook": {
    "host": "yourdomain.com",
    "port": 443,
    "path": "/telegram/webhook"
}
```

你可以选择性配置证书内容或路径：
- `"cert_content"`: PEM 格式的证书字符串；
- `"cert_path"`: 本地证书文件路径；

如果不使用 Telegram 的证书验证，可通过反向代理（如 Nginx/Caddy）处理 HTTPS。

## 代理设置（可选）

如果需要通过代理连接 Telegram API，可在配置中添加：

```python
"proxy": {
    "host": "127.0.0.1",
    "port": 1080,
    "type": "socks5"
}
```

目前支持 `socks5` 和 `socks4` 类型的代理。

## 注意事项
- 二进制内容（如图片、视频等）应以 `bytes` 形式传入；
- 推荐使用反向代理处理 HTTPS 请求，避免手动管理 SSL 证书。

---

## 参考链接

- [ErisPulse 主库](https://github.com/ErisPulse/ErisPulse/)
- [Telegram Bot API 官方文档](https://core.telegram.org/bots/api)
- [ErisPulse 模块开发指南](https://github.com/ErisPulse/ErisPulse/tree/main/docs/DEVELOPMENT.md)