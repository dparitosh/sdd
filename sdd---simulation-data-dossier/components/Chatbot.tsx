
import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, User } from 'lucide-react';
import { getGeminiResponse } from '../services/geminiService';

interface ChatbotProps {
  context: any;
}

const Chatbot: React.FC<ChatbotProps> = ({ context }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{role: 'bot' | 'user', text: string}[]>([
    { role: 'bot', text: 'Welcome to SDD Intelligence. How can I assist you with your motor simulation data or MOSSEC compliance today?' }
  ]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setLoading(true);

    const response = await getGeminiResponse(userMsg, context);
    setMessages(prev => [...prev, { role: 'bot', text: response }]);
    setLoading(false);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {isOpen ? (
        <div className="w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-200">
          <div className="p-4 bg-slate-900 text-white flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Bot size={20} className="text-[#00B0E4]" />
              <span className="font-semibold">SDD AI Assistant</span>
            </div>
            <button onClick={() => setIsOpen(false)} className="hover:text-slate-300">
              <X size={20} />
            </button>
          </div>
          
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                  m.role === 'user' ? 'bg-[#004A99] text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-700 rounded-tl-none'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-200 p-3 rounded-2xl rounded-tl-none animate-pulse">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-slate-200 bg-white">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Query dossier status..."
                className="flex-1 bg-slate-100 border-none rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#004A99]"
              />
              <button 
                onClick={handleSend}
                disabled={loading}
                className="bg-[#004A99] text-white p-2 rounded-lg hover:bg-[#003d7a] transition-colors disabled:opacity-50"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button 
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 bg-[#004A99] text-white rounded-full shadow-lg flex items-center justify-center hover:scale-110 transition-transform"
        >
          <MessageSquare size={24} />
        </button>
      )}
    </div>
  );
};

export default Chatbot;
