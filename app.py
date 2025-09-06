import streamlit as st
import pandas as pd
import numpy as np
import json
import tempfile
import re
from fpdf import FPDF
from openai import OpenAI
from datetime import datetime

# ***************************************************
# 1. PHYSICS ENGINE MODULE
# ***************************************************
def calculate_compressed_air_power(flow_rate_cfm, inlet_pressure_psia, discharge_pressure_psia, efficiency=0.72):
    GAMMA = 1.4
    R = 53.3
    T_inlet = 520
    mass_flow = (inlet_pressure_psia * flow_rate_cfm) / (R * T_inlet)
    head = (GAMMA / (GAMMA - 1)) * R * T_inlet * (
            (discharge_pressure_psia / inlet_pressure_psia) ** ((GAMMA - 1) / GAMMA) - 1)
    power_hp = (mass_flow * head) / (550 * 60 * efficiency)
    return power_hp

# ***************************************************
# 2. STREAMLIT APP UI
# ***************************************************
st.title("♻️ CarbonSight AI: Physics-Based Waste Detection")
st.header("Compressed Air System Analysis")

col1, col2 = st.columns(2)
with col1:
    flow_rate_cfm = st.number_input("Flow Rate (CFM)", min_value=50, max_value=2000000, value=300, step=10)
    inlet_pressure_psia = st.number_input("Inlet Pressure (PSIA)", min_value=14.0, max_value=20.0, value=14.7, step=0.1)
with col2:
    discharge_pressure_psia = st.number_input("Discharge Pressure (PSIA)", min_value=50.0, max_value=2000000.0, value=110.0, step=1.0)
    system_efficiency = st.slider("System Adiabatic Efficiency", min_value=0.1, max_value=0.95, value=0.72, step=0.01,
                                 help="A well-maintained system might be 0.7-0.75. A poorly maintained system could be 0.5-0.65.")

actual_power_kw = st.number_input("Actual Measured Electrical Input Power (kW)", min_value=10.0, max_value=500.0, value=75.0, step=1.0,
                                 help="Measured power from meter or electrical bill.")

# ***************************************************
# 3. CALCULATIONS
# ***************************************************
theoretical_power_hp = calculate_compressed_air_power(flow_rate_cfm, inlet_pressure_psia, discharge_pressure_psia, system_efficiency)
theoretical_power_kw = theoretical_power_hp * 0.7457
theoretical_specific_power = theoretical_power_kw / flow_rate_cfm
actual_specific_power = actual_power_kw / flow_rate_cfm
theoretical_specific_power_per_100 = theoretical_specific_power * 100
actual_specific_power_per_100 = actual_specific_power * 100
efficiency_gap = actual_specific_power - theoretical_specific_power
efficiency_gap_percent = (efficiency_gap / theoretical_specific_power) * 100

# ***************************************************
# 4. DISPLAY RESULTS & AI WASTE LOGIC
# ***************************************************
st.subheader("🔍 Analysis Results")
col1, col2, col3 = st.columns(3)
col1.metric("Theoretical Power", f"{theoretical_power_kw:.1f} kW")
col2.metric("Actual Power", f"{actual_power_kw:.1f} kW")
col3.metric("System Efficiency", f"{(theoretical_power_kw / actual_power_kw) * 100:.1f}%")

st.divider()
col4, col5 = st.columns(2)
col4.metric("Theoretical Specific Power", f"{theoretical_specific_power_per_100:.1f} kW/100 CFM", help="The power an IDEAL system should consume.")
col5.metric("Actual Specific Power", f"{actual_specific_power_per_100:.1f} kW/100 CFM", help="The power YOUR ACTUAL system consumes.")

st.subheader("🤖 AI Waste Diagnosis")
if efficiency_gap_percent > 50:
    st.error("🚨 CRITICAL INEFFICIENCY")
    st.write(f"Your system is consuming **{efficiency_gap_percent:.0f}%** more power than theoretical optimum.")
