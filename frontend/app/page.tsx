'use client'

import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import PDFUpload from './components/PDFUpload'
import PDFChatInterface from './components/PDFChatInterface'

type TabType = 'chat' | 'pdf' | 'medical'

interface PDFData {
  filename: string
  pages: number
  chunks: number
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('chat')
  const [pdfData, setPDFData] = useState<PDFData | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const handleUploadSuccess = (filename: string, pages: number, chunks: number) => {
    setPDFData({ filename, pages, chunks })
    setUploadError(null)
    // Switch to PDF chat after successful upload
    setActiveTab('pdf')
  }

  const handleUploadError = (error: string) => {
    setUploadError(error)
  }

  const tabs = [
    { id: 'chat' as TabType, label: 'General Chat', icon: '💬' },
    { id: 'pdf' as TabType, label: 'PDF Upload', icon: '📄' },
    { id: 'medical' as TabType, label: 'Medical Analysis', icon: '🏥' }
  ]

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            ChatGPT Clone
          </h1>
          <p className="text-gray-600 mt-1">
            Phase 2: Chat, PDF Analysis & Medical Analysis
          </p>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {activeTab === 'chat' && <ChatInterface />}
          
          {activeTab === 'pdf' && (
            <>
              {!pdfData ? (
                <PDFUpload 
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={handleUploadError}
                />
              ) : (
                <PDFChatInterface 
                  filename={pdfData.filename}
                  pages={pdfData.pages}
                  chunks={pdfData.chunks}
                />
              )}
            </>
          )}
          
          {activeTab === 'medical' && (
            <div className="p-6 text-center">
              <div className="text-6xl mb-4">🏥</div>
              <h2 className="text-xl font-semibold mb-2">Medical Analysis</h2>
              <p className="text-gray-600">
                Phase 3: Medical analysis functionality coming soon!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t mt-8">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <p className="text-center text-gray-500 text-sm">
            Built with FastAPI, Next.js, and OpenAI
          </p>
        </div>
      </footer>
    </main>
  )
}
