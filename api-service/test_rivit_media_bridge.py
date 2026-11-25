"""Offline tests for the Rivit media bridge.

No Twilio account, no OpenAI call, no network, no real audio and no database. The
Twilio side is driven over a real Starlette WebSocket through TestClient; the
Realtime side is a scripted fake, so every frame the bridge emits and every field
it stores can be asserted exactly. Audio payloads here are opaque base64 strings:
the bridge must never decode them, so their content is irrelevant.
"""
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rivit_media_bridge import (  # noqa: E402
    DEFAULT_MAX_CALL_SECONDS,
    INTAKE_TOOL,
    BridgeSession,
    build_instructions,
    create_voice_stream_router,
    max_call_seconds,
    parse_intake_call,
    session_update,
)
from twilio_voice import stream_token  # noqa: E402

from test_twilio_voice import FakeDb  # noqa: E402

BRIDGE_KEY = "test-bridge-key-not-real-1111"
CALL_SID = "CA00000000000000000000000000000042"
STREAM_SID = "MZ00000000000000000000000000000042"
OPENAI_KEY = "sk-test-not-real-0000"
GREETING = "Hi, I'm Rivit. You've reached Griffin Muffler & Brake Center. How can I help you today?"
TENANTS = {
    "+15555550100": {
        "tenant_id": "griffin-muffler",
        "shop_name": "Griffin Muffler & Brake Center",
        "greeting": GREETING,
        "operator_emails": ["owner@griffin.example"],
        "recording": "disclosure",
    },
}
ENV = {
    "WRENCHRELAY_VOICE_LIVE_APPROVED": "true",
    "WRENCHRELAY_VOICE_BRIDGE_KEY": BRIDGE_KEY,
    "WRENCHRELAY_VOICE_TENANTS": json.dumps(TENANTS),
    "OPENAI_API_KEY": OPENAI_KEY,
    "WRENCHRELAY_VOICE_MODEL": "",
    "WRENCHRELAY_VOICE_NAME": "",
}

START = {
    "event": "start",
    "start": {
        "streamSid": STREAM_SID,
        "callSid": CALL_SID,
        "customParameters": {
            "tenant_id": "griffin-muffler",
            "shop_name": "Griffin Muffler & Brake Center",
            "call_sid": CALL_SID,
            "recording": "disclosure",
        },
    },
}
TOOL_CALL = {
    "type": "response.function_call_arguments.done",
    "call_id": "call_abc123",
    "name": "record_intake",
    "arguments": json.dumps({
        "caller_name": "Test Caller",
        "callback_number": "+15555550123",
        "vehicle_year": "2016",
        "vehicle_make": "Honda",
        "vehicle_model": "Accord",
        "service_request": "Grinding noise when braking",
    }),
}


class FakeRealtime:
    """Scripted Realtime socket: replays events, records what the bridge sends."""

    def __init__(self, script=()):
        self.script = list(script)
        self.sent = []
        self.urls = []
        self.closed = False

    async def send(self, message):
        self.sent.append(json.loads(message))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.script:
            return json.dumps(self.script.pop(0))
        # Hold the pump open until the route cancels it.
        await __import__("asyncio").Event().wait()
        raise StopAsyncIteration

    async def close(self):
        self.closed = True


def build(script=(), env=None, db=None):
    app = FastAPI()
    fake = FakeRealtime(script)
    database = db or FakeDb()

    async def connect(url, api_key):
        fake.urls.append((url, api_key))
        return fake

    app.include_router(create_voice_stream_router(lambda: database, connect))
    return app, fake, database


def stream_url(token=None, call_sid=CALL_SID):
    token = stream_token(call_sid) if token is None else token
    return f"/api/voice/stream?call_sid={call_sid}&token={token}"


