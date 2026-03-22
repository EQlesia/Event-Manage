# Event Management System

GitHub Pages + GitHub Actions + Slack によるイベント管理システムです。

---

## セットアップ

### 1. リポジトリの準備

```bash
git clone <your-repo-url>
cd event-system
```

### 2. Slack Webhook URL の設定

GitHub リポジトリの **Settings → Secrets and variables → Actions** で以下を追加：

| Secret名 | 値 |
|---|---|
| `SLACK_WEBHOOK_URL` | Slack の Incoming Webhook URL |

### 3. 動作確認

```bash
pip install pyyaml

# サンプルイベントでテスト
cp events/templates/meeting.md events/2026/20260325-meeting-test.md
# ファイルを編集してバリデーション実行
python scripts/validate_event.py events/2026/20260325-meeting-test.md
```

---

## イベント登録方法

### ① テンプレートをコピー

```bash
cp events/templates/{type}.md events/{YYYY}/{YYYYMMDD}-{type}-001.md
```

例：
```bash
cp events/templates/meeting.md events/2026/20260325-meeting-001.md
```

### ② ファイルを編集

```yaml
---
id: auto           ← そのままでOK（自動採番されます）
type: meeting
title: 週次定例ミーティング
start_time: 2026-03-25T14:00
end_time: 2026-03-25T15:00
location: 会議室A
location_type: offline
url:               ← オンラインの場合はURLを記入
organizer: 山田太郎
---
```

### ③ push または PR を作成

```bash
git add events/2026/20260325-meeting-001.md
git commit -m "feat: 週次定例ミーティングを追加"
git push
```

GitHub Actions が自動で：
1. バリデーションを実行
2. `id: auto` を採番済み id に書き換え
3. Slack に通知

---

## バリデーションルール

| チェック項目 | 内容 |
|---|---|
| 必須項目 | id, type, title, start_time, end_time, location, location_type, organizer |
| type の値 | meeting / seminar / social / study |
| location_type の値 | online / offline |
| 日時形式 | ISO 8601（例: `2026-03-25T14:00`） |
| 時刻論理 | end_time > start_time |
| Markdown構造 | `## 概要` セクションの存在（警告のみ） |

---

## ディレクトリ構成

```
event-system/
├── .github/
│   └── workflows/
│       └── event-validate.yml   # GitHub Actions ワークフロー
├── events/
│   ├── templates/               # 種別別テンプレート
│   │   ├── meeting.md
│   │   ├── seminar.md
│   │   ├── social.md
│   │   └── study.md
│   └── 2026/                    # 年別イベントファイル
├── scripts/
│   ├── validate_event.py        # バリデーション & id採番
│   └── notify_slack.py          # Slack通知
├── SPEC.md                      # 仕様書 v2.1
└── README.md
```

---

## Slack通知サンプル

```
📅 *週次定例ミーティング*

■ 種別：ミーティング
■ 日時：2026-03-25T14:00 - 2026-03-25T15:00
■ 場所：会議室A（offline）
■ 主催：山田太郎

📝 概要：
今週のタスク進捗確認と来週の計画についてすり合わせます。

🔗 詳細：https://github.com/.../events/2026/20260325-meeting-001.md
```