'use client'

import { useState, useRef } from 'react'

interface PDFUploadProps {
  onUploadSuccess: (filename: string, pages: number, chunks: number) => void
  onUploadError: (error: string) => void
}

export default function PDFUpload({ onUploadSuccess, onUploadError }: PDFUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      onUploadError('Please select a PDF file')
      return
    }

    setIsUploading(true)
    setUploadStatus('Uploading and processing PDF...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload-pdf', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      setUploadStatus(`✅ PDF processed successfully!`)
      onUploadSuccess(result.filename, result.pages, result.chunks)
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setUploadStatus(`❌ ${errorMessage}`)
      onUploadError(errorMessage)
    } finally {
      setIsUploading(false)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0])
    }
  }

  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Upload PDF Document</h2>
      
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="text-6xl text-gray-400">📄</div>
          
          <div>
            <p className="text-lg font-medium text-gray-700">
              {isUploading ? 'Processing PDF...' : 'Drop your PDF here'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or click to browse files
            </p>
          </div>

          <button
            onClick={openFileDialog}
            disabled={isUploading}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? 'Processing...' : 'Choose PDF File'}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileInput}
            className="hidden"
          />
        </div>
      </div>

      {/* Status */}
      {uploadStatus && (
        <div className={`mt-4 p-3 rounded-lg ${
          uploadStatus.startsWith('✅') 
            ? 'bg-green-100 text-green-700' 
            : 'bg-red-100 text-red-700'
        }`}>
          {uploadStatus}
        </div>
      )}

      {/* Instructions */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-medium text-gray-700 mb-2">How it works:</h3>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Upload a PDF document</li>
          <li>• The system extracts and processes the text</li>
          <li>• You can then ask questions about the content</li>
          <li>• If the PDF doesn't contain the answer, ChatGPT will respond with a note</li>
        </ul>
      </div>
    </div>
  )
}