class RefusalTests(unittest.TestCase):
    def assertRefused(self, app, url, expected_code=1008):
        with TestClient(app) as client:
            with self.assertRaises(WebSocketDisconnect) as caught:
                with client.websocket_connect(url) as websocket:
                    websocket.receive_json()
        self.assertEqual(caught.exception.code, expected_code)

    def test_stream_refused_when_live_audio_is_not_approved(self):
        env = dict(ENV, WRENCHRELAY_VOICE_LIVE_APPROVED="false")
        app, fake, _ = build()
        with patch.dict(os.environ, env):
            self.assertRefused(app, stream_url())
        self.assertEqual(fake.urls, [], "no upstream connection is opened when refused")

    def test_stream_refused_without_bridge_key(self):
        env = dict(ENV, WRENCHRELAY_VOICE_BRIDGE_KEY="")
        app, _, _ = build()
        with patch.dict(os.environ, env):
            self.assertRefused(app, stream_url(token="forged"))

    def test_stream_refused_with_forged_token(self):
        app, fake, _ = build()
        with patch.dict(os.environ, ENV):
            self.assertRefused(app, stream_url(token="not-the-call-token"))
        self.assertEqual(fake.urls, [])

    def test_stream_refused_without_openai_credential(self):
        env = dict(ENV, OPENAI_API_KEY="")
        app, _, _ = build()
        with patch.dict(os.environ, env):
            self.assertRefused(app, stream_url())

    def test_stream_refused_for_unmapped_tenant(self):
        app, fake, _ = build()
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with self.assertRaises(WebSocketDisconnect) as caught:
                    with client.websocket_connect(stream_url()) as websocket:
                        websocket.send_json({
                            "event": "start",
                            "start": {"streamSid": STREAM_SID, "callSid": CALL_SID,
                                      "customParameters": {"tenant_id": "some-other-shop",
                                                           "call_sid": CALL_SID}},
                        })
                        websocket.receive_json()
        self.assertEqual(caught.exception.code, 1008)
        self.assertEqual(fake.urls, [])

    def test_stream_refused_when_call_identity_does_not_match(self):
        app, fake, _ = build()
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with self.assertRaises(WebSocketDisconnect):
                    with client.websocket_connect(stream_url()) as websocket:
                        websocket.send_json({
                            "event": "start",
                            "start": {"streamSid": STREAM_SID, "callSid": "CA-other",
                                      "customParameters": {"tenant_id": "griffin-muffler",
                                                           "call_sid": "CA-other"}},
                        })
                        websocket.receive_json()
        self.assertEqual(fake.urls, [])


class SessionConfigTests(unittest.TestCase):
    def test_session_configures_telephony_audio_and_grounded_instructions(self):
        config = session_update(TENANTS["+15555550100"])
        session = config["session"]
        self.assertEqual(config["type"], "session.update")
        self.assertEqual(session["audio"]["input"]["format"], {"type": "audio/pcmu"})
        self.assertEqual(session["audio"]["output"]["format"], {"type": "audio/pcmu"})
        self.assertEqual(session["audio"]["input"]["turn_detection"]["type"], "server_vad")
        self.assertEqual(session["output_modalities"], ["audio"])
        self.assertEqual([tool["name"] for tool in session["tools"]], ["record_intake"])
        self.assertLessEqual(session["max_output_tokens"], 400)
        instructions = session["instructions"]
        self.assertIn("Griffin Muffler & Brake Center", instructions)
        self.assertIn("one question at a time", instructions)
        self.assertIn("record_intake", instructions)
        # Grounding: no shop fact the configuration does not hold, no operator PII.
        for forbidden in ("$", "open until", "in stock", "appointment is confirmed", "owner@griffin.example"):
            self.assertNotIn(forbidden, instructions)

    def test_tool_schema_matches_the_intake_allow_list(self):
        properties = set(INTAKE_TOOL["parameters"]["properties"])
        self.assertIn("service_request", INTAKE_TOOL["parameters"]["required"])
        self.assertFalse({"price", "quote", "hours", "availability", "appointment"} & properties)
        self.assertTrue(INTAKE_TOOL["parameters"]["additionalProperties"] is False)

    def test_audio_is_relayed_in_both_directions_without_touching_payloads(self):
        session = BridgeSession(STREAM_SID)
        self.assertEqual(
            session.from_twilio({"event": "media", "media": {"track": "inbound", "payload": "AAECAwQ="}}),
            [{"type": "input_audio_buffer.append", "audio": "AAECAwQ="}],
        )
        self.assertEqual(session.from_twilio({"event": "media", "media": {"track": "outbound", "payload": "x"}}), [])
        self.assertEqual(
            session.from_realtime({"type": "response.output_audio.delta", "delta": "BQYHCA=="}),
            [{"event": "media", "streamSid": STREAM_SID, "media": {"payload": "BQYHCA=="}}],
        )
        self.assertEqual(
            session.from_realtime({"type": "input_audio_buffer.speech_started"}),
            [{"event": "clear", "streamSid": STREAM_SID}],
        )
        self.assertEqual(session.from_realtime({"type": "response.done"}), [])

    def test_malformed_or_unsupported_frames_are_ignored(self):
        session = BridgeSession(STREAM_SID)
        for event in ({}, {"event": "media"}, {"event": "mark"}, {"event": "media", "media": {"track": "inbound"}},
                      {"type": "session.updated"}, {"type": None}):
            self.assertEqual(session.from_twilio(event), [])
            self.assertEqual(session.from_realtime(event), [])

    def test_instructions_never_include_a_second_tenant(self):
        text = build_instructions(TENANTS["+15555550100"])
        self.assertNotIn("Second Shop", text)


