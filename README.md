# 🧪 Web Test Script Generator

AI-powered Playwright test automation tool with visual element capture, network interception, and intelligent test generation.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-SocketIO-green.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automation-orange.svg)

## ✨ Features

- **🎯 Visual Element Capture** - Click elements in browser to capture locators
- **⚡ Auto-Scrape All Elements** - Automatically detect all interactive elements
- **🌐 Network Interception** - Capture and inspect all API calls
- **🤖 AI Test Generation** - Describe tests in plain English, get executable code
- **▶️ Test Runner** - Execute tests with credentials and see real-time results
- **📝 Manual Test Cases** - Generate CSV documentation for QA
- **🔌 Chrome Extension** - Capture from any open tab

## 🚀 Quick Start

\`\`\`bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/testgenforWeb.git
cd testgenforWeb

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Start the server
python server.py

# 5. Open in browser
open http://localhost:5001
\`\`\`

## 🎮 Usage

### 1. Capture Elements
1. Click **Launch browser** - Playwright opens Chromium
2. Navigate to your app
3. **Click elements** to capture, or **⚡ Scrape All** to auto-capture
4. Name the screen and **Save**

### 2. Generate Test Scripts
1. Go to **Generate** tab
2. Enter Claude API key
3. Describe the test scenario
4. Click **✦ Generate scripts**

### 3. Run Tests
1. Go to **Test Runner** tab
2. **🔍 Scan Current Page** for locators
3. Enter credentials
4. Describe test or add steps manually
5. **▶ Run Test**

### 4. Network Inspection
- API calls auto-captured
- View headers and bodies
- Filter "API only" calls

## 📝 License

MIT License
