import React, { useState, useEffect, useCallback } from 'react';

// --- CONFIG ---
const GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025';
const API_KEY = ""; // Đặt API key sau
const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${API_KEY}`;

// Tạo UID ổn định mỗi lần load app
const userId = 'GiaSu_' + crypto.randomUUID().slice(0, 8);
const appId = 'SAFE-MODE-APP';

// Format giờ
const formatTime = (timestamp) => {
  if (!timestamp) return '...';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
};

// API Gemini
const fetchGeminiResponse = async (prompt) => {
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    systemInstruction: {
      parts: [{ text: "Bạn là Gia sư ảo thân thiện, giải thích chậm rãi, dễ hiểu." }]
    },
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
        return data.candidates?.[0]?.content?.parts?.[0]?.text || "Xin lỗi, tôi không tìm thấy câu trả lời.";
      }

      retry++;
      await new Promise(r => setTimeout(r, 1000 * 2 ** retry));
    }

    return "Xin lỗi, API hiện không phản hồi. Hãy thử lại.";
  } catch (err) {
    console.error(err);
    return "Đã xảy ra lỗi không xác định.";
  }
};

// Dashboard
const ActivityDashboard = ({ currentUserId }) => (
  <div className="mt-4 p-4 rounded-xl bg-yellow-50 border border-yellow-200">
    <h2 className="text-xl font-bold text-yellow-700 mb-2">Bảng Điều Khiển Hoạt Động (Chế Độ An Toàn)</h2>
    <p className="text-sm text-yellow-600 font-semibold">Tính năng lưu trữ tạm thời bị tắt để ổn định ứng dụng.</p>
    <p className="text-xs text-yellow-600 mt-1">Chỉ hỗ trợ chat với Gia sư ảo.</p>
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
    console.log(`[LOG] ${type}`, { userId, time: Date.now(), ...details });
  }, [ready]);

  // Gửi tin nhắn
  const handleSend = async () => {
    const text = input.trim();
    if (!text || isTyping || !ready) return;

    const newMsg = {
      id: crypto.randomUUID(),
      userId,
      message: text,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setIsTyping(true);

    logActivity('USER_MESSAGE', { length: text.length });

    // Lấy phản hồi AI
    const reply = await fetchGeminiResponse(text);

    const aiMsg = {
      id: crypto.randomUUID(),
      userId: 'AI-GiaSu',
      message: reply,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, aiMsg]);
    setIsTyping(false);
    logActivity('AI_MESSAGE', { length: reply.length });
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4 flex flex-col items-center">
      <div className="w-full max-w-xl bg-white p-6 rounded-xl shadow-2xl">
        <h1 className="text-3xl font-extrabold text-center text-green-700 mb-2">Gia Sư Ảo Chat</h1>
        <p className="text-sm text-center text-gray-500 mb-4">Chế độ an toàn / Không lưu trữ</p>

        <div className="p-3 mb-4 rounded-lg border bg-green-100 border-green-400">
          <p className="text-sm font-bold text-green-700">[OK] Sẵn sàng sử dụng</p>
          <p className="text-xs text-gray-600">UID: <span className="font-mono bg-gray-200 px-1 rounded">{userId}</span></p>
        </div>

        <ActivityDashboard currentUserId={userId} />

        {/* Messages */}
        <div className="h-96 overflow-y-auto p-3 bg-gray-50 rounded-lg my-4 border space-y-3">
          {messages.length === 0 ? (
            <p className="text-center text-gray-400 italic">Hãy hỏi Gia sư ảo một câu!</p>
          ) : messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.userId === userId ? 'justify-end' : 'justify-start'}`}>
              <div className={`p-3 rounded-xl max-w-[80%] shadow-md ${msg.userId === userId ? 'bg-green-500 text-white rounded-tr-sm' : 'bg-indigo-100 text-gray-800 rounded-tl-sm'}`}>
                <p className={`text-xs font-bold mb-1 ${msg.userId === userId ? 'text-green-200' : 'text-indigo-600'}`}>
                  {msg.userId === userId ? 'Bạn' : 'Gia sư ảo'}
                </p>
                <p className="text-sm whitespace-pre-wrap">{msg.message}</p>
                <span className="text-xs block text-right opacity-70">{formatTime(msg.timestamp)}</span>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="p-3 bg-gray-200 rounded-xl shadow-md animate-pulse">
                Gia sư đang gõ...
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex space-x-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isTyping ? "Đang chờ AI..." : "Nhập câu hỏi..."}
            disabled={!ready || isTyping}
            className="flex-grow p-3 border rounded-lg focus:ring-green-500 focus:border-green-500 disabled:bg-gray-200"
          />

          <button
            onClick={handleSend}
            disabled={!ready || !input.trim() || isTyping}
            className="px-4 py-3 bg-green-600 text-white rounded-lg shadow-md hover:bg-green-700 disabled:opacity-50"
          >
            {isTyping ? 'Đang gửi...' : 'Gửi'}
          </button>
        </div>

        <p className="text-center mt-4 text-xs text-gray-400">App ID: {appId}</p>
      </div>
    </div>
  );
}
