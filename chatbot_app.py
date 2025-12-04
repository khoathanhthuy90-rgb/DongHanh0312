import React, { useState, useEffect, useCallback } from 'react';

// CONFIG
// Note: Add your API key here. Do not leave it empty.
const GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025';
const API_KEY = ""; // Add your API key here
const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${API_KEY}`;

// Create unique ID
const userId = 'GiaSu_' + (window.crypto?.randomUUID?.().slice(0, 8) || "User1234");
const appId = 'SAFE-MODE-APP';

// Format timestamp
const formatTime = (timestamp) => {
  if (!timestamp) return '...';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
};

// Gemini API
const fetchGeminiResponse = async (prompt) => {
  if (!API_KEY) return "Loi: Ban chua nhap API KEY.";

  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    systemInstruction: {
      parts: [{ text: "Ban la gia su ao than thien, giai thich cham rai, de hieu." }]
    }
  };

  try {
    let retry = 0;
    const maxRetry = 3;

    while (retry < maxRetry) {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || "Khong tim thay cau tra loi.";
      }

      retry++;
      await new Promise(r => setTimeout(r, 1000 * 2 ** retry));
    }

    return "API hien khong phan hoi. Vui long thu lai.";
  } catch (err) {
    console.error(err);
    return "Da xay ra loi.";
  }
};

// Dashboard
const ActivityDashboard = ({ currentUserId }) => (
  <div className="mt-4 p-4 rounded-xl bg-yellow-50 border border-yellow-200">
    <h2 className="text-xl font-bold text-yellow-700 mb-2">Bang dieu khien hoat dong (Safe Mode)</h2>
    <p className="text-sm text-yellow-600 font-semibold">Luu tru tam thoi da tat.</p>
    <p className="text-xs text-yellow-600 mt-1">Chi ho tro chat voi Gia su ao.</p>
  </div>
);

// APP
export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
    console.log("APP LOADED — UID:", userId);
  }, []);

  const logActivity = useCallback((type, details = {}) => {
    if (!ready) return;
    console.log("[LOG]", type, { userId, time: Date.now(), ...details });
  }, [ready]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isTyping || !ready) return;

    const newMsg = {
      id: window.crypto.randomUUID(),
      userId,
      message: text,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setIsTyping(true);

    logActivity("USER_MESSAGE", { length: text.length });

    const reply = await fetchGeminiResponse(text);

    const aiMsg = {
      id: window.crypto.randomUUID(),
      userId: 'AI-GiaSu',
      message: reply,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, aiMsg]);
    setIsTyping(false);
    logActivity("AI_MESSAGE", { length: reply.length });
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4 flex flex-col items-center">
      <div className="w-full max-w-xl bg-white p-6 rounded-xl shadow-2xl">
        <h1 className="text-3xl font-extrabold text-center text-green-700 mb-2">Gia Su Ao Chat</h1>
        <p className="text-sm text-center text-gray-500 mb-4">Safe Mode / Khong luu tru</p>

        <div className="p-3 mb-4 rounded-lg border bg-green-100 border-green-400">
          <p className="text-sm font-bold text-green-700">Da san sang</p>
          <p className="text-xs text-gray-600">UID: {userId}</p>
        </div>

        <ActivityDashboard currentUserId={userId} />

        <div className="h-96 overflow-y-auto p-3 bg-gray-50 rounded-lg my-4 border space-y-3">
          {messages.length === 0 ? (
            <p className="text-center text-gray-400 italic">Hay bat dau hoi mot cau hoi!</p>
          ) : messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.userId === userId ? 'justify-end' : 'justify-start'}`}>
              <div className={`p-3 rounded-xl max-w-[80%] shadow-md ${msg.userId === userId ? 'bg-green-500 text-white' : 'bg-indigo-100 text-gray-800'}`}>
                <p className="text-xs font-bold mb-1">
                  {msg.userId === userId ? 'Ban' : 'Gia su ao'}
                </p>
                <p>{msg.message}</p>
                <span className="text-xs block text-right opacity-70">{formatTime(msg.timestamp)}</span>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="p-3 bg-gray-200 rounded-xl shadow-md animate-pulse">
                Gia su dang go...
              </div>
            </div>
          )}
        </div>

        <div className="flex space-x-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Nhap cau hoi..."
            disabled={!ready || isTyping}
            className="flex-grow p-3 border rounded-lg"
          />

          <button
            onClick={handleSend}
            disabled={!ready || !input.trim() || isTyping}
            className="px-4 py-3 bg-green-600 text-white rounded-lg"
          >
            {isTyping ? 'Dang gui...' : 'Gui'}
          </button>
        </div>

        <p className="text-center mt-4 text-xs text-gray-400">App ID: {appId}</p>
      </div>
    </div>
  );
}
