# type: ignore
from typing import Any
from unittest import mock

import pytest

from aiohttp import streams


@pytest.fixture
def protocol():
    return mock.Mock(_reading_paused=False)


@pytest.fixture
def stream(loop: Any, protocol: Any):
    out = streams.StreamReader(protocol, limit=1, loop=loop)
    out._allow_pause = True
    return out


@pytest.fixture
def buffer(loop: Any, protocol: Any):
    out = streams.FlowControlDataQueue(protocol, limit=1, loop=loop)
    out._allow_pause = True
    return out


class TestFlowControlStreamReader:
    async def test_read(self, stream: Any) -> None:
        stream.feed_data(b"da")
        res = await stream.read(1)
        assert res == b"d"
        assert not stream._protocol.resume_reading.called

    async def test_read_resume_paused(self, stream: Any) -> None:
        stream.feed_data(b"test")
        stream._protocol._reading_paused = True

        res = await stream.read(1)
        assert res == b"t"
        assert stream._protocol.pause_reading.called

    async def test_readline(self, stream: Any) -> None:
        stream.feed_data(b"d\n")
        res = await stream.readline()
        assert res == b"d\n"
        assert not stream._protocol.resume_reading.called

    async def test_readline_resume_paused(self, stream: Any) -> None:
        stream._protocol._reading_paused = True
        stream.feed_data(b"d\n")
        res = await stream.readline()
        assert res == b"d\n"
        assert stream._protocol.resume_reading.called

    async def test_readany(self, stream: Any) -> None:
        stream.feed_data(b"data")
        res = await stream.readany()
        assert res == b"data"
        assert not stream._protocol.resume_reading.called

    async def test_readany_resume_paused(self, stream: Any) -> None:
        stream._protocol._reading_paused = True
        stream.feed_data(b"data")
        res = await stream.readany()
        assert res == b"data"
        assert stream._protocol.resume_reading.called

    async def test_readchunk(self, stream: Any) -> None:
        stream.feed_data(b"data")
        res, end_of_http_chunk = await stream.readchunk()
        assert res == b"data"
        assert not end_of_http_chunk
        assert not stream._protocol.resume_reading.called

    async def test_readchunk_resume_paused(self, stream: Any) -> None:
        stream._protocol._reading_paused = True
        stream.feed_data(b"data")
        res, end_of_http_chunk = await stream.readchunk()
        assert res == b"data"
        assert not end_of_http_chunk
        assert stream._protocol.resume_reading.called

    async def test_readexactly(self, stream: Any) -> None:
        stream.feed_data(b"data")
        res = await stream.readexactly(3)
        assert res == b"dat"
        assert not stream._protocol.resume_reading.called

    async def test_feed_data(self, stream: Any) -> None:
        stream._protocol._reading_paused = False
        stream.feed_data(b"datadata")
        assert stream._protocol.pause_reading.called

    async def test_read_nowait(self, stream: Any) -> None:
        stream._protocol._reading_paused = True
        stream.feed_data(b"data1")
        stream.feed_data(b"data2")
        stream.feed_data(b"data3")
        res = await stream.read(5)
        assert res == b"data1"
        assert stream._protocol.resume_reading.call_count == 0

        res = stream.read_nowait(5)
        assert res == b"data2"
        assert stream._protocol.resume_reading.call_count == 0

        res = stream.read_nowait(5)
        assert res == b"data3"
        assert stream._protocol.resume_reading.call_count == 1

        stream._protocol._reading_paused = False
        res = stream.read_nowait(5)
        assert res == b""
        assert stream._protocol.resume_reading.call_count == 1


class TestFlowControlDataQueue:
    def test_feed_pause(self, buffer: Any) -> None:
        buffer._protocol._reading_paused = False
        buffer.feed_data("x" * 100)

        assert buffer._protocol.pause_reading.called

    async def test_resume_on_read(self, buffer: Any) -> None:
        buffer.feed_data("x" * 100)

        buffer._protocol._reading_paused = True
        await buffer.read()
        assert buffer._protocol.resume_reading.called