class ToolCallTests(unittest.TestCase):
    def test_valid_tool_call_is_parsed_into_allowed_fields(self):
        call_id, fields, reason = parse_intake_call(TOOL_CALL)
        self.assertIsNone(reason)
        self.assertEqual(call_id, "call_abc123")
        self.assertEqual(fields["vehicle_model"], "Accord")

    def test_invented_shop_fact_is_refused_before_storage(self):
        event = dict(TOOL_CALL, arguments=json.dumps({"service_request": "brake noise", "price": "$149"}))
        _, fields, reason = parse_intake_call(event)
        self.assertIsNone(fields)
        self.assertIn("shop facts", reason)

    def test_malformed_tool_arguments_are_refused(self):
        for arguments in ("not json", "[]", "{}"):
            _, fields, reason = parse_intake_call(dict(TOOL_CALL, arguments=arguments))
            self.assertIsNone(fields)
            self.assertTrue(reason)

    def test_unknown_tool_is_refused(self):
        _, fields, reason = parse_intake_call(dict(TOOL_CALL, name="dial_a_human"))
        self.assertIsNone(fields)
        self.assertEqual(reason, "unknown_tool")


class StreamFlowTests(unittest.TestCase):
    def test_media_and_interruption_reach_both_sides(self):
        script = [
            {"type": "response.output_audio.delta", "delta": "BQYHCA=="},
            {"type": "input_audio_buffer.speech_started"},
        ]
        app, fake, _ = build(script)
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_json({"event": "connected"})
                    websocket.send_json(START)
                    websocket.send_json({"event": "media", "media": {"track": "inbound", "payload": "AAECAwQ="}})
                    self.assertEqual(websocket.receive_json()["media"]["payload"], "BQYHCA==")
                    self.assertEqual(websocket.receive_json(), {"event": "clear", "streamSid": STREAM_SID})
                    websocket.send_json({"event": "stop"})
        self.assertEqual(fake.sent[0]["type"], "session.update")
        self.assertEqual(fake.sent[1], {"type": "input_audio_buffer.append", "audio": "AAECAwQ="})
        self.assertEqual(fake.urls[0][0], "wss://api.openai.com/v1/realtime?model=gpt-realtime")
        self.assertEqual(fake.urls[0][1], OPENAI_KEY)
        self.assertTrue(fake.closed)

    def test_tool_call_stores_only_what_the_caller_supplied(self):
        app, fake, db = build([TOOL_CALL])
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_json(START)
                    websocket.send_json({"event": "stop"})
        intakes = db.voice_intakes.docs
        self.assertEqual(len(intakes), 1)
        self.assertEqual(intakes[0]["tenant_id"], "griffin-muffler")
        self.assertEqual(intakes[0]["call_sid"], CALL_SID)
        self.assertEqual(intakes[0]["fields"]["vehicle_model"], "Accord")
        self.assertEqual(intakes[0]["status"], "complete")
        outputs = [frame for frame in fake.sent if frame["type"] == "conversation.item.create"]
        self.assertEqual(len(outputs), 1)
        self.assertEqual(json.loads(outputs[0]["item"]["output"]), {"recorded": True})
        self.assertIn({"type": "response.create"}, fake.sent)

    def test_refused_tool_call_stores_nothing_and_tells_the_model(self):
        event = dict(TOOL_CALL, arguments=json.dumps({"service_request": "brake noise", "quote": "$99"}))
        app, fake, db = build([event])
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_json(START)
                    websocket.send_json({"event": "stop"})
        self.assertEqual(db.voice_intakes.docs, [])
        output = [frame for frame in fake.sent if frame["type"] == "conversation.item.create"][0]
        self.assertFalse(json.loads(output["item"]["output"])["recorded"])

    def test_stop_ends_the_stream_and_records_call_state(self):
        app, fake, db = build()
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_json(START)
                    websocket.send_json({"event": "stop"})
        record = db.voice_calls.find_one({"call_sid": CALL_SID})
        self.assertEqual(record["media_stream"], "ended")
        self.assertEqual(record["tenant_id"], "griffin-muffler")
        self.assertTrue(fake.closed)

    def test_streams_oversized_junk_do_not_crash_the_bridge(self):
        app, fake, db = build()
        with patch.dict(os.environ, ENV):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_text("not json at all")
                    websocket.send_json({"event": "media", "media": {"track": "inbound", "payload": ""}})
                    websocket.send_json(START)
                    websocket.send_json({"event": "stop"})
        self.assertEqual([frame for frame in fake.sent if frame["type"] == "input_audio_buffer.append"], [])
        self.assertEqual(db.voice_calls.find_one({"call_sid": CALL_SID})["media_stream"], "ended")


