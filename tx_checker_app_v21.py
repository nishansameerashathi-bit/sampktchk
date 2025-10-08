import pandas as pd
import streamlit as st
from datetime import datetime

st.title("📊 TX KPI Forward Drops + VPLS Analysis")

# ======================
# Upload Section
# ======================
uploaded_huawei = st.file_uploader("📤 Upload Huawei TX KPI CSV", type=["csv"])


if uploaded_huawei :
    # Read Huawei KPI file (skip first 6 rows)
    df = pd.read_csv(uploaded_huawei, skiprows=6)

    # Clean column names
    df.columns = df.columns.str.strip().str.replace("\ufeff", "", regex=True).str.replace(" ", "_")

    # Detect time/date column
    time_col = None
    for col in df.columns:
        if col.lower().startswith("time") or col.lower().startswith("date"):
            time_col = col
            break

    if not time_col:
        st.error("❌ No 'Time' or 'Date' column found in Huawei file!")
    else:
        # Handle datetime
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
        df["date_only"] = df[time_col].dt.date
        df["week"] = df[time_col].dt.isocalendar().week

        # Find forward drops column
        drop_col = [c for c in df.columns if "Forword" in c or "Forward" in c]
        if not drop_col:
            st.error("❌ Couldn’t find Forward Drops column!")
        else:
            drop_col = drop_col[0]

            # Filter threshold > 0.1
            df_filtered = df[df[drop_col] > 0.1].copy()
            
            
            # ==============================
            # Button 1: Sites with drops > 0.1 for 4+ days in a week
            # ==============================
            if st.button("📌 Show Sites with 4+ Days Drops"):
                df_grouped = (
                    df_filtered.groupby(["NE_Name", "Name_of_IPPM_task", "week"])["date_only"]
                    .nunique()
                    .reset_index(name="days_above_threshold")
                )
                df_result = df_grouped[df_grouped["days_above_threshold"] >= 4]
                
                  # ✅ Sort results by days_above_threshold (descending)
                df_result = df_result.sort_values(by="days_above_threshold", ascending=False)


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
                 # ==============================

# ==========================
# VPLS Mapping
# ==========================
uploaded_vpls = st.file_uploader("📤 Upload VPLS Mapping File (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_vpls:
    if uploaded_vpls.name.endswith(".csv"):
        vpls_map = pd.read_csv(uploaded_vpls)
    else:
        vpls_map = pd.read_excel(uploaded_vpls)

    # Let user pick mapping columns
    site_col = st.selectbox("🔑 Select Site Column", vpls_map.columns, index=0)
    vpls_col = st.selectbox("🔗 Select VPLS Column", vpls_map.columns, index=1)

    # Clean site column in VPLS mapping (make it comparable to Huawei short names)
    vpls_map[site_col] = (
        vpls_map[site_col].astype(str).str.upper().str.strip().str[:6]
    )

    # Build site→VPLS dictionary
    vpls_dict = dict(zip(vpls_map[site_col], vpls_map[vpls_col]))

    # ==========================
    # Button 2: Common Drops + VPLS Mapping
    # ==========================
    if st.button("📊 Show Common Drops with VPLS Mapping"):
        # Extract site short names
        df_filtered["site_short"] = df_filtered["Name_of_IPPM_task"].str[:6].str.upper().str.strip()

        # Group by time → unique sites
        grouped = (
            df_filtered.groupby(time_col)["site_short"]
            .apply(lambda x: sorted(x.unique()))
            .reset_index(name="Sites_with_Drops")
        )

        # Add site count
        grouped["Common_Site_Count"] = grouped["Sites_with_Drops"].apply(len)

        # Keep only count > 5
        grouped = grouped[grouped["Common_Site_Count"] > 5]

        # Sort by count
        grouped = grouped.sort_values(by="Common_Site_Count", ascending=False)

        # Map sites → VPLS
        def map_sites_to_vpls(sites):
            vpls_counts = {}
            for site in sites:
                vpls = vpls_dict.get(site, "UNKNOWN")
                vpls_counts[vpls] = vpls_counts.get(vpls, 0) + 1
            return ",".join([f"{vpls}-{count}" for vpls, count in vpls_counts.items()])

        grouped["vpls affected"] = grouped["Sites_with_Drops"].apply(map_sites_to_vpls)

        # Reorder columns
        grouped = grouped[[time_col, "Common_Site_Count", "vpls affected", "Sites_with_Drops"]]

        # Show dataframe
        st.subheader("📊 Common Drops with VPLS Mapping")
        st.dataframe(grouped)

        # ==========================
        # CSV Download with timestamp
        # ==========================
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_common = grouped.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Common Drops + VPLS CSV",
            data=csv_common,
            file_name=f"TX_common_vpls_{current_time}.csv",
            mime="text/csv",
        )
