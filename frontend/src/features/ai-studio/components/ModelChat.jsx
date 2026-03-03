import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Card, CardContent } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { ScrollArea } from '@ui/scroll-area';
import { Sparkles, Send, Bot, User, Loader2, Search, MessageSquare } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { runOrchestrator, semanticSearch, semanticInsight } from '@/services/agents.service';

// Enable GFM line-breaks in markdown responses
marked.setOptions({ breaks: true });

/** Inject page context hint into queries */
function buildPageContext(pathname) {
  const parts = pathname.split('/').filter(Boolean);
  const dossierIdx = parts.indexOf('dossiers');
  if (dossierIdx !== -1 && parts[dossierIdx + 1])
    return `User is viewing Simulation Dossier "${parts[dossierIdx + 1]}".`;
  if (parts.includes('requirements')) return 'User is on the Requirements page.';
  if (parts.includes('traceability')) return 'User is viewing the Traceability Matrix.';
  if (parts.includes('graph')) return 'User is in the Graph Browser.';
  if (parts.includes('parts')) return 'User is on the Parts Explorer.';
  if (parts.includes('ontolog')) return 'User is viewing the Ontology section.';
  if (parts.includes('step')) return 'User is in the STEP files section.';
  if (parts.includes('admin')) return 'User is in the Admin portal.';
  return '';
}

const QUICK_PROMPTS = [
  { label: 'Show requirements',      query: 'Show all requirements',                               taskType: 'traceability'    },
  { label: 'KG overview',            query: 'Give me a MoSSEC knowledge graph overview',            taskType: 'knowledge_query' },
  { label: 'Ingestion status',       query: 'What is the current ingestion status and pipeline?',   taskType: 'knowledge_query' },
  { label: 'Schema & labels',        query: 'Show all node labels and relationship types',          taskType: 'knowledge_query' },
  { label: 'Ontology summary',       query: 'Summarise loaded ontologies and reference data',       taskType: 'knowledge_query' },
  { label: 'STEP files',             query: 'What STEP files are loaded and how many instances?',   taskType: 'knowledge_query' },
  { label: 'Unlinked requirements',  query: 'Find requirements with no traceability links',         taskType: 'traceability'    },
  { label: 'Simulation artifacts',   query: 'Simulation dossiers and artifacts summary',            taskType: 'knowledge_query' },
];
export default function ModelChat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hello! I can help you explore your knowledge graph. Ask me about requirements, ontologies, STEP files, simulations, traceability, or import/ingestion status.',
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [searchMode, setSearchMode] = useState('general'); // 'general' | 'semantic'
  const scrollRef = useRef(null);
  const location = useLocation();

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        '[data-radix-scroll-area-viewport]',
      );
      if (viewport) viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text, taskType = 'knowledge_query') => {
    const userMsg = (text || input).trim();
    if (!userMsg || sending) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMsg, timestamp: Date.now() },
    ]);
    setInput('');
    setSending(true);

    // Inject page context into the prompt
    const ctx = buildPageContext(location.pathname);
    const prompt = ctx ? `[Context: ${ctx}]\n${userMsg}` : userMsg;

    try {
      let reply = '';
      let sources = [];

      if (searchMode === 'semantic') {
        // Semantic RAG pipeline
        const result = await semanticInsight(prompt);
        const data = result?.data ?? result;
        reply = data?.answer || 'No semantic insight generated.';
        sources = data?.sources || [];
      } else {
        // Standard orchestrator
        const result = await runOrchestrator(prompt, taskType);
        const data = result?.data ?? result;
        reply =
          data?.messages?.length > 0
            ? data.messages[data.messages.length - 1]?.content ??
              JSON.stringify(data.final_state ?? data, null, 2)
            : data?.final_state
              ? JSON.stringify(data.final_state, null, 2)
              : 'No response received from the orchestrator.';
      }

      // Append source citations if present
      if (sources.length > 0) {
        reply +=
          '\n\n---\n**Sources:**\n' +
          sources
            .slice(0, 10)
            .map((s) => `- \`${s.uid || '?'}\` ${s.name || ''}`)
            .join('\n');
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply, timestamp: Date.now(), sources },
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
  };

  return (
    <div className="container mx-auto p-6 h-[calc(100vh-8rem)] flex flex-col space-y-6">
      <PageHeader
        title="Model Chat"
        description="Conversational interface to explore your knowledge graph using natural language"
        icon={<Sparkles className="h-6 w-6 text-primary" />}
        badge="AI Beta"
        breadcrumbs={[
          { label: 'GenAI Studio', href: '/ai/insights' },
          { label: 'Model Chat' },
        ]}
      />

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardContent className="flex-1 flex flex-col gap-4 pt-6 overflow-hidden">
          {/* Message list */}
          <ScrollArea ref={scrollRef} className="flex-1 pr-4">
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] p-4 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div
                        className="text-sm prose prose-sm dark:prose-invert max-w-none
                          [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1
                          [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1
                          [&_ul]:mt-1 [&_ul]:mb-1 [&_li]:my-0 [&_table]:text-xs
                          [&_strong]:font-semibold [&_code]:text-xs [&_p]:my-1"
                        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(msg.content)) }}
                      />
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    )}
                    {msg.timestamp && (
                      <p className="text-[10px] opacity-50 mt-1 text-right">
                        {new Date(msg.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0 mt-0.5">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {sending && (
                <div className="flex gap-3 justify-start">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-muted p-4 rounded-lg flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      {searchMode === 'semantic'
                        ? 'Searching graph + OpenSearch...'
                        : 'Processing...'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Quick prompts */}
          <div className="flex gap-2 flex-wrap">
            {QUICK_PROMPTS.map(({ label, query, taskType }) => (
              <Badge
                key={label}
                variant="outline"
                className="cursor-pointer hover:bg-primary/10 transition-colors text-xs"
                onClick={() => handleSend(query, taskType)}
              >
                {label}
              </Badge>
            ))}
          </div>

          {/* Search mode toggle + Input */}
          <div className="flex gap-2 border-t pt-3">
            <Button
              variant={searchMode === 'general' ? 'default' : 'outline'}
              size="sm"
              className="shrink-0"
              onClick={() => setSearchMode('general')}
              title="General KG query"
            >
              <MessageSquare className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={searchMode === 'semantic' ? 'default' : 'outline'}
              size="sm"
              className="shrink-0"
              onClick={() => setSearchMode('semantic')}
              title="Semantic search (RAG)"
            >
              <Search className="h-3.5 w-3.5" />
            </Button>
            <Input
              placeholder={
                searchMode === 'semantic'
                  ? 'Semantic search across graph + vectors...'
                  : 'Ask me anything about your knowledge graph...'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              className="flex-1"
              disabled={sending}
            />
            <Button onClick={() => handleSend()} disabled={sending}>
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
