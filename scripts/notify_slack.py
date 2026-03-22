#!/usr/bin/env python3
"""
Slack 通知スクリプト
Usage: python notify_slack.py <path_to_event.md> --webhook-url <URL> --github-url <URL>
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.error

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML が必要です。pip install pyyaml を実行してください。")
    sys.exit(1)

TYPE_LABELS = {
    "meeting": "ミーティング",
    "seminar": "外部説明会",
    "social":  "飲み会",
    "study":   "勉強会",
}

SUMMARY_MAX_CHARS = 200


# ─────────────────────────────────────────
# フロントマターパース
# ─────────────────────────────────────────
def parse_frontmatter(content: str):
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(content)
    if not match:
        raise ValueError("YAMLフロントマターが見つかりません")
    data = yaml.safe_load(match.group(1))
    body = content[match.end():]
    return data, body


# ─────────────────────────────────────────
# ## 概要 セクション抽出
# 仕様：先頭200文字、超過時は「…」付加
# ─────────────────────────────────────────
def extract_summary(body: str) -> str:
    match = re.search(r"##\s*概要\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
    if not match:
        return "（概要なし）"

    raw = match.group(1).strip()
    # 空行・Markdownヘッダ・リストマーカーを除去して結合
    lines = [
        re.sub(r"^[-*]\s*", "", line).strip()
        for line in raw.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    text = "　".join(lines)

    if len(text) > SUMMARY_MAX_CHARS:
        text = text[:SUMMARY_MAX_CHARS] + "…"

    return text if text else "（概要なし）"


# ─────────────────────────────────────────
# Slack メッセージ組み立て
# ─────────────────────────────────────────
def build_message(data: dict, body: str, github_url: str) -> dict:
    type_label = TYPE_LABELS.get(data.get("type", ""), data.get("type", "不明"))
    location = data.get("location", "未設定")
    location_type = data.get("location_type", "")
    location_str = f"{location}（{location_type}）" if location_type else location

    url_line = ""
    if data.get("url"):
        url_line = f"\n🔗 URL：{data['url']}"

    summary = extract_summary(body)
    start = str(data.get("start_time", ""))
    end = str(data.get("end_time", ""))

    text = (
        f"📅 *{data.get('title', '（タイトルなし）')}*\n"
        f"\n"
        f"■ 種別：{type_label}\n"
        f"■ 日時：{start} - {end}\n"
        f"■ 場所：{location_str}{url_line}\n"
        f"■ 主催：{data.get('organizer', '未設定')}\n"
        f"\n"
        f"📝 概要：\n{summary}\n"
        f"\n"
        f"🔗 詳細：{github_url}"
    )

    return {"text": text}


# ─────────────────────────────────────────
# Slack 送信
# ─────────────────────────────────────────
def send_to_slack(webhook_url: str, message: dict) -> None:
    payload = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Slack API エラー: status={resp.status}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Slack 送信失敗: {e.code} {e.reason}")


# ─────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Slack 通知スクリプト")
    parser.add_argument("filepath", help="通知対象の Markdown ファイル")
    parser.add_argument("--webhook-url", required=True, help="Slack Webhook URL")
    parser.add_argument("--github-url", default="（GitHub リンク未設定）", help="GitHub 上のファイルURL")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"ERROR: ファイルが見つかりません: {args.filepath}")
        sys.exit(1)

    with open(args.filepath, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data, body = parse_frontmatter(content)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    message = build_message(data, body, args.github_url)
    print("送信メッセージ：")
    print(message["text"])
    print("─" * 40)

    send_to_slack(args.webhook_url, message)
    print("Slack 通知を送信しました。")


if __name__ == "__main__":
    main()