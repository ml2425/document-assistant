'use client'

import { useState } from 'react'
import ChatInterface from './components/ChatInterface'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            ChatGPT Clone
          </h1>
          <p className="text-gray-600 mt-1">
            Phase 1: Simple Conversation
          </p>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <ChatInterface />
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
