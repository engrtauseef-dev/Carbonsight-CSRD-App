#♻️ CarbonSight AI: CSRD Report Generator
⚡ AI-Powered Sustainability Reporting Made Simple




🌍 Overview

CarbonSight AI is a physics + AI powered tool that helps companies generate CSRD (Corporate Sustainability Reporting Directive) audit-ready reports for their energy systems.

It combines:

✅ Physics-based modeling (compressed air system efficiency, energy savings potential)

✅ AI-powered CSRD compliance reports (aligned with ESRS standards)

✅ Actionable recommendations for energy optimization & carbon reduction

This project is designed as an MVP but scalable towards a $1B sustainability SaaS platform.

⚙️ Features

📊 Input plant data (flow rate, pressure, power, efficiency)

🔬 Run physics model → calculate theoretical vs actual power use

🧮 Gap Analysis → identify efficiency gap & savings opportunity

🤖 AI Report Generation → GPT-4.1-mini generates CSRD/ESRS audit-ready reports

📥 Downloadable reports in Markdown / PDF

🚀 Getting Started

1️⃣ Clone repo
git clone https://github.com/YOUR_USERNAME/Carbonsight-CSRD-App.git
cd Carbonsight-CSRD-App

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Add API Key

Create a file .streamlit/secrets.toml (not committed to GitHub):

OPENAI_API_KEY="sk-xxxxxx"

4️⃣ Run locally
streamlit run app.py

🌐 Deployment

This app is ready to deploy on:

Streamlit Community Cloud
 (free hosting)

Hugging Face Spaces

Railway

On Streamlit Cloud:

Connect GitHub repo → Deploy

Add your API key in App Settings → Secrets

You’ll get a public URL:

https://yourusername-csrdsight.streamlit.app

📸 App Preview

(Insert screenshot of your Streamlit app here once deployed)

📈 Roadmap

✅ MVP with compressed air system physics + CSRD reporting

🔄 Add support for boilers, chillers, turbines, and motors

🧾 Auto-export reports in CSRD-compliant PDF

🌍 SaaS Platform with client logins & dashboards

💰 Subscription model for SMEs + Enterprises

🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss.

📜 License

MIT License – free to use and adapt.
