'use client'

import { useState } from 'react'

interface MedicalExportModalProps {
  isOpen: boolean
  onClose: () => void
  filename: string
  onExport: (title: string, journalSource: string) => void
}

export default function MedicalExportModal({ 
  isOpen, 
  onClose, 
  filename, 
  onExport 
}: MedicalExportModalProps) {
  // Use PDF filename (without extension) as default title
  const defaultTitle = filename.replace(/\.pdf$/i, '')
  const [title, setTitle] = useState(defaultTitle)
  const [journalSource, setJournalSource] = useState('')
  const [isExporting, setIsExporting] = useState(false)

  if (!isOpen) return null

  const handleExport = async () => {
    if (!title.trim() || !journalSource.trim()) {
      alert('Please fill in both title and journal/source fields')
      return
    }

    setIsExporting(true)
    try {
      await onExport(title.trim(), journalSource.trim())
      onClose()
      setTitle('')
      setJournalSource('')
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-semibold mb-4">Export Medical Document</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Document Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter document title..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Journal/Source *
            </label>
            <input
              type="text"
              value={journalSource}
              onChange={(e) => setJournalSource(e.target.value)}
              placeholder="Enter journal name or source..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>

          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-sm text-blue-700">
              <strong>Note:</strong> The exported JSON file can be uploaded to ChatGPT for additional context in future conversations.
            </p>
          </div>
        </div>

        <div className="flex justify-end space-x-3 mt-6">
          <button
            onClick={onClose}
            disabled={isExporting}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting || !title.trim() || !journalSource.trim()}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isExporting ? 'Exporting...' : 'Export JSON'}
          </button>
        </div>
      </div>
    </div>
  )
}
