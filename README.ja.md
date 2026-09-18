<div align="center">

<img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/docs/assets/cpap-sd-card-report-banner.jpg" alt="レスメド CPAP の SD カードデータから、設定変更で区切った残存イベント推移グラフを生成" width="880">

# resmed-sd-monitor

**レスメド CPAP / APAP の SD カードを治療モニタリングレポートに。**

[English](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/README.md) · [简体中文](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/README.zh.md) · **日本語**

[![CI](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/resmed-sd-monitor.svg)](https://pypi.org/project/resmed-sd-monitor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/pyproject.toml)
[![医療機器ではありません](https://img.shields.io/badge/%E2%9A%A0-%E5%8C%BB%E7%99%82%E6%A9%9F%E5%99%A8%E3%81%A7%E3%81%AF%E3%81%82%E3%82%8A%E3%81%BE%E3%81%9B%E3%82%93-red.svg)](#免責事項)

[クイックスタート](#クイックスタート) · [できること](#できること) · [OSCAR との関係](#他のツールとの関係) · [コマンド](#コマンド) · [出力の読み方](#出力の読み方) · [免責事項](#免責事項)

</div>

---

`resmed-sd-monitor` は、レスメドの AirSense 10 / AirSense 11 / AirCurve が
SD カードにもともと書き出している EDF ファイルを読み、睡眠専門医に渡せる
治療モニタリングレポートを生成します。処方変更ログで区切った効果推移、
1 呼吸ごとの気流解析、そして「これ以上昇圧する余地はあるか」への筋の通った答えです。

すべてローカルでオフラインに動作し、データはどこにも送信されません。

> **医療機器ではありません。** 装置が記録した推定値をスクリーニングの手がかりと
> 確認事項に変えるだけで、睡眠時無呼吸の診断、圧力設定の決定、睡眠専門医の代替は
> できません。全文は[免責事項](#免責事項)を参照してください。

## 仕組み

<img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/docs/assets/pipeline.svg" alt="パイプライン：SD カード → 解析 → 品質ゲート → 夜間サマリと波形層 → 昇圧余地の判定 → レポート保存" width="880">

## できること

### 自分の処方変更履歴で区切られた効果

設定を変えるたびに 1 行ずつ書き足す小さな `tuning_log.json` を用意します。レポートは
夜をセグメントに分け、Mann–Whitney + Hodges–Lehmann で比較します。`p ≥ 0.05` のときは
「差は検出されず、同等性も証明されていない」と表示し、「差がない」とは言いません。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/residual_rei.png" width="820" alt="夜ごとの残存イベント指数、5 晩移動中央値、セグメント帯と目標線"></p>

### 昇圧余地

APAP 調整で一番難しいのは「まだ昇圧する余地があるか」です。素朴な答えを誤らせる
交絡が 2 つあり、どちらも明示的に処理しています。

- **APAP はイベントに反応して昇圧する。** つまり「高圧帯でイベントが多かった」は
  フィードバックループのこだまであって、圧力が効いていない兆候ではありません。
  本ツールは圧力指標より先にフィードバック検証（イベント後の圧力変化とランダム時点
  対照の比較）を実行し、その結果を表示します。
- **Ramp 通過の低圧ビン。** 開始圧から治療圧への上昇は低圧帯に数百呼吸を残します。
  これを満負荷の高圧ビンと比べると、用量効果ではなく「Ramp 対 治療」を測ることに
  なるため、曝露 3 % 未満のビンは除外します。

残るのがクリーンな信号、すなわち圧力ビンをまたいだ背景の流量制限（吸気の平坦化）です。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/pressure_fi.png" width="760" alt="圧力と吸気平坦化指数、イベントのヒストグラムを重ねた図"></p>

### 1 呼吸ごとの波形層

25 Hz の気流チャネルから直接：呼吸ごとの吸気平坦化指数、イベントのクラスタリング
（体位性/REM の手がかり）、較正済みサインフィットによる周期性呼吸の検出、そして
イベントがいつ起きたかが一目で分かるタイムライン図。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/cluster_timeline.png" width="860" alt="イベントの時間分布図、クラスタ内イベントは赤"></p>

### 品質ゲート

治療記録が 2 時間未満の夜、チャネル欠損、Leak95 > 24 L/min の夜は除外し、その理由を
1 件ずつ表示します。SpO2 のカバー率が 70 % 未満なら T90 をでっち上げず「判定不能」と
します。各セクションには臨床側が必要とする注意書きが付きます。REI の分母は治療時間で
あること、EEG / 体位 / 呼吸努力のチャネルがないこと、装置のイベントはアルゴリズムに
よる推定であること。

<details>
<summary><b>レポート抜粋</b>（クリックで展開）</summary>

```text
## 4b. Flow waveform layer (per-breath, last 5 nights)
- Feedback check: within 120 s after 36 events, pressure changed by median
  +0.67 cmH2O (56% rose above 0.5, 0% fell below -0.5); across 150 random-time
  controls, median +0.03, 3% rose. The device does pressurize reactively to
  events, so any "high pressure <-> many events" co-occurrence is that
  feedback echoing back. It is not evidence that pressure is ineffective.
- Periodic-breathing fit: 1/5 nights reach the threshold (corr²>=0.1);
  dominant period 46 s. Periodic ventilatory instability needs manual waveform
  review. The device has no EEG/effort channels, so Cheyne-Stokes or TECSA
  cannot be declared from this.
- Pressure–flatness curve: therapy pressure range 11.0–13.5 cmH2O (5 bins,
  Ramp drive-by low bins excluded): FI median at 11.0 bin 0.087 → at 13.0 bin
  0.071; weighted slope -0.0087/cmH2O.
```

完全なサンプル：[examples/demo/sample_report/](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/examples/demo/sample_report/sample_report.md)

</details>

## クイックスタート

```bash
pip install "resmed-sd-monitor[charts]"
```

SD カードから `DATALOG` ディレクトリと `STR.edf` をコピーし（ezShare の無線 SD カード
アダプタでも可）、そのコピーに対して実行します。

```bash
resmed-sd-monitor --data-dir /path/to/sdcard-copy --report
```

カードが手元にない場合、リポジトリには決定論的な合成データ（10 晩）の生成器が
同梱されています。

```bash
git clone https://github.com/CaufieldZ/resmed-sd-monitor
python resmed-sd-monitor/examples/generate_demo_data.py /tmp/demo
resmed-sd-monitor --data-dir /tmp/demo --report
```

## 他のツールとの関係

| ツール | 何か | このツールとの違い |
| --- | --- | --- |
| [OSCAR](https://www.sleepfiles.com/OSCAR/) | オープンソース CPAP ビューアの事実上の標準。SleepyHead から派生。対話的なグラフで 1 呼吸まで拡大できる。 | OSCAR はデータを見せ、こちらはレポートを書きます。セグメント統計、表示される品質ゲート、昇圧余地の判定で、GUI はありません。併用が自然です。ある晩を OSCAR で眺め、書面の結論はこちらで出す。 |
| SleepHQ、CPAP Insights | ホスト型の Web サービス。カードの中身をアップロードするとダッシュボードと共有が得られる。 | ローカルでオフライン。アカウント登録もアップロードもサブスクリプションも不要。 |
| SleepyHead | OSCAR の前身。OSCAR が分岐して以降メンテナンスされていない。 | どちらにせよビューアの代替ではありません。 |

すでに OSCAR を使っているなら、ここにそれをやめろという話は一つもありません。

## コマンド

| コマンド | 得られるもの |
| --- | --- |
| `--report` | 完全なモニタリングレポート：品質ゲート、セグメント別推移＋統計、臨床確認の手がかり、波形層、グラフ（md ＋ json スナップショット＋ png を `<data-dir>/reports/` に保存） |
| `--wave [N]` | 直近 N 晩の波形詳細：平坦化指数、クラスタ、周期性呼吸、圧力—平坦化曲線、フィードバック検証 |
| `--pressure` | 記述的なイベント-圧力の関連（従来の粗い見方） |
| `<YYYYMMDD>` | 単一の晩の詳細：各イベント発生時の圧力付きイベント一覧 |
| `--settings` | `STR.edf` から解析した現在の処方 |
| *(引数なし)* | 全ての晩のサマリ表 |
| `--csv` | 同じ表を CSV（21 列）で出力 |
| `resmed-sd-monitor-maskoff` | マスク外しタイミングの監査：早期の取り外しがイベント由来かどうか |

オプション：`--data-dir`（または `$RSDM_DATA_DIR` / 旧 `$CPAP_DATA_DIR`）、`--lang en|zh|ja`。

## 出力の読み方

まず [docs/interpretation-guide.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/interpretation-guide.md) を読んでください。要点だけ：

| 問い | どこを見るか | 落とし穴 |
| --- | --- | --- |
| 治療は効いているか | 5 晩移動中央値、セグメント統計 | 単一の晩は 1–10 件/時で揺れるので、1 晩だけで読まない |
| もっと昇圧すべきか | 圧力—平坦化曲線、上限滞留時間 | 「高圧でイベントが多い」は APAP 自身のフィードバックのこだま |
| 体位性 / REM 関連か | イベントのクラスタ、発生時刻の分布 | 装置は体位も睡眠段階も記録しないので手がかりに留まる |
| 中枢性イベントの出現 | 昇圧 / EPR 変更後の CAI 推移 | 昇圧後の CAI 上昇は TECSA の警告であり、調整の細部ではない |
| マスクを早く外していないか | `resmed-sd-monitor-maskoff` | 短いセッション 1 回は耐容性の問題、断片化は覚醒由来 |

データ形式と癖（STR.edf の手動解析、EDF+ アノテーション、1 晩に複数セグメント）：
[docs/data-format.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/data-format.md)。
チューニングログの形式：[docs/tuning-log.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/tuning-log.md)。

## 言語

英語（基準）、簡体中文、日本語をリポジトリに同梱しています。出力・レポート・グラフの
ラベルは `--lang` またはロケール検出で切り替わります。日本語テーブルは機械翻訳を
ベースにしており、ネイティブによる確認を待っています。ロケールの追加は小さなファイル
1 つで済みます。[docs/translating.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/translating.md) を参照してください。

## インストール

Python ≥ 3.10。主要な依存：`numpy`、`scipy`、`edfio`。グラフ（matplotlib）は任意で、
なくてもレポートは画像なしで生成されます。

```bash
pip install resmed-sd-monitor            # コア
pip install "resmed-sd-monitor[charts]"  # + matplotlib
```

ソースから開発する場合：

```bash
git clone https://github.com/CaufieldZ/resmed-sd-monitor
cd resmed-sd-monitor
pip install -e .[dev]                    # + pytest（テストスイート 106 件）
```

## プロジェクト構成

```text
src/resmed_sd_monitor/
  monitor.py      解析エンジン＋ CLI（report / wave / pressure / detail / settings）
  maskoff.py      マスク外しタイミングの監査
  i18n/           en / zh / ja 文字列テーブル（＋整合性テスト）
examples/
  generate_demo_data.py   決定論的な合成データ生成器
  demo/sample_report/     コミット済みのサンプル出力（CI が鮮度を検査）
docs/             判読ガイド · データ形式 · チューニングログ · 翻訳
```

## コントリビュート

Issue と PR を歓迎します。特に、他のレスメド機種での実測、ロケールテーブル、EDF の
エッジケースに強いパーサ。医学的安全性に関わる文言の変更は慎重に扱います。出力中の
「非診断」の境界は意図的なもので、緩めることはありません。

```bash
pytest -q && ruff check src tests examples
```

## 免責事項

本ソフトウェアは情報提供および教育目的でのみ提供されます。**医療機器ではなく**、
いかなる規制当局の審査も受けていません。出力は診断でも、治療の推奨でも、処方でも
ありません。装置由来の指標（イベント指数、圧力、オキシメトリ）は既知の盲点（リーク、
覚醒、睡眠段階の欠如）を持つアルゴリズム推定値です。治療の判断には必ず睡眠専門医を
関与させてください。緊急時はただちに医療機関を受診してください。

ResMed、AirSense、AirCurve、AutoSet は ResMed Ltd. の商標です。本プロジェクトは独立
した非提携の個人プロジェクトであり、それらの装置がもともと SD カードに書き出している
データを読むだけです。

## ライセンス

[MIT](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/LICENSE)
