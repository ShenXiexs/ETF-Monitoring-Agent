from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
import re
import sqlite3
import ssl
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from openpyxl import load_workbook

try:
    from .financial_skills import DOCUMENT_WORKFLOWS, MODULE_SKILLS, build_skillbook, get_module_skill_cards
except ImportError:
    from financial_skills import DOCUMENT_WORKFLOWS, MODULE_SKILLS, build_skillbook, get_module_skill_cards

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    load_dotenv()

MODULES = [
    {
        "key": "product_research",
        "label": "产品研究",
        "summary": "回答产品属性、规模、代码、成立信息与结构化基础事实。",
        "prompt": "你是资管产品工作台中的产品研究模块，负责提供准确、克制、结构化的产品事实说明。",
    },
    {
        "key": "market_monitoring",
        "label": "市场监测",
        "summary": "跟踪成交活跃度、资金流向、重点指数波动和日内异动。",
        "prompt": "你是资管产品工作台中的市场监测模块，负责解释行情信号、成交变化与资金流向。",
    },
    {
        "key": "content_strategy",
        "label": "内容策略",
        "summary": "将市场事实整理成传播卖点、节奏建议与内容框架。",
        "prompt": "你是资管产品工作台中的内容策略模块，负责将事实整理为可执行的沟通框架与节奏建议。",
    },
    {
        "key": "policy_analysis",
        "label": "政策解析",
        "summary": "处理监管动态、制度文件摘要与政策研判报告。",
        "prompt": "你是资管产品工作台中的政策解析模块，负责解读政策文件、识别影响并给出中性判断。",
    },
]

