<div align="center">

<img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/docs/assets/cpap-sd-card-report-banner.jpg" alt="瑞思迈 CPAP SD 卡数据生成按调参分段的每晚残余事件趋势图" width="880">

# resmed-sd-monitor

**把瑞思迈 CPAP / APAP 的 SD 卡变成一份治疗监测报告。**

[English](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/README.md) · **简体中文** · [日本語](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/README.ja.md)

[![CI](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/resmed-sd-monitor.svg)](https://pypi.org/project/resmed-sd-monitor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/pyproject.toml)
[![非医疗器械](https://img.shields.io/badge/%E2%9A%A0-%E9%9D%9E%E5%8C%BB%E7%96%97%E5%99%A8%E6%A2%B0-red.svg)](#免责声明)

[快速上手](#快速上手) · [它做什么](#它做什么) · [和 OSCAR 的关系](#和其他工具的关系) · [命令](#命令) · [怎么读结果](#怎么读结果) · [免责声明](#免责声明)

</div>

---

`resmed-sd-monitor` 读取瑞思迈 AirSense 10、AirSense 11 或 AirCurve 呼吸机本来就写在 SD 卡里的 EDF 文件，产出一份可以拿给睡眠科医生看的治疗监测报告：按你自己的调参日志分段的疗效趋势、逐拍气流分析，以及「再加压有没有用」这个问题的完整推演。

全程本地运行、离线，数据不上传到任何地方。

> **不是医疗器械。** 它把机器记录的估算值转成筛查线索与复核提示，不能诊断睡眠呼吸暂停、不能决定你的处方压力、不能替代睡眠科医生。完整声明见[文末](#免责声明)。

## 工作原理

<img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/docs/assets/pipeline.svg" alt="管线图：SD 卡 → 解析 → 质量门控 → 每晚汇总与波形层 → 加压空间判读 → 归档报告" width="880">

## 它做什么

### 疗效按你自己的调参史分段

维护一个小小的 `tuning_log.json`，每次改设置记一条。每份报告把夜晚切成段，用 Mann–Whitney + Hodges–Lehmann 做统计比较。`p ≥ 0.05` 时打印的是「未检出明确差异，不能证明等效」，而不是「没有差异」。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/residual_rei.png" width="820" alt="每晚残余事件指数、5 晚滚动中位、分段色带与目标线"></p>

### 加压空间

APAP 调参里最难的问题是「还有没有加压空间」。有两个混淆会让幼稚的答案出错，这里都做了显式处理：

- **APAP 是「对事件作出反应」才升压的。** 所以「事件大多发生在高压段」是反馈回路的回声，不是压力无效的迹象。工具在任何压力指标之前先跑反馈检验（事件后压力变化 vs 随机时点对照），并把结果打出来。
- **Ramp 路过的低压档。** 从起始压爬升到治疗压会在低压档留下几百拍。拿它们跟满负荷的高压档比，量到的是「爬坡 vs 治疗」而不是剂量效应，所以暴露不足 3% 的压力档直接剔除。

剩下的才是干净信号：跨压力档的背景气流受限（吸气平坦指数）。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/pressure_fi.png" width="760" alt="压力 vs 吸气平坦指数，叠加事件压力分布"></p>

### 逐拍气流波形层

直接从 25 Hz 气流通道重建：每一拍的吸气平坦指数、事件成簇（体位性/REM 线索）、用合成信号标定过的正弦拟合周期性呼吸检测，以及一眼看出事件发生在什么时候的时间轴图。

<p align="center"><img src="https://raw.githubusercontent.com/CaufieldZ/resmed-sd-monitor/main/examples/demo/sample_report/cluster_timeline.png" width="860" alt="事件时间分布图，成簇事件标红"></p>

### 质量门控

治疗记录不足 2 小时、缺通道、Leak95 > 24 L/min 的夜晚会被剔除，原因逐条打印。血氧覆盖率不足 70% 时给出「不可判定」，而不是编一个 T90 出来。报告的每一节都带着临床医生需要的告诫：REI 的分母是治疗时长、没有 EEG / 体位 / 胸腹努力通道、设备事件是算法估算。

<details>
<summary><b>报告样张段落</b>（点击展开）</summary>

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

完整样张：[examples/demo/sample_report/](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/examples/demo/sample_report/sample_report.md)

</details>

## 快速上手

```bash
pip install "resmed-sd-monitor[charts]"
```

把 SD 卡里的 `DATALOG` 目录和 `STR.edf` 拷出来（用 ezShare 无线 SD 卡适配器也行），然后对着副本跑：

```bash
resmed-sd-monitor --data-dir /path/to/sdcard-copy --report
```

手边没有卡？仓库自带一个确定性合成数据（10 晚）的生成器：

```bash
git clone https://github.com/CaufieldZ/resmed-sd-monitor
python resmed-sd-monitor/examples/generate_demo_data.py /tmp/demo
resmed-sd-monitor --data-dir /tmp/demo --report
```

## 和其他工具的关系

| 工具 | 是什么 | 这个有什么不同 |
| --- | --- | --- |
| [OSCAR](https://www.sleepfiles.com/OSCAR/) | 开源 CPAP 数据查看器的事实标准，从 SleepyHead 衍生而来。交互式图表，能放大到单次呼吸。 | OSCAR 把数据摆给你看，这个写报告：分段统计、打印出来的质量门控、加压空间判读，没有图形界面。两者可以配合：在 OSCAR 里翻某一晚的波形，用这个出书面结论。 |
| SleepHQ、CPAP Insights | 托管的 Web 服务，上传卡里的数据，给你仪表盘和分享链接。 | 本地离线，不用注册、不用上传、不用订阅。 |
| SleepyHead | OSCAR 的前身，自 OSCAR 从它分叉后已停止维护。 | 两边都不是查看器的替代品。 |

已经在用 OSCAR 的话，这里没有任何一条要你换掉它。

## 命令

| 命令 | 得到什么 |
| --- | --- |
| `--report` | 完整监测报告：质量门控、分段趋势 + 统计、临床复核提示、波形层、图表（md + json 快照 + png，归档到 `<data-dir>/reports/`） |
| `--wave [N]` | 最近 N 晚的波形深挖：平坦指数、成簇、周期性呼吸、压力—平坦曲线、反馈检验 |
| `--pressure` | 描述性的事件-压力关联（旧口径，较粗） |
| `<YYYYMMDD>` | 单晚明细：事件清单，带每个事件发生时的压力 |
| `--settings` | 从 `STR.edf` 解析当前处方 |
| *（无参数）* | 全部夜晚汇总表 |
| `--csv` | 同一张表导 CSV（21 列），接 Excel |
| `resmed-sd-monitor-maskoff` | 摘罩时机审计：早摘是事件驱动的还是别的原因 |

选项：`--data-dir`（或 `$RSDM_DATA_DIR` / 旧版 `$CPAP_DATA_DIR`）、`--lang en|zh|ja`。

## 怎么读结果

先读 [docs/interpretation-guide.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/interpretation-guide.md)，简版：

| 问题 | 去哪看 | 陷阱 |
| --- | --- | --- |
| 治疗有没有效？ | 5 晚滚动中位、分段统计 | 单晚波动 1–10 次/小时，永远别只看一晚 |
| 再加压有没有用？ | 压力—平坦曲线；上限停留时长 | 「高压段事件多」是 APAP 自己的反馈在回声 |
| 体位性 / REM 相关？ | 事件成簇；事件的时间分布 | 设备不记录体位、不记录睡眠分期，这些只是线索 |
| 有没有中枢事件抬头？ | 加压 / 改 EPR 后的 CAI 趋势 | 加压后 CAI 上升是 TECSA 警示，不是调参细节 |
| 面罩是不是早摘了？ | `resmed-sd-monitor-maskoff` | 单个短 session 是耐受问题，碎片化是憋醒导致 |

数据格式与各种坑（STR.edf 手工解析、EDF+ 注释、一晚多段治疗）：[docs/data-format.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/data-format.md)。
调参日志格式：[docs/tuning-log.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/tuning-log.md)。

## 语言

英文（基准）、简体中文与日本語随仓库附带，输出、报告与图表标签都能通过 `--lang` 或系统 locale 切换。日文表为机器辅助翻译，待母语者校对。想加其他语言只需一个小文件，见 [docs/translating.md](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/docs/translating.md)。

## 安装

需要 Python ≥ 3.10。核心依赖：`numpy`、`scipy`、`edfio`。图表（matplotlib）是可选的，没有它报告照常生成，只是没有图。

```bash
pip install resmed-sd-monitor            # 核心
pip install "resmed-sd-monitor[charts]"  # + matplotlib
```

从源码开发：

```bash
git clone https://github.com/CaufieldZ/resmed-sd-monitor
cd resmed-sd-monitor
pip install -e .[dev]                    # + pytest，跑测试套件（106 个测试）
```

## 项目结构

```text
src/resmed_sd_monitor/
  monitor.py      分析引擎 + CLI（report / wave / pressure / detail / settings）
  maskoff.py      摘罩时机审计
  i18n/           en / zh / ja 字符串表（含一致性测试）
examples/
  generate_demo_data.py   确定性合成数据生成器
  demo/sample_report/     已提交的样张输出（CI 校验其新鲜度）
docs/             判读指南 · 数据格式 · 调参日志 · 翻译指南
```

## 参与贡献

欢迎 issue 与 PR，尤其欢迎：更多瑞思迈机型实测、语言表、更严格的 EDF 边界情况解析。涉及医学安全措辞的改动会被认真对待，输出里那些「非诊断」的边界是刻意的，不会放宽。

```bash
pytest -q && ruff check src tests examples
```

## 免责声明

本软件仅供信息与教育用途。它**不是医疗器械**，未经任何监管机构审查。它的输出不是诊断、不是治疗建议、不是处方。设备导出的指标（事件指数、压力、血氧）都是算法估算，有已知盲区（漏气、清醒状态、缺少睡眠分期）。治疗决策请务必咨询有资质的睡眠专科医生。紧急情况请立即就医。

ResMed、AirSense、AirCurve、AutoSet 是 ResMed Ltd. 的商标。这是一个独立的、无关联的个人项目，只读取那些机器本来就会写到 SD 卡上的数据。

## 许可

[MIT](https://github.com/CaufieldZ/resmed-sd-monitor/blob/main/LICENSE)
