import re
import pandas as pd
import streamlit as st

# ------------------------------
# Function to parse Huawei config
# ------------------------------
def parse_huawei_config(file):
    node, interface, site, vlan = None, None, None, None
    records = []

    # Read file content
    content = file.read().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    for i, line in enumerate(lines):
        line = line.strip()

        # NODE (sysname)
        if line.startswith("sysname"):
            node = line.split()[1]

        # INTERFACE
        if line.startswith("interface Eth-Trunk5."):
            interface = line.split()[1]

            # DESCRIPTION (next line)
            if i + 1 < len(lines) and "description" in lines[i + 1]:
                desc_line = lines[i + 1]
                match = re.search(r"TO\s+([A-Z0-9]+)[_-]", desc_line, re.IGNORECASE)
                if match:
                    site = match.group(1)
                else:
                    site = None

            # VLAN (check next few lines)
            vlan = None
            for j in range(i, min(i + 10, len(lines))):
                if "qinq termination" in lines[j]:
                    vlan_match = re.search(r"pe-vid\s+(\d+)", lines[j])
                    if vlan_match:
                        vlan = vlan_match.group(1)
                        break

            # Save record
            records.append({
                "NODE": node,
                "Interface": interface,
                "Site Name": site,
                "VPLS Vlan": vlan
            })

    return pd.DataFrame(records)


# ------------------------------
# Streamlit UI
# ------------------------------
st.title("📂 Huawei Config Extractor – ROOM11 & ROOM12 with VPLS Mapping")

st.write("Upload **two Huawei config files** (ROOM11 and ROOM12) and a **VPLS mapping CSV** to extract and map configuration data.")

# Upload ROOM11 and ROOM12 config files
room11_file = st.file_uploader("📘 Upload ROOM11 Config File (.txt or .log)", type=["txt", "log"])
room12_file = st.file_uploader("📗 Upload ROOM12 Config File (.txt or .log)", type=["txt", "log"])

# Upload VPLS mapping CSV
uploaded_mapping = st.file_uploader("📊 Upload VPLS Mapping CSV (.csv)", type=["csv"])

if room11_file and room12_file:
    st.info("✅ Both ROOM11 and ROOM12 files uploaded. Parsing...")

    try:
        df_room11 = parse_huawei_config(room11_file)
        df_room12 = parse_huawei_config(room12_file)

        df_combined = pd.concat([df_room11, df_room12], ignore_index=True)
        st.success(f"✅ Parsed successfully. Total records: {len(df_combined)}")
       

        if uploaded_mapping:
            try:
                df_mapping = pd.read_csv(uploaded_mapping)

                # Normalize column names
                df_combined["VPLS Vlan"] = df_combined["VPLS Vlan"].astype(str).str.strip()
                df_mapping["VPLS Vlan"] = df_mapping["VPLS Vlan"].astype(str).str.strip()

                # Merge on VPLS Vlan
                df_merged = pd.merge(df_combined, df_mapping, on="VPLS Vlan", how="left")

                st.success("✅ Extraction and mapping successful!")
                st.dataframe(df_merged)

                st.download_button(
                    label="⬇️ Download Merged CSV",
                    data=df_merged.to_csv(index=False),
                    file_name="huawei_config_with_vpls.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"❌ Error reading mapping CSV: {e}")

        else:
            st.warning("Please upload the VPLS mapping CSV file to continue.")

    except Exception as e:
        st.error(f"❌ Error while parsing configuration files: {e}")

else:
    st.info("📥 Please upload both ROOM11 and ROOM12 Huawei configuration files to begin.")

