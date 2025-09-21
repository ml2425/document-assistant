'use client'

import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import PDFUpload from './components/PDFUpload'
import PDFChatInterface from './components/PDFChatInterface'
import MedicalUpload from './components/MedicalUpload'
import MedicalChatInterface from './components/MedicalChatInterface'
import MedicalExportModal from './components/MedicalExportModal'

type TabType = 'chat' | 'pdf' | 'medical'

interface PDFData {
  filename: string
  pages: number
  chunks: number
}

interface MedicalData {
  filename: string
  pages: number
  chunks: number
  category: string
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('chat')
  const [pdfData, setPDFData] = useState<PDFData | null>(null)
  const [medicalData, setMedicalData] = useState<MedicalData | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showExportModal, setShowExportModal] = useState(false)

  const handleUploadSuccess = (filename: string, pages: number, chunks: number) => {
    setPDFData({ filename, pages, chunks })
    setUploadError(null)
    // Switch to PDF chat after successful upload
    setActiveTab('pdf')
  }

  const handleUploadError = (error: string) => {
    setUploadError(error)
  }

  const handleMedicalUploadSuccess = (filename: string, pages: number, chunks: number, category: string) => {
    setMedicalData({ filename, pages, chunks, category })
    setUploadError(null)
    // Switch to medical chat after successful upload
    setActiveTab('medical')
  }

  const handleMedicalUploadError = (error: string) => {
    setUploadError(error)
  }

  const handleExport = async (title: string, journalSource: string) => {
    if (!medicalData) return

    try {
      const response = await fetch('/api/export-medical', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: medicalData.filename,
          title: title,
          journal_source: journalSource
        }),
      })

      if (!response.ok) {
        throw new Error('Export failed')
      }

      const data = await response.json()
      
      // Create and download JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${medicalData.filename}_medical_export.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
    } catch (error) {
      console.error('Export error:', error)
      throw error
    }
  }

  const handleImport = async (importData: any) => {
    try {
      const response = await fetch('/api/import-medical', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: importData.document.filename,
          title: importData.document.title,
          journal_source: importData.document.journal_source,
          conversation_history: importData.conversation
        }),
      })

      if (!response.ok) {
        throw new Error('Import failed')
      }

      const result = await response.json()
      
      // Update the medical data with imported information
      setMedicalData({
        filename: result.filename,
        pages: 0, // Unknown for imported documents
        chunks: 0, // Unknown for imported documents
        category: 'Imported Document'
      })
      
    } catch (error) {
      console.error('Import error:', error)
      throw error
    }
  }

  const tabs = [
    { id: 'chat' as TabType, label: 'General Chat', icon: '💬' },
    { id: 'pdf' as TabType, label: 'PDF Upload', icon: '📄' },
    { id: 'medical' as TabType, label: 'Medical Documents', icon: '🏥' }
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
            Phase 3: Chat, PDF Analysis & Medical Documents
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
            <>
              {!medicalData ? (
                <MedicalUpload 
                  onUploadSuccess={handleMedicalUploadSuccess}
                  onUploadError={handleMedicalUploadError}
                />
              ) : (
                <MedicalChatInterface 
                  filename={medicalData.filename}
                  pages={medicalData.pages}
                  chunks={medicalData.chunks}
                  category={medicalData.category}
                  onExport={() => setShowExportModal(true)}
                  onImport={handleImport}
                />
              )}
            </>
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

      {/* Export Modal */}
      {medicalData && (
        <MedicalExportModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
          filename={medicalData.filename}
          onExport={handleExport}
        />
      )}
    </main>
  )
}
