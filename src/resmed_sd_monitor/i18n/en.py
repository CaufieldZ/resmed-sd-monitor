"""English string table (base locale). Placeholders are str.format named fields."""

STRINGS = {
    # ── quality-gate reasons (night_summary codes → display) ──────────────
    'qr_short_use': 'therapy record <{h:g} h',
    'qr_no_eve': 'EVE event files missing',
    'qr_no_leak': 'Leak channel missing',
    'qr_high_leak': 'Leak95 > {v:g} L/min',

    # ── statistics verdicts ───────────────────────────────────────────────
    'verdict_insufficient_n': 'insufficient sample',
    'verdict_decrease': 'decrease observed (exploratory)',
    'verdict_increase': 'increase observed (exploratory)',
    'verdict_no_clear_diff': 'no clear difference detected; equivalence not proven',

    # ── pressure_response ─────────────────────────────────────────────────
    'pr_insufficient': 'insufficient descriptive evidence',
    'pr_insufficient_why': ('only {n} clearly-labelled obstructive events were pressure-aligned '
                            '(need at least {min_events} events across {min_nights} nights); '
                            'do not read a pressure-adjustment direction from this'),
    'pr_cooccurrence': 'event-pressure co-occurrence only; no cause can be inferred',
    'pr_ratio_tail': '; exposure-corrected high/other event-rate ratio {rr}',
    'pr_cooccurrence_why': ('{pct}% of {n} clearly-labelled obstructive events occurred above the '
                            "night's P90 (that pressure band occupies {exposure}% of the therapy "
                            'record){ratio}. Because APAP raises pressure after events, dwelling in '
                            'the high band is itself event-triggered, so a high event rate there is '
                            'the echo of that feedback and is not evidence that pressure is '
                            'ineffective. Positional or REM relevance cannot be judged either, for '
                            'want of position, sleep staging and manual waveform review.'),

    # ── timing_verdict ────────────────────────────────────────────────────
    'timing_late_heavy': ('more events in the later therapy record; review together with symptoms, '
                          'sleep diary, position/PSG data'),
    'timing_uniform': ('roughly even distribution within the therapy record; no anatomical or '
                       'positional conclusion can be drawn'),
    'timing_uneven': 'uneven distribution within the therapy record; without position and sleep staging, no attribution',

    # ── wave_verdict ──────────────────────────────────────────────────────
    'wv_fi_summary': ('Per-breath flattening index median {med} ({n} nights; a relative measure '
                      "against each night's own baseline, not an absolute verdict)."),
    'wv_cluster': ('Event clustering: {clusters} clusters across {nights} nights (>={min_ev} events '
                   'with adjacent gaps <={gap_min} min); the in-cluster share of all events has '
                   'median {pct}%. Clustering is the classic cue for positional/REM-related OSA, '
                   'but the device records neither position nor sleep stage, so this alone supports '
                   'no attribution.'),
    'wv_period_none': 'Periodic-breathing fit: {n} nights below threshold',
    'wv_period_weak_tail': ' ({n} with weak signal)',
    'wv_period_none_tail': '; no periodic ventilatory instability at the waveform layer.',
    'wv_period_flagged': ('Periodic-breathing fit: {flagged}/{total} nights reach the threshold '
                          '(corr²>={corr2}); dominant period {period} s, of which short-period '
                          '(<40 s): {n_short} nights. Periodic ventilatory instability needs manual '
                          'waveform review. The device has no EEG/effort channels, so Cheyne-Stokes '
                          'or TECSA cannot be declared from this.'),
    'wv_curve_base': ('Pressure–flatness curve: therapy pressure range {t_lo}–{t_hi} cmH2O '
                      '({n_bins} bins, Ramp drive-by low bins excluded): FI median at {lo_p} bin '
                      '{lo_fi} → at {hi_p} bin {hi_fi}; weighted slope {slope}/cmH2O.'),
    'wv_gain_txt': 'lowest three bins → highest three bins (spanning {span} cmH2O) differ in FI median by only {gain}',
    'wv_curve_negative': ('Limited breaths increase as pressure rises (negative slope). This is mostly '
                          'reverse causation from APAP reactive pressurization: events trigger the '
                          'rise, and those breaths are still recovering. It does not mean pressure is '
                          'harmful.'),
    'wv_curve_gain_flat': ('{gain_txt}. Almost no gainable improvement from lowest to highest '
                           'pressure: background limitation has flattened within this range, so '
                           'further pressure (floor or ceiling) has limited expected benefit.'),
    'wv_curve_ushape': ('{gain_txt}. The curve is **U-shaped**: minimum near {p_min} cmH2O, rising '
                        'again with pressure afterwards (top bin {rise} above the minimum). The '
                        'high-segment recovery is the device pressurizing reactively against flow '
                        'limitation, an echo rather than a sign that pressure is harmful. Climbing '
                        'all the way to the top of the range is the signature of a segment that '
                        'still wants more pressure but is held by the ceiling, which is the same '
                        'fact as the pressure–flatness curve not having finished rising here.'),
    'wv_curve_plateau': ('{gain_txt}, but the improvement concentrates in the low segment; middle and '
                         'above have flattened (within-middle rise {tail_gain}). The current pressure '
                         'range has basically exhausted the gain, and further pressure has diminishing '
                         'returns.'),
    'wv_curve_responsive': ('{gain_txt}: background flow limitation keeps decreasing as pressure rises; '
                            'the airway responds to pressure in this range. Note this measures '
                            '**background limitation**, not whether residual events are suppressed '
                            '(see the pressure-exposure section).'),
    'wv_event_press': ('Pressure at obstructive events: median {med} cmH2O; share >=14 cmH2O: {p14}%, '
                       '>=15 cmH2O: {p15}%.'),

    # ── pressure_exposure_verdict ─────────────────────────────────────────
    'pev_split': ('Split by delivered pressure: low segment (<{p90} cmH2O, P90) {lo_rate} events per '
                  '100 breaths, high segment (>={p90}) {hi_rate} ({lo_br} low / {hi_br} high breaths). '
                  '⚠ Per the feedback check above, this ratio is **not** evidence of whether pressure '
                  'works; it only shows the device does work up there.'),
    'pev_delivered': ('Delivered pressure: median {med}, P90 {p90}, peak {mx} cmH2O; {frac}% of '
                      'inspiratory breaths dwell within 0.5 of the ceiling.'),
    'pev_not_binding': ('Device-set ceiling {set_max} cmH2O was never exceeded (actual peak {press_max}). '
                        'Within this therapy the ceiling is not the limiting factor: raising it '
                        'changes no delivered pressure. What changes outcomes is the floor (min) or '
                        'the mode/mechanism direction.'),
    'pev_binding': ('Peak reaches the set ceiling {set_max} cmH2O and {frac}% of time dwells near it. '
                    'The ceiling is genuinely limiting therapy, and raising it is an evidence-backed step.'),
    'pev_touch_only': ('Peak touches the set ceiling {set_max} cmH2O but only for {frac}% of time '
                       '(scattered transient touches, no sustained dwell). Occasional touching is '
                       'not a limitation, so raising the ceiling alone has small expected benefit.'),

    # ── event-type / chart labels ─────────────────────────────────────────
    'ev_oa': 'obstructive', 'ev_ca': 'central', 'ev_hyp': 'hypopnea', 'ev_ua': 'unclassified apnea',
    'axis_press_cmh2o': 'Pressure cmH2O',
    'axis_press': 'Pressure (cmH2O)',
    'axis_press95': 'Pressure P95 (cmH2O)',
    'axis_fi': 'Inspiratory flattening index',
    'axis_fi_limited': 'Inspiratory flattening index (low = limited)',
    'axis_flowlim': 'Flow limitation',
    'axis_hours_since_start': 'Hours since therapy record start',
    'axis_hours_since_first': 'Hours since first therapy segment',
    'axis_insp_press': 'Pressure during inspiration (cmH2O)',
    'axis_event_count': 'Events',
    'axis_events_cumulative': 'Events (all nights pooled)',
    'axis_minutes': 'Cumulative time (minutes)',
    'axis_oa_press': 'Pressure at obstructive events (cmH2O)',
    'axis_oai': 'OAI (obstructive events/hour)',
    'axis_rei': 'Device residual event index (events/therapy hour)',
    'axis_spo2_min': 'Nightly minimum SpO2 (%)',
    'label_fi': 'Flattening index',
    'legend_fi_med': 'FI median',
    'legend_p25_med': 'P25–median',
    'legend_median': 'median {m}',
    'legend_rolling5': '5-night rolling median',
    'legend_target': 'common therapy target {v}/h',
    'legend_review': 'review line {v}/h',
    'legend_spo2_90': 'SpO2=90% warning line',
    'legend_spo2_94': 'SpO2=94% reference line',
    'chart_wp_title': '{date} pressure curve + obstructive events (red lines)',
    'chart_wp_p10_legend': "night p10 = {q10} (most limited tenth)",
    'chart_wp_fi_title': 'Per-breath inspiratory flattening index (low = plateau-like waveform = flow limitation)',
    'chart_pf_title': 'Pressure vs inspiratory flatness ({n} breaths)',
    'chart_pf_slope': 'weighted slope {slope}/cmH2O',
    'chart_pf_bias_note': ' (under APAP, pressure is raised reactively to events, so this is not a dose–response experiment)',
    'chart_ct_title': ('Event time distribution (red = in-cluster; ○ obstructive △ central '
                       '□ hypopnea × unclassified)\nX axis clipped to the event body; late-night '
                       'weighting must be read together with sleep onset/offset, as the device has '
                       'no sleep staging'),
    'chart_at_title': 'Residual events during PAP therapy (not PSG-AHI)',
    'chart_po_title': 'Pressure P95 vs obstructive index OAI',
    'chart_po_subtitle': '(under APAP pressure rises with events, so a positive correlation does not mean pressure causes events; reference only)',
    'chart_eh_title': 'Therapy-time distribution of device residual events (no sleep staging/position)',
    'chart_ph_title': 'Cumulative dwell time per pressure bin (current settings)',
    'chart_st_title': 'Nightly minimum SpO2 trend (by tuning segment)',
    'chart_st_note': 'Note: SpO2 from the device SAD channel; nights without SAD signal plot no point',
    'chart_ep_title': 'Pressure at clearly-labelled obstructive events (descriptive; not a pressure conclusion)',
    'chart_nd_title': '{date} single night: pressure + obstructive events (red lines)',

    # ── cmd_wave ──────────────────────────────────────────────────────────
    'wave_no_nights': 'No usable nights: no therapy records found under {root}',
    'wave_header': '=== Flow waveform analysis (per-breath, last {n} therapy dates) ===',
    'wave_range': 'Date range {d0} – {d1}',
    'wave_table_header': 'Date      Breaths    RR  VT med  VT CV  FI medEventsClust In-cl% Period  corr² Sigh/h',
    'wave_table_row': ('{date:<10}{breaths:>8}{rr:>6}{tv:>8}{cv:>6}%{fi:>8}{ev:>7}'
                       '{cl:>6}{clpct:>6}%{per:>7}{c2:>7}{sigh:>7}'),
    'wave_row_skip': '{date:<10}{dash:>6}  (BRP flow insufficient, waveform layer skipped)',
    'wave_verdict_header': '--- Reading points ---',
    'wave_feedback': ('· Feedback check (read this first; every "pressure<->event" ratio below is '
                      'bounded by it): within 120 s after {n} events, pressure changed by median '
                      '{med} cmH2O, {rise}% rose / {fall}% fell; random-time controls '
                      '{ctrl_med}/{ctrl_rise}%. '),
    'wave_feedback_confirmed': ('The device does pressurize reactively to events, so event-rate ratios '
                                'are echoes rather than evidence against pressure.'),
    'wave_feedback_not_confirmed': 'No clear post-event pressurization; event-rate ratios may serve as weaker circumstantial evidence.',
    'wave_merge_climbing': ('· Merge: the curve\'s bottom sits at mid-range pressure and the right end '
                            'still climbs (cross-segment difference {gain}). More pressure is '
                            'gainable and the low segment is near the optimum, so **raise the ceiling '
                            'rather than the floor**.'),
    'wave_merge_tail_binding': ' and the device has long dwelt near the ceiling (the ceiling is limiting therapy)',
    'wave_merge_tail_not_binding': ' but the peak has not reached the ceiling',
    'wave_merge_disclaimer': ' Residual event rates are contaminated by APAP reactive pressurization and take no part in this judgment.',
    'wave_merge_flat': ('· Merge: the only clean evidence is the pressure–flatness curve, and it shows '
                        'almost no improvement in background limitation from low to high. The current '
                        'range has already pressed the limitation floor into place. Residual events in '
                        'the high segment are more likely brief positional/REM-related collapses: the '
                        'next step is position and timing rather than a higher ceiling. (Event-rate ratios '
                        'are not evidence here; see the feedback check.)'),
    'wave_merge_responsive': ('· Merge: background limitation improves monotonically with pressure '
                              '(cross-segment difference {gain}); the low segment still has headroom, so '
                              'raising the floor pressure is worth trying, with a re-evaluation in 1–2 weeks. '
                              'Residual event rates are themselves contaminated by APAP reactive '
                              'pressurization and take no part in this judgment.'),

    # ── clinical_assessment ───────────────────────────────────────────────
    'assess_level_insufficient': 'insufficient data',
    'assess_summary_insufficient': 'No therapy records pass the quality gates; no trend reading possible.',
    'assess_level_specialist': 'sleep-specialist review recommended',
    'assess_level_followup': 'routine follow-up recommended',
    'assess_level_near_target': 'device trend near the common therapy target',
    'assess_finding_rei_name': 'Residual events during therapy',
    'assess_finding_rei_text': ('Median device residual event index over {n} analyzable nights: '
                                '{med}/h (therapy usage time as denominator, not PSG-AHI).'),
    'assess_finding_exposure_name': 'Therapy exposure',
    'assess_finding_exposure_text': '{pct}% of analyzable nights >= {h} h ({k}/{n}).',
    'assess_action_rei_high': ('Residual events repeatedly elevated: take this report, symptoms and raw '
                               'device waveforms to a sleep specialist; do not change the prescription '
                               'on your own based on this tool.'),
    'assess_action_rei_target': ('Residual events not reliably below the common therapy target; arrange '
                                 'follow-up considering sleepiness, arousals, leak and actual wear time.'),
    'assess_action_near_target': ('Device trend near the common therapy target; if daytime sleepiness, '
                                  'morning headaches or marked arousals persist, clinical evaluation of '
                                  'other sleep/medical causes is still needed.'),
    'assess_finding_central_name': 'Central event screen',
    'assess_finding_central_high': 'CAI median {med}/h; {pct}% of nights have CAI >= {c}/h and CAI >= OAI.',
    'assess_finding_central_low': ('CAI median {med}/h; the device record shows no sustained screen '
                                   'signal of CAI >= {c}/h with dominance.'),
    'assess_action_central': ('When central-event signals stay elevated/dominant, a sleep specialist '
                              'must evaluate with history, medications and PSG; the device '
                              'classification alone cannot diagnose TECSA.'),
    'assess_finding_spo2_name': 'Continuous oximetry',
    'assess_finding_spo2_text': 'Over {n} nights of continuous SAD oximetry: T90 median {t90}%, SpO2<88% minutes median {b88}.',
    'assess_action_spo2': ('Continuous oximetry shows a hypoxic burden; have clinical personnel review '
                           'promptly. With breathlessness, chest pain, altered consciousness or hypoxia '
                           'while awake, seek emergency care.'),
    'assess_finding_spo2_none': ('No continuous SAD oximetry usable for hypoxia-time computation; '
                                 'T90 stays undetermined rather than estimated from sparse samples.'),
    'assess_summary_normal': 'Based on device therapy records after quality gating; not a formal diagnosis of sleep apnea.',

    # ── matplotlib fonts/messages ─────────────────────────────────────────
    'msg_mpl_missing': '[warn] matplotlib unavailable, skipping charts: {err}',
    'msg_chart_fail': '[warn] chart {tag} failed: {err}',
    'msg_charts_saved': '[charts] {names}  (in {dir}/)',
    'msg_chart_list': '[charts] {names}',
    'msg_report_saved': '[archived] {md}\n[snapshot] {json}',
    'msg_night_chart': '[night chart] {path}',
    'msg_night_chart_fail': '[warn] night chart failed: {err}',

    # ── cmd_settings ──────────────────────────────────────────────────────
    'settings_no_file': 'No {path}: copy STR.edf from the SD card into the data directory first',
    'settings_header': '=== Device prescription (STR.edf day {day}/{total}) ===',
    'settings_mode': 'Mode             {v}',
    'settings_range': 'Pressure range   {lo} – {hi} cmH2O',
    'settings_start': 'Start pressure   {v} cmH2O',
    'settings_fixed': 'Fixed pressure   {v} cmH2O',
    'settings_epr': 'EPR              {onoff}  level {lvl}  type {eprtype}',
    'settings_ramp': 'Ramp             {onoff}  {n} min',
    'settings_smartstart': 'SmartStart       {onoff}',
    'settings_mask': 'Mask type        {v}',
    'settings_humid': 'Humidifier       {onoff}  level {lvl}  heated tube {tube}  temp {temp}°C',
    'mode_cpap': 'CPAP (fixed pressure)', 'mode_apap': 'APAP (auto-adjusting)', 'mode_bilevel': 'VPAP/bilevel',
    'mask_pillow': 'pillow', 'mask_nasal': 'nasal mask', 'mask_nasal2': 'nasal mask', 'mask_full': 'full face',
    'epr_off': 'off', 'epr_full': 'full-time', 'epr_ramp': 'ramp only',
    'onoff_off': 'off', 'onoff_on': 'on', 'onoff_auto': 'on/auto',

    # ── cmd_report ────────────────────────────────────────────────────────
    'report_no_data': 'No data: no usable nights under {root} (copy the SD card DATALOG there and rerun)',
    'seg_all_label': 'All',
    'report_title': '# PAP Therapy Monitoring Report (clinical decision support)  {ts}',
    'report_disclaimer': ('> This report is based on ResMed flow/pressure-algorithm event estimates and '
                          'therapy *usage* time. It is not PSG and does not constitute a diagnosis of '
                          'sleep apnea, REM/positional OSA or TECSA. Have a sleep specialist review it '
                          'together with symptoms, history, raw waveforms and, where needed, PSG / '
                          'continuous oximetry.'),
    'report_device': '**Device** {device} ({mask})',
    'report_current_settings': ('**Recorded current settings** ({label}, since {since}): pressure '
                                '{pmin}–{pmax} cmH2O, EPR {epr} (recorded only, not a prescription '
                                'suggestion from this tool)'),
    'report_s1_title': '\n## 1. Data quality and scope of validity',
    'report_s1_coverage': ('- Covers {n} therapy dates ({d0}–{d1}); {an} nights enter trend analysis '
                           '(record >={h} h, EVE/Leak present, Leak95 <={leak} L/min).'),
    'report_s1_short': '- Nights with therapy record <{h} h: {k}; this means insufficient therapy exposure, not sleep duration and not a mask-off reason.',
    'report_s1_leak': '- Leak95 median {v} L/min. {mx} L/min is a local screening line; a large leak may reduce the reliability of device event estimates rather than prove events absent.',
    'report_s1_reasons': '- Excluded from trend analysis: {items}',
    'report_s1_reason_item': '{reason}: {n} nights',
    'report_s1_scope': '- No EEG sleep staging, position, thoracoabdominal effort or manual waveform scoring; the device REI denominator is therapy time and must not be mapped onto PSG-AHI severity grades.',
    'report_s2_title': '\n## 2. Current-segment clinical review cues: {level}',
    'report_s2_actions_head': '**Suggested actions**',
    'report_s3_title': '\n## 3. Segmented therapy trends (by tuning log; exploratory comparisons)',
    'report_s3_table_header': '| Segment | Settings | Analyzable/total | Usage h mean | Device REI median[IQR] | OAI | CAI | UAI | Press P95 | FL95 |',
    'report_s3_comparison': ('**{la} → {lb}**: device REI median {rei_a}→{rei_b} (exploratory p={p1}, '
                             '{v1}); OAI {oai_a}→{oai_b} (p={p2}, {v2})'),
    'report_s3_mwu_note': ('> Mann–Whitney comparisons describe independent-night distributions; no '
                           'multiple-comparison correction, no control for position, REM, alcohol, '
                           'nasal obstruction, illness fluctuation and other confounders; a statistical '
                           'difference is not a clinical benefit caused by the parameter change.'),
    'report_s3_skip': 'No therapy records pass the quality gates; segmented trends and statistical comparisons skipped.',
    'report_s4_title': '\n## 4. Event–pressure association (descriptive; no pressure conclusions generated)',
    'report_s4_meds': '- Pressure at clearly-labelled obstructive events: median {ev} cmH2O; therapy pressure median {th} cmH2O.',
    'report_s4_aligned': '- {n} aligned obstructive events, {m} above the night\'s P90 ({pct}%); high-pressure (>=P90) exposure occupies {e}% of the record.',
    'report_s4_ratio': ('- High-segment/other event-rate ratio {rr} (exposure-corrected by pressure '
                        'sample). **This ratio must not be read as "more pressure does not help"**; '
                        'see the verdict below and the section 4b feedback check.'),
    'report_s4_spearman': '- Cross-night Spearman ρ(pressure P95, OAI)={rho} (n={n}); post-event pressurization reverses the causal direction here, so no causal reading.',
    'report_s4_verdict': '- **{v}**: {why}',
    'report_s4_timing': '- Distribution within the therapy record ({n} events): first {t1}% / middle {t2}% / last {t3}%; {v}',
    'report_s4b_title': '\n## 4b. Flow waveform layer (per-breath, last {n} nights)',
    'report_s4b_preamble': ('> Breathing is rebuilt breath-by-breath from BRP 25 Hz flow (inspiratory-peak '
                            'detection + inspiratory flattening index). The FI is a relative measure '
                            "against each night's own baseline, not a literature absolute; device flow "
                            'is not PSG nasal pressure: no EEG arousals, no position, no thoracoabdominal '
                            'effort. Every item below is a relative device-trend cue.'),
    'report_s4b_feedback': ('- Feedback check: within 120 s after {n} events, pressure changed by median '
                            '{med} cmH2O ({rise}% rose above 0.5, {fall}% fell below -0.5); across '
                            '{ctrl_n} random-time controls, median {ctrl_med}, {ctrl_rise}% rose. The '
                            'device does pressurize reactively to events, so any "high pressure <-> many '
                            'events" co-occurrence is that feedback echoing back. It is not evidence '
                            'that pressure is ineffective.'),
    'report_s4b_skip': 'Not enough BRP flow data for per-breath reconstruction; section skipped.',
    'report_s5_title': '\n## 5. Ventilation, flow limitation and oxygenation (monitoring metrics)',
    'report_s5_flowlim': '- FlowLim95 {fl}, snore P95 {snore}; useful for trend review on the same device/settings, though alone they cannot diagnose airway collapse.',
    'report_s5_vent': '- Resp rate median {rr} /min · tidal volume median {tv} L · minute ventilation median {mv} L/min. Device estimates are affected by leak and wakefulness.',
    'report_s5_spo2': '- Nightly minimum SpO2 median {v}% (mean {avg}%){src}. Continuous SAD feeds the section-2 hypoxia screen; nights without sufficient SAD coverage are excluded rather than estimated.',
    'report_s5_src': ' (sources: {src})',
    'report_s6_title': '\n## 6. Last 7 therapy dates',
    'report_s6_header': '| Date | Record h | Device REI | OAI | CAI | UAI | Press P95 | Leak95 | SpO2 min |',
    'report_s6_header_nospo2': '| Date | Record h | Device REI | OAI | CAI | UAI | Press P95 | Leak95 |',
    'report_charts_title': '## Charts',
    'report_handoff_title': '## Handoff notes',
    'report_handoff_emergency': '- For emergency symptoms (chest pain, marked breathlessness, altered consciousness, hypoxia while awake), seek emergency care. This report is not an emergency-triage instrument.',
    'report_handoff_medical': '- Parameter changes are medical decisions. Hand this report, symptom changes, medications/comorbidities and the raw SD-card data to the sleep specialist or prescribing team for review.',

    # ── cmd_pressure ──────────────────────────────────────────────────────
    'pressure_no_data': 'No therapy records pass the quality gates (need >={h} h, EVE and Leak present); event-pressure analysis impossible.',
    'pressure_header': '=== Event-pressure association (descriptive clinical decision support) ===',
    'pressure_nights': 'Analyzable nights {n} (>={h} h, leak within bounds)',
    'pressure_meds': 'Median pressure at obstructive events   {ev} cmH2O   (therapy pressure median {th})',
    'pressure_above90': "Share of obstructive events above each night's pressure P90   {pct}%",
    'pressure_spearman': 'Cross-night correlation Spearman ρ(Pressure P95, OAI) = {rho}  (n={n})',
    'pressure_spearman_note': '  Note: APAP pressure rises with events, so a positive correlation does not mean pressure causes events; reference only',
    'pressure_exposure': 'High-pressure-segment therapy exposure   {pct}%',
    'pressure_ratio': 'High/other event-rate ratio        {v}',
    'pressure_verdict': 'Screening conclusion: {v}',
    'pressure_why': 'Basis: {w}',
    'pressure_timing': 'Distribution: first {t1}% / middle {t2}% / last {t3}% → {v}',

    # ── cmd_summary ───────────────────────────────────────────────────────
    'summary_header': 'Date       Hours   REI   OAI   CAI    HI Press md/95  FL95 Leak95 EvPress',
    'summary_avg_row': 'Average     {usage:>5} {ahi:>5} {oai:>5} {cai:>5} {hi:>5}',
    'summary_legend': ('Notes: device REI is a device event index over therapy-time denominators, not '
                       'PSG-AHI severity; OAI obstructive, CAI central, HI hypopnea, UAI unclassified '
                       'apnea; FL flow limitation; * marks therapy records failing quality gates '
                       '(<{h} h, missing channels or high leak)'),

    # ── cmd_detail ────────────────────────────────────────────────────────
    'detail_no_dir': 'No such directory: {path}',
    'detail_header': '=== {date} (single-night therapy record) ===',
    'detail_summary': ('Usage {h} h   Device REI {rei}  (obstructive {oa} central {ca} hypopnea {hyp} '
                       'unclassified {ua})'),
    'detail_not_analyzable': '  [not analyzable]',
    'detail_pressure': 'Pressure median {med} / P95 {p95} / peak {mx} cmH2O',
    'detail_oa_press': 'Pressure at obstructive events: median {med}  above-P90 share {pct}',
    'detail_oa_press_none': 'Pressure at obstructive events: none',
    'detail_flowlim': 'Flow limitation median {fl_med} / P95 {fl95}   snore P95 {snore95}',
    'detail_vent': 'Resp rate {rr} /min  tidal volume {tv} L  minute ventilation {mv} L/min',
    'detail_leak': 'Leak median {med} / P95 {p95} L/min',
    'detail_thirds': 'Events within therapy record: first {t1}% / middle {t2}% / last {t3}%',
    'detail_spo2': 'SpO2 min {v}% / mean {avg}%{src}',
    'detail_src_tag': ' ({src})',
    'detail_event_list_head': '--- Event list (first 40; onset / duration / type / pressure at onset) ---',
    'detail_event_more': '  ... {n} events in total',

    # ── maskoff ───────────────────────────────────────────────────────────
    'maskoff_header': 'Date       Hours   Ended   LastEvGapEv last30m  kind  final events',
    'maskoff_counts': 'Kind counts: {counts}',
    'maskoff_end_dist': 'End-time distribution: 00:00-01:00 {early} nights / 01:00-03:30 {mid} nights / 03:30+ {late} nights',
}
