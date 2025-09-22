# ChatGPT Clone - Phase 1

A simple ChatGPT clone with streaming conversation functionality.

## 🚀 Phase 1 Features

- **Real-time Chat**: Streaming responses from OpenAI GPT-3.5-turbo
- **Message History**: Maintains conversation context
- **Clean UI**: Modern interface with Tailwind CSS
- **Error Handling**: Graceful error handling and user feedback

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Python web framework
- **OpenAI** - GPT-3.5-turbo integration
- **Streaming** - Real-time response streaming

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Server-Sent Events** - Real-time streaming

## 📁 Project Structure

```
cloneGPT/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── vercel.json        # Vercel config
│   └── env.example        # Environment template
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   └── ChatInterface.tsx
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── tsconfig.json
└── vercel.json            # Root Vercel config
```

## 🔧 Setup Instructions

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Variables

Create `backend/.env` file:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run Locally

**Terminal 1 (Backend):**
```bash
cd backend
python app.py
```
Backend runs on: http://localhost:8000

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
Frontend runs on: http://localhost:3000

## 🧪 Testing

1. Open http://localhost:3000
2. Type a message and press Enter
3. Watch the AI response stream in real-time
4. Test conversation history and context

## 📋 API Endpoints

- `GET /api/health` - Health check
- `GET /api/debug` - Environment variables status
- `POST /api/chat` - Streaming chat endpoint

## 📄 Medical Document Export/Import Guide

### How to Use Export/Import Feature

#### **Export Process (Local Only):**
1. **Upload medical document** → PDF gets processed
2. **Ask questions** → Build conversation history
3. **Click "Export JSON"** → Download conversation file
4. **File contains:** Questions, responses (100 words max), metadata

#### **Import Process (Local Only):**
1. **Return to page** → Upload same PDF again
2. **Click "Import JSON"** → Select exported file
3. **Conversation restored** → Continue where you left off
4. **Fresh start** → Previous conversation replaced (no merge)

#### **What Gets Restored:**
- ✅ **Conversation history** → Previous Q&A available to ChatGPT
- ✅ **Document context** → PDF search capability restored
- ✅ **Full context** → Both PDF and conversation history

#### **Workflow Example:**
```
Day 1: Upload PDF → Ask 5 questions → Export JSON
Day 2: Upload same PDF → Import JSON → Ask "What did we discuss about symptoms?"
       → ChatGPT knows previous conversation!
```

#### **Important Notes:**
- **Export/Import only works locally** (not on Vercel)
- **Must re-upload PDF** before importing
- **Small JSON files** (only conversation, not PDF content)
- **100-word response limit** for storage efficiency

## 🎯 Next Steps (Phase 2)

- PDF upload functionality
- PDF text extraction and querying
- Fallback to ChatGPT when PDF doesn't contain answer
- Enhanced UI with tabs for different functions

## 🔐 Security Notes

- API key stored in environment variables only
- No API key exposure in frontend
- CORS configured for local development
