"""Chinese string table（简体）。占位符与 en.py 同名，可自由调整语序。"""

STRINGS = {
    # ── 质量门控原因 ──────────────────────────────────────────────────────
    'qr_short_use': '治疗记录<{h:g}h',
    'qr_no_eve': '缺少 EVE 事件文件',
    'qr_no_leak': '缺少 Leak 通道',
    'qr_high_leak': 'Leak95>{v:g}L/min',

    # ── 统计判定 ──────────────────────────────────────────────────────────
    'verdict_insufficient_n': '样本不足',
    'verdict_decrease': '观察到下降（探索性）',
    'verdict_increase': '观察到上升（探索性）',
    'verdict_no_clear_diff': '未检出明确差异，不能证明等效',

    # ── pressure_response ─────────────────────────────────────────────────
    'pr_insufficient': '描述性证据不足',
    'pr_insufficient_why': ('仅 {n} 个明确阻塞事件完成压力对齐（需至少 {min_events} 个、'
                            '{min_nights} 晚）；不据此解读调压方向'),
    'pr_cooccurrence': '仅见事件-压力共现，不能推断病因',
    'pr_ratio_tail': '；按暴露校正后高压/其余时段事件率比 {rr}',
    'pr_cooccurrence_why': ('{n} 个明确阻塞事件中 {pct}% 发生在各晚 P90 以上（该压力段占治疗记录 '
                            '{exposure}%）{ratio}。APAP 在事件后主动升压，高段停留天然由事件触发，'
                            '事件率高是升压反馈的回声，不能读作「压力无效」。缺少体位、睡眠分期与'
                            '人工波形复核，也不能判定体位/REM 相关或复杂性。'),

    # ── timing_verdict ────────────────────────────────────────────────────
    'timing_late_heavy': '治疗记录后段事件较多；可与症状、睡眠日志、体位/PSG 数据一并复核',
    'timing_uniform': '治疗记录内分布大致均匀；不能据此判断解剖或体位因素',
    'timing_uneven': '治疗记录内分布不均；缺少体位和睡眠分期，不能归因',

    # ── wave_verdict ──────────────────────────────────────────────────────
    'wv_fi_summary': '逐拍平坦指数中位 {med}（{n} 晚；这是与各晚自身基线比较的相对量，不做绝对判定）。',
    'wv_cluster': ('事件成簇：{nights} 晚共 {clusters} 簇（≥{min_ev} 个事件且相邻≤{gap_min} 分钟），'
                   '簇内事件占全部事件的中位 {pct}%。成簇是体位性/REM 相关 OSA 的经典线索，'
                   '但设备不记录体位与睡眠分期，不能据此归因。'),
    'wv_period_none': '周期性呼吸拟合：{n} 晚均未达门限',
    'wv_period_weak_tail': '（其中 {n} 晚为弱信号）',
    'wv_period_none_tail': '，波形层未见周期性通气不稳定。',
    'wv_period_flagged': ('周期性呼吸拟合：{flagged}/{total} 晚达到门限（corr²≥{corr2}），'
                          '主周期 {period}s，其中短周期（<40s）{n_short} 晚。周期化通气不稳定需'
                          '人工复核波形，设备无 EEG/胸腹努力，不能据此判 Cheyne-Stokes 或 TECSA。'),
    'wv_curve_base': ('压力—平坦曲线：治疗压区间 {t_lo}–{t_hi} cmH2O（{n_bins} 档，已剔除 Ramp 路过的'
                      '低压档）：{lo_p} 档 FI 中位 {lo_fi} → {hi_p} 档 {hi_fi}，加权斜率 {slope}/cmH2O。'),
    'wv_gain_txt': '最低三档 → 最高三档（跨 {span} cmH2O）FI 中位只差 {gain}',
    'wv_curve_negative': ('压力升高时受限拍反而增多（斜率为负）：多为 APAP 反应性升压的反向因果'
                          '（事件触发升压后仍处恢复期），不能读作「压力有害」。'),
    'wv_curve_gain_flat': ('{gain_txt}。从最低到最高压力几乎没有可赚的改善：背景受限在该区间已走平，'
                           '抬压（无论地板还是上限）预期收益有限。'),
    'wv_curve_ushape': ('{gain_txt}。曲线呈 **U 型**：最低点在约 {p_min} cmH2O，之后随压力回升'
                        '（最高档比最低点高 {rise}）。高段的回升是设备对气流受限的反应性升压'
                        '（回声），不能读作「压力有害」。它一路升到区间顶端，正是「还想要更多压力'
                        '但被上限挡住」的形态，与「压力—平坦」在这一段还没走完是同一件事。'),
    'wv_curve_plateau': ('{gain_txt}，但改善集中在低段，中段以上已走平（中段内再升 {tail_gain}）。'
                         '当前压力区间基本把能赚的赚完了，继续抬压边际递减。'),
    'wv_curve_responsive': ('{gain_txt}：背景气流受限随压力升高持续减少，气道在该区间对压力有反应。'
                            '注意它量的是**背景受限程度**，与残余事件是否被压住是两回事（见压力暴露一节）。'),
    'wv_event_press': '阻塞事件发生时压力中位 {med} cmH2O，≥14 cmH2O 的占比 {p14}%、≥15 cmH2O 的占比 {p15}%。',

    # ── pressure_exposure_verdict ─────────────────────────────────────────
    'pev_split': ('按实际送达压力切：低段（<{p90} cmH2O，P90）每 100 拍 {lo_rate} 个事件，'
                  '高段（≥{p90}）{hi_rate} 个（低段 {lo_br} 拍 / 高段 {hi_br} 拍）。⚠ 按上一条反馈检验，'
                  '该比率**不是**「压力有没有效」的证据，它只说明设备确实在高段工作。'),
    'pev_delivered': '实际送达压力中位 {med}、P90 {p90}、峰值 {mx} cmH2O；{frac}% 的吸气拍待在上限 0.5 以内。',
    'pev_not_binding': ('设备设定上限 {set_max} cmH2O，但实际从未超过 {press_max}。该段治疗里压力上限'
                        '不是限制因素，抬上限本身不改变任何送达压力；要改的是地板压（min）或模式/机制方向。'),
    'pev_binding': ('峰值触到设定上限 {set_max} cmH2O，且 {frac}% 的时间停在上限附近。上限在真实限制'
                    '治疗，存在被截断的可能，抬上限是有依据的一步。'),
    'pev_touch_only': ('峰值触到设定上限 {set_max} cmH2O，但只占 {frac}% 的时间（零星瞬时触及，非持续'
                       '停留）。上限偶有触碰但不构成限制，抬上限单独做预期收益很小。'),

    # ── 事件类型 / 图表标签 ───────────────────────────────────────────────
    'ev_oa': '阻塞', 'ev_ca': '中枢', 'ev_hyp': '低通气', 'ev_ua': '未分类暂停',
    'axis_press_cmh2o': '压力 cmH2O',
    'axis_press': '压力（cmH2O）',
    'axis_press95': '压力 95%（cmH2O）',
    'axis_fi': '吸气平坦指数',
    'axis_fi_limited': '吸气平坦指数（低 = 受限）',
    'axis_flowlim': '流量受限',
    'axis_hours_since_start': '治疗记录开始后小时',
    'axis_hours_since_first': '首段治疗开始后小时',
    'axis_insp_press': '吸气时压力（cmH2O）',
    'axis_event_count': '事件数',
    'axis_events_cumulative': '事件数（跨全部夜晚累计）',
    'axis_minutes': '累计时长（分钟）',
    'axis_oa_press': '阻塞事件发生时压力（cmH2O）',
    'axis_oai': 'OAI（阻塞次/小时）',
    'axis_rei': '设备残余事件指数（次/治疗小时）',
    'axis_spo2_min': '夜间最低 SpO₂（%）',
    'label_fi': '平坦指数',
    'legend_fi_med': '平坦指数中位',
    'legend_p25_med': 'p25~中位',
    'legend_median': '中位 {m}',
    'legend_rolling5': '5 晚滚动中位',
    'legend_target': '常用治疗目标 {v}/h',
    'legend_review': '建议复核线 {v}/h',
    'legend_spo2_90': 'SpO₂=90% 警戒线',
    'legend_spo2_94': 'SpO₂=94% 参考线',
    'chart_wp_title': '{date} 压力曲线 + 阻塞事件（红线）',
    'chart_wp_p10_legend': '当晚 p10 = {q10}（最受限的一成）',
    'chart_wp_fi_title': '逐拍吸气平坦指数（低 = 波形平台样 = 气流受限）',
    'chart_pf_title': '压力 vs 吸气平坦（{n} 拍）',
    'chart_pf_slope': '加权斜率 {slope}/cmH2O',
    'chart_pf_bias_note': '（APAP 下压力对事件反应性上调，非剂量—反应实验）',
    'chart_ct_title': ('事件时间分布（红 = 属于成簇；○ 阻塞 △ 中枢 □ 低通气 × 未分类）\n'
                       '横轴按事件主体裁切；后半夜偏重需结合睡眠起止判读，设备无睡眠分期'),
    'chart_at_title': 'PAP 治疗期残余事件趋势（非 PSG-AHI）',
    'chart_po_title': '压力95 vs 阻塞指数 OAI',
    'chart_po_subtitle': '（APAP 下压力随事件上调，正相关不代表压力致病，仅参考）',
    'chart_eh_title': '设备残余事件的治疗时段分布（无睡眠分期/体位信息）',
    'chart_ph_title': '当前设置各压力档累计时长',
    'chart_st_title': '夜间最低 SpO₂ 趋势（按调参分段）',
    'chart_st_note': '注：SpO₂ 取自设备 SAD 通道；无 SAD 信号的夜晚不画点',
    'chart_ep_title': '明确阻塞事件发生时的压力分布（描述性，非调压结论）',
    'chart_nd_title': '{date} 单晚：压力 + 阻塞事件（红线）',

    # ── cmd_wave ──────────────────────────────────────────────────────────
    'wave_no_nights': '没有可用夜晚：{root} 下没找到治疗记录',
    'wave_header': '=== 气流波形分析（逐拍，最近 {n} 个治疗日期）===',
    'wave_range': '日期范围 {d0} – {d1}',
    'wave_table_header': '日期            拍数    RR    VT中位  VT CV    FI中位   事件   簇    簇内%    周期s  corr²   叹息/h',
    'wave_table_row': ('{date:<10}{breaths:>6}{rr:>6}{tv:>8}{cv:>6}%{fi:>8}{ev:>5}'
                       '{cl:>4}{clpct:>6}%{per:>7}{c2:>7}{sigh:>7}'),
    'wave_row_skip': '{date:<10}{dash:>6}  （BRP 气流不足，跳过波形层）',
    'wave_verdict_header': '--- 判读要点 ---',
    'wave_feedback': ('· 反馈检验（先看这条，后面所有「压力↔事件」的比率都受它约束）：{n} 个事件后 '
                      '120 秒内压力中位 {med} cmH2O，{rise}% 上升、{fall}% 下降；随机时点对照 '
                      '{ctrl_med}/{ctrl_rise}%。'),
    'wave_feedback_confirmed': '设备确在按事件反应性升压，因此事件率比是回声，不能当压力无效的证据。',
    'wave_feedback_not_confirmed': '未见明显的事件后升压，事件率比可作较弱的旁证。',
    'wave_merge_climbing': ('· 合并：曲线底部在中间压力，右端仍在上爬（跨段差 {gain}）。更高的压力还有'
                            '可赚的空间，且低段已接近最优点，**该抬上限而不是抬地板**。'),
    'wave_merge_tail_binding': '且设备已长时间停在上限附近（上限在限制治疗）',
    'wave_merge_tail_not_binding': '但峰值尚未顶到上限',
    'wave_merge_disclaimer': '残余事件率受 APAP 反应性升压污染，不参与此判断。',
    'wave_merge_flat': ('· 合并：可用的干净证据只有「压力—平坦曲线」，它显示从低段到高段背景受限几乎'
                        '没有改善。当前压力区间已经把气流受限的底色压到位了。残余事件在高段仍出现，'
                        '更可能是体位/REM 相关的短暂塌陷：下一步查体位与发生时段，而不是继续抬上限。'
                        '（事件率比在这里不作证据，原因见反馈检验。）'),
    'wave_merge_responsive': ('· 合并：背景受限随压力单调改善（跨段差 {gain}），低段尚有可赚，抬地板压'
                              '值得一试，1~2 周后复评。残余事件率本身受 APAP 反应性升压污染，不参与此判断。'),

    # ── clinical_assessment ───────────────────────────────────────────────
    'assess_level_insufficient': '数据不足',
    'assess_summary_insufficient': '无满足质量门控的治疗记录，无法做趋势判读。',
    'assess_level_specialist': '建议睡眠专科复核',
    'assess_level_followup': '建议常规随访',
    'assess_level_near_target': '设备趋势接近常用治疗目标',
    'assess_finding_rei_name': '治疗期残余事件',
    'assess_finding_rei_text': '{n} 晚可分析记录的设备残余事件指数中位数 {med}/h（治疗使用时长作分母，非 PSG-AHI）。',
    'assess_finding_exposure_name': '治疗暴露',
    'assess_finding_exposure_text': '≥{h}h 的可分析夜占 {pct}%（{k}/{n}）。',
    'assess_action_rei_high': '残余事件反复偏高：请携带此报告、症状和设备原始波形咨询睡眠专科；勿仅凭本工具自行改处方。',
    'assess_action_rei_target': '残余事件未稳定低于常用治疗目标，建议结合嗜睡、觉醒、漏气和实际佩戴时间安排随访。',
    'assess_action_near_target': '设备趋势接近常用治疗目标；若仍有日间嗜睡、晨起头痛或明显觉醒，仍需临床评估其他睡眠/躯体原因。',
    'assess_finding_central_name': '中枢事件筛查',
    'assess_finding_central_high': 'CAI 中位数 {med}/h；{pct}% 夜晚 CAI≥{c}/h 且不低于 OAI。',
    'assess_finding_central_low': 'CAI 中位数 {med}/h；设备记录中未见持续达到 CAI≥{c}/h 且占优的筛查信号。',
    'assess_action_central': '中枢事件信号持续偏高/占优时，需由睡眠专科结合病史、药物和 PSG 评估；设备分类不能单独诊断 TECSA。',
    'assess_finding_spo2_name': '连续血氧',
    'assess_finding_spo2_text': '{n} 晚连续 SAD 的 T90 中位数 {t90}%、SpO₂<88% 时长中位数 {b88} 分钟。',
    'assess_action_spo2': '连续血氧显示低氧负担，建议尽快由临床人员复核；若伴呼吸困难、胸痛、意识异常或清醒低氧，请及时急诊。',
    'assess_finding_spo2_none': '没有可用于低氧时间计算的连续 SAD 血氧；T90 宁缺毋滥，不从稀疏样本估。',
    'assess_summary_normal': '基于质量门控后的设备治疗记录；不是睡眠呼吸暂停的正式诊断。',

    # ── matplotlib 提示 ───────────────────────────────────────────────────
    'msg_mpl_missing': '[提示] matplotlib 不可用，跳过图表：{err}',
    'msg_chart_fail': '[提示] 图 {tag} 失败：{err}',
    'msg_charts_saved': '[图表] {names}  （在 {dir}/）',
    'msg_chart_list': '[图表] {names}',
    'msg_report_saved': '[已归档] {md}\n[快照] {json}',
    'msg_night_chart': '[单晚图] {path}',
    'msg_night_chart_fail': '[提示] 单晚图失败：{err}',

    # ── cmd_settings ──────────────────────────────────────────────────────
    'settings_no_file': '没有 {path}：把 SD 卡里的 STR.edf 拷到数据目录后再查',
    'settings_header': '=== 设备处方参数（STR.edf 第 {day}/{total} 日记录）===',
    'settings_mode': '模式            {v}',
    'settings_range': '压力区间        {lo} – {hi} cmH2O',
    'settings_start': '起始压          {v} cmH2O',
    'settings_fixed': '定压            {v} cmH2O',
    'settings_epr': 'EPR 呼气释压     {onoff}  档位 {lvl}  类型 {eprtype}',
    'settings_ramp': 'Ramp 缓升        {onoff}  {n} 分钟',
    'settings_smartstart': 'SmartStart      {onoff}',
    'settings_mask': '面罩类型        {v}',
    'settings_humid': '湿化            {onoff}  档 {lvl}  加热管 {tube}  温度 {temp}°C',
    'mode_cpap': 'CPAP 定压', 'mode_apap': 'APAP 自动调压', 'mode_bilevel': 'VPAP/双水平',
    'mask_pillow': '枕式', 'mask_nasal': '鼻罩', 'mask_nasal2': '鼻罩', 'mask_full': '全脸罩',
    'epr_off': '关', 'epr_full': '全程', 'epr_ramp': '仅 Ramp',
    'onoff_off': '关', 'onoff_on': '开', 'onoff_auto': '开/自动',

    # ── cmd_report ────────────────────────────────────────────────────────
    'report_no_data': '没有数据：{root} 下没有可用夜晚（把 SD 卡 DATALOG 拷到数据目录后重跑）',
    'seg_all_label': '全部',
    'report_title': '# PAP 治疗监测报告（临床决策支持）  {ts}',
    'report_disclaimer': ('> 本报告基于 ResMed 的气流/压力算法事件和治疗使用时长，不是 PSG，也不构成'
                          '睡眠呼吸暂停、REM/体位相关 OSA 或 TECSA 的正式诊断；请由睡眠专科结合症状、'
                          '病史、原始波形和必要的 PSG/连续血氧复核。'),
    'report_device': '**设备** {device}（{mask}）',
    'report_current_settings': ('**记录的当前设置**（{label}，自 {since}）：压力 {pmin}–{pmax} cmH2O，'
                                'EPR {epr}（仅记录，不是本工具的处方建议）'),
    'report_s1_title': '\n## 1. 数据质量与适用范围',
    'report_s1_coverage': ('- 覆盖 {n} 个治疗日期（{d0}–{d1}），纳入趋势分析 {an} 晚（记录≥{h}h、'
                           '存在 EVE/Leak 且 Leak95≤{leak} L/min）。'),
    'report_s1_short': '- 治疗记录<{h}h 的夜晚 {k} 晚；这表示治疗暴露不足，不等同于睡眠时长或摘罩原因。',
    'report_s1_leak': '- Leak95 中位数 {v} L/min。{mx} L/min 是本地筛查线；大漏气可能降低设备事件估算的可靠性，而非证明事件真实不存在。',
    'report_s1_reasons': '- 未纳入趋势的原因：{items}',
    'report_s1_reason_item': '{reason} {n} 晚',
    'report_s1_scope': '- 无 EEG 睡眠分期、体位、胸腹努力和人工波形评分；设备 REI 的分母是治疗时间，不能直接套用 PSG-AHI 的诊断严重度分级。',
    'report_s2_title': '\n## 2. 当前段临床复核提示：{level}',
    'report_s2_actions_head': '**建议行动**',
    'report_s3_title': '\n## 3. 分段治疗趋势（按调参日志；探索性比较）',
    'report_s3_table_header': '| 段 | 记录设置 | 可分析/总 | 使用h均值 | 设备REI 中位[IQR] | OAI | CAI | UAI | 压力95 | FL95 |',
    'report_s3_comparison': ('**{la} → {lb}**：设备 REI 中位 {rei_a}→{rei_b}（探索性 p={p1}，{v1}）；'
                             'OAI {oai_a}→{oai_b}（p={p2}，{v2}）'),
    'report_s3_mwu_note': ('> Mann–Whitney 比较用于描述独立夜晚分布，未做多重比较校正，也不能控制体位、'
                           'REM、饮酒、鼻塞、疾病波动等混杂因素；统计差异不等于调参造成的临床获益。'),
    'report_s3_skip': '没有满足质量门控的治疗记录，跳过分段趋势与统计比较。',
    'report_s4_title': '\n## 4. 事件—压力关联（描述性，不生成调压结论）',
    'report_s4_meds': '- 明确阻塞事件发生压力中位数 {ev} cmH2O；治疗压力中位数 {th} cmH2O。',
    'report_s4_aligned': '- 已对齐的明确阻塞事件 {n} 个，其中 P90 以上 {m} 个（{pct}%）；P90 以上压力暴露占 {e}%。',
    'report_s4_ratio': ('- 高压段/其余时段的事件率比 {rr}（按压力采样点暴露校正）。**该比值不可读作'
                        '「加压无效」**，理由见下方结论与第 4b 节的反馈检验。'),
    'report_s4_spearman': '- 跨夜 Spearman ρ(压力95, OAI)={rho}（n={n}）；事件后升压在这里把因果方向反了过来，不能做因果解读。',
    'report_s4_verdict': '- **{v}**：{why}',
    'report_s4_timing': '- 治疗记录时段分布（{n} 个事件）：前 {t1}% / 中 {t2}% / 后 {t3}%；{v}',
    'report_s4b_title': '\n## 4b. 气流波形层（逐拍，最近 {n} 晚）',
    'report_s4b_preamble': ('> 由 BRP 25Hz 气流逐拍重建呼吸（吸气峰检测 + 吸气平坦指数）。平坦指数是'
                            '与各晚自身基线比的相对量，不是文献绝对阈值；设备气流不是 PSG 的鼻压信号，'
                            '无 EEG 觉醒、无体位、无胸腹努力，下列条目均为设备相对趋势线索。'),
    'report_s4b_feedback': ('- 反馈检验：{n} 个事件后 120 秒内压力中位变化 {med} cmH2O（{rise}% 上升超过 '
                            '0.5、{fall}% 下降超过 0.5）；同期随机时点 {ctrl_n} 个对照中位 {ctrl_med}、'
                            '上升占比 {ctrl_rise}%。设备确实按事件反应性升压，因此任何「压力高 ↔ 事件多」'
                            '的共现都是该反馈的回声，不能读作压力无效。'),
    'report_s4b_skip': '没有足够的 BRP 气流数据做逐拍重建，本节跳过。',
    'report_s5_title': '\n## 5. 通气、流量受限与氧合（监测指标）',
    'report_s5_flowlim': '- FlowLim95 {fl}、鼾声95 {snore}；可用于同一设备/设置下的趋势复核，不能单独诊断气道塌陷。',
    'report_s5_vent': '- 呼吸率中位 {rr} 次/分 · 潮气量中位 {tv} L · 分钟通气量中位 {mv} L/min。设备估算受漏气和清醒状态影响。',
    'report_s5_spo2': '- 夜间最低 SpO₂ 中位 {v}%（均值 {avg}%）{src}。连续 SAD 才用于第 2 节的低氧筛查；覆盖不足的夜晚剔除、不估算。',
    'report_s5_src': '（来源：{src}）',
    'report_s6_title': '\n## 6. 最近 7 个治疗日期',
    'report_s6_header': '| 日期 | 记录h | 设备REI | OAI | CAI | UAI | 压力95 | Leak95 | SpO₂最低 |',
    'report_s6_header_nospo2': '| 日期 | 记录h | 设备REI | OAI | CAI | UAI | 压力95 | Leak95 |',
    'report_charts_title': '## 图表',
    'report_handoff_title': '## 交接提示',
    'report_handoff_emergency': '- 若出现胸痛、明显呼吸困难、意识异常、清醒状态低氧等急症症状，请及时急诊；本报告不能作急诊分诊依据。',
    'report_handoff_medical': '- 参数变更属于医疗决定。请将报告、症状变化、用药/合并症和原始 SD 卡数据一并交给睡眠专科或处方团队复核。',

    # ── cmd_pressure ──────────────────────────────────────────────────────
    'pressure_no_data': '没有满足质量门控的治疗记录（需 ≥{h}h、有 EVE 和 Leak），无法做压力关联分析。',
    'pressure_header': '=== 事件-压力关联（描述性临床决策支持）===',
    'pressure_nights': '可分析夜数 {n}（≥{h}h 且漏气达标）',
    'pressure_meds': '阻塞事件中位发生压力   {ev} cmH2O   （治疗压力中位 {th}）',
    'pressure_above90': '发生在各晚压力90分位以上的阻塞占比   {pct}%',
    'pressure_spearman': '跨夜相关 Spearman ρ(压力95, OAI) = {rho}  (n={n})',
    'pressure_spearman_note': '  注：APAP 压力随事件上调，正相关不代表压力致病，此项仅参考',
    'pressure_exposure': '高压段治疗暴露占比           {pct}%',
    'pressure_ratio': '高压/其余时段事件率比        {v}',
    'pressure_verdict': '筛查结论：{v}',
    'pressure_why': '依据：{w}',
    'pressure_timing': '时段分布：前 {t1}% / 中 {t2}% / 后 {t3}% → {v}',

    # ── cmd_summary ───────────────────────────────────────────────────────
    'summary_header': '日期           时长h   REI   OAI   CAI    HI     压力中/95  FL95   漏气95    事件压力',
    'summary_avg_row': '均值        {usage:>5} {ahi:>5} {oai:>5} {cai:>5} {hi:>5}',
    'summary_legend': ('说明：设备 REI 是治疗时长分母的设备事件指数，不是 PSG-AHI 诊断分级；OAI 阻塞、'
                       'CAI 中枢、HI 低通气、UAI 未分类暂停；FL 流量受限；* 标记未通过质量门控的治疗'
                       '记录(<{h}h、缺通道或高漏气)'),

    # ── cmd_detail ────────────────────────────────────────────────────────
    'detail_no_dir': '没有 {path}',
    'detail_header': '=== {date}（单晚治疗记录）===',
    'detail_summary': '使用时长 {h} h   设备REI {rei}  （阻塞 {oa} 中枢 {ca} 低通气 {hyp} 未分类暂停 {ua}）',
    'detail_not_analyzable': '  [非可分析夜]',
    'detail_pressure': '压力 中位 {med} / 95% {p95} / 峰值 {mx} cmH2O',
    'detail_oa_press': '阻塞事件发生时压力 中位 {med}  高压占比 {pct}%',
    'detail_oa_press_none': '阻塞事件发生时压力：无',
    'detail_flowlim': '流量受限 中位 {fl_med} / 95% {fl95}   鼾声 95% {snore95}',
    'detail_vent': '呼吸率 {rr} 次/分  潮气量 {tv} L  分钟通气 {mv} L/min',
    'detail_leak': '漏气 中位 {med} / 95% {p95} L/min',
    'detail_thirds': '治疗记录内事件时段 前 {t1}% / 中 {t2}% / 后 {t3}%',
    'detail_spo2': 'SpO₂ 最低 {v} % / 均值 {avg} %{src}',
    'detail_src_tag': '（{src}）',
    'detail_event_list_head': '--- 事件清单（前 40 条，起始 / 时长 / 类型 / 发生时压力）---',
    'detail_event_more': '  ... 共 {n} 条',

    # ── maskoff ───────────────────────────────────────────────────────────
    'maskoff_header': '日期           时长h    结束时刻     最后事件距摘罩  末30分事件  类型  末段事件',
    'maskoff_counts': '分类计数: {counts}',
    'maskoff_end_dist': '结束时刻分布: 00:00-01:00 {early} 晚 / 01:00-03:30 {mid} 晚 / 03:30+ {late} 晚',
}
