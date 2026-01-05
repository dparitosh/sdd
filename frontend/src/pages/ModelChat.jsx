import { useState } from 'react';
import { Card, CardContent } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { ScrollArea } from '@ui/scroll-area';
import { Sparkles, Send, Bot, User } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
export default function ModelChat() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: 'Hello! I can help you explore your knowledge graph. Ask me about requirements, components, simulations, or traceability.'
  }]);
  const [input, setInput] = useState('');
  const handleSend = () => {
    if (!input.trim()) return;
    setMessages([...messages, {
      role: 'user',
      content: input
    }]);
    setInput('');
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'This is a placeholder response. The AI chat will be integrated with your knowledge graph to provide intelligent answers about your engineering data.'
      }]);
    }, 1000);
  };
  return <div className="container mx-auto p-6 h-[calc(100vh-8rem)] flex flex-col space-y-6"><PageHeader title="Model Chat" description="Conversational interface to explore your knowledge graph using natural language" icon={<Sparkles className="h-6 w-6 text-primary" />} badge="AI Beta" breadcrumbs={[{
      label: 'GenAI Studio',
      href: '/ai/insights'
    }, {
      label: 'Model Chat'
    }]} /><Card className="flex-1 flex flex-col"><CardContent className="flex-1 flex flex-col gap-4 pt-6"><ScrollArea className="flex-1 pr-4"><div className="space-y-4">{messages.map((msg, idx) => <div className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>{msg.role === 'assistant' && <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0"><Bot className="h-4 w-4 text-primary" /></div>}<div className={`max-w-[80%] p-4 rounded-lg ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}><p className="text-sm">{msg.content}</p></div>{msg.role === 'user' && <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0"><User className="h-4 w-4 text-primary-foreground" /></div>}</div>)}</div></ScrollArea><div className="flex gap-2"><Input placeholder="Ask me anything about your knowledge graph..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSend()} className="flex-1" /><Button onClick={handleSend}><Send className="h-4 w-4" /></Button></div><div className="flex gap-2 flex-wrap"><Badge variant="outline" className="cursor-pointer hover:bg-primary/10">Show all requirements</Badge><Badge variant="outline" className="cursor-pointer hover:bg-primary/10">Find unlinked components</Badge><Badge variant="outline" className="cursor-pointer hover:bg-primary/10">Simulation results summary</Badge></div></CardContent></Card></div>;
}
