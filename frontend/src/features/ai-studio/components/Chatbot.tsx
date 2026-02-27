/**
 * Floating AI Chatbot — global assistant available on all pages.
 * Sends messages to POST /api/agents/orchestrator/run with page context.
 * Renders as a floating action button (bottom-right) that opens a chat drawer.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { ScrollArea } from '@ui/scroll-area';
import {
  MessageCircle,
  Send,
  Bot,
  User,
  Loader2,
  X,
  Minus,
  Sparkles,
} from 'lucide-react';
import { runOrchestrator } from '@/services/agents.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

/** Extract page context from the current URL to inject into the AI prompt */
function buildPageContext(pathname: string): string {
  const parts = pathname.split('/').filter(Boolean);

  // Detect dossier detail pages: /engineer/simulation/dossiers/:id
  const dossierIdx = parts.indexOf('dossiers');
  if (dossierIdx !== -1 && parts[dossierIdx + 1]) {
    return `User is viewing Simulation Dossier ID "${parts[dossierIdx + 1]}".`;
  }

  // Detect requirements page
  if (parts.includes('requirements')) return 'User is viewing the Requirements page.';
  if (parts.includes('traceability')) return 'User is viewing the Traceability Matrix.';
  if (parts.includes('graph')) return 'User is viewing the Graph Browser.';
  if (parts.includes('parts')) return 'User is viewing the Parts Explorer.';
  if (parts.includes('semantic')) return 'User is in the Semantic Web tools section.';
  if (parts.includes('quality')) return 'User is in the Quality Head portal.';
  if (parts.includes('admin')) return 'User is in the Admin portal.';

  return '';
}

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [minimised, setMinimised] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Hi! I\'m the KnowledgeGraph AI assistant. Ask me about dossiers, requirements, simulations, traceability, or anything in your graph.',
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Auto-scroll to newest message
  useEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        '[data-radix-scroll-area-viewport]',
      );
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [messages]);

  const handleSend = useCallback(
    async (text?: string) => {
      const userMsg = (text ?? input).trim();
      if (!userMsg || sending) return;

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: userMsg, timestamp: Date.now() },
      ]);
      setInput('');
      setSending(true);

      // Build prompt with page context
      const ctx = buildPageContext(location.pathname);
      const prompt = ctx ? `[Context: ${ctx}]\n${userMsg}` : userMsg;

      try {
        const result = await runOrchestrator(prompt, 'knowledge_query');
        const data = (result as any)?.data ?? result;
        const reply =
          data?.messages?.length > 0
            ? data.messages[data.messages.length - 1]?.content ??
              JSON.stringify(data.final_state ?? data, null, 2)
            : data?.final_state
              ? JSON.stringify(data.final_state, null, 2)
              : 'No response received from the orchestrator.';
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: reply, timestamp: Date.now() },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `Error: ${err instanceof Error ? err.message : 'Failed to reach the AI agent. Please ensure the backend is running.'}`,
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [input, sending, location.pathname],
  );

  // ----- Floating Action Button (always visible) -----
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-primary text-primary-foreground shadow-xl flex items-center justify-center hover:scale-110 active:scale-95 transition-transform"
        aria-label="Open AI Chatbot"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    );
  }

  // ----- Minimised pill -----
  if (minimised) {
    return (
      <button
        onClick={() => setMinimised(false)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-primary-foreground shadow-xl hover:scale-105 active:scale-95 transition-transform"
        aria-label="Expand chatbot"
      >
        <Bot className="h-4 w-4" />
        <span className="text-sm font-medium">AI Chat</span>
        {sending && <Loader2 className="h-3 w-3 animate-spin" />}
      </button>
    );
  }

  // ----- Full chat drawer -----
  return (
    <Card className="fixed bottom-6 right-6 z-50 w-96 shadow-2xl flex flex-col max-h-150 rounded-2xl border border-border/60 overflow-hidden">
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 py-3 bg-primary text-primary-foreground rounded-t-2xl">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          <CardTitle className="text-sm font-semibold">KnowledgeGraph AI</CardTitle>
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            Beta
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-primary-foreground hover:bg-primary-foreground/20"
            onClick={() => setMinimised(true)}
            aria-label="Minimise chat"
          >
            <Minus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-primary-foreground hover:bg-primary-foreground/20"
            onClick={() => setOpen(false)}
            aria-label="Close chat"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      {/* Messages */}
      <CardContent className="flex-1 flex flex-col gap-3 p-3 overflow-hidden">
        <ScrollArea ref={scrollRef} className="flex-1 pr-2">
          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-sm'
                      : 'bg-muted rounded-bl-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>
                {msg.role === 'user' && (
                  <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center shrink-0 mt-0.5">
                    <User className="h-3.5 w-3.5 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="flex gap-2 justify-start">
                <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="bg-muted px-3 py-2 rounded-xl rounded-bl-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="flex gap-2 pt-1 border-t">
          <Input
            placeholder="Ask anything…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            className="flex-1 text-sm"
            disabled={sending}
          />
          <Button
            size="icon"
            onClick={() => handleSend()}
            disabled={sending}
            className="shrink-0"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
