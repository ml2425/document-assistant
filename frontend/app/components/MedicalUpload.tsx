'use client'

import { useState, useRef } from 'react'

interface MedicalUploadProps {
  onUploadSuccess: (filename: string, pages: number, chunks: number, category: string) => void
  onUploadError: (error: string) => void
}

export default function MedicalUpload({ onUploadSuccess, onUploadError }: MedicalUploadProps) {
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
    setUploadStatus('Uploading and processing medical document...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload-medical', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      setUploadStatus(`✅ Medical document processed successfully!`)
      onUploadSuccess(result.filename, result.pages, result.chunks, result.category)
      
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
      <h2 className="text-xl font-semibold mb-4">Upload Medical Document</h2>
      
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="text-6xl text-gray-400">🏥</div>
          
          <div>
            <p className="text-lg font-medium text-gray-700">
              {isUploading ? 'Processing medical document...' : 'Drop your medical PDF here'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Lab results, clinical notes, research papers, etc.
            </p>
          </div>

          <button
            onClick={openFileDialog}
            disabled={isUploading}
            className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? 'Processing...' : 'Choose Medical PDF'}
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
      <div className="mt-6 p-4 bg-green-50 rounded-lg">
        <h3 className="font-medium text-green-700 mb-2">Medical Document Analysis:</h3>
        <ul className="text-sm text-green-600 space-y-1">
          <li>• Upload medical documents (lab results, clinical notes, research papers)</li>
          <li>• AI will categorize the document after your first question</li>
          <li>• Smart quality assessment determines response strategy</li>
          <li>• Export conversation as JSON for external ChatGPT use</li>
          <li>• Includes medical disclaimers - not valid medical advice</li>
        </ul>
      </div>

      {/* Medical Disclaimer */}
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          <strong>Medical Disclaimer:</strong> This tool provides information based on uploaded documents and AI analysis. 
          It is not a substitute for professional medical advice, diagnosis, or treatment. 
          Always consult with qualified healthcare professionals for medical decisions.
        </p>
      </div>
    </div>
  )
}
