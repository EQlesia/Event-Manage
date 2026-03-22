# Event Management System 仕様書（v2.1）

> v2.0 からの変更点：① id生成ルール明記 ② Actionsトリガー・権限明記
> ③ 時刻論理チェック追加 ④ location_type / url フィールド追加
> ⑤ Slack切り取りロジック明記 ⑥ public/private を将来拡張へ移動
> ⑦ ファイル命名衝突ルール追加 ⑧ Slice 0 採用方式明記

---

## 1. 概要

本システムは、ミーティング・外部説明会・飲み会・勉強会などのイベントを
**統一フォーマットで登録・通知・管理する仕組み**を提供する。

GitHub Pages + GitHub Actions + Slack連携を前提とし、
以下を満たすことを目的とする：

* フォーマットの強制（破綻防止）
* 自由記述による柔軟性
* 無料かつ安全な運用
* 拡張可能な設計

---

## 2. 設計方針

### 2.1 ハイブリッド構造

本システムは以下の2層構造を採用する：

* 構造データ（YAMLフロントマター）
* 自由記述（Markdown本文）

これにより、

* 機械処理の安定性
* 人間にとっての書きやすさ

を両立する。

---

### 2.2 責務分離

| レイヤ            | 役割              |
| -------------- | --------------- |
| YAML           | データ管理（壊してはいけない） |
| Markdown       | 表現（自由編集可能）      |
| GitHub Actions | バリデーション・通知      |
| Slack          | 通知ビュー           |

---

## 3. 投稿フォーマット仕様

### 3.1 全体構造

```md
---
id: auto
type: meeting | seminar | social | study
title: 
start_time: 
end_time: 
location: 
location_type: online | offline
url:           # オプション（オンライン開催時のURL等）
organizer: 
---

# {title}

## 概要
（自由記述）

## 詳細
（自由記述）

## 補足
（自由記述）
```

---

## 4. 必須項目（YAML）

### 4.1 定義

| フィールド         | 型        | 必須 | 説明                       |
| ------------- | -------- | -- | ------------------------ |
| id            | string   | ○  | 一意識別子（自動生成）              |
| type          | enum     | ○  | イベント種別                   |
| title         | string   | ○  | タイトル                     |
| start_time    | datetime | ○  | 開始日時（ISO 8601形式）         |
| end_time      | datetime | ○  | 終了日時（ISO 8601形式）         |
| location      | string   | ○  | 開催場所名                    |
| location_type | enum     | ○  | online / offline         |
| url           | string   | -  | 任意。オンライン会議URL等           |
| organizer     | string   | ○  | 主催者                      |

---

### 4.2 id 自動生成ルール ✅ NEW

形式：`YYYYMMDD-{type}-{NNN}`

例：`20260325-meeting-001`

* `YYYYMMDD`：start_time の日付部分
* `{type}`：イベント種別（meeting / seminar / social / study）
* `{NNN}`：同日・同typeのファイルが複数ある場合の3桁連番（001始まり）

生成タイミング：GitHub Actions のバリデーション時に `id: auto` を検出した場合、
上記ルールで採番しファイルを上書きする。

---

### 4.3 type 定義

```text
meeting  : ミーティング
seminar  : 外部説明会
social   : 飲み会
study    : 勉強会
```

---

## 5. Markdownテンプレート仕様

### 5.1 基本テンプレート

```md
# {{title}}

## 概要
このイベントは〜

## 詳細
- 内容：
- 持ち物：
- 事前準備：

## 補足
自由に記述してください
```

---

### 5.2 種別別拡張テンプレ

#### ミーティング

```md
## 議題
-
```

#### 外部説明会

```md
## 主催団体
-

## 対象
-
```

#### 飲み会

```md
## 店情報
- 予約名：
- 予算：
```

#### 勉強会

```md
## トピック
-

## 難易度
-
```

---

## 6. 処理フロー

```text
[ユーザー入力]
    ↓
[Markdownファイル作成 → events/ へ push or PR]
    ↓
[GitHub Actions（トリガー：push / pull_request）]
    ↓
[バリデーション（scripts/validate_event.py）]
    ↓（失敗時：CIエラー + PRコメント）
[id 自動採番（id: auto の場合）]
    ↓
[Slack通知]
```

