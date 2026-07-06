/** 依存方向の機械強制（backend の import-linter に相当・ハーネス層③）。
 *  ルールの正本: frontend-architecture スキル（lib は純粋 / api 集約 / Smart=pages のみフック / canvas 分離）。
 *  実行: npm run arch:check（pre-commit / CI / spec-compliance レビュアーが回す）。
 *  型だけの import（import type）はコンパイル時に消えるため対象外（既定 tsPreCompilationDeps: false）。
 */
module.exports = {
  forbidden: [
    {
      name: "no-circular",
      severity: "error",
      comment: "循環依存の禁止",
      from: {},
      to: { circular: true },
    },
    {
      name: "lib-stays-pure",
      severity: "error",
      comment: "lib/ は FW 非依存の純粋ロジック層。UI・データ取得・描画層へ依存しない",
      from: { path: "^src/lib" },
      to: { path: "^src/(components|api|canvas)" },
    },
    {
      name: "only-pages-import-api",
      severity: "error",
      comment:
        "サーバ状態フック（api/）を呼べるのは Smart（components/pages）のみ — Smart/Dumb 分離",
      from: { path: "^src/components", pathNot: "^src/components/pages" },
      to: { path: "^src/api" },
    },
    {
      name: "canvas-independent-of-ui-and-api",
      severity: "error",
      comment:
        "canvas/（命令的描画）は React UI・データ取得へ依存しない（橋渡しは Smart 側で行う）",
      from: { path: "^src/canvas" },
      to: { path: "^src/(components|api)" },
    },
    {
      name: "api-is-not-ui",
      severity: "error",
      comment: "api/ はデータ層。UI・描画層へ依存しない",
      from: { path: "^src/api" },
      to: { path: "^src/(components|canvas)" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
    exclude: { path: "\\.d\\.ts$" },
  },
};
