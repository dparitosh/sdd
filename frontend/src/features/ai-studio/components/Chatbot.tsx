/**
 * Floating AI Chatbot — global assistant available on all pages.
 * Sends messages to POST /api/agents/orchestrator/run with page context.
 * Renders as a floating action button (bottom-right) that opens a chat drawer.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
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

// ---------------------------------------------------------------------------
// Page context + quick-prompt suggestions
// ---------------------------------------------------------------------------

interface PageInfo {
  label: string;
  context: string;       // injected into AI prompt
  suggestions: string[]; // quick-prompt chips shown in chat
}

function buildPageInfo(pathname: string): PageInfo {
  const parts = pathname.split('/').filter(Boolean);

  // Dossier detail: /engineer/simulation/dossiers/:id
  const dossierIdx = parts.indexOf('dossiers');
  if (dossierIdx !== -1 && parts[dossierIdx + 1]) {
    const id = parts[dossierIdx + 1];
    return {
      label: 'Dossier Detail',
      context: `User is viewing Simulation Dossier ID "${id}". Answer questions about this dossier's simulation runs, artifacts, evidence categories, KPIs, verification status, and linked requirements via the digital thread.`,
      suggestions: [
        `What simulation runs are linked to dossier ${id}?`,
        `Show evidence categories for dossier ${id}`,
        `Which requirements does dossier ${id} verify?`,
        `Summarise the results and KPIs of dossier ${id}`,
      ],
    };
  }

  if (parts.includes('mossec-dashboard'))
    return {
      label: 'MoSSEC Dashboard',
      context: 'User is viewing the MoSSEC AP243 Dashboard. Answer queries about the MoSSEC knowledge graph: AP243 node counts, simulation dossiers, runs, artifacts, evidence categories, KPIs, workflow methods, and the digital thread chain.',
      suggestions: [
        'Give me an overview of the MoSSEC knowledge graph',
        'List all simulation dossiers and their evidence categories',
        'Show AP243 model instances and workflow methods',
        'How many AP243 simulation nodes are in the graph?',
      ],
    };

  if (parts.includes('requirements') && parts.includes('ap239'))
    return {
      label: 'AP239 Requirements',
      context: 'User is viewing the AP239 Requirements Dashboard. Answer queries about AP239 PLCS requirements, traceability chains, and OSLC links.',
      suggestions: [
        'List all AP239 requirements',
        'Show traceability from AP239 requirements to design elements',
        'Which AP239 requirements are linked via OSLC?',
        'Find requirements without traceability links',
      ],
    };

  if (parts.includes('requirements'))
    return {
      label: 'Requirements',
      context: 'User is viewing the Requirements Manager. Answer queries about requirements in the graph — search, detail, status, priority, traceability, and satisfaction links.',
      suggestions: [
        'List all requirements in the graph',
        'Find requirements with status "open"',
        'Which components satisfy requirements?',
        'Show requirements missing traceability links',
      ],
    };

  if (parts.includes('traceability'))
    return {
      label: 'Traceability Matrix',
      context: 'User is viewing the Traceability Matrix. Answer queries about full AP239→AP242→AP243 traceability chains: requirements → design elements (Parts) → simulation dossiers → runs → evidence categories. Relationships: SATISFIES, VERIFIED_BY, ALLOCATED_TO, EVIDENCE_FOR.',
      suggestions: [
        'Show traceability from requirements to simulation dossiers',
        'Which requirements are verified by simulation evidence?',
        'List requirements with no linked dossier (unverified)',
        'Show all evidence categories in the graph',
      ],
    };

  if (parts.includes('graph'))
    return {
      label: 'Graph Explorer',
      context: 'User is in the Graph Browser / Knowledge Graph Explorer. The graph has five views: Enterprise, AP239 PLCS, AP242 Product Model, AP243 MoSSEC Simulation, and Digital Thread. Answer queries about node types, relationships, BOM hierarchies, digital thread chains (Req→Part→Dossier→Run→Evidence), and cross-domain AP239/AP242/AP243 linkages.',
      suggestions: [
        'Trace the full digital thread from requirements to evidence',
        'Show the complete AP242 product model graph',
        'List AP243 simulation dossiers and evidence categories',
        'How many nodes are in the graph by type?',
      ],
    };

  if (parts.includes('parts') || parts.includes('ap242'))
    return {
      label: 'Parts (AP242)',
      context: 'User is viewing the AP242 Parts Explorer. Answer queries about the complete AP242 product model: parts, assemblies, BOM hierarchy, materials, CAD geometry, product definitions, and cross-links to requirements and simulation dossiers.',
      suggestions: [
        'Show the complete AP242 product model graph',
        'Show BOM hierarchy — assemblies and their child parts',
        'Which parts have material assignments?',
        'Find parts without a linked requirement',
      ],
    };

  if (parts.includes('product-specs'))
    return {
      label: 'Product Specs',
      context: 'User is on the Product Specifications page. Answer queries about product specifications, parameters, constraints, and their links to requirements and design.',
      suggestions: [
        'List all product specifications',
        'Show parameters for a product spec',
        'Which specs are linked to requirements?',
        'Find overridden or conflicting specs',
      ],
    };

  if (parts.includes('simulation') && parts.includes('models'))
    return {
      label: 'Simulation Models',
      context: 'User is on the AP243 Simulation Models page. Answer queries about simulation model definitions, ModelInstance and ModelType nodes, analysis models, parameter studies, workflow methods, KPIs, and links to AP243 simulation dossiers and evidence chains.',
      suggestions: [
        'List all AP243 simulation model instances',
        'Show ModelType and ModelInstance nodes in the graph',
        'What AP243 workflow methods and task elements are defined?',
        'Show simulation models linked to dossiers and evidence',
      ],
    };

  if (parts.includes('simulation') && parts.includes('runs'))
    return {
      label: 'Simulation Runs',
      context: 'User is on the Simulation Runs page. Answer queries about simulation run status, results, parameters, and linked dossiers.',
      suggestions: [
        'List all simulation runs',
        'Show failed simulation runs',
        'What were the results of the latest run?',
        'Which requirements were verified by simulation?',
      ],
    };

  if (parts.includes('simulation') && parts.includes('results'))
    return {
      label: 'Simulation Results',
      context: 'User is on the Simulation Results page. Answer queries about simulation results, outputs, convergence, and validation outcomes.',
      suggestions: [
        'Summarise latest simulation results',
        'Which simulations passed validation?',
        'Show results for a specific dossier',
        'What were the key output parameters?',
      ],
    };

  if (parts.includes('ontology'))
    return {
      label: 'Ontology Manager',
      context: 'User is in the Ontology Manager. Answer queries about OWL ontologies, classes, properties, namespaces, and loaded ontology files.',
      suggestions: [
        'List all loaded ontologies',
        'What OWL classes exist in the graph?',
        'Show ontology property counts',
        'Which ontologies support AP243?',
      ],
    };

  if (parts.includes('oslc'))
    return {
      label: 'OSLC Browser',
      context: 'User is browsing OSLC resources. Answer queries about OSLC lifecycle links, requirements management resources, and cross-tool traceability via OSLC.',
      suggestions: [
        'Show all OSLC requirement resources',
        'Which OSLC domains are registered?',
        'Find OSLC links to requirements',
        'What is the TRS feed status?',
      ],
    };

  if (parts.includes('shacl'))
    return {
      label: 'SHACL Validator',
      context: 'User is on the SHACL Validator page. Answer queries about SHACL shapes, validation results, constraint violations, and graph conformance.',
      suggestions: [
        'What SHACL shapes are loaded?',
        'Are there any validation violations?',
        'Which nodes fail SHACL constraints?',
        'Summarise the latest validation report',
      ],
    };

  if (parts.includes('plm'))
    return {
      label: 'PLM Integration',
      context: 'User is on the PLM Integration page. Answer queries about PLM connectors, Teamcenter/Windchill integration, BOM data, and part synchronisation.',
      suggestions: [
        'Show configured PLM connectors',
        'List parts synced from Teamcenter',
        'What BOM data is available in the graph?',
        'Show change impact for a part',
      ],
    };

  if (parts.includes('import'))
    return {
      label: 'Data Import',
      context: 'User is on the Data Import page. Answer queries about ingested files, import status, supported formats (XMI, STEP, PLMXML, ontology), and data loading.',
      suggestions: [
        'What data has been imported?',
        'How do I import a STEP file?',
        'Show recent import history',
        'What file formats are supported?',
      ],
    };

  if (parts.includes('insights'))
    return {
      label: 'AI Insights',
      context: 'User is on the AI Insights page. Provide intelligent summaries, anomaly detection, cluster analysis, and recommendations from the knowledge graph.',
      suggestions: [
        'Give me AI insights about the graph',
        'What anomalies exist in the model?',
        'Identify highly connected node clusters',
        'Recommend areas for improvement',
      ],
    };

  if (parts.includes('search'))
    return {
      label: 'Search & Discovery',
      context: 'User is on the Search & Discovery page. Answer queries about any artifact, node, or concept in the knowledge graph.',
      suggestions: [
        'Search for nodes named "Control"',
        'Find all classes related to materials',
        'Search for simulation-related entities',
        'Find nodes with missing properties',
      ],
    };

  if (parts.includes('quality'))
    return {
      label: 'Quality Portal',
      context: 'User is in the Quality Head portal. Answer queries about quality metrics, compliance status, validation findings, and engineering standards.',
      suggestions: [
        'Show current quality metrics',
        'Are there open compliance violations?',
        'Summarise validation findings',
        'What standards are being tracked?',
      ],
    };

  if (parts.includes('admin'))
    return {
      label: 'Admin Portal',
      context: 'User is in the Admin portal. Answer queries about system health, database statistics, index status, and configuration.',
      suggestions: [
        'What are the current graph statistics?',
        'Show database index status',
        'Are there any system errors?',
        'How many nodes were added this week?',
      ],
    };

  // Default / engineer dashboard
  return {
    label: 'Dashboard',
    context: 'User is on the Engineer Dashboard. Answer queries about the overall knowledge graph, recent activity, and any engineering domain.',
    suggestions: [
      'Give me an overview of the knowledge graph',
      'How many requirements are in the system?',
      'What simulations have been run recently?',
      'Show the most connected nodes in the graph',
    ],
  };
}

/** Legacy helper kept for backward compatibility */
function buildPageContext(pathname: string): string {
  return buildPageInfo(pathname).context;
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

      const ctx = buildPageContext(location.pathname);
      const pageInfo = buildPageInfo(location.pathname);
      const prompt = ctx ? `[Context: ${ctx}]\n[Page: ${pageInfo.label}]\n${userMsg}` : userMsg;

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
  const pageInfo = buildPageInfo(location.pathname);
  const showSuggestions = messages.length <= 1 && !sending;
  return (
    <Card className="fixed bottom-6 right-6 z-50 w-96 shadow-2xl flex flex-col max-h-150 rounded-2xl border border-border/60 overflow-hidden">
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 py-3 bg-primary text-primary-foreground rounded-t-2xl">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          <CardTitle className="text-sm font-semibold">KnowledgeGraph AI</CardTitle>
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {pageInfo.label}
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
                  {msg.role === 'assistant' ? (
                    <div
                      className="prose prose-sm dark:prose-invert max-w-none
                        [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-2 [&_h3]:mb-0.5
                        [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-0.5
                        [&_ul]:mt-0.5 [&_ul]:mb-0.5 [&_li]:my-0 [&_table]:text-xs
                        [&_strong]:font-semibold [&_code]:text-xs [&_p]:my-0.5"
                      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(msg.content) as string) }}
                    />
                  ) : (
                    <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                  )}
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

            {/* Page-specific quick prompt suggestions */}
            {showSuggestions && (
              <div className="pt-1 space-y-1.5">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide px-1">Suggested for this page</p>
                {pageInfo.suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(s)}
                    className="w-full text-left text-xs px-3 py-1.5 rounded-lg border border-border/60 bg-muted/40 hover:bg-muted hover:border-primary/40 transition-colors leading-snug"
                  >
                    {s}
                  </button>
                ))}
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
