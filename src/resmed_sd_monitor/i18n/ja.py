"""Japanese string table（日本語）。機械翻訳ベースのため母語話者のレビューを歓迎：
docs/translating.md を参照。"""

STRINGS = {
    # ── 品質ゲート理由 ────────────────────────────────────────────────────
    'qr_short_use': '治療記録<{h:g}時間',
    'qr_no_eve': 'EVE イベントファイルなし',
    'qr_no_leak': 'Leak チャネルなし',
    'qr_high_leak': 'Leak95 > {v:g} L/min',

    # ── 統計判定 ──────────────────────────────────────────────────────────
    'verdict_insufficient_n': 'サンプル不足',
    'verdict_decrease': '低下が観察された（探索的）',
    'verdict_increase': '上昇が観察された（探索的）',
    'verdict_no_clear_diff': '明確な差は検出されず、等価性も証明されない',

    # ── pressure_response ─────────────────────────────────────────────────
    'pr_insufficient': '記述的証拠は不十分',
    'pr_insufficient_why': ('圧力整列できた明確な閉塞イベントは {n} 件のみ（{min_events} 件・'
                            '{min_nights} 晩以上が必要）。ここから圧力調整の方向は読み取らない'),
    'pr_cooccurrence': 'イベントと圧力の共起のみ。病因は推定できない',
    'pr_ratio_tail': '。曝露補正後の高圧/その他帯のイベント率比 {rr}',
    'pr_cooccurrence_why': ('明確な閉塞イベント {n} 件のうち {pct}% は各晩の P90 以上で発生'
                            '（この圧力帯は治療記録の {exposure}% を占める）{ratio}。APAP はイベント後に'
                            '反応的に昇圧するため、高圧帯への滞留は本来イベントが引き起こす。高い'
                            'イベント率はこのフィードバックのこだまであり、「圧力が効いていない」では'
                            'ない。体位・睡眠段階・手動波形確認がない以上、体位/REM 関連や複雑性の'
                            '判定もできない。'),

    # ── timing_verdict ────────────────────────────────────────────────────
    'timing_late_heavy': '治療記録の後半にイベントが多い。症状・睡眠日誌・体位/PSG データと併せて要確認',
    'timing_uniform': '治療記録内の分布はほぼ均一。解剖学・体位要因の結論は出せない',
    'timing_uneven': '治療記録内で分布が不均一。体位と睡眠段階がないため帰属はできない',

    # ── wave_verdict ──────────────────────────────────────────────────────
    'wv_fi_summary': ('1 呼吸ごとの平坦化指数の中央値 {med}（{n} 晩。各晩自身のベースラインとの'
                      '相対値であり、絶対判定ではない）。'),
    'wv_cluster': ('イベント クラスタリング：{nights} 晩で {clusters} クラスタ（≥{min_ev} 件・隣接間隔'
                   '≤{gap_min} 分）。全イベントに占めるクラスタ内の割合の中央値は {pct}%。クラスタは'
                   '体位性/REM 関連 OSA の典型的な手がかりだが、装置は体位も睡眠段階も記録しないため、'
                   'これだけで帰属してはいけない。'),
    'wv_period_none': '周期性呼吸フィッティング：{n} 晩すべてが閾値未満',
    'wv_period_weak_tail': '（うち {n} 晩は弱信号）',
    'wv_period_none_tail': '。波形層に周期性換気不安定は見られない。',
    'wv_period_flagged': ('周期性呼吸フィッティング：{flagged}/{total} 晩が閾値到達（corr²≥{corr2}）。'
                          '主要周期 {period} 秒、うち短周期（<40 秒）は {n_short} 晩。周期性換気不安定は'
                          '手動での波形確認が必要。装置に EEG/努力チャネルはなく、Cheyne-Stokes や '
                          'TECSA の判定はここからはできない。'),
    'wv_curve_base': ('圧力—平坦化曲線：治療圧レンジ {t_lo}–{t_hi} cmH2O（{n_bins} ビン、Ramp 通過の'
                      '低圧ビンは除外）。{lo_p} ビンの FI 中央値 {lo_fi} → {hi_p} ビン {hi_fi}、'
                      '重み付き傾き {slope}/cmH2O。'),
    'wv_gain_txt': '最下位 3 ビン → 最上位 3 ビン（{span} cmH2O にわたり）の FI 中央値の差はわずか {gain}',
    'wv_curve_negative': ('圧力が上がると制限呼吸がむしろ増える（傾き負）。多くは APAP 反応性昇圧の'
                          '逆因果（イベントが上昇を引き起こし、その呼吸はまだ回復途中）。「圧力が有害」'
                          'とは読まないこと。'),
    'wv_curve_gain_flat': ('{gain_txt}。最低圧から最高圧まで稼げる改善はほぼない。このレンジでは背景'
                           '制限はすでに平坦化しており、さらなる昇圧（下限・上限とも）の期待効果は限定的。'),
    'wv_curve_ushape': ('{gain_txt}。曲線は **U 字型**：約 {p_min} cmH2O が最低で、以後圧力とともに再上昇'
                        '（最上位ビンは最低点より {rise} 上）。高圧側の回復は流量制限への反応的な昇圧'
                        '（こだま）であり「圧力が有害」ではない。そして区間の上限まで昇り続けているのは'
                        '「さらに圧力を欲しているが上限に阻まれている」形であり、「圧力—平坦化曲線がこの区間で'
                        'まだ伸びきっていない」ことと同じ事実。'),
    'wv_curve_plateau': ('{gain_txt}。ただし改善は低圧側に集中し、中域以上は平坦化（中域内の再上昇 '
                         '{tail_gain}）。現在の圧力レンジはほぼ稼げる分を稼ぎ終えており、さらなる昇圧は'
                         '収穫逓減。'),
    'wv_curve_responsive': ('{gain_txt}：背景の流量制限は圧力上昇とともに減少し続けており、気道はこの'
                            'レンジで圧力に反応している。ただしこれは**背景制限の程度**であって、残存'
                            'イベントが抑えられたかとは別物（圧力曝露の節を参照）。'),
    'wv_event_press': ('閉塞イベント発生時の圧力：中央値 {med} cmH2O。≥14 cmH2O の割合 {p14}%、'
                       '≥15 cmH2O の割合 {p15}%。'),

    # ── pressure_exposure_verdict ─────────────────────────────────────────
    'pev_split': ('実際の送達圧で分割：低圧帯（<{p90} cmH2O、P90）は 100 呼吸あたり {lo_rate} 件、'
                  '高圧帯（≥{p90}）は {hi_rate} 件（低圧 {lo_br} 呼吸 / 高圧 {hi_br} 呼吸）。⚠ 上のフィード'
                  'バック検証のとおり、この比は「圧力が効くか」の証拠では**ない**。装置が確かに'
                  '高圧帯で動作していることだけを示す。'),
    'pev_delivered': ('送達圧：中央値 {med}、P90 {p90}、ピーク {mx} cmH2O。吸気呼吸の {frac}% が上限の'
                      '0.5 以内に滞留。'),
    'pev_not_binding': ('設定上限 {set_max} cmH2O を実際には一度も超えていない（実測ピーク {press_max}）。'
                        'この治療では上限は制約要因ではない。上限を上げても送達圧は一切変わらない。'
                        '変えるべきは下限（min）かモード/メカニズムの方向。'),
    'pev_binding': ('ピークが設定上限 {set_max} cmH2O に達し、{frac}% の時間そこに滞留。上限が実際に'
                    '治療を制限している。上限を上げることは根拠のある一歩。'),
    'pev_touch_only': ('ピークは設定上限 {set_max} cmH2O に触れるが、時間にして {frac}% のみ（散発的な'
                       '瞬間的接触で持続滞留ではない）。上限に触れることは制約ではなく、上限だけを'
                       '上げる効果は小さい。'),

    # ── イベント型 / チャートラベル ──────────────────────────────────────
    'ev_oa': '閉塞性', 'ev_ca': '中枢性', 'ev_hyp': '低換気', 'ev_ua': '分類不能の無呼吸',
    'axis_press_cmh2o': '圧力 cmH2O',
    'axis_press': '圧力（cmH2O）',
    'axis_press95': '圧力 P95（cmH2O）',
    'axis_fi': '吸気平坦化指数',
    'axis_fi_limited': '吸気平坦化指数（低い＝制限）',
    'axis_flowlim': '流量制限',
    'axis_hours_since_start': '治療記録開始からの経過時間（時間）',
    'axis_hours_since_first': '最初の治療セグメント開始からの時間（時間）',
    'axis_insp_press': '吸気時圧力（cmH2O）',
    'axis_event_count': 'イベント数',
    'axis_events_cumulative': 'イベント数（全晩合算）',
    'axis_minutes': '累積時間（分）',
    'axis_oa_press': '閉塞イベント発生時の圧力（cmH2O）',
    'axis_oai': 'OAI（閉塞イベント/時）',
    'axis_rei': '装置の残存イベント指数（イベント/治療時間）',
    'axis_spo2_min': '夜間最低 SpO2（%）',
    'label_fi': '平坦化指数',
    'legend_fi_med': 'FI 中央値',
    'legend_p25_med': 'P25〜中央値',
    'legend_median': '中央値 {m}',
    'legend_rolling5': '5 晩移動中央値',
    'legend_target': '一般的治疗目標 {v}/時',
    'legend_review': '要確認ライン {v}/時',
    'legend_spo2_90': 'SpO2=90% 警戒ライン',
    'legend_spo2_94': 'SpO2=94% 参考ライン',
    'chart_wp_title': '{date} 圧力曲線＋閉塞イベント（赤線）',
    'chart_wp_p10_legend': '当晩 p10 = {q10}（最も制限された 1 割）',
    'chart_wp_fi_title': '1 呼吸ごとの吸気平坦化指数（低い＝平坦な波形＝流量制限）',
    'chart_pf_title': '圧力 vs 吸気平坦化（{n} 呼吸）',
    'chart_pf_slope': '重み付き傾き {slope}/cmH2O',
    'chart_pf_bias_note': '（APAP 下では圧力はイベントに反応して上がる。用量反応実験ではない）',
    'chart_ct_title': ('イベントの時間分布（赤＝クラスタ内。○ 閉塞 △ 中枢 □ 低換気 × 分類不能）\n'
                       '横軸はイベント本体で切り詰め。深夜への偏りは睡眠の開始終了と併せて判読。'
                       '装置に睡眠段階はない'),
    'chart_at_title': 'PAP 治療中の残存イベント推移（PSG-AHI ではない）',
    'chart_po_title': '圧力 P95 vs 閉塞指数 OAI',
    'chart_po_subtitle': '（APAP 下では圧力はイベントとともに上昇。正の相関＝圧力が原因ではない。参考値）',
    'chart_eh_title': '装置残存イベントの治療時間帯分布（睡眠段階・体位なし）',
    'chart_ph_title': '現在の設定での圧力帯別累積滞留時間',
    'chart_st_title': '夜間最低 SpO2 推移（調整セグメント別）',
    'chart_st_note': '注：SpO2 は装置の SAD チャネルから。SAD 信号のない晩はプロットされない',
    'chart_ep_title': '明確な閉塞イベント発生時の圧力分布（記述的。圧力結論ではない）',
    'chart_nd_title': '{date} 単晩：圧力＋閉塞イベント（赤線）',

    # ── cmd_wave ──────────────────────────────────────────────────────────
    'wave_no_nights': '使える晩がない：{root} に治療記録が見つからない',
    'wave_header': '=== 気流波形分析（1 呼吸ごと、直近 {n} 治療日）===',
    'wave_range': '日付範囲 {d0} – {d1}',
    'wave_table_header': '日付           呼吸数    RR    VT中央  VT CV    FI中央  イベント    クラスタ   クラスタ内%    周期s  corr²   ため息/h',
    'wave_table_row': ('{date:<10}{breaths:>6}{rr:>6}{tv:>8}{cv:>6}%{fi:>8}{ev:>6}'
                       '{cl:>8}{clpct:>8}%{per:>7}{c2:>7}{sigh:>8}'),
    'wave_row_skip': '{date:<10}{dash:>6}  （BRP 気流不足のため波形層をスキップ）',
    'wave_verdict_header': '--- 判読ポイント ---',
    'wave_feedback': ('· フィードバック検証（これを最初に読むこと。以下のすべての「圧力↔イベント」比は'
                      'これに拘束される）：{n} 件のイベント後 120 秒以内の圧力変化の中央値は {med} cmH2O、'
                      '{rise}% 上昇・{fall}% 下降。ランダム時点対照は {ctrl_med}/{ctrl_rise}%。'),
    'wave_feedback_confirmed': '装置はイベントに反応して昇圧しているため、イベント率比はこだまであり、圧力無効の証拠にはならない。',
    'wave_feedback_not_confirmed': '明確なイベント後昇圧は見られず。イベント率比はより弱い傍証として扱える。',
    'wave_merge_climbing': ('· 統合：曲線の底は中圧域にあり、右端がまだ上っている（セグメント間差 {gain}）。'
                            'さらに圧力を稼げる余地があり、低圧側はすでに最適点付近。**下限ではなく'
                            '上限を上げるべき**。'),
    'wave_merge_tail_binding': 'そして装置は長時間上限付近に滞留している（上限が治療を制限している）',
    'wave_merge_tail_not_binding': 'ただしピークはまだ上限に達していない',
    'wave_merge_disclaimer': ' 残存イベント率は APAP 反応性昇圧に汚染されており、この判断には使わない。',
    'wave_merge_flat': ('· 統合：使えるクリーンな証拠は「圧力—平坦化曲線」だけで、それは低圧から高圧で'
                        '背景制限がほとんど改善していないことを示す。現在のレンジはすでに流量制限の'
                        '底を押さえ切っている。高圧帯にも出る残存イベントは、体位/REM 関連の一過性の'
                        '虚脱である可能性が高い。次の一手は体位と発生時間帯の確認で、上限をさらに上げる'
                        'ことではない。（イベント率比はここでは証拠にならない。理由はフィードバック検証。）'),
    'wave_merge_responsive': ('· 統合：背景制限は圧力に対して単調に改善（セグメント間差 {gain}）。低圧側に'
                              'まだ余地があり、下限圧を上げる価値はある。1〜2 週間後に再評価。残存イベント'
                              '率自体は APAP 反応性昇圧に汚染されており、この判断には使わない。'),

    # ── clinical_assessment ───────────────────────────────────────────────
    'assess_level_insufficient': 'データ不足',
    'assess_summary_insufficient': '品質ゲートを通過する治療記録がなく、推移の判読はできない。',
    'assess_level_specialist': '睡眠専門医の確認を推奨',
    'assess_level_followup': '定期フォローアップを推奨',
    'assess_level_near_target': '装置の推移は一般的治疗目標に近い',
    'assess_finding_rei_name': '治療中の残存イベント',
    'assess_finding_rei_text': '分析可能な {n} 晩の装置残存イベント指数の中央値 {med}/時（分母は治療使用時間で PSG-AHI ではない）。',
    'assess_finding_exposure_name': '治療曝露',
    'assess_finding_exposure_text': '分析可能な晩のうち {pct}% が ≥{h} 時間（{k}/{n}）。',
    'assess_action_rei_high': ('残存イベントが繰り返し高値。このレポート・症状・装置の生波形を持って'
                               '睡眠専門医に相談すること。このツールのみでの処方変更はしない。'),
    'assess_action_rei_target': ('残存イベントが一般的治疗目標を安定的に下回っていない。傾眠・覚醒・'
                                 '漏れ・実際の装着時間を踏まえてフォローアップを計画すること。'),
    'assess_action_near_target': ('装置の推移は一般的治疗目標に近い。それでも日中の傾眠・朝の頭痛・'
                                  '著明な覚醒が続くなら、他の睡眠・身体的原因の臨床評価が引き続き必要。'),
    'assess_finding_central_name': '中枢イベント スクリーニング',
    'assess_finding_central_high': 'CAI 中央値 {med}/時。{pct}% の晩で CAI≥{c}/時 かつ OAI 以上。',
    'assess_finding_central_low': 'CAI 中央値 {med}/時。CAI≥{c}/時 で優位という持続的なスクリーニング信号は見られない。',
    'assess_action_central': ('中枢イベント信号が持続的に高値・優位な場合は、睡眠専門医が病歴・投薬・'
                              'PSG をもって評価する必要がある。装置の分類だけで TECSA は診断できない。'),
    'assess_finding_spo2_name': '連続パルスオキシメトリー',
    'assess_finding_spo2_text': '連続 SAD 測定 {n} 晩：T90 中央値 {t90}%、SpO2<88% 時間の中央値 {b88} 分。',
    'assess_action_spo2': ('連続測定で低酸素負荷を示している。臨床担当者による至急確認を。呼吸困難・'
                           '胸痛・意識異常・覚醒時の低酸素を伴う場合は救急受診を。'),
    'assess_finding_spo2_none': ('低酸素時間の計算に使える連続 SAD 血液酸素なし。T90 は疎なサンプル'
                                 'から推定せず、判定不能のままにする。'),
    'assess_summary_normal': '品質ゲート通過後の装置治療記録に基づく。睡眠時無呼吸の正式な診断ではない。',

    # ── matplotlib / メッセージ ──────────────────────────────────────────
    'msg_mpl_missing': '[警告] matplotlib 利用不可。チャートをスキップ：{err}',
    'msg_chart_fail': '[警告] チャート {tag} 失敗：{err}',
    'msg_charts_saved': '[チャート] {names}  （{dir}/ 内）',
    'msg_chart_list': '[チャート] {names}',
    'msg_report_saved': '[保存] {md}\n[スナップショット] {json}',
    'msg_night_chart': '[単晩チャート] {path}',
    'msg_night_chart_fail': '[警告] 単晩チャート失敗：{err}',

    # ── cmd_settings ──────────────────────────────────────────────────────
    'settings_no_file': '{path} がない。SD カードの STR.edf をデータディレクトリにコピーしてから再実行',
    'settings_header': '=== 装置の処方パラメータ（STR.edf 第 {day}/{total} 日記録）===',
    'settings_mode': 'モード          {v}',
    'settings_range': '圧力レンジ      {lo} – {hi} cmH2O',
    'settings_start': '開始圧          {v} cmH2O',
    'settings_fixed': '固定圧          {v} cmH2O',
    'settings_epr': 'EPR             {onoff}  レベル {lvl}  タイプ {eprtype}',
    'settings_ramp': 'Ramp            {onoff}  {n} 分',
    'settings_smartstart': 'SmartStart      {onoff}',
    'settings_mask': 'マスクタイプ    {v}',
    'settings_humid': '加湿            {onoff}  レベル {lvl}  加温チューブ {tube}  温度 {temp}°C',
    'mode_cpap': 'CPAP 固定圧', 'mode_apap': 'APAP 自動調圧', 'mode_bilevel': 'VPAP/バイレベル',
    'mask_pillow': 'ピロー', 'mask_nasal': 'ナスマスク', 'mask_nasal2': 'ナスマスク', 'mask_full': 'フルフェイス',
    'epr_off': 'オフ', 'epr_full': '全時間', 'epr_ramp': 'Ramp のみ',
    'onoff_off': 'オフ', 'onoff_on': 'オン', 'onoff_auto': 'オン/自動',

    # ── cmd_report ────────────────────────────────────────────────────────
    'report_no_data': 'データなし：{root} に使える晩がない（SD カードの DATALOG をコピーして再実行）',
    'seg_all_label': '全期間',
    'report_title': '# PAP 治療モニタリングレポート（臨床意思決定支援）  {ts}',
    'report_disclaimer': ('> 本レポートは ResMed の気流/圧力アルゴリズムによるイベント推定と治療*使用*'
                          '時間に基づく。PSG ではなく、睡眠時無呼吸・REM/体位関連 OSA・TECSA の診断も'
                          '構成しない。睡眠専門医が症状・病歴・生波形・必要に応じて PSG/連続酸素測定と'
                          '併せて確認すること。'),
    'report_device': '**装置** {device}（{mask}）',
    'report_current_settings': ('**記録された現在の設定**（{label}、{since} 以降）：圧力 {pmin}–{pmax} '
                                'cmH2O、EPR {epr}（記録のみ。このツールの処方提案ではない）'),
    'report_s1_title': '\n## 1. データ品質と適用範囲',
    'report_s1_coverage': ('- {n} 治療日をカバー（{d0}–{d1}）。うち {an} 晩が推移分析に入る（記録≥{h}時間・'
                           'EVE/Leak あり・Leak95≤{leak} L/min）。'),
    'report_s1_short': '- 治療記録<{h} 時間の晩は {k} 晩。これは治療曝露の不足を意味し、睡眠時間でもマスク外しの理由でもない。',
    'report_s1_leak': '- Leak95 中央値 {v} L/min。{mx} L/min はローカルなスクリーニングライン。大きい漏れは装置のイベント推定の信頼性を下げうる。',
    'report_s1_reasons': '- 推移分析から除外した理由：{items}',
    'report_s1_reason_item': '{reason}：{n} 晩',
    'report_s1_scope': '- EEG 睡眠段階・体位・呼吸努力・手動波形スコアリングなし。装置 REI の分母は治療時間で、PSG-AHI の重症度区分にそのまま当てはめてはいけない。',
    'report_s2_title': '\n## 2. 現在セグメントの臨床確認事項：{level}',
    'report_s2_actions_head': '**推奨アクション**',
    'report_s3_title': '\n## 3. セグメント別治療推移（調整ログによる。探索的比較）',
    'report_s3_table_header': '| セグメント | 設定 | 分析可能/総数 | 使用時間平均 | 装置 REI 中央値[IQR] | OAI | CAI | UAI | 圧力 P95 | FL95 |',
    'report_s3_comparison': ('**{la} → {lb}**：装置 REI 中央値 {rei_a}→{rei_b}（探索的 p={p1}、{v1}）。'
                             'OAI {oai_a}→{oai_b}（p={p2}、{v2}）'),
    'report_s3_mwu_note': ('> Mann–Whitney 比較は独立した晩の分布の記述である。多重比較の補正なし、'
                           '体位・REM・飲酒・鼻閉・病状変動などの交絡の制御もなし。統計的差はパラメータ'
                           '変更による臨床的利益ではない。'),
    'report_s3_skip': '品質ゲートを通過する治療記録がなく、セグメント推移と統計比較はスキップ。',
    'report_s4_title': '\n## 4. イベント—圧量の関連（記述的。圧力結論は生成しない）',
    'report_s4_meds': '- 明確な閉塞イベント発生圧の中央値 {ev} cmH2O。治療圧中央値 {th} cmH2O。',
    'report_s4_aligned': '- 整列した閉塞イベント {n} 件のうち {m} 件が各晩の P90 以上（{pct}%）。高圧帯（≥P90）の曝露は記録の {e}%。',
    'report_s4_ratio': ('- 高圧帯/その他のイベント率比 {rr}（圧力サンプルの曝露で補正）。**この比を'
                        '「昇圧が無効」と読んではいけない**。理由は下の結論とセクション 4b の'
                        'フィードバック検証を参照。'),
    'report_s4_spearman': '- 晩をまたぐ Spearman ρ(圧力 P95, OAI)={rho}（n={n}）。イベント後昇圧がここでは因果の向きを逆転させるため、因果として読めない。',
    'report_s4_verdict': '- **{v}**：{why}',
    'report_s4_timing': '- 治療記録内の分布（{n} 件）：前半 {t1}% / 中盤 {t2}% / 後半 {t3}%。{v}',
    'report_s4b_title': '\n## 4b. 気流波形層（1 呼吸ごと、直近 {n} 晩）',
    'report_s4b_preamble': ('> BRP 25 Hz 気流から呼吸を 1 回ごとに再構築（吸気ピーク検出＋吸気平坦化指数）。'
                            'FI は各晩自身のベースラインとの相対値で文献の絶対値ではない。装置の気流は '
                            'PSG の鼻圧信号ではなく、EEG 覚醒・体位・呼吸努力はない。以下はすべて装置の'
                            '相対トレンドの手がかり。'),
    'report_s4b_feedback': ('- フィードバック検証：{n} 件のイベント後 120 秒以内の圧力変化中央値 {med} '
                            'cmH2O（{rise}% が 0.5 超の上昇、{fall}% が -0.5 未満の下降）。ランダム時点'
                            ' 対照 {ctrl_n} 件では中央値 {ctrl_med}、上昇 {ctrl_rise}%。装置は実際に'
                            'イベントへ反応して昇圧しており、「高圧 ↔ イベント多」の共起はすべてこの'
                            'フィードバックのこだまであり「圧力が無効」ではない。'),
    'report_s4b_skip': '1 呼吸ごとの再構築に足りる BRP 気流データがないため、このセクションはスキップ。',
    'report_s5_title': '\n## 5. 換気・流量制限・酸素化（モニタリング指標）',
    'report_s5_flowlim': '- FlowLim95 {fl}、いびき P95 {snore}。同一装置/設定での推移確認に有用。単独で気道虚脱は診断できない。',
    'report_s5_vent': '- 呼吸数中央値 {rr} 回/分・1 回換気量中央値 {tv} L・分時換気量中央値 {mv} L/min。装置の推定は漏れと覚醒の影響を受ける。',
    'report_s5_spo2': '- 夜間最低 SpO2 中央値 {v}%（平均 {avg}%）{src}。第 2 節の低酸素スクリーニングには連続 SAD を使用。カバー不足の晩は除外され推定されない。',
    'report_s5_src': '（ソース：{src}）',
    'report_s6_title': '\n## 6. 直近 7 治療日',
    'report_s6_header': '| 日付 | 記録 h | 装置 REI | OAI | CAI | UAI | 圧力 P95 | Leak95 | SpO2 最低 |',
    'report_s6_header_nospo2': '| 日付 | 記録 h | 装置 REI | OAI | CAI | UAI | 圧力 P95 | Leak95 |',
    'report_charts_title': '## チャート',
    'report_handoff_title': '## 引き継ぎメモ',
    'report_handoff_emergency': '- 胸痛・著明な呼吸困難・意識異常・覚醒時の低酸素などの緊急症状がある場合は直ちに救急受診を。本レポートは救急トリアージには使えない。',
    'report_handoff_medical': '- パラメータ変更は医療上の意思決定である。本レポート・症状の変化・投薬/合併症・SD カードの生データを、睡眠専門医または処方チームに渡して確認すること。',

    # ── cmd_pressure ──────────────────────────────────────────────────────
    'pressure_no_data': '品質ゲートを通過する治療記録がない（≥{h} 時間・EVE と Leak が必要）。イベント-圧力分析は不可能。',
    'pressure_header': '=== イベント-圧力関連（記述的な臨床意思決定支援）===',
    'pressure_nights': '分析可能な晩 {n}（≥{h} 時間・漏れは基準内）',
    'pressure_meds': '閉塞イベント発生時の圧力中央値   {ev} cmH2O   （治療圧中央値 {th}）',
    'pressure_above90': '各晩の圧力 P90 以上で発生した閉塞イベントの割合   {pct}%',
    'pressure_spearman': '晩をまたぐ相関 Spearman ρ(圧力 P95, OAI) = {rho}  (n={n})',
    'pressure_spearman_note': '  注：APAP はイベントで圧力が上がる。正の相関＝圧力が原因ではない。参考値',
    'pressure_exposure': '高圧帯の治療曝露の割合           {pct}%',
    'pressure_ratio': '高圧/その他のイベント率比        {v}',
    'pressure_verdict': 'スクリーニング結論：{v}',
    'pressure_why': '根拠：{w}',
    'pressure_timing': '時間帯分布：前半 {t1}% / 中盤 {t2}% / 後半 {t3}% → {v}',

    # ── cmd_summary ───────────────────────────────────────────────────────
    'summary_header': '日付            時間   REI   OAI   CAI    HI    圧力中/95  FL95   漏れ95     イベント圧',
    'summary_avg_row': '平均      {usage:>5} {ahi:>5} {oai:>5} {cai:>5} {hi:>5}',
    'summary_legend': ('注：装置 REI は治療時間を分母とする装置イベント指数で PSG-AHI の重症度ではない。'
                       'OAI 閉塞、CAI 中枢、HI 低換気、UAI 分類不能の無呼吸、FL 流量制限。* は品質'
                       'ゲート不通過の治療記録（<{h} 時間・チャネル欠損・大きい漏れ）'),

    # ── cmd_detail ────────────────────────────────────────────────────────
    'detail_no_dir': '{path} がない',
    'detail_header': '=== {date}（単晩の治療記録）===',
    'detail_summary': '使用時間 {h} 時間   装置 REI {rei}  （閉塞 {oa} 中枢 {ca} 低換気 {hyp} 分類不能 {ua}）',
    'detail_not_analyzable': '  [分析不可の晩]',
    'detail_pressure': '圧力 中央値 {med} / P95 {p95} / ピーク {mx} cmH2O',
    'detail_oa_press': '閉塞イベント発生時の圧力 中央値 {med}  高圧帯割合 {pct}%',
    'detail_oa_press_none': '閉塞イベント発生時の圧力：なし',
    'detail_flowlim': '流量制限 中央値 {fl_med} / P95 {fl95}   いびき P95 {snore95}',
    'detail_vent': '呼吸数 {rr} 回/分  1 回換気量 {tv} L  分時換気量 {mv} L/min',
    'detail_leak': '漏れ 中央値 {med} / P95 {p95} L/min',
    'detail_thirds': '治療記録内のイベント時間帯：前半 {t1}% / 中盤 {t2}% / 後半 {t3}%',
    'detail_spo2': 'SpO2 最低 {v}% / 平均 {avg}%{src}',
    'detail_src_tag': '（{src}）',
    'detail_event_list_head': '--- イベント一覧（先頭 40 件。発症時刻 / 長さ / タイプ / 発生時圧力）---',
    'detail_event_more': '  ... 全 {n} 件',

    # ── maskoff ───────────────────────────────────────────────────────────
    'maskoff_header': '日付            時間    終了時刻    最終イベントからの差    末30分  分類  末尾のイベント',
    'maskoff_counts': '分類カウント: {counts}',
    'maskoff_end_dist': '終了時刻分布: 00:00-01:00 {early} 晩 / 01:00-03:30 {mid} 晩 / 03:30+ {late} 晩',
}