---

## 7. Slack通知仕様

### 7.1 投稿フォーマット

```text
📅 {{title}}

■ 種別：{{type}}
■ 日時：{{start_time}} - {{end_time}}
■ 場所：{{location}}（{{location_type}}）

📝 概要：
{{## 概要 セクションの本文、先頭200文字}}

🔗 詳細：
GitHubリンク
```

---

### 7.2 概要テキスト抽出ルール ✅ NEW

1. Markdown本文から `## 概要` セクションを抽出する
2. セクション内のテキストを改行・空行を除去して結合する
3. 先頭200文字で切り捨て、超える場合は末尾に `…` を付加する
4. `## 概要` セクションが存在しない場合は `（概要なし）` と表示する

---

### 7.3 設計方針

* 本文は全文送信しない
* 要約のみ表示
* 詳細はリンク参照

---

## 8. バリデーション仕様

### 8.1 実行主体

GitHub Actions にて実施（`scripts/validate_event.py`）

---

### 8.2 Actionsトリガーと権限 ✅ NEW

```yaml
on:
  push:
    paths:
      - 'events/**/*.md'
  pull_request:
    paths:
      - 'events/**/*.md'

permissions:
  contents: write        # id 自動採番でファイルを上書きするため
  pull-requests: write   # PRへのコメントフィードバックのため
  issues: write          # Issueへのコメントフィードバックのため
```

---

### 8.3 チェック項目

* YAMLフロントマターの存在
* 必須項目の欠損チェック
* typeの値検証（meeting / seminar / social / study）
* location_typeの値検証（online / offline）
* datetime形式チェック（ISO 8601）
* **start_time < end_time の論理チェック** ✅ NEW
* Markdown構造の簡易検査（`## 概要` セクション存在確認）

---

### 8.4 エラー時挙動

* CI失敗
* PR / Issueコメントによるフィードバック（エラー内容を日本語で明示）

---

## 9. セキュリティ設計

* Slack WebhookはGitHub Secretsで管理（`SLACK_WEBHOOK_URL`）
* 入力値サニタイズ（YAML injection 対策）

> 📌 **public / private の公開範囲制御は将来拡張**（v3.0 以降）とする。
> 現バージョンではリポジトリの公開設定に依存する。

---

## 10. ストレージ設計

### 10.1 ファイル形式

* Markdown（.md）

### 10.2 保存構造・命名規則 ✅ NEW

```text
/events/
  └── {YYYY}/
        ├── {YYYYMMDD}-{type}-{NNN}.md
        └── ...
```

例：

```text
/events/
  └── 2026/
        ├── 20260325-meeting-001.md
        ├── 20260325-meeting-002.md   ← 同日同typeの2件目
        └── 20260326-seminar-001.md
```

**衝突回避ルール：** 同日・同typeのファイルが既に存在する場合、
GitHub Actions が連番を自動インクリメントして採番する。

---

## 11. 実装方式（Slice 0）✅ NEW

**Slice 0 はファイル管理ベース（11.2）を採用する。**

理由：
* GitHub Pages との連携が容易
* Git による変更履歴が自動で残る
* Issue テンプレは将来拡張（v2.x）として対応

---

## 12. スケーラビリティ

### 将来拡張案

* Google Calendar連携（ICS生成）
* 参加登録機能
* 承認フロー
* UI改善（イベント一覧ページ）
* public / private 公開範囲制御
* Issueベース入力対応

---

## 13. 最小構成（Slice 0）

### 機能

* イベント作成（ファイル管理ベース）
* YAMLバリデーション（全チェック項目）
* id 自動採番
* Slack通知

### 制約

* type は全4種対応（meeting / seminar / social / study）
* 拡張テンプレあり

---

## 14. 設計の本質

本システムは以下の構造を持つ：

* YAML = データ層
* Markdown = 表現層
* Slack = 通知ビュー

GitHubをCMSとして活用することで、
**軽量かつ強力なイベント管理基盤**を実現する。