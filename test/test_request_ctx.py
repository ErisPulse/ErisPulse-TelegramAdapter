"""
请求处理测试：chat_join_request 转换 / 上下文留存（写入、过期、成功清理）/
查询类事件类型修正（inline_query 等归 notice）

桩化 HTTP：monkeypatch 替换 ``adapter.call_api``，不发起真实网络请求。
"""

import asyncio
import time
from types import SimpleNamespace

from ErisPulse.Core import logger as global_logger

from TelegramAdapter.Converter import TelegramConverter
from TelegramAdapter.Core import TelegramAdapter, REQUEST_CTX_TTL

TOKEN = "12345:testtoken"

CHAT_JOIN_UPDATE = {
    "update_id": 1,
    "chat_join_request": {
        "chat": {"id": -100123, "type": "supergroup", "title": "G"},
        "from": {"id": 7, "first_name": "U"},
        "date": 1700000000,
        "user_chat_id": 7,
    },
}

INLINE_QUERY_UPDATE = {
    "update_id": 2,
    "inline_query": {"id": "q1", "from": {"id": 42, "first_name": "T"}, "query": "hi", "offset": ""},
}


def make_adapter():
    sdk_stub = SimpleNamespace(
        logger=SimpleNamespace(get_child=lambda name, relative=False: global_logger),
    )
    adapter = TelegramAdapter(sdk_ref=sdk_stub)

    calls = []

    async def fake_call_api(endpoint, _account_id=None, **params):
        calls.append((endpoint, params))
        return {"status": "ok", "retcode": 0, "data": True, "message_id": "", "message": ""}

    adapter.call_api = fake_call_api
    return adapter, calls


def test_chat_join_request_conversion():
    converter = TelegramConverter(TOKEN)
    event = converter.convert(CHAT_JOIN_UPDATE)
    assert event["type"] == "request"
    # 标准请求事件 detail_type 必须为 "group"，命中 request.on_group_request 过滤
    assert event["detail_type"] == "group"
    assert event["request_id"] == "tjr_-100123_7_1700000000"
    assert event["user_id"] == "7"
    assert event["group_id"] == "-100123"


def test_query_events_are_notice():
    """inline_query / shipping_query / pre_checkout_query 是查询交互，归 notice 非 request"""
    converter = TelegramConverter(TOKEN)

    event = converter.convert(INLINE_QUERY_UPDATE)
    assert event["type"] == "notice"
    assert event["detail_type"] == "telegram_inline_query"
    assert event["telegram_query_id"] == "q1"

    shipping = converter.convert(
        {"update_id": 3, "shipping_query": {"id": "s1", "from": {"id": 42}, "invoice_payload": "p"}}
    )
    assert shipping["type"] == "notice"
    assert shipping["detail_type"] == "telegram_shipping_query"

    checkout = converter.convert(
        {"update_id": 4, "pre_checkout_query": {"id": "c1", "from": {"id": 42}, "currency": "USD"}}
    )
    assert checkout["type"] == "notice"
    assert checkout["detail_type"] == "telegram_pre_checkout_query"


def test_register_request_writes_context_with_ts():
    adapter, _ = make_adapter()
    converter = TelegramConverter(TOKEN)
    event = converter.convert(CHAT_JOIN_UPDATE)

    adapter._register_request(event, "default")
    entry = adapter._pending_requests["tjr_-100123_7_1700000000"]
    assert entry["chat_id"] == "-100123"
    assert entry["user_id"] == "7"
    assert entry["account_name"] == "default"
    assert 0 <= time.time() - entry["ts"] < 5


def test_expired_context_returns_34001():
    adapter, calls = make_adapter()
    rid = "tjr_-100123_7_1700000000"
    adapter._pending_requests[rid] = {
        "chat_id": "-100123",
        "user_id": "7",
        "account_name": "default",
        "ts": time.time() - REQUEST_CTX_TTL - 1,
    }
    result = asyncio.run(adapter._handle_chat_join_request(rid, True))
    assert result["retcode"] == 34001
    assert result["status"] == "failed"
    # 过期视同未留存：读后即删，且不得发起审批请求
    assert rid not in adapter._pending_requests
    assert calls == []


def test_success_clears_entry():
    adapter, calls = make_adapter()
    converter = TelegramConverter(TOKEN)
    event = converter.convert(CHAT_JOIN_UPDATE)
    rid = event["request_id"]
    adapter._register_request(event, "default")

    result = asyncio.run(adapter._handle_chat_join_request(rid, True))
    assert result["status"] == "ok"
    assert rid not in adapter._pending_requests
    endpoint, params = calls[0]
    assert endpoint == "approveChatJoinRequest"
    assert params["chat_id"] == -100123
    assert params["user_id"] == 7

    # 拒绝路径同样清理
    adapter._register_request(event, "default")
    result = asyncio.run(adapter._handle_chat_join_request(rid, False))
    assert result["status"] == "ok"
    assert rid not in adapter._pending_requests
    assert calls[1][0] == "declineChatJoinRequest"
