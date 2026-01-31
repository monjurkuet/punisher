import pytest
import os
from punisher.bus.queue import MessageQueue


def test_queue_push_pop(tmp_path):
    db_path = tmp_path / "test_queue.db"
    q = MessageQueue(str(db_path))

    q.push("test_channel", "hello world")

    msg = q.pop("test_channel", timeout=1)
    assert msg == "hello world"

    msg_empty = q.pop("test_channel", timeout=1)
    assert msg_empty is None


def test_queue_json(tmp_path):
    db_path = tmp_path / "test_queue_json.db"
    q = MessageQueue(str(db_path))

    payload = {"foo": "bar"}
    q.push("json_channel", payload)

    # Pop returns string, need to parse if we want dict
    msg = q.pop("json_channel", timeout=1)
    assert '"foo": "bar"' in msg
