    st.markdown("---")
    st.subheader("VISUAL: NORMALIZED MID PRICE (ALL START AT 100)")

    if chart_rows:
        chart_df = pd.DataFrame(chart_rows).sort_values(["Ticker", "Date"])

        # Normalize each ticker so first value in range = 100
        chart_df["Mid Price (Norm 100)"] = (
            chart_df.groupby("Ticker")["Mid Price"]
            .transform(lambda s: (s / s.iloc[0]) * 100.0 if len(s) else s)
        )

        fig = px.line(
            chart_df,
            x="Date",
            y="Mid Price (Norm 100)",
            color="Ticker",
            title="Normalized Mid Price (Start = 100)"
        )

        fig.update_layout(
            paper_bgcolor="black",
            plot_bgcolor="black",
            font=dict(color="#ff9900", family="Courier New"),
            legend=dict(font=dict(color="#ff9900")),
            xaxis=dict(gridcolor="#222222", zerolinecolor="#222222"),
            yaxis=dict(gridcolor="#222222", zerolinecolor="#222222"),
            title=dict(font=dict(color="#ff9900")),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough range data to draw lines (try a wider date range).")