elif efficiency_gap_percent > 20:
    st.warning("⚠️ SIGNIFICANT WASTE DETECTED")
    st.write(f"Your system is consuming **{efficiency_gap_percent:.0f}%** more power than it should.")
elif efficiency_gap_percent > 5:
    st.info("ℹ️ MODERATE INEFFICIENCY")
    st.write(f"Your system is consuming **{efficiency_gap_percent:.0f}%** more power than baseline.")
else:
    st.success("✅ HIGH EFFICIENCY")
    st.write("System operating close to theoretical optimum!")

# ***************************************************
# 5. AI CSRD REPORT GENERATOR (JSON + Audit-Ready PDF)
# ***************************************************
st.divider()
st.subheader("📑 Generate Audit-Ready CSRD Report")

esrs_mapping = pd.DataFrame({
    'ESRS Standard': ['ESRS S1', 'ESRS S1', 'ESRS 2', 'ESRS 2', 'ESRS S1'],
    'Disclosure Requirement': [
        'S1-5: Energy consumption and mix',
        'S1-6: Gross Scopes 1, 2, and 3 emissions',
        'GOV-3: Integration into strategy',
        'SBM-3: Material impacts, risks and opportunities',
        'S1-7: Emission removals and mitigation efforts'
    ],
    'Our Analysis Provides': [
        f'Detailed energy consumption: {actual_power_kw:.1f} kW',
        'Scope 2 emissions calculation basis',
        'Strategic energy efficiency opportunities',
        f'Material risk: {efficiency_gap_percent:.0f}% energy waste',
        'Specific mitigation recommendations'
    ]
})

if st.button("✨ Generate Audit-Ready CSRD Report", type="primary"):

    expert_prompt = f"""
    ACT as a senior sustainability consultant (CEM, CAP, GRI certified). Write a **machine-readable JSON CSRD report** for an industrial compressed air system. Include fields: 
    executive_summary, esrs_s1_analysis, esrs_2_analysis, materiality_assessment, actionable_recommendations, estimated_impact, technical_analysis, ai_waste_diagnosis.

    TECHNICAL ANALYSIS:
    - Flow Rate: {flow_rate_cfm} CFM
    - Discharge Pressure: {discharge_pressure_psia} PSIA
    - Theoretical Power: {theoretical_power_kw:.1f} kW
    - Actual Power: {actual_power_kw:.1f} kW
    - System Efficiency: {(theoretical_power_kw / actual_power_kw) * 100:.1f}%
    - Efficiency Gap: {efficiency_gap_percent:.0f}%
    """

    with st.spinner("🧠 Generating JSON and PDF..."):
        try:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert sustainability consultant providing audit-ready CSRD reports in structured JSON format."},
                    {"role": "user", "content": expert_prompt}
                ],
                temperature=0.2
            )

            final_report_str = response.choices[0].message.content.strip()
            final_report_str = re.sub(r"^```json\s*|\s*```$", "", final_report_str)
            final_report_json = json.loads(final_report_str)

            st.success("✅ Audit-ready JSON generated successfully!")
            st.json(final_report_json, expanded=True)

            st.download_button(
                label="📥 Download Report (JSON)",
                data=json.dumps(final_report_json, indent=4),
                file_name=f"CSRD_Report_{flow_rate_cfm}CFM_{discharge_pressure_psia}PSIA.json",
                mime="application/json"
            )

           # ***************************************************
# 6. POLISHED PDF REPORT GENERATION (Fixed Version)
# ***************************************************

from fpdf import FPDF
import tempfile
from datetime import datetime

