#!/usr/bin/env python3
"""
Event Markdown ファイルのバリデーション & id 自動採番スクリプト
Usage: python validate_event.py <path_to_event.md> [--auto-id]
"""

import sys
import os
import re
import glob
import argparse
from datetime import datetime

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML が必要です。pip install pyyaml を実行してください。")
    sys.exit(1)

# ─────────────────────────────────────────
# 定数
# ─────────────────────────────────────────
VALID_TYPES = {"meeting", "seminar", "social", "study"}
VALID_LOCATION_TYPES = {"online", "offline"}
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"     # ISO 8601 簡易形式（秒省略可）
DATETIME_FORMAT_FULL = "%Y-%m-%dT%H:%M:%S"
REQUIRED_FIELDS = ["id", "type", "title", "start_time", "end_time", "location", "location_type", "organizer"]


# ─────────────────────────────────────────
# YAML フロントマター パーサ
# ─────────────────────────────────────────
def parse_frontmatter(content: str):
    """
    Markdown ファイルの YAML フロントマターを抽出・パースする。
    Returns: (yaml_dict, markdown_body) or raises ValueError
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(content)
    if not match:
        raise ValueError("YAMLフロントマターが見つかりません（--- で囲まれたブロックが必要です）")

    yaml_str = match.group(1)
    body = content[match.end():]

    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML パースエラー: {e}")

    if not isinstance(data, dict):
        raise ValueError("YAMLフロントマターが辞書形式ではありません")

    return data, body


# ─────────────────────────────────────────
# datetime パーサ（ISO 8601 簡易対応）
# ─────────────────────────────────────────
def parse_datetime(value) -> datetime:
    value = str(value).strip()
    for fmt in (DATETIME_FORMAT_FULL, DATETIME_FORMAT):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"日時形式が正しくありません: '{value}'（例: 2026-03-25T14:00 または 2026-03-25T14:00:00）"
    )


# ─────────────────────────────────────────
# Markdown 構造チェック
# ─────────────────────────────────────────
def check_markdown_structure(body: str) -> list:
    warnings = []
    if "## 概要" not in body:
        warnings.append("WARNING: '## 概要' セクションが見つかりません（Slack通知時に '（概要なし）' と表示されます）")
    return warnings


# ─────────────────────────────────────────
# id 自動採番
# ─────────────────────────────────────────
def generate_id(start_dt: datetime, event_type: str, events_dir: str) -> str:
    date_str = start_dt.strftime("%Y%m%d")
    year_str = start_dt.strftime("%Y")
    prefix = f"{date_str}-{event_type}"

    # 同日・同typeのファイルを検索して最大連番を取得
    pattern = os.path.join(events_dir, year_str, f"{prefix}-*.md")
    existing = glob.glob(pattern)

    max_seq = 0
    for path in existing:
        basename = os.path.basename(path).replace(".md", "")
        parts = basename.split("-")
        if len(parts) >= 3:
            try:
                seq = int(parts[-1])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    new_seq = max_seq + 1
    return f"{prefix}-{new_seq:03d}"


# ─────────────────────────────────────────
# フロントマター書き換え（id: auto → 採番済みid）
# ─────────────────────────────────────────
def rewrite_id_in_content(content: str, new_id: str) -> str:
    return re.sub(r"(^---\s*\n.*?)id:\s*auto", f"\\1id: {new_id}", content, count=1, flags=re.DOTALL)


# ─────────────────────────────────────────
# メインバリデーション
# ─────────────────────────────────────────
def validate(filepath: str, auto_id: bool = False) -> bool:
    errors = []
    warnings = []
    updated_content = None

    # ファイル読み込み
    if not os.path.exists(filepath):
        print(f"ERROR: ファイルが見つかりません: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # フロントマターパース
    try:
        data, body = parse_frontmatter(content)
    except ValueError as e:
        print(f"❌ {filepath}")
        print(f"  ERROR: {e}")
        return False

    # ① 必須項目チェック
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            errors.append(f"必須項目 '{field}' が未入力です")

    # ② type 値チェック
    if "type" in data and data["type"] not in VALID_TYPES:
        errors.append(f"type の値が不正です: '{data['type']}'（有効値: {', '.join(sorted(VALID_TYPES))}）")

    # ③ location_type 値チェック
    if "location_type" in data and data["location_type"] not in VALID_LOCATION_TYPES:
        errors.append(f"location_type の値が不正です: '{data['location_type']}'（有効値: online / offline）")

    # ④ datetime 形式チェック
    start_dt = end_dt = None
    if "start_time" in data and data["start_time"]:
        try:
            start_dt = parse_datetime(data["start_time"])
        except ValueError as e:
            errors.append(f"start_time: {e}")

    if "end_time" in data and data["end_time"]:
        try:
            end_dt = parse_datetime(data["end_time"])
        except ValueError as e:
            errors.append(f"end_time: {e}")

    # ⑤ start_time < end_time 論理チェック
    if start_dt and end_dt:
        if end_dt <= start_dt:
            errors.append(
                f"end_time は start_time より後の日時である必要があります"
                f"（start: {start_dt}, end: {end_dt}）"
            )

    # ⑥ id 自動採番
    if errors == [] and str(data.get("id", "")).strip().lower() == "auto":
        if auto_id and start_dt:
            events_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(filepath))), "events")
            new_id = generate_id(start_dt, data["type"], events_dir)
            updated_content = rewrite_id_in_content(content, new_id)
            warnings.append(f"id を自動採番しました: {new_id}")
        else:
            warnings.append("id が 'auto' のままです（--auto-id フラグで自動採番できます）")

    # ⑦ Markdown 構造チェック
    warnings.extend(check_markdown_structure(body))

    # ─── 結果出力 ───
    if errors:
        print(f"❌ {filepath}")
        for e in errors:
            print(f"  ERROR: {e}")
        return False
    else:
        print(f"✅ {filepath}")
        for w in warnings:
            print(f"  {w}")

        # ファイル更新（id採番）
        if updated_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"  ファイルを更新しました（id採番）")

        return True


# ─────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Event Markdown バリデーター")
    parser.add_argument("files", nargs="+", help="バリデーション対象の Markdown ファイル")
    parser.add_argument("--auto-id", action="store_true", help="id: auto を自動採番で置換する")
    args = parser.parse_args()

    all_ok = True
    for filepath in args.files:
        ok = validate(filepath, auto_id=args.auto_id)
        if not ok:
            all_ok = False

    if not all_ok:
        print("\nバリデーション失敗：上記のエラーを修正してください。")
        sys.exit(1)
    else:
        print("\nすべてのファイルがバリデーションをパスしました。")
        sys.exit(0)


if __name__ == "__main__":
    main()