class CallLimitTests(unittest.TestCase):
    def test_call_limit_falls_back_to_the_default_for_junk(self):
        for value in ("", "abc", "0", "-5", "nan", "inf"):
            with patch.dict(os.environ, {"WRENCHRELAY_VOICE_MAX_CALL_SECONDS": value}):
                self.assertEqual(max_call_seconds(), float(DEFAULT_MAX_CALL_SECONDS))
        with patch.dict(os.environ, {"WRENCHRELAY_VOICE_MAX_CALL_SECONDS": "90"}):
            self.assertEqual(max_call_seconds(), 90.0)

    def test_stream_is_cut_off_when_the_call_limit_elapses(self):
        app, fake, db = build()
        env = dict(ENV, WRENCHRELAY_VOICE_MAX_CALL_SECONDS="0.2")
        with patch.dict(os.environ, env):
            with TestClient(app) as client:
                with client.websocket_connect(stream_url()) as websocket:
                    websocket.send_json(START)
                    codes = []

                    def read_until_closed():
                        try:
                            websocket.receive_json()
                        except WebSocketDisconnect as exc:
                            codes.append(exc.code)

                    reader = threading.Thread(target=read_until_closed, daemon=True)
                    reader.start()
                    reader.join(10)
                    self.assertFalse(reader.is_alive(), "the bridge left the stream open past its call limit")
                    self.assertEqual(codes, [1000])
        self.assertEqual(db.voice_calls.find_one({"call_sid": CALL_SID})["media_stream"], "max_duration")
        self.assertTrue(fake.closed)
        self.assertEqual(fake.sent[0]["type"], "session.update")


class TokenTests(unittest.TestCase):
    def test_token_is_per_call_deterministic_and_absent_without_a_key(self):
        with patch.dict(os.environ, ENV):
            first = stream_token(CALL_SID)
            self.assertEqual(first, stream_token(CALL_SID))
            self.assertNotEqual(first, stream_token("CA-different-call"))
            self.assertGreaterEqual(len(first), 32)
            self.assertNotIn(BRIDGE_KEY, first)
        with patch.dict(os.environ, dict(ENV, WRENCHRELAY_VOICE_BRIDGE_KEY="")):
            self.assertEqual(stream_token(CALL_SID), "")


if __name__ == "__main__":
    unittest.main()