# Define a custom PDF class for better styling (Compatible with newer fpdf2)
class CSRDPDF(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Title
        self.cell(0, 10, 'CSRD Compliance & Energy Efficiency Report', 0, 0, 'C')
        # Line break
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
    
    def section_title(self, title):
        # Arial 12, bold
        self.set_font('Arial', 'B', 12)
        # Background color
        self.set_fill_color(200, 220, 255)
        # Title
        self.cell(0, 6, title, 0, 1, 'L', 1)
        # Line break
        self.ln(4)
    
    def body_text(self, text):
        # Times 12
        self.set_font('Times', '', 12)
        # Output justified text (compatible method)
        self.multi_cell(0, 5, text)
        # Line break
        self.ln(2)
    
    def key_value_line(self, key, value):
        # Times 12, bold for key
        self.set_font('Times', 'B', 12)
        self.cell(50, 5, key, 0, 0)
        # Times 12 for value
        self.set_font('Times', '', 12)
        self.multi_cell(0, 5, value)
        self.ln(1)

# ... [Your existing code above remains the same] ...

# Inside your report generation button block, replace the PDF section with this:

            # -------------------------------
            # Generate Polished PDF Report (FIXED VERSION)
            # -------------------------------
            pdf = CSRDPDF()
            pdf.alias_nb_pages()  # For page numbering in footer
            pdf.add_page()

            # Title Page
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 20, 'CSRD Compliance & Energy Efficiency Report', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', '', 16)
            pdf.cell(0, 10, 'Generated by CarbonSight AI', 0, 1, 'C')
            pdf.ln(15)
            
            pdf.set_font('Arial', '', 14)
            pdf.cell(0, 10, f'Date: {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'C')
            pdf.cell(0, 10, f'System: Compressed Air - {flow_rate_cfm} CFM', 0, 1, 'C')
            pdf.ln(20)
            
            pdf.set_font('Arial', 'I', 12)
            pdf.multi_cell(0, 10, 'This report contains analysis of energy efficiency and CSRD compliance readiness based on physics-based modeling and AI analysis.')

            # Executive Summary
            pdf.add_page()
            pdf.section_title('EXECUTIVE SUMMARY')
            exec_summary = final_report_json.get("executive_summary", "No executive summary available.")
            if isinstance(exec_summary, dict):
                # If it's a dictionary, convert to string
                exec_summary = "\n".join([f"{k}: {v}" for k, v in exec_summary.items()])
            pdf.body_text(exec_summary)
            
            # Technical Analysis
            pdf.add_page()
            pdf.section_title('TECHNICAL ANALYSIS')
            
            # Technical data in key-value format
            tech_data = [
                ("Flow Rate:", f"{flow_rate_cfm} CFM"),
                ("Discharge Pressure:", f"{discharge_pressure_psia} PSIA"),
                ("Theoretical Power:", f"{theoretical_power_kw:.1f} kW"),
                ("Actual Power:", f"{actual_power_kw:.1f} kW"),
                ("System Efficiency:", f"{(theoretical_power_kw / actual_power_kw) * 100:.1f}%"),
                ("Efficiency Gap:", f"{efficiency_gap_percent:.0f}% above theoretical optimum")
            ]
            
            for key, value in tech_data:
                pdf.key_value_line(key, value)
            
            pdf.ln(5)
            tech_analysis = final_report_json.get("technical_analysis", "")
            if isinstance(tech_analysis, dict):
                tech_analysis = "\n".join([f"{k}: {v}" for k, v in tech_analysis.items()])
            pdf.body_text(tech_analysis)

            # ESRS Analysis
            pdf.add_page()
            pdf.section_title('ESRS S1 CLIMATE ANALYSIS')
            esrs_s1 = final_report_json.get("esrs_s1_analysis", "")
            if isinstance(esrs_s1, dict):
                esrs_s1 = "\n".join([f"{k}: {v}" for k, v in esrs_s1.items()])
            pdf.body_text(esrs_s1)
            
            pdf.section_title('ESRS 2 GENERAL DISCLOSURES')
            esrs_2 = final_report_json.get("esrs_2_analysis", "")
            if isinstance(esrs_2, dict):
                esrs_2 = "\n".join([f"{k}: {v}" for k, v in esrs_2.items()])
            pdf.body_text(esrs_2)

            # Materiality Assessment
            pdf.section_title('MATERIALITY ASSESSMENT')
            materiality = final_report_json.get("materiality_assessment", "")
            if isinstance(materiality, dict):
                materiality = "\n".join([f"{k}: {v}" for k, v in materiality.items()])
            pdf.body_text(materiality)

            # Recommendations
            pdf.add_page()
            pdf.section_title('ACTIONABLE RECOMMENDATIONS')
            recommendations = final_report_json.get("actionable_recommendations", {})
            
            if isinstance(recommendations, dict):
                for key, value in recommendations.items():
                    pdf.set_font('Times', 'B', 12)
                    pdf.cell(0, 6, f'• {key}', 0, 1)
                    pdf.set_font('Times', '', 12)
                    if isinstance(value, dict):
                        value = "\n".join([f"  - {k}: {v}" for k, v in value.items()])
                    pdf.multi_cell(0, 5, f'  {value}')
                    pdf.ln(2)
            else:
                pdf.body_text(str(recommendations))

            # Estimated Impact
            pdf.section_title('ESTIMATED IMPACT')
            impact = final_report_json.get("estimated_impact", "")
            if isinstance(impact, dict):
                impact = "\n".join([f"{k}: {v}" for k, v in impact.items()])
            pdf.body_text(impact)

            # AI Waste Diagnosis
            pdf.section_title('AI WASTE DIAGNOSIS')
            diagnosis = final_report_json.get("ai_waste_diagnosis", "")
            if isinstance(diagnosis, dict):
                diagnosis = "\n".join([f"{k}: {v}" for k, v in diagnosis.items()])
            pdf.body_text(diagnosis)

            # ESRS Mapping Table (Simplified for compatibility)
            pdf.add_page()
            pdf.section_title('ESRS DISCLOSURE MAPPING')
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(90, 8, 'ESRS Standard', 1, 0, 'C')
            pdf.cell(0, 8, 'Our Analysis Provides', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 9)
            for _, row in esrs_mapping.iterrows():
                pdf.cell(90, 6, str(row['ESRS Standard']), 1, 0)
                pdf.multi_cell(0, 6, str(row['Our Analysis Provides']), 1, 'L')
                # Reset x position after multi_cell
                pdf.set_x(10)

            # Disclaimer
            pdf.add_page()
            pdf.section_title('DISCLAIMER')
            pdf.set_font('Times', 'I', 10)
            disclaimer_text = (
                "This report is generated automatically by CarbonSight AI based on user inputs "
                "and physics-based modeling. While we strive for accuracy, this report should be "
                "reviewed by qualified sustainability professionals before use for compliance "
                "purposes. CarbonSight AI is not liable for decisions made based on this report."
            )
            pdf.multi_cell(0, 5, disclaimer_text)

            # Save and offer download
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                pdf.output(tmp_file.name)
                with open(tmp_file.name, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button(
                    label="📥 Download Professional PDF Report",
                    data=pdf_bytes,
                    file_name=f"CarbonSight_CSRD_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )

# ... [The rest of your code remains the same] ...
        except json.JSONDecodeError:
            st.error("⚠️ Failed to parse AI response as JSON. Displaying raw output:")
            st.code(final_report_str)
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            st.info("Ensure your OpenAI API key is set correctly in .streamlit/secrets.toml")

# ***************************************************
# 7. PILOT PROJECT & COST SAVINGS
# ***************************************************
st.divider()
with st.expander("🚀 Interested in a Full Pilot?"):
    st.write("**Get a comprehensive analysis for your entire facility.**")
    col1, col2 = st.columns(2)
    with col1:
        pilot_name = st.text_input("Your Name")
        pilot_company = st.text_input("Company Name")
    with col2:
        pilot_email = st.text_input("Work Email")
        pilot_phone = st.text_input("Phone")
    if st.button("Request Full Pilot"):
        st.success("Thanks! We'll contact you within 24 hours to discuss your pilot project.")

cost_per_kwh = st.number_input("Your Electricity Cost (€/kWh)", value=0.15)
annual_hours = st.number_input("Annual Operating Hours", value=8000)
annual_waste_cost = (actual_power_kw - theoretical_power_kw) * annual_hours * cost_per_kwh
if annual_waste_cost > 0:
    st.info(f"**Estimated Annual Waste:** €{annual_waste_cost:,.0f}")