class AssetWorkbenchManager:
    def __init__(self, data_source_dir: Optional[str] = None, profile_path: Optional[str] = None) -> None:
        self.base_dir = BASE_DIR
        self.data_source_dir = Path(data_source_dir).expanduser() if data_source_dir else self._resolve_data_source_dir()
        self.profile_path = Path(profile_path).expanduser() if profile_path else None
        self.data: Dict[str, dict] = {}
        self.dates: List[str] = []
        self.current_index = 0
        self.policies: List[dict] = []
        self.all_signals: Dict[str, List[dict]] = {}
        self.warnings: List[str] = []
        self.profile = self._load_profile()
        self.cache_path = Path(tempfile.gettempdir()) / "asset_intel_workbench_llm_cache.db"
        self._init_cache()
        self._load_external_data()
        self.vector_store = None
        if self.dates:
            self._precalculate_all_signals()
            self._init_vector_store()

    def _resolve_data_source_dir(self) -> Optional[Path]:
        raw = os.getenv("DATA_SOURCE_DIR", "").strip()
        return Path(raw).expanduser() if raw else None

    def _profile_default(self) -> dict:
        default_path = self.base_dir / "config" / "default_profile.json"
        return json.loads(default_path.read_text(encoding="utf-8"))

    def _profile_path(self) -> Optional[Path]:
        if self.profile_path:
            return self.profile_path
        raw = os.getenv("DATA_PROFILE_PATH", "").strip()
        return Path(raw).expanduser() if raw else None

    def _merge_dicts(self, base: dict, override: dict) -> dict:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_profile(self) -> dict:
        profile = self._profile_default()
        custom_path = self._profile_path()
        if custom_path:
            if custom_path.exists():
                custom = json.loads(custom_path.read_text(encoding="utf-8"))
                profile = self._merge_dicts(profile, custom)
            else:
                self.warnings = getattr(self, "warnings", [])
                self.warnings.append(f"未找到 DATA_PROFILE_PATH 指定的配置文件：{custom_path}")
        return profile

    def _init_cache(self) -> None:
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key_hash TEXT PRIMARY KEY,
                prompt TEXT,
                response TEXT,
                model TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def _get_cache(self, key_hash: str) -> Optional[str]:
        try:
            conn = sqlite3.connect(self.cache_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT response
                FROM cache
                WHERE key_hash = ?
                  AND timestamp > datetime('now', '-1 day')
                """,
                (key_hash,),
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def _set_cache(self, key_hash: str, prompt: str, response: str, model: str) -> None:
        try:
            conn = sqlite3.connect(self.cache_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache (key_hash, prompt, response, model, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (key_hash, prompt, response, model),
            )
            conn.commit()
            conn.close()
        except Exception:
            return

    def _load_external_data(self) -> None:
        existing_warnings = list(self.warnings)
        self.data = {}
        self.policies = []
        self.warnings = existing_warnings

        if not self.data_source_dir:
            self.warnings.append("未配置 DATA_SOURCE_DIR，工作台以空态模式启动。")
            return

        if not self.data_source_dir.exists():
            self.warnings.append(f"未找到外部数据目录：{self.data_source_dir}")
            return

        files = self.profile.get("files", {})
        snapshot_path = self.data_source_dir / files.get("market_snapshot", "market_snapshot.json")
        policy_path = self.data_source_dir / files.get("policy_catalog", "policy_catalog.xlsx")

        if snapshot_path.exists():
            self.data = self._load_market_snapshot(snapshot_path)
            self.dates = sorted(self.data.keys())
        else:
            self.warnings.append(f"缺少文件：{snapshot_path.name}")

        if policy_path.exists():
            self.policies = self._load_policies(policy_path)
        else:
            self.warnings.append(f"缺少文件：{policy_path.name}")

        if not self.data:
            self.warnings.append("当前未加载任何市场快照，监测与日报区域将显示空态。")

    def _load_market_snapshot(self, snapshot_path: Path) -> Dict[str, dict]:
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        normalized: Dict[str, dict] = {}
        snapshot_profile = self.profile.get("snapshot", {})
        date_field = snapshot_profile.get("date_field", "date")
        products_field = snapshot_profile.get("products_field", "products")
        indices_field = snapshot_profile.get("indices_field", "indices")

        if isinstance(raw, list):
            iterable = []
            for item in raw:
                if isinstance(item, dict) and item.get(date_field):
                    iterable.append((item[date_field], item))
        elif isinstance(raw, dict):
            iterable = raw.items()
        else:
            iterable = []

        for date_key, payload in iterable:
            date_str = self._normalize_date(str(date_key))
            if not date_str or not isinstance(payload, dict):
                continue

            products = [
                item
                for item in (self._normalize_product(entry) for entry in payload.get(products_field, []))
                if item
            ]
            indices = self._normalize_indices(payload.get(indices_field, {}))
            normalized[date_str] = {"products": products, "indices": indices}

        return normalized

    def _load_policies(self, policy_path: Path) -> List[dict]:
        policy_profile = self.profile.get("policy", {})
        workbook = load_workbook(policy_path, data_only=True, read_only=True)
        sheet_name = policy_profile.get("sheet_name")
        sheet = workbook[sheet_name] if sheet_name and sheet_name in workbook.sheetnames else workbook.active
        headers = [cell.value for cell in sheet[1]]
        header_lookup = {str(header).strip(): idx for idx, header in enumerate(headers) if header is not None}
        date_idx = self._match_header(header_lookup, policy_profile.get("columns", {}).get("date", ["公告日期"]))
        title_idx = self._match_header(header_lookup, policy_profile.get("columns", {}).get("title", ["标题"]))
        rank_idx = self._match_header(header_lookup, policy_profile.get("columns", {}).get("rank", ["法律位阶"]))
        source_idx = self._match_header(header_lookup, policy_profile.get("columns", {}).get("source", ["来源"]))
        policies: List[dict] = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            record = list(row)
            policies.append(
                {
                    "公告日期": self._normalize_date(record[date_idx]) if date_idx is not None and date_idx < len(record) else None,
                    "标题": str(record[title_idx] if title_idx is not None and title_idx < len(record) else "").strip(),
                    "法律位阶": str(
                        (record[rank_idx] if rank_idx is not None and rank_idx < len(record) else "")
                        or policy_profile.get("default_rank", "行业规定")
                    ).strip(),
                    "来源": str(record[source_idx] if source_idx is not None and source_idx < len(record) else "").strip(),
                }
            )
        return policies

    def _match_header(self, header_lookup: Dict[str, int], aliases: List[str]) -> Optional[int]:
        for alias in aliases:
            if alias in header_lookup:
                return header_lookup[alias]
        lowered_lookup = {key.lower(): value for key, value in header_lookup.items()}
        for alias in aliases:
            if alias.lower() in lowered_lookup:
                return lowered_lookup[alias.lower()]
        return None

    def _normalize_indices(self, raw_indices: object) -> Dict[str, dict]:
        normalized: Dict[str, dict] = {}
        index_fields = self.profile.get("snapshot", {}).get("index_fields", {})
        code_field = index_fields.get("code", "code")
        if isinstance(raw_indices, list):
            iterator = []
            for item in raw_indices:
                if isinstance(item, dict) and item.get(code_field):
                    iterator.append((item[code_field], item))
        elif isinstance(raw_indices, dict):
            iterator = raw_indices.items()
        else:
            iterator = []

        for code, payload in iterator:
            if not isinstance(payload, dict):
                continue
            normalized[str(code)] = {
                "name": str(payload.get(index_fields.get("name", "name"), "")).strip(),
                "prev_close": self._safe_float(payload.get(index_fields.get("prev_close", "prev_close"))),
                "open": self._safe_float(payload.get(index_fields.get("open", "open"))),
                "change": self._safe_float(payload.get(index_fields.get("change", "change"))),
                "volume": self._safe_float(payload.get(index_fields.get("volume", "volume"))),
            }
        return normalized

    def _normalize_product(self, payload: object) -> Optional[dict]:
        if not isinstance(payload, dict):
            return None
        product_fields = self.profile.get("snapshot", {}).get("product_fields", {})
        code = str(payload.get(product_fields.get("code", "code"), "")).strip()
        name = str(payload.get(product_fields.get("name", "name"), "")).strip()
        if not code or not name:
            return None
        return {
            "code": code,
            "name": name,
            "setup_date": self._normalize_date(payload.get(product_fields.get("setup_date", "setup_date"))),
            "list_date": self._normalize_date(payload.get(product_fields.get("list_date", "list_date"))),
            "scale": self._safe_float(payload.get(product_fields.get("scale", "scale"))),
            "volume": self._safe_float(payload.get(product_fields.get("volume", "volume"))),
            "inflow": self._safe_float(payload.get(product_fields.get("inflow", "inflow"))),
            "index_code": str(payload.get(product_fields.get("index_code", "index_code"), "")).strip(),
        }

    def _normalize_date(self, value: object) -> Optional[str]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        text = str(value).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        match = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        return None

    @staticmethod
    def _safe_float(value: object) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            text = str(value).strip().replace(",", "")
            if text in {"", "--", "-"}:
                return 0.0
            return float(text)
        except Exception:
            return 0.0

    def _precalculate_all_signals(self) -> None:
        original_index = self.current_index
        for idx, _ in enumerate(self.dates):
            self.current_index = idx
            self.all_signals[self.dates[idx]] = self.check_rules()
        self.current_index = original_index

    def _init_vector_store(self) -> None:
        try:
            try:
                from .vector_store import get_vector_store
            except ImportError:
                from vector_store import get_vector_store
            self.vector_store = get_vector_store()
            self.vector_store.build_signal_index(self.all_signals)
        except Exception:
            self.vector_store = None

    def has_data(self) -> bool:
        return bool(self.dates)

    def reset_cycle(self) -> None:
        self.current_index = 0

    def next_step(self) -> bool:
        if not self.has_data():
            return False
        if self.current_index < len(self.dates) - 1:
            self.current_index += 1
            return True
        return False

    def get_current_date(self) -> Optional[str]:
        state = self.get_current_state()
        return state["date"] if state else None

    def get_current_state(self) -> Optional[dict]:
        if not self.has_data() or self.current_index >= len(self.dates):
            return None
        current_date = self.dates[self.current_index]
        return {
            "date": current_date,
            "products": self.data[current_date].get("products", []),
            "indices": self.data[current_date].get("indices", {}),
            "policies": [item for item in self.policies if item.get("公告日期") == current_date],
        }

    def get_all_products(self) -> List[dict]:
        seen = set()
        products: List[dict] = []
        for date in self.dates:
            for item in self.data[date].get("products", []):
                if item["code"] in seen:
                    continue
                seen.add(item["code"])
                products.append({"code": item["code"], "name": item["name"]})
        return sorted(products, key=lambda item: item["name"])

    def get_market_leaderboard(self, category: str = "volume", top_n: int = 3) -> List[dict]:
        state = self.get_current_state()
        if not state:
            return []
        if category not in {"volume", "inflow", "scale"}:
            category = "volume"
        return sorted(state["products"], key=lambda item: item.get(category, 0), reverse=True)[:top_n]

    def get_daily_summary(self) -> str:
        state = self.get_current_state()
        if not state:
            return "当前未加载外部市场快照。"

        date = state["date"]
        summary_lines = [f"【{date} 市场摘要】"]
        signals = self.all_signals.get(date, [])
        highlights = [item["content"] for item in signals if item["category"] in {"规模里程碑", "行情异动"}][:3]
        if highlights:
            summary_lines.append("- 重点信号：" + "；".join(highlights))

        indices = state.get("indices", {})
        index_lines = []
        for item in indices.values():
            change = item.get("change", 0)
            if abs(change) < 0.8:
                continue
            direction = "上涨" if change > 0 else "下跌"
            index_lines.append(f"{item['name']} {direction}{abs(change):.1f}%")
        if index_lines:
            summary_lines.append("- 指数表现：" + "，".join(index_lines[:3]))
        return "\n".join(summary_lines)

    def get_date_summary(self, date_str: str) -> str:
        if date_str not in self.data:
            return f"未找到 {date_str} 的快照数据。"

        day_data = self.data[date_str]
        signals = self.all_signals.get(date_str, [])
        lines = [f"### {date_str} 数据摘要", ""]

        if signals:
            lines.append("**当日信号**")
            lines.extend(f"- [{item['category']}] {item['content']}" for item in signals[:5])
            lines.append("")

        top_volume = sorted(day_data.get("products", []), key=lambda item: item.get("volume", 0), reverse=True)[:3]
        if top_volume:
            lines.append("**成交活跃 Top 3**")
            lines.extend(
                f"{idx}. {item['name']} ({item['code']}) 成交额 {item['volume']:.2f} 亿"
                for idx, item in enumerate(top_volume, 1)
            )
            lines.append("")

        top_inflow = sorted(day_data.get("products", []), key=lambda item: item.get("inflow", 0), reverse=True)[:3]
        if top_inflow:
            lines.append("**资金流入 Top 3**")
            lines.extend(
                f"{idx}. {item['name']} ({item['code']}) 净流入 {item['inflow']:.2f} 亿"
                for idx, item in enumerate(top_inflow, 1)
            )

        return "\n".join(lines).strip()

    def get_date_range_comparison(self, start_date: str, end_date: str, product_code: Optional[str] = None) -> str:
        dates_in_range = [date for date in self.dates if start_date <= date <= end_date]
        if not dates_in_range:
            return f"未找到 {start_date} 至 {end_date} 的数据。"

        if product_code:
            rows = []
            for date in dates_in_range:
                product = self.find_product(product_code, date)
                if product:
                    rows.append(product)
            if not rows:
                return f"区间内未找到产品 {product_code}。"

            lines = [
                f"### {product_code} 区间对比",
                "",
                "| 日期 | 规模(亿) | 成交额(亿) | 净流入(亿) |",
                "|:---|---:|---:|---:|",
            ]
            for idx, date in enumerate(dates_in_range):
                product = self.find_product(product_code, date)
                if not product:
                    continue
                lines.append(
                    f"| {date} | {product['scale']:.2f} | {product['volume']:.2f} | {product['inflow']:.2f} |"
                )
            return "\n".join(lines)

        total_inflow = 0.0
        total_volume = 0.0
        highlights: List[str] = []
        for date in dates_in_range:
            products = self.data[date].get("products", [])
            total_inflow += sum(item.get("inflow", 0) for item in products)
            total_volume += sum(item.get("volume", 0) for item in products)
            highlights.extend(item["content"] for item in self.all_signals.get(date, [])[:2])

        lines = [
            f"### {start_date} 至 {end_date} 区间对比",
            "",
            f"- 累计净流入：{total_inflow:.2f} 亿",
            f"- 累计成交额：{total_volume:.2f} 亿",
        ]
        if highlights:
            lines.append("- 重点信号：")
            lines.extend(f"  - {item}" for item in highlights[:6])
        return "\n".join(lines)

    def empty_daily_report(self) -> dict:
        return {
            "available": False,
            "date": None,
            "highlights": [],
            "news": [],
            "suggestions": ["当前未加载外部数据，日报内容暂不可用。"],
        }

    def get_daily_report(self, date_str: Optional[str]) -> dict:
        if not date_str or date_str not in self.data:
            return self.empty_daily_report()

        state = self.data[date_str]
        products = state.get("products", [])
        signals = self.all_signals.get(date_str, [])
        highlights = []

        for category, metric, unit in (
            ("规模领先", "scale", "亿"),
            ("成交活跃", "volume", "亿"),
            ("资金流入", "inflow", "亿"),
        ):
            ranked = sorted(products, key=lambda item: item.get(metric, 0), reverse=True)
            if ranked:
                top_item = ranked[0]
                highlights.append(
                    {
                        "category": category,
                        "product_name": top_item["name"],
                        "product_code": top_item["code"],
                        "value": top_item.get(metric, 0),
                        "unit": unit,
                    }
                )

        news = [item["content"] for item in signals[:6]]
        suggestions = []
        if highlights:
            suggestions.append(f"围绕 {highlights[0]['product_name']} 的当日优势制作简洁的事实卡片。")
        if len(news) >= 2:
            suggestions.append("将当日重点信号拆分为“市场变化 + 对应解读”两段式内容。")
        suggestions.append("对外内容保留事实依据与风险提示，避免夸张表述。")

        return {
            "available": True,
            "date": date_str,
            "highlights": highlights,
            "news": news,
            "suggestions": suggestions[:4],
        }

    def get_bootstrap_state(self, simulation_state: dict) -> dict:
        state = self.get_current_state()
        current_date = state["date"] if state else None
        workspace = self.profile.get("workspace", {})
        modules = self._module_definitions()
        return {
            "app_name": workspace.get("app_name", "资管产品洞察协作台"),
            "workspace": workspace,
            "modules": [{**item, "skills": self.module_skill_cards(item["key"])} for item in modules],
            "has_data": self.has_data(),
            "warnings": self.warnings,
            "simulation": {
                "is_running": simulation_state["is_running"],
                "interval": simulation_state["interval"],
                "current_date": current_date,
            },
            "summary": {
                "product_count": len(self.get_all_products()),
                "policy_count": len(self.policies),
                "signal_count": len(self.all_signals.get(current_date, [])) if current_date else 0,
                "status": "已接入" if self.has_data() else "空态",
            },
            "current_state": state
            or {
                "date": None,
                "products": [],
                "indices": {},
                "policies": [],
            },
            "products": self.get_all_products(),
            "signals": self.all_signals.get(current_date, []) if current_date else [],
            "history": {date: self.all_signals.get(date, []) for date in reversed(self.dates[-10:])},
            "daily_report": self.get_daily_report(current_date),
        }

    def _module_definitions(self) -> List[dict]:
        overrides = self.profile.get("workspace", {}).get("module_overrides", {})
        definitions = []
        for item in MODULES:
            override = overrides.get(item["key"], {}) if isinstance(overrides, dict) else {}
            merged = dict(item)
            if isinstance(override, dict):
                merged.update({key: value for key, value in override.items() if value})
            definitions.append(merged)
        return definitions

    def _module_map(self) -> Dict[str, dict]:
        return {item["key"]: item for item in self._module_definitions()}

    def find_product(self, query: str, date_str: Optional[str] = None) -> Optional[dict]:
        target_date = date_str or self.get_current_date()
        if not target_date or target_date not in self.data:
            return None

        query_lower = query.lower().strip()
        products = self.data[target_date].get("products", [])
        for item in products:
            if item["code"].lower() == query_lower:
                return item
        for item in products:
            if query_lower in item["name"].lower():
                return item
        return None

    def render_product_snapshot(self, product: dict, date_str: str) -> str:
        return (
            f"### 产品快照\n\n"
            f"- 日期：{date_str}\n"
            f"- 名称：{product['name']}\n"
            f"- 代码：{product['code']}\n"
            f"- 规模：{product['scale']:.2f} 亿\n"
            f"- 成交额：{product['volume']:.2f} 亿\n"
            f"- 净流入：{product['inflow']:.2f} 亿"
        )

    def render_leaderboard(self, category: str) -> str:
        label_map = {"volume": ("成交活跃", "成交额"), "inflow": ("资金流入", "净流入"), "scale": ("规模领先", "规模")}
        category_label, metric_label = label_map[category]
        products = self.get_market_leaderboard(category, top_n=3)
        if not products:
            return "当前无可用排行数据。"

        date_str = self.get_current_date() or "-"
        rows = "\n".join(
            f"| {idx} | {item['name']} ({item['code']}) | {item[category]:.2f} 亿 |"
            for idx, item in enumerate(products, 1)
        )
        return (
            f"### {date_str} {category_label}排行榜\n\n"
            f"| 排名 | 产品名称 | {metric_label} |\n"
            f"|:---|:---|---:|\n"
            f"{rows}"
        )

    def detect_structured_response(self, message: str, module_key: str) -> Optional[str]:
        if not self.has_data():
            if module_key == "policy_analysis":
                return None
            return "当前未加载外部数据目录。请先配置 `DATA_SOURCE_DIR`，或在空态下使用政策解析能力。"

        code_match = re.search(r"([0-9]{6}(?:\.[A-Z]{2})?)", message)
        if code_match:
            product = self.find_product(code_match.group(1))
            if product:
                return self.render_product_snapshot(product, self.get_current_date() or "-")

        if any(keyword in message for keyword in ["成交活跃", "成交额排行", "谁成交最多", "成交额排名"]):
            return self.render_leaderboard("volume")

        if any(keyword in message for keyword in ["净流入", "资金流入", "谁吸金", "流入排行"]):
            return self.render_leaderboard("inflow")

        if any(keyword in message for keyword in ["规模领先", "规模排行", "规模排名"]):
            return self.render_leaderboard("scale")

        range_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s*[到至\-~]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", message)
        if range_match:
            return self.get_date_range_comparison(
                self._normalize_date(range_match.group(1)) or range_match.group(1),
                self._normalize_date(range_match.group(2)) or range_match.group(2),
                code_match.group(1) if code_match else None,
            )

        date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", message)
        if date_match:
            normalized_date = self._normalize_date(date_match.group(1))
            if normalized_date:
                return self.get_date_summary(normalized_date)

        return None

    def module_label(self, module_key: str) -> str:
        return self._module_map().get(module_key, MODULES[0])["label"]

    def module_skill_cards(self, module_key: str) -> List[dict]:
        return get_module_skill_cards(module_key)

    def _workflow_skill_keys(self, workflow_key: str) -> List[str]:
        return DOCUMENT_WORKFLOWS.get(workflow_key, [])

    def build_system_prompt(self, module_key: str) -> str:
        module_info = self._module_map().get(module_key, MODULES[0])
        context = self.get_daily_summary()
        skillbook = build_skillbook(MODULE_SKILLS.get(module_key, []))
        return (
            f"{module_info.get('prompt', MODULES[0]['prompt'])}\n\n"
            f"当前启用的专家 skills：\n{skillbook}\n\n"
            f"回答要求：综合这些技能视角作答，但不要机械罗列技能名；明确区分事实、判断、建议和风险边界。\n\n"
            f"当前上下文：\n{context}"
        )

    def build_llm_prompt(self, message: str, module_key: str) -> str:
        intent = self.get_user_intent(message)
        history_context = ""
        if intent in {"planning", "comparison", "policy"}:
            similar = self.get_similar_signals(message, top_k=2)
            if similar:
                history_context = "\n\n历史参考：\n" + "\n".join(
                    f"- [{item['date']}] {item['content']}" for item in similar
                )
        state_date = self.get_current_date() or "未加载数据"
        skillbook = build_skillbook(MODULE_SKILLS.get(module_key, []), include_contract=False)
        return (
            f"当前日期：{state_date}\n"
            f"模块：{self.module_label(module_key)}\n"
            f"当前技能编排：\n{skillbook}\n\n"
            f"用户问题：{message}{history_context}"
        )

    def check_rules(self) -> List[dict]:
        state = self.get_current_state()
        if not state:
            return []

        date_str = state["date"]
        products = state["products"]
        indices = state["indices"]
        signals: List[dict] = []

        ranked_scale = sorted(products, key=lambda item: item.get("scale", 0), reverse=True)
        for idx, item in enumerate(ranked_scale[:3], 1):
            signals.append(
                {
                    "type": "scale",
                    "category": "规模里程碑",
                    "content": f"{item['name']} 规模位列样本产品第 {idx}，当前为 {item['scale']:.2f} 亿。",
                    "date": date_str,
                }
            )

        for index_item in indices.values():
            change = index_item.get("change", 0)
            if abs(change) >= 1.5:
                direction = "上涨" if change > 0 else "下跌"
                signals.append(
                    {
                        "type": "market",
                        "category": "行情异动",
                        "content": f"{index_item['name']} 日内{direction} {abs(change):.1f}%。",
                        "date": date_str,
                    }
                )

        top_inflow = sorted(products, key=lambda item: item.get("inflow", 0), reverse=True)[:3]
        for item in top_inflow:
            if item.get("inflow", 0) > 0:
                signals.append(
                    {
                        "type": "product",
                        "category": "产品动态",
                        "content": f"{item['name']} 当日净流入 {item['inflow']:.2f} 亿。",
                        "date": date_str,
                    }
                )

        current_dt = datetime.strptime(date_str, "%Y-%m-%d")
        for item in products:
            setup_date = item.get("setup_date")
            if not setup_date:
                continue
            try:
                setup_dt = datetime.strptime(setup_date, "%Y-%m-%d")
            except ValueError:
                continue
            if setup_dt.month == current_dt.month and setup_dt.day == current_dt.day:
                years = current_dt.year - setup_dt.year
                if years > 0:
                    signals.append(
                        {
                            "type": "anniversary",
                            "category": "周年提醒",
                            "content": f"{item['name']} 迎来成立 {years} 周年。",
                            "date": date_str,
                        }
                    )

        for item in self.policies:
            if item.get("公告日期") == date_str and item.get("标题"):
                signals.append(
                    {
                        "type": "policy",
                        "category": "监管政策",
                        "content": f"[{item['法律位阶']}] {item['标题']}",
                        "date": date_str,
                        "link": item.get("来源", ""),
                    }
                )

        return signals

    def summarize_document(self, text: str) -> str:
        if not self._get_llm_api_key():
            return self._offline_document_summary(text)

        skill_notes = self._generate_document_skill_notes(text, workflow_key="summary")
        prompt = (
            "请基于以下金融专家 skills 分析笔记，为业务用户输出一份四点式政策解析摘要。"
            "每一点都要同时覆盖条款变化、影响路径或注意事项，使用“标题：说明”的形式，"
            "说明控制在 60 至 90 字。\n\n"
            f"技能笔记：\n{skill_notes}\n\n"
            f"原文节选：\n{text[:3200]}"
        )
        return self.call_llm(
            prompt,
            system_content=(
                "你是政策解析模块的编审器。你的工作是综合金融专家 skills 笔记，"
                "输出短而准的摘要，避免空话和确定性过强的表述。"
            ),
            model="qwen-flash",
        )

    def analyze_document(self, text: str) -> str:
        if not self._get_llm_api_key():
            return self._offline_document_report(text)

        skill_notes = self._generate_document_skill_notes(text, workflow_key="report")
        prompt = (
            "请基于以下金融专家 skills 笔记和文件原文，生成一份结构化研判报告。"
            "报告必须包含以下层级：\n"
            "# 政策概要\n# 关键变化\n# 市场与业务影响\n# 产品策略观察\n# 风险与合规边界\n# 执行优先级\n\n"
            "写作要求：\n"
            "1. 先事实，后判断，再建议。\n"
            "2. 避免宏大口号和夸张收益表述。\n"
            "3. 每个章节都要给出明确落点。\n\n"
            f"技能笔记：\n{skill_notes}\n\n"
            f"原文节选：\n{text[:5000]}"
        )
        return self.call_llm(
            prompt,
            system_content=(
                "你是政策解析模块的报告编审器，负责融合多位金融专家 skill 的观点，"
                "输出层次清楚、专业克制、可落地的研判报告。"
            ),
            max_tokens=3000,
            model="qwen-flash",
        )

    def _generate_document_skill_notes(self, text: str, workflow_key: str) -> str:
        skill_keys = self._workflow_skill_keys(workflow_key)
        skillbook = build_skillbook(skill_keys)
        prompt = (
            "请围绕以下文件，按专家 skills 逐个生成分析笔记。每个 skill 输出一个小节，"
            "格式为 `## 技能名` 加 2 到 3 条短要点。每条要点都必须是具体观察、影响判断或边界提醒。\n\n"
            f"启用技能：\n{skillbook}\n\n"
            f"文件内容：\n{text[:5000]}"
        )
        return self.call_llm(
            prompt,
            system_content="你是金融研究技能编排器，负责先分技能拆解问题，再为后续摘要和报告提供高质量笔记。",
            max_tokens=2200,
            model="qwen-flash",
        )

    def _offline_document_summary(self, text: str) -> str:
        clauses = self._extract_document_clauses(text, limit=4)
        titles = ["政策主旨", "影响路径", "业务观察", "风险提示"]
        lines = []
        for idx, title in enumerate(titles, 1):
            clause = clauses[idx - 1] if idx - 1 < len(clauses) else "原文信息有限，建议结合正式文本复核。"
            lines.append(f"{idx}. **{title}**：{clause}")
        return "\n".join(lines)

    def _offline_document_report(self, text: str) -> str:
        clauses = self._extract_document_clauses(text, limit=6)
        while len(clauses) < 6:
            clauses.append("原文信息有限，当前内容仅作内部研判草稿，正式使用前需结合完整文本复核。")
        return (
            "# 政策概要\n"
            f"{clauses[0]}\n\n"
            "# 关键变化\n"
            f"{clauses[1]}\n\n"
            "# 市场与业务影响\n"
            f"{clauses[2]}\n\n"
            "# 产品策略观察\n"
            f"{clauses[3]}\n\n"
            "# 风险与合规边界\n"
            f"{clauses[4]}\n\n"
            "# 执行优先级\n"
            f"{clauses[5]}"
        )

    def _extract_document_clauses(self, text: str, limit: int = 6) -> List[str]:
        candidates: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                candidates.append(stripped)
        if len(candidates) < limit:
            flattened = re.split(r"[。；;\n]", text)
            for item in flattened:
                stripped = item.strip()
                if stripped:
                    candidates.append(stripped)
        unique: List[str] = []
        seen = set()
        for item in candidates:
            short = item[:120]
            if short in seen:
                continue
            seen.add(short)
            unique.append(short)
            if len(unique) >= limit:
                break
        return unique

    def build_docx_report(self, content: str) -> bytes:
        app_name = self.profile.get("workspace", {}).get("app_name", "资管产品洞察协作台")
        paragraphs = [
            self._docx_paragraph("政策研判报告", bold=True, size=34),
            self._docx_paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            self._docx_paragraph(f"分析引擎：{app_name}"),
            self._docx_paragraph("=" * 48),
        ]

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                heading_text = stripped.replace("#", "").strip()
                paragraphs.append(self._docx_paragraph(heading_text, bold=True, size=26))
            else:
                paragraphs.append(self._docx_paragraph(stripped))

        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
            'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
            'xmlns:o="urn:schemas-microsoft-com:office:office" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
            'xmlns:v="urn:schemas-microsoft-com:vml" '
            'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:w10="urn:schemas-microsoft-com:office:word" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
            'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
            'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
            'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
            'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14">'
            f"<w:body>{''.join(paragraphs)}"
            "<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" "
            "w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr>"
            "</w:body></w:document>"
        )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>",
            )
            archive.writestr(
                "_rels/.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>",
            )
            archive.writestr(
                "word/_rels/document.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )
            archive.writestr("word/document.xml", document_xml)
        buffer.seek(0)
        return buffer.getvalue()

    def _docx_paragraph(self, text: str, bold: bool = False, size: int = 22) -> str:
        safe_text = escape(text)
        bold_xml = "<w:b/>" if bold else ""
        return (
            "<w:p><w:r><w:rPr>"
            f"{bold_xml}<w:sz w:val=\"{size}\"/><w:szCs w:val=\"{size}\"/>"
            "</w:rPr>"
            f"<w:t xml:space=\"preserve\">{safe_text}</w:t>"
            "</w:r></w:p>"
        )

    def _get_llm_api_key(self) -> str:
        return os.getenv("LLM_API_KEY", "").strip() or os.getenv("DASHSCOPE_API_KEY", "").strip()

    def call_llm_stream(
        self,
        prompt: str,
        system_content: str = "你是一个专业的业务助手。",
        history: Optional[List[dict]] = None,
        max_tokens: int = 2000,
        model: str = "qwen-turbo",
    ) -> Iterable[str]:
        api_key = self._get_llm_api_key()
        if not api_key:
            yield self._offline_response(prompt)
            return

        history_str = json.dumps(history or [], ensure_ascii=False)
        state_date = self.get_current_date() or "nodate"
        cache_key = hashlib.md5((model + system_content + prompt + history_str + state_date).encode("utf-8")).hexdigest()
        cached = self._get_cache(cache_key)
        if cached:
            yield cached
            return

        full_response = ""
        try:
            messages = [{"role": "system", "content": system_content}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})
            payload = json.dumps(
                {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.5,
                    "stream": True,
                }
            )
            conn = http.client.HTTPSConnection("dashscope.aliyuncs.com", context=ssl.create_default_context())
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            conn.request("POST", "/compatible-mode/v1/chat/completions", payload, headers)
            response = conn.getresponse()
            while True:
                line = response.readline().decode("utf-8").strip()
                if not line:
                    if response.isclosed():
                        break
                    continue
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_response += content
                    yield content
            if full_response:
                self._set_cache(cache_key, prompt, full_response, model)
        except Exception:
            yield self._offline_response(prompt)

    def call_llm(
        self,
        prompt: str,
        system_content: str = "你是一个专业的业务助手。",
        history: Optional[List[dict]] = None,
        max_tokens: int = 2000,
        model: str = "qwen-turbo",
    ) -> str:
        api_key = self._get_llm_api_key()
        if not api_key:
            return self._offline_response(prompt)

        history_str = json.dumps(history or [], ensure_ascii=False)
        state_date = self.get_current_date() or "nodate"
        cache_key = hashlib.md5((model + system_content + prompt + history_str + state_date).encode("utf-8")).hexdigest()
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            messages = [{"role": "system", "content": system_content}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})
            payload = json.dumps(
                {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.5,
                }
            )
            conn = http.client.HTTPSConnection("dashscope.aliyuncs.com", context=ssl.create_default_context())
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            conn.request("POST", "/compatible-mode/v1/chat/completions", payload, headers)
            response = conn.getresponse()
            result = json.loads(response.read().decode("utf-8"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                return self._offline_response(prompt)
            self._set_cache(cache_key, prompt, content, model)
            return content
        except Exception:
            return self._offline_response(prompt)

    def _offline_response(self, prompt: str) -> str:
        trimmed = prompt.strip().replace("\n", " ")
        return (
            "当前未配置语言模型服务，以下为基于现有上下文生成的离线说明：\n\n"
            f"{trimmed[:360]}"
        )

    def get_similar_signals(self, query: str, top_k: int = 3) -> List[dict]:
        if self.vector_store:
            return self.vector_store.search_similar_signals(query, top_k=top_k)
        return []

    def get_user_intent(self, message: str) -> str:
        if self.vector_store:
            return self.vector_store.get_intent(message)
        if any(keyword in message for keyword in ["政策", "监管", "文件", "合规"]):
            return "policy"
        if any(keyword in message for keyword in ["建议", "策略", "传播", "文案"]):
            return "planning"
        if any(keyword in message for keyword in ["对比", "趋势", "变化", "区间"]):
            return "comparison"
        return "query"
