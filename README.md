# Event Management System

GitHub Pages のフォームから入力 → GitHub Issue 作成 → Slack 通知まで自動で行うイベント管理システムです。

---

## アーキテクチャ

```
GitHub Pages（ブラウザ）
  └─ フォーム送信
       │  Fine-Grained PAT（issues: write のみ）
       ↓
GitHub Issues API
       ↓ issues: opened トリガー
GitHub Actions
       │  SLACK_WEBHOOK_URL（GitHub Secrets に保管）
       ↓
Slack
```

**セキュリティモデル**
- Slack Webhook URL は GitHub Secrets にのみ存在 → HTML 上に一切現れない
- ブラウザに埋め込む PAT は `issues: write` のみ → 漏れても「issueスパム」どまり

---

## セットアップ手順

### 1. リポジトリを作成して push

```bash
git init && git add . && git commit -m "initial commit"
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

### 2. `event-registration` ラベルを作成

**Issues → Labels → New label** で `event-registration` ラベルを作成する。

### 3. Fine-Grained PAT を作成（最小権限）

1. https://github.com/settings/personal-access-tokens/new を開く
2. **Repository access** → このリポジトリのみ
3. **Permissions → Issues → Read and Write** のみ ON（他はすべて No access）
4. トークンをコピー

### 4. Slack Webhook URL を GitHub Secrets に登録

**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/...` |

### 5. `index.html` の CONFIG を書き換え

```js
const CONFIG = {
  owner: "your-username",
  repo:  "event-system",
  pat:   "github_pat_xxxxxxxxxx"
};
```

### 6. GitHub Pages を有効化

**Settings → Pages → Source**: `main` / `/ (root)`

---

## よくある問題

| 症状 | 対処 |
|------|------|
| `401 Unauthorized` | PAT の権限・有効期限を確認 |
| `404 Not Found` | CONFIG の owner / repo を確認 |
| `422 Unprocessable` | `event-registration` ラベルが未作成 |
| Slack に届かない | Secrets の SLACK_WEBHOOK_URL を確認 |
| Actions が動かない | Actions タブで workflow を Enable |
