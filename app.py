import streamlit as st
import pandas as pd
import numpy as np
import json
import tempfile
import re
from fpdf import FPDF
from openai import OpenAI

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
st.title("♻️ CarbonSight AI: Physics-Based Waste Detection + Audit Ready CSRD Report")
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
# -------------------------------
# Inside the "Generate Audit-Ready CSRD Report" button block
# -------------------------------

# ESRS Disclosure Mapping (needed for PDF)
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

            # -------------------------------
            # Extract AI response safely
            # -------------------------------
            final_report_str = response.choices[0].message.content.strip()
            final_report_str = re.sub(r"^```json\s*|\s*```$", "", final_report_str)
            final_report_json = json.loads(final_report_str)

            st.success("✅ Audit-ready JSON generated successfully!")
            st.json(final_report_json, expanded=True)

            # -------------------------------
            # Download JSON
            # -------------------------------
            st.download_button(
                label="📥 Download Report (JSON)",
                data=json.dumps(final_report_json, indent=4),
                file_name=f"CSRD_Report_{flow_rate_cfm}CFM_{discharge_pressure_psia}PSIA.json",
                mime="application/json"
            )

            # -------------------------------
            # Generate PDF using fpdf2
            # -------------------------------
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            

            # ---- Cover Page ----
            pdf.add_page()
            pdf.set_font("Arial", "B", 20)
            pdf.cell(0, 15, "CSRD Compliance Report", ln=True, align="C")
            pdf.set_font("Arial", "", 14)
            pdf.ln(5)
            pdf.cell(0, 10, f"System: Industrial Compressed Air System", ln=True, align="C")
            pdf.cell(0, 10, f"Report Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}", ln=True, align="C")
            pdf.ln(10)

            # ---- Helper for Section ----
            def add_section(title, content, is_table=False):
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, title, ln=True)
                pdf.ln(2)
                pdf.set_font("Arial", "", 11)

                if is_table and isinstance(content, dict):
                    col_width = pdf.w / 2.5
                    for key, value in content.items():
                        pdf.cell(col_width, 8, str(key), border=1)
                        pdf.cell(col_width, 8, str(value), border=1, ln=True)
                    pdf.ln(5)
                elif isinstance(content, (dict, list)):
                    pdf.multi_cell(0, 6, json.dumps(content, indent=4))
                    pdf.ln(5)
                else:
                    pdf.multi_cell(0, 6, str(content))
                    pdf.ln(5)

            # ---- Add Sections ----
            add_section("Technical Analysis", final_report_json.get("technical_analysis", {}), is_table=True)
            add_section("Executive Summary", final_report_json.get("executive_summary", {}))
            add_section("ESRS S1 Analysis", final_report_json.get("esrs_s1_analysis", {}))
            add_section("ESRS 2 Analysis", final_report_json.get("esrs_2_analysis", {}))
            add_section("Materiality Assessment", final_report_json.get("materiality_assessment", {}))
            add_section("Actionable Recommendations", final_report_json.get("actionable_recommendations", {}))
            add_section("Estimated Impact", final_report_json.get("estimated_impact", {}))
            add_section("AI Waste Diagnosis", final_report_json.get("ai_waste_diagnosis", {}))

            # ---- ESRS Disclosure Mapping Table ----
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "ESRS Disclosure Mapping", ln=True)
            pdf.ln(2)
            pdf.set_font("Arial", "", 11)

            col_width = pdf.w / 3.5
            pdf.cell(col_width, 8, "ESRS Standard", border=1)
            pdf.cell(col_width, 8, "Disclosure Requirement", border=1)
            pdf.cell(col_width, 8, "Analysis Provided", border=1, ln=True)

            for idx, row in esrs_mapping.iterrows():
                pdf.cell(col_width, 8, str(row['ESRS Standard']), border=1)
                pdf.cell(col_width, 8, str(row['Disclosure Requirement']), border=1)
                pdf.cell(col_width, 8, str(row['Our Analysis Provides']), border=1, ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", "I", 10)
            pdf.multi_cell(0, 6, "This audit-ready report provides structured CSRD compliance data for review by regulatory bodies or audit committees.")

            # ---- Download PDF ----
            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
                pdf.output(tmp_file.name)
                tmp_file.seek(0)
                st.download_button(
                    label="📥 Download Audit-Ready PDF",
                    data=tmp_file.read(),
                    file_name=f"CSRD_Audit_Report_{flow_rate_cfm}CFM_{discharge_pressure_psia}PSIA.pdf",
                    mime="application/pdf"
                )

        except json.JSONDecodeError:
            st.error("⚠️ Failed to parse AI response as JSON. Displaying raw output:")
            st.code(final_report_str)
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            st.info("Ensure your OpenAI API key is set correctly in .streamlit/secrets.toml")
from fpdf import FPDF

def generate_csrd_pdf(report_data, filename="CSRD_Report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Title
    pdf.cell(200, 10, "CSRD Compliance Report", ln=True, align="C")
    pdf.ln(10)

    # Section 1: Summary
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, report_data.get("summary", "No summary available"))
    pdf.ln(5)

    # Section 2: Emissions
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Carbon Emissions", ln=True)
    pdf.set_font("Arial", '', 12)

    emissions = report_data.get("emissions", {})
    for scope, value in emissions.items():
        pdf.cell(0, 10, f"{scope}: {value} tonnes CO₂e", ln=True)
    pdf.ln(5)

    # Section 3: Actionable Recommendations
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Actionable Recommendations", ln=True)
    pdf.set_font("Arial", '', 12)

    recommendations = report_data.get("recommendations", [])
    if recommendations:
        for rec in recommendations:
            pdf.multi_cell(
                0, 10, f"- {rec['recommendation']} (Priority: {rec['priority']})"
            )
    else:
        pdf.multi_cell(0, 10, "No recommendations available.")
    pdf.ln(5)

    # Section 4: ESRS / CSRD Mapping
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "CSRD / ESRS Disclosures Mapping", ln=True)
    pdf.set_font("Arial", '', 12)

    csrd = report_data.get("csrd_mapping", [])
    if csrd:
        for item in csrd:
            pdf.multi_cell(
                0,
                10,
                f"Disclosure: {item['disclosure']} | Status: {item['status']} | Notes: {item['notes']}",
            )
    else:
        pdf.multi_cell(0, 10, "No CSRD mapping available.")

    # Save
    pdf.output(filename)
    return filename

