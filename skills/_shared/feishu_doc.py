"""飞书云文档：目录规范、标题生成（上传由 lark-cli + lark-doc/lark-drive Skill 完成）。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DOC_IDS_FILE = _REPO / "reports" / "feishu_doc_ids.json"


@dataclass(frozen=True)
class DocTypeSpec:
    """一种可同步到飞书的报告类型。"""

    key: str
    folder_name: str
    title_prefix: str
    local_md: str
    env_doc_id: str
    default_doc_id: str | None
    env_folder_token: str
    source_skill: str  # 生成正文时先执行的 QMT Skill


DOC_TYPES: dict[str, DocTypeSpec] = {
    "daily-eval": DocTypeSpec(
        key="daily-eval",
        folder_name="每日复盘",
        title_prefix="QMT Bridge 当日复盘",
        local_md="reports/feishu_daily_eval.md",
        env_doc_id="FEISHU_DAILY_EVAL_DOC_ID",
        default_doc_id="JHyMdkU7boAaonxpsHScfewOnYe",
        env_folder_token="FEISHU_FOLDER_DAILY_EVAL_TOKEN",
        source_skill="qmt-bridge-execution-review",
    ),
    "daily-pnl": DocTypeSpec(
        key="daily-pnl",
        folder_name="盈亏快照",
        title_prefix="QMT Bridge 当日盈亏",
        local_md="reports/feishu_daily_pnl.md",
        env_doc_id="FEISHU_DAILY_PNL_DOC_ID",
        default_doc_id=None,
        env_folder_token="FEISHU_FOLDER_DAILY_PNL_TOKEN",
        source_skill="qmt-bridge-daily-pnl",
    ),
    "return-analysis": DocTypeSpec(
        key="return-analysis",
        folder_name="涨跌分析",
        title_prefix="QMT Bridge 涨跌分析",
        local_md="reports/feishu_return_analysis.md",
        env_doc_id="FEISHU_RETURN_ANALYSIS_DOC_ID",
        default_doc_id=None,
        env_folder_token="FEISHU_FOLDER_RETURN_ANALYSIS_TOKEN",
        source_skill="qmt-bridge-return-analysis",
    ),
    "portfolio-risk": DocTypeSpec(
        key="portfolio-risk",
        folder_name="组合风控",
        title_prefix="QMT Bridge 组合风险",
        local_md="reports/feishu_portfolio_risk.md",
        env_doc_id="FEISHU_PORTFOLIO_RISK_DOC_ID",
        default_doc_id=None,
        env_folder_token="FEISHU_FOLDER_PORTFOLIO_RISK_TOKEN",
        source_skill="qmt-bridge-portfolio-risk",
    ),
}


def format_title(
    prefix: str,
    *,
    trade_date: str | None = None,
    subject: str | None = None,
    synced_at: str | None = None,
) -> str:
    """云文档标题与 Markdown H1：`前缀 主题 同步时刻`。"""
    synced = synced_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if trade_date:
        if synced.startswith(trade_date):
            time_part = synced[len(trade_date) :].strip() or synced
            return f"{prefix} {trade_date} {time_part}"
        return f"{prefix} {trade_date} {synced}"
    if subject:
        return f"{prefix} {subject} {synced}"
    return f"{prefix} {synced}"


def title_from_markdown(md_path: Path) -> str | None:
    for line in md_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            return s[2:].strip()
        return s
    return None


def load_doc_ids() -> dict[str, str]:
    ids: dict[str, str] = {}
    if _DOC_IDS_FILE.is_file():
        try:
            data = json.loads(_DOC_IDS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ids = {k: str(v) for k, v in data.items() if v}
        except json.JSONDecodeError:
            pass
    legacy = _REPO / "reports" / "feishu_daily_eval_doc_id.txt"
    if legacy.is_file() and "daily-eval" not in ids:
        token = legacy.read_text(encoding="utf-8").strip()
        if token:
            ids["daily-eval"] = token
    return ids


def resolve_doc_token(spec: DocTypeSpec) -> str | None:
    env_val = os.environ.get(spec.env_doc_id, "").strip()
    if env_val:
        return env_val
    file_ids = load_doc_ids()
    if spec.key in file_ids:
        return file_ids[spec.key]
    return spec.default_doc_id


def resolve_wiki_parent_token(
    *,
    user_parent: str | None = None,
    doc_type_key: str = "daily-eval",
) -> str | None:
    """解析 wiki 父节点 token。

    优先级：用户对话指定 > 环境变量 > feishu_doc_ids.json。
    未配置则返回 None，Agent 应在知识库根创建（不传 --parent-node-token）。
    """
    if user_parent and user_parent.strip():
        return user_parent.strip()
    env_key = "FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN"
    if doc_type_key != "daily-eval":
        env_key = f"FEISHU_{doc_type_key.upper().replace('-', '_')}_WIKI_PARENT_TOKEN"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        return env_val
    file_ids = load_doc_ids()
    parent = file_ids.get(f"{doc_type_key}-wiki-parent", "").strip()
    return parent or None


def parse_wiki_token_from_url(url_or_token: str) -> str:
    """从飞书 wiki URL 或裸 token 提取 node_token。"""
    s = (url_or_token or "").strip()
    if "/wiki/" in s:
        return s.split("/wiki/", 1)[-1].split("?")[0].split("/")[0].strip()
    return s
