# specs/ — SDD 成果物

機能ごとに1フォルダ。**`specs/NNNN-kebab-name/`**（4桁連番＋ケバブ。discover が採番）。

## 各フォルダの成果物と段階

| ファイル | 段階 | 作る人（委譲先） |
|---|---|---|
| `discovery.md` | 0. discover | product/quality/solution-analyst（進行役が統合） |
| `requirements.md`（EARS）＋ `acceptance.feature`（Gherkin） | 1. specify | scenario-author |
| `design.md` | 2. plan | solution-analyst |
| `tasks.md` | 3. tasks | solution-analyst |

## Status フロー（人間ゲート）

各文書は先頭に `Status: Draft` を持ち、**人間の承認で `Approved`** になる。次段は前段が Approved になるまで着手できない。

```
discovery.md ──Approved──▶ requirements.md + acceptance.feature ──Approved──▶ design.md ──Approved──▶ tasks.md ──Approved──▶ implement
```

- **順序と凍結はフックが決定論的に強制する**（`.claude/hooks/guard_sdd_gates.py`）:
  - 前段が `Approved` でなければ次段の成果物は書けない
  - `Approved` の文書（discovery / requirements / design）は編集不可。変更するには **Status を Draft に戻して再承認**（Status 行を触る編集だけ許可される）
  - `acceptance.feature` は requirements.md の Status に従って凍結（仕様変更は specify 経由）
  - `tasks.md` は実装中の追記がありうるため凍結しない（順序ゲートのみ）
- 承認の**主体**（人間であること）はフックでは判定できない。人間ゲートはプロセス規律として守る。

## 記法

要件は EARS、受け入れ基準は Gherkin（キーワード英語・本文日本語）。詳細は `.claude/skills/specify/` と `.claude/skills/bdd/`。
