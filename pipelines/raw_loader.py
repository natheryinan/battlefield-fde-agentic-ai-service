from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from collections import deque


@dataclass
class RawBatch:
    source: str
    timestamp: float
    payload: Dict[str, Any]
    meta: Optional[Dict[str, Any]] = None


class RawLoader:
    def __init__(self, source_name: str, max_queue_size: int = 1000):
        """
        source_name: 数据源名称（kafka topic / exchange / vendor tag）
        max_queue_size: 内部缓冲队列最大长度，超出时自动丢弃最早的元素
        """
        self.source_name = source_name
        self.max_queue_size = max_queue_size
        self._queue = deque()  # 队列本体

    # === 主职：立即装配一个 RawBatch 返回 ===
    def load(self, record: Dict[str, Any]) -> RawBatch:
        return RawBatch(
            source=self.source_name,
            timestamp=record.get("ts") or record.get("timestamp"),
            payload=record,
            meta={
                "ingest_version": "v1",
                "schema": "raw-pass-through"
            }
        )

    # === 副职 1：排队入列 ===
    def enqueue(self, record: Dict[str, Any]) -> None:
        """
        把一条原始记录装配成 RawBatch 并放入内部队列。
        如果超过 max_queue_size，就弹出最早的一条（丢历史、保最新）。
        """
        batch = self.load(record)
        self._queue.append(batch)
        if len(self._queue) > self.max_queue_size:
            self._queue.popleft()

    # === 副职 2：批量入列 ===
    def enqueue_many(self, records: List[Dict[str, Any]]) -> None:
        """
        批量入队，遵守相同的 max_queue_size 限制。
        """
        for r in records:
            self.enqueue(r)

    # === 副职 3：一次性取出当前所有排队的批次 ===
    def drain(self) -> List[RawBatch]:
        """
        取出并清空当前队列中的所有 RawBatch，按时间/入队顺序返回。
        """
        items: List[RawBatch] = list(self._queue)
        self._queue.clear()
        return items

    # === 副职 4：窥视 / 状态查询 ===
    def peek(self) -> Optional[RawBatch]:
        """
        看一眼队首元素，不弹出；如果队列为空，返回 None。
        """
        return self._queue[0] if self._queue else None

    def has_pending(self) -> bool:
        """
        是否还有待处理的 RawBatch。
        """
        return bool(self._queue)

    def __len__(self) -> int:
        """
        当前队列长度。
        """
        return len(self._queue)
