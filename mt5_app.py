                    future_low  = df_bt["low"].iloc[i + j]

                    if signal_bt == "BUY":
                        if future_low <= sl_bt:
                            outcome = "LOSS"; exit_price = sl_bt; exit_candle = j; break
                        elif future_high >= tp1_bt:
                            outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break
                    else:
                        if future_high >= sl_bt:
                            outcome = "LOSS"; exit_price = sl_bt; exit_candle = j; break
                        elif future_low <= tp1_bt:
                            outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break

                if outcome == "OPEN":
                    continue

                # Auto-detect pip size berdasarkan harga
                # Forex (EURUSD dll): harga < 100 → pip = 0.00010
                # Gold (XAUUSD):      harga > 100 → pip = 0.10
                # Indices/Oil:        fallback ke persentase
                if entry_price < 10:
                    pip_size  = 0.00010   # JPY pairs & crypto-like
                elif entry_price < 100:
                    pip_size  = 0.00010   # Forex majors
                else:
                    pip_size  = 0.10      # Gold, Silver, Indices

                sl_pips  = abs(entry_price - sl_bt) / pip_size
                tp_pips  = abs(tp1_bt - entry_price) / pip_size

                # Lot size: untuk gold, 1 lot = 100 oz, mini lot = 10 oz
                # Estimasi lot dari modal: modal / (entry * 10) untuk gold
                if entry_price > 100:
                    lot_size = round(bt_modal / (entry_price * 10), 4)
                else:
                    lot_size = round(bt_modal / (entry_price * 1000), 4)

                if outcome == "WIN":
                    pnl = round(tp_pips * lot_size, 2)
                else:
                    pnl = round(-sl_pips * lot_size, 2)

                rr_actual = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

                trades.append({
                    "timestamp":   str(df_bt["timestamp"].iloc[i])[:16],
                    "signal":      signal_bt,
                    "entry":       round(entry_price, 5),
                    "exit":        round(exit_price, 5),
                    "outcome":     outcome,
                    "pnl":         pnl,
                    "rr":          rr_actual,
                    "score":       score_bt["total"],
                    "exit_candle": exit_candle,
                })

            if not trades:
                st.warning("Tidak ada trade yang tereksekusi. Coba kurangi threshold score atau tambah candles.")
            else:
                total_trades = len(trades)
                wins         = [t for t in trades if t["outcome"] == "WIN"]
                losses       = [t for t in trades if t["outcome"] == "LOSS"]
                win_rate     = round(len(wins) / total_trades * 100, 1)
                total_pnl    = round(sum(t["pnl"] for t in trades), 2)
                avg_win      = round(sum(t["pnl"] for t in wins)   / len(wins),   2) if wins   else 0
                avg_loss     = round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0
                avg_rr       = round(sum(t["rr"]  for t in trades) / total_trades, 2)
                avg_score    = round(sum(t["score"] for t in trades) / total_trades, 1)

                pnl_color = "#3fb950" if total_pnl >= 0 else "#f85149"
                wr_color  = "#3fb950" if win_rate >= 55 else "#f0883e" if win_rate >= 45 else "#f85149"

                st.markdown("<br>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5 = st.columns(5)
                for col, label, val, color in [
                    (c1, "Total Trade", str(total_trades), "#e6edf3"),
                    (c2, "Win Rate",    f"{win_rate}%",    wr_color),
                    (c3, "Total P&L",   f"{'+'if total_pnl>=0 else ''}{total_pnl}$", pnl_color),
                    (c4, "Avg RR",      f"1:{avg_rr}",     "#388bfd"),
                    (c5, "Avg Score",   f"{avg_score}/100","#d2a8ff"),
                ]:
                    with col:
                        st.markdown(f"""
                        <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px; text-align:center;">
                            <p style="color:#8b949e; font-size:11px; margin:0 0 6px 0; text-transform:uppercase;">{label}</p>
                            <p style="color:{color}; font-size:22px; font-weight:800; margin:0;">{val}</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                col_wl1, col_wl2 = st.columns(2)
                with col_wl1:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px;">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; margin:0 0 10px 0;">Win Summary</p>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Win</span><span style="color:#3fb950; font-weight:700;">{len(wins)} trade</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Profit</span><span style="color:#3fb950; font-weight:700;">+${avg_win}</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Profit</span><span style="color:#3fb950; font-weight:700;">+${round(sum(t["pnl"] for t in wins),2)}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_wl2:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px;">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; margin:0 0 10px 0;">Loss Summary</p>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">{len(losses)} trade</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Loss</span><span style="color:#f85149; font-weight:700;">${avg_loss}</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">${round(sum(t["pnl"] for t in losses),2)}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-header">Trade History</p>', unsafe_allow_html=True)
                for t in reversed(trades[-30:]):
                    oc = "#3fb950" if t["outcome"] == "WIN" else "#f85149"
                    sc = "#3fb950" if t["signal"]  == "BUY" else "#f85149"
                    ps = "+" if t["pnl"] >= 0 else ""
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                         padding:8px 12px; margin:3px 0; background:#161b22;
                         border:1px solid #30363d; border-radius:6px; font-size:12px;">
                        <span style="color:#8b949e; width:130px;">{t["timestamp"]}</span>
                        <span style="color:{sc}; font-weight:700; width:45px;">{t["signal"]}</span>
                        <span style="color:#e6edf3; width:90px;">Entry: {t["entry"]:.5f}</span>
                        <span style="color:#e6edf3; width:90px;">Exit: {t["exit"]:.5f}</span>
                        <span style="color:#8b949e; width:60px;">RR 1:{t["rr"]}</span>
                        <span style="color:#8b949e; width:60px;">Score: {t["score"]}</span>
                        <span style="color:{oc}; font-weight:700; width:60px;">{t["outcome"]}</span>
                        <span style="color:{oc}; font-weight:700;">{ps}{t["pnl"]}$</span>
                    </div>
                    """, unsafe_allow_html=True)

# ─── TAB 5: SETTINGS ───
with tab5:
    st.markdown('<p class="section-header">⚙️ Settings</p>', unsafe_allow_html=True)
    auto_refresh = st.checkbox("🔄 Auto Refresh setiap 30 detik", value=st.session_state["auto_refresh_mt5"])
    st.session_state["auto_refresh_mt5"] = auto_refresh
    if auto_refresh:
        st.success("✅ Auto refresh aktif")
    else:
        st.info("ℹ️ Auto refresh nonaktif")

    st.markdown("---")
    account = mt5.account_info()
    if account:
        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
            <p style="color:#8b949e; font-size:12px; margin:0;">
            👤 <strong style="color:#e6edf3;">{account.name}</strong><br>
            🏦 Server: <span style="color:#e6edf3;">{account.server}</span><br>
            💰 Balance: <span style="color:#3fb950;">${account.balance:,.2f} {account.currency}</span><br>
            📊 Leverage: <span style="color:#e6edf3;">1:{account.leverage}</span><br>
            🔗 Status: <span style="color:#3fb950;">🟢 Connected</span><br>
            Ⓥ Version: <span style="color:#e6edf3;">v2.4.3 (AI Reasoning)</span><br>
            </p>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────
if st.session_state.get("auto_refresh_mt5"):
    time.sleep(30)
    st.rerun()
