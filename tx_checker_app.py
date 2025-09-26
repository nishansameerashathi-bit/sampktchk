import pandas as pd
import streamlit as st

st.title("📊 TX KPI Forward Drops Checker")

# Upload file
uploaded_file = st.file_uploader("Upload your TX KPI CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file,skiprows=6)

    # 🔧 Clean column names
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace("\ufeff", "", regex=True)
    df.columns = df.columns.str.replace(" ", "_")

 

    # 🕒 Handle Time/Date
    time_col = None
    for col in df.columns:
        if col.lower().startswith("time") or col.lower().startswith("date"):
            time_col = col
            break

    if not time_col:
        st.error("❌ No 'Time' or 'Date' column found!")
    else:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])  # drop invalid dates

        # Add week number and date-only columns
        df["date_only"] = df[time_col].dt.date
        df["week"] = df[time_col].dt.isocalendar().week

        # Column with Forward Drops
        drop_col = [c for c in df.columns if "Forword" in c or "Forward" in c]
        if not drop_col:
            st.error("❌ Couldn’t find Forward Drops column!")
        else:
            drop_col = drop_col[0]

            # 🔎 Filter > 0.1
            df_filtered = df[df[drop_col] > 0.1]

            # Count days per NE/task per week
            df_grouped = (
                df_filtered.groupby(["NE_Name", "Name_of_IPPM_task", "week"])["date_only"]
                .nunique()
                .reset_index(name="days_above_threshold")
            )

            # Keep only >= 3 days
            df_result = df_grouped[df_grouped["days_above_threshold"] >= 4]

            st.subheader("📌 Sites with drops > 0.1 for 4+ days in a week")
            st.dataframe(df_result)

            # Allow CSV download
            csv = df_result.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Results as CSV",
                data=csv,
                file_name="TX_filtered_results.csv",
                mime="text/csv",
            )
