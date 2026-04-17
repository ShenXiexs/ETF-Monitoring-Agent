from __future__ import annotations

import http.client
import json
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np


class VectorStore:
    """Lightweight embedding-backed search for historical signals."""

    INTENT_DEFINITIONS = {
        "query": "查询产品基础信息、当日规模、成交额、净流入、产品代码或名称",
        "planning": "生成内容策略、传播建议、文案框架、活动安排、策略分析",
        "comparison": "跨日期对比分析、趋势总结、多日表现回顾、数据汇总",
        "policy": "解读政策、合规要求、行业通知、监管动态影响评估",
    }

    def __init__(self) -> None:
        self.api_key = (
            os.getenv("EMBEDDING_API_KEY")
            or os.getenv("LLM_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
        )
        self.signal_index: List[Tuple[dict, np.ndarray]] = []
        self.intent_embeddings: Dict[str, np.ndarray] = {}
        self.model = "text-embedding-v3"

    def _get_embeddings(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        if not self.api_key or not texts:
            return None

        try:
            conn = http.client.HTTPSConnection("dashscope.aliyuncs.com")
            payload = json.dumps({"model": self.model, "input": texts})
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            conn.request("POST", "/compatible-mode/v1/embeddings", payload, headers)
            res = conn.getresponse()
            result = json.loads(res.read().decode("utf-8"))
            items = sorted(result.get("data", []), key=lambda item: item.get("index", 0))
            return [np.array(item["embedding"]) for item in items]
        except Exception:
            return None

    def build_signal_index(self, all_signals: Dict[str, List[Dict]]) -> None:
        self.signal_index = []
        signal_texts: List[str] = []
        signal_metadata: List[dict] = []

        for date, signals in all_signals.items():
            for signal in signals:
                content = signal.get("content", "").strip()
                if not content:
                    continue
                signal_texts.append(content[:500])
                signal_metadata.append(
                    {
                        "date": date,
                        "content": content,
                        "category": signal.get("category", ""),
                    }
                )

        if not signal_texts:
            return

        for start in range(0, len(signal_texts), 8):
            embeddings = self._get_embeddings(signal_texts[start : start + 8])
            if embeddings:
                for offset, embedding in enumerate(embeddings):
                    self.signal_index.append((signal_metadata[start + offset], embedding))
            time.sleep(0.2)

        self._build_intent_embeddings()

    def _build_intent_embeddings(self) -> None:
        intents = list(self.INTENT_DEFINITIONS.keys())
        embeddings = self._get_embeddings([self.INTENT_DEFINITIONS[key] for key in intents])
        if not embeddings:
            return

        for idx, embedding in enumerate(embeddings):
            self.intent_embeddings[intents[idx]] = embedding

    def search_similar_signals(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.signal_index:
            return []

        query_embeddings = self._get_embeddings([query])
        if not query_embeddings:
            return []

        query_embedding = query_embeddings[0]
        ranked: List[Tuple[float, dict]] = []
        for metadata, embedding in self.signal_index:
            ranked.append((self._cosine_similarity(query_embedding, embedding), metadata))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "date": metadata["date"],
                "content": metadata["content"],
                "category": metadata["category"],
                "similarity": float(score),
            }
            for score, metadata in ranked[:top_k]
        ]

    def get_intent(self, message: str) -> str:
        if not self.intent_embeddings:
            return self._keyword_intent(message)

        query_embeddings = self._get_embeddings([message])
        if not query_embeddings:
            return self._keyword_intent(message)

        query_embedding = query_embeddings[0]
        best_intent = "query"
        best_score = -1.0
        for intent, embedding in self.intent_embeddings.items():
            score = self._cosine_similarity(query_embedding, embedding)
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_score < 0.35:
            return self._keyword_intent(message)
        return best_intent

    def _keyword_intent(self, message: str) -> str:
        planning_keywords = ["策略", "建议", "文案", "活动", "传播", "内容"]
        comparison_keywords = ["对比", "趋势", "变化", "区间", "到", "至"]
        policy_keywords = ["政策", "监管", "合规", "文件"]
        if any(keyword in message for keyword in planning_keywords):
            return "planning"
        if any(keyword in message for keyword in comparison_keywords):
            return "comparison"
        if any(keyword in message for keyword in policy_keywords):
            return "policy"
        return "query"

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

