import React, { useState, useEffect, useCallback } from 'react';

// CẢNH BÁO: ĐÃ LOẠI BỎ TẤT CẢ CODE FIREBASE ĐỂ TRÁNH LỖI CẤU HÌNH
// Ứng dụng đang chạy ở chế độ giả lập (In-Memory). Dữ liệu sẽ mất khi làm mới trang.

// --- Cấu hình Giả lập & API ---
let chatMessages = [];
const userId = 'GiaSu_' + Math.random().toString(36).substring(2, 8); 
const appId = 'In-Memory-App';

// Cấu hình API Gemini
const GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025';
const API_KEY = ""; // Sẽ được Canvas cung cấp
const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${API_KEY}`;
// --- KẾT THÚC CẤU HÌNH ---

// Hàm định dạng thời gian
const formatTime = (timestamp) => {
    if (!timestamp) return '...';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
};

// Component Giả lập Dashboard Hoạt động
const ActivityDashboard = ({ currentUserId }) => {
    return (
        <div className="mt-4 p-4 rounded-xl bg-yellow-50 border border-yellow-200">
            <h2 className="text-xl font-bold text-yellow-700 mb-2">Bảng Điều Khiển Hoạt Động (ĐANG GIẢ LẬP)</h2>
            <p className="text-sm text-yellow-600 font-semibold">
                ❌ LỖI KỸ THUẬT FIREBASE ĐÃ XẢY RA! Ứng dụng đang chạy chế độ ổn định/không lưu trữ.
            </p>
            <p className="text-xs text-yellow-600 mt-2">
                Hoạt động chỉ được **GHI LOG VÀO CONSOLE** để mô phỏng. Dữ liệu sẽ không được lưu vĩnh viễn lúc này.
            </p>
        </div>
    );
};

// --- LOGIC GỌI API GEMINI MỚI ---
const fetchGeminiResponse = async (prompt) => {
    const systemInstruction = "Bạn là Gia sư ảo thân thiện và kiên nhẫn. Nhiệm vụ của bạn là giải đáp các câu hỏi về Toán, Lý, Hóa cho học sinh cấp 2 và cấp 3. Hãy đưa ra câu trả lời chi tiết, dễ hiểu và khuyến khích học sinh đặt thêm câu hỏi.";
    
    const payload = {
        contents: [{ parts: [{ text: prompt }] }],
        systemInstruction: {
            parts: [{ text: systemInstruction }]
        },
    };

    try {
        let response;
        let retryCount = 0;
        const maxRetries = 3;
        
        // Thực hiện Retry với Exponential Backoff
        while (retryCount < maxRetries) {
            response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const result = await response.json();
                const text = result.candidates?.[0]?.content?.parts?.[0]?.text || "Xin lỗi, tôi không thể tìm thấy câu trả lời.";
                return text;
            }

            // Nếu không OK, chờ và thử lại
            retryCount++;
            const delay = Math.pow(2, retryCount) * 1000;
            if (retryCount < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        // Nếu tất cả các lần thử đều thất bại
        return "Xin lỗi, tôi đang gặp lỗi kết nối API. Vui lòng thử lại sau.";

    } catch (error) {
        console.error("Lỗi gọi API Gemini:", error);
        return "Xin lỗi, đã xảy ra lỗi không xác định khi xử lý yêu cầu của bạn.";
    }
};

const App = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isAppReady, setIsAppReady] = useState(false);
    const [isTyping, setIsTyping] = useState(false); // Trạng thái AI đang gõ
    
    useEffect(() => {
        setMessages([...chatMessages]); 
        setIsAppReady(true);
        console.log(`[LOG GIẢ LẬP] APP_LOAD_SUCCESS: User ${userId} tải ứng dụng.`);
    }, []);

    const logActivity = useCallback((activityType, details = {}) => {
        if (!isAppReady) return;
        console.log(`[LOG GIẢ LẬP] ${activityType}:`, { userId, timestamp: Date.now(), ...details });
    }, [isAppReady]);


    // --- 3. Xử lý Gửi Tin nhắn (Tích hợp AI) ---
    const handleSendMessage = async () => {
        const userMessage = inputMessage.trim();
        if (!userMessage || !isAppReady || isTyping) return;

        // 1. Hiển thị tin nhắn của người dùng ngay lập tức
        const newUserMessage = {
            id: Date.now(),
            userId: userId,
            message: userMessage,
            timestamp: Date.now()
        };
        chatMessages.push(newUserMessage);
        setMessages([...chatMessages]);
        
        logActivity('SEND_MESSAGE_USER', { messageLength: userMessage.length });

        setInputMessage('');
        setIsTyping(true); // Bắt đầu trạng thái "AI đang gõ"
        
        // 2. Gọi API để lấy phản hồi của Gia sư ảo
        const aiResponseText = await fetchGeminiResponse(userMessage);

        // 3. Hiển thị phản hồi của Gia sư ảo
        const aiMessage = {
            id: Date.now() + 1,
            userId: 'Gemini-GiaSu', // ID đặc biệt cho AI
            message: aiResponseText,
            timestamp: Date.now() + 1 // Đảm bảo ID và thời gian khác nhau
        };

        chatMessages.push(aiMessage);
        setMessages([...chatMessages]);
        
        logActivity('SEND_MESSAGE_AI', { messageLength: aiResponseText.length });

        setIsTyping(false); // Kết thúc trạng thái "AI đang gõ"
    };

    // --- Giao Diện ---
    return (
        <div className="min-h-screen bg-gray-100 p-4 flex flex-col items-center">
            <div className="w-full max-w-xl bg-white p-6 rounded-xl shadow-2xl">
                <h1 className="text-3xl font-extrabold text-center text-green-700 mb-2">Gia Sư Ảo Chat (Có AI)</h1>
                <p className="text-sm text-center text-gray-500 mb-4">Ứng dụng ổn định, có thể hỏi đáp Toán Lý Hóa.</p>

                {/* HỘP TRẠNG THÁI MỚI (Màu Xanh Lá) */}
                <div className="p-3 mb-4 rounded-lg border shadow-sm bg-green-100 border-green-400">
                    <p className="text-sm font-bold text-green-700">
                        ✅ Sẵn sàng (AI Đã Tích hợp)
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                        UID Giả Lập: <span className="font-mono text-xs p-1 bg-gray-200 rounded">{userId}</span>
                    </p>
                </div>
                
                {/* Dashboard Hoạt động (Giả lập) */}
                <ActivityDashboard currentUserId={userId} />

                {/* Khu Vực Hiển Thị Tin Nhắn */}
                <div className="h-96 overflow-y-auto p-3 bg-gray-50 rounded-lg my-4 border border-gray-200 space-y-3">
                    {messages.length === 0 ? (
                        <p className="text-center text-gray-400 italic">
                            Chào bạn! Hãy hỏi Gia sư ảo của bạn một câu hỏi về Toán, Lý, Hóa!
                        </p>
                    ) : (
                        messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.userId === userId ? 'justify-end' : 'justify-start'}`}>
                                <div className={`p-3 rounded-xl max-w-[80%] shadow-md ${msg.userId === userId 
                                    ? 'bg-green-500 text-white rounded-tr-sm' 
                                    : 'bg-indigo-100 text-gray-800 rounded-tl-sm'}`}>
                                    <p className={`text-xs font-bold mb-1 ${msg.userId === userId ? 'text-green-200' : 'text-indigo-600'}`}>
                                        {msg.userId === userId ? 'Bạn' : 'Gia sư ảo Gemini'}
                                    </p>
                                    <p className="text-sm break-words whitespace-pre-wrap">{msg.message}</p>
                                    <span className={`text-xs italic mt-1 block text-right ${msg.userId === userId ? 'text-green-300' : 'text-indigo-400'}`}>
                                        {formatTime(msg.timestamp)}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                    {/* Hiển thị trạng thái "Đang gõ" */}
                    {isTyping && (
                        <div className="flex justify-start">
                            <div className="p-3 rounded-xl max-w-[80%] bg-gray-200 text-gray-800 rounded-tl-sm shadow-md">
                                <span className="animate-pulse text-sm">Gia sư ảo đang gõ...</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Khu Vực Nhập Tin Nhắn */}
                <div className="flex space-x-2">
                    <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder={isTyping ? "Đang chờ Gia sư trả lời..." : "Nhập câu hỏi về Toán, Lý, Hóa..."}
                        className="flex-grow p-3 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 disabled:bg-gray-50"
                        disabled={!isAppReady || isTyping}
                    />
                    <button
                        onClick={handleSendMessage}
                        className="px-4 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 transition duration-150 disabled:opacity-50"
                        disabled={!isAppReady || !inputMessage.trim() || isTyping}
                    >
                        {isTyping ? 'Đang gửi...' : 'Gửi'}
                    </button>
                </div>
                
                <p className="text-center mt-4 text-xs text-gray-400">App ID: {appId}</p>
            </div>
        </div>
    );
};

export default App;