# Add this to your imports at the top
import smtplib
from email.mime.text import MIMEText

# ... [your existing code] ...

st.divider()
with st.expander("🚀 Interested in a Full Pilot Project?"):
    st.write("**Get a comprehensive CSRD and energy analysis for your entire facility.**")
    
    with st.form("pilot_request_form"):
        col1, col2 = st.columns(2)
        with col1:
            pilot_name = st.text_input("Your Name*")
            pilot_company = st.text_input("Company Name*")
        with col2:
            pilot_email = st.text_input("Work Email*")
            pilot_phone = st.text_input("Phone Number")
        
        comments = st.text_area("What are your biggest sustainability challenges?*", 
                               placeholder="CSRD compliance, energy costs, reporting, etc.")
        
        submitted = st.form_submit_button("✅ Request Full Pilot Proposal")
        
        if submitted:
            # Validate required fields
            if not pilot_name or not pilot_company or not pilot_email or not comments:
                st.error("⚠️ Please fill in all required fields (marked with *)")
            else:
                # Prepare professional email content
                subject = f"CarbonSight Pilot Request: {pilot_company}"
                
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <h2 style="color: #2E86AB;">New Pilot Project Request</h2>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                        <h3 style="color: #333;">Contact Information</h3>
                        <p><strong>Name:</strong> {pilot_name}</p>
                        <p><strong>Company:</strong> {pilot_company}</p>
                        <p><strong>Email:</strong> {pilot_email}</p>
                        <p><strong>Phone:</strong> {pilot_phone or 'Not provided'}</p>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <h3 style="color: #333;">Their Challenges</h3>
                        <p style="background-color: #fff3cd; padding: 10px; border-radius: 5px;">{comments}</p>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <h3 style="color: #333;">Analysis Context</h3>
                        <p><strong>System Analyzed:</strong> Compressed Air ({flow_rate_cfm} CFM)</p>
                        <p><strong>Efficiency Gap:</strong> {efficiency_gap_percent:.0f}% above optimal</p>
                        <p><strong>Potential Savings:</strong> Significant energy and cost reduction identified</p>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background-color: #e2e3e5; border-radius: 5px;">
                        <p><strong>Next Steps:</strong> This lead was generated through the CarbonSight AI tool. 
                        They've already seen value and are requesting a full pilot.</p>
                    </div>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        Sent automatically from CarbonSight AI Platform | Sustainability Ventures Ltd
                    </p>
                </body>
                </html>
                """
                
                try:
                    # Email configuration for your company email
                    sender_email = "tauseef@sustainabilityventuresltd.com"
                    receiver_email = "tauseef@sustainabilityventuresltd.com"  # Sends to yourself
                    password = st.secrets["GMAIL_APP_PASSWORD"]  # Your Gmail App Password
                    
                    # Create message
                    msg = MIMEMultipart()
                    msg['Subject'] = subject
                    msg['From'] = f"CarbonSight AI <{sender_email}>"
                    msg['To'] = receiver_email
                    msg['Reply-To'] = pilot_email  # So you can reply directly to the lead
                    
                    # Attach HTML body
                    msg.attach(MIMEText(html_body, 'html'))
                    
                    # Send email using Gmail SMTP (simplest for now)
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                        server.login(sender_email, password)
                        server.sendmail(sender_email, receiver_email, msg.as_string())
                    
                    # Success message to user
                    st.success("""
                    ✅ Thank you! Your request has been received.
                    
                    **What happens next:**
                    1. Our team will review your challenges
                    2. We'll contact you within 24 hours to discuss your specific needs
                    3. We'll prepare a customized pilot proposal
                    """)
                    
                    # Also show confirmation in the app
                    st.info(f"""
                    **Lead Captured:** 
                    - **Company:** {pilot_company}
                    - **Contact:** {pilot_name} ({pilot_email})
                    - **Priority:** High (Pilot Request)
                    """)
                    
                except Exception as e:
                    st.error(f"""
                    ❌ Sorry, there was an error sending your request. 
                    
                    Please email us directly at **tauseef@sustainabilityventuresltd.com** with:
                    - Your name and company
                    - The challenges you're facing
                    - Reference: Compressed Air Analysis
                    """)
                    # Display the error for debugging (remove in production)
                    st.write(f"Technical details: {str(e)}")
# After the efficiency results
cost_per_kwh = st.number_input("Your Electricity Cost (€/kWh)", value=0.15)
annual_hours = st.number_input("Annual Operating Hours", value=8000)
annual_waste_cost = (actual_power_kw - theoretical_power_kw) * annual_hours * cost_per_kwh
if annual_waste_cost > 0:
    st.info(f"**Estimated Annual Waste:** €{annual_waste_cost:,.0f}")

