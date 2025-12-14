import { useState } from 'react';
import { Card, CardContent } from '@ui/card';
import { Badge } from '@ui/badge';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { ScrollArea } from '@ui/scroll-area';
import { Sparkles, Send, Bot, User } from 'lucide-react';
import PageHeader from '@/components/PageHeader';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function ModelChat() {
  const [messages, setMessages] = useState([
  {
    role: 'assistant',
    content: 'Hello! I can help you explore your knowledge graph. Ask me about requirements, components, simulations, or traceability.'
  }]
  );
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;

    setMessages([...messages, { role: 'user', content: input }]);
    setInput('');

    // Simulate AI response
    setTimeout(() => {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'This is a placeholder response. The AI chat will be integrated with your knowledge graph to provide intelligent answers about your engineering data.'
      }]);
    }, 1000);
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 h-[calc(100vh-8rem)] flex flex-col space-y-6", children: [/*#__PURE__*/
      _jsx(PageHeader, {
        title: "Model Chat",
        description: "Conversational interface to explore your knowledge graph using natural language",
        icon: /*#__PURE__*/_jsx(Sparkles, { className: "h-6 w-6 text-primary" }),
        badge: "AI Beta",
        breadcrumbs: [
        { label: 'GenAI Studio', href: '/ai/insights' },
        { label: 'Model Chat' }] }

      ), /*#__PURE__*/

      _jsx(Card, { className: "flex-1 flex flex-col", children: /*#__PURE__*/
        _jsxs(CardContent, { className: "flex-1 flex flex-col gap-4 pt-6", children: [/*#__PURE__*/

          _jsx(ScrollArea, { className: "flex-1 pr-4", children: /*#__PURE__*/
            _jsx("div", { className: "space-y-4", children:
              messages.map((msg, idx) => /*#__PURE__*/
              _jsxs("div", {

                className: `flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`, children: [

                msg.role === 'assistant' && /*#__PURE__*/
                _jsx("div", { className: "h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0", children: /*#__PURE__*/
                  _jsx(Bot, { className: "h-4 w-4 text-primary" }) }
                ), /*#__PURE__*/

                _jsx("div", {
                  className: `max-w-[80%] p-4 rounded-lg ${
                  msg.role === 'user' ?
                  'bg-primary text-primary-foreground' :
                  'bg-muted'}`, children: /*#__PURE__*/


                  _jsx("p", { className: "text-sm", children: msg.content }) }
                ),
                msg.role === 'user' && /*#__PURE__*/
                _jsx("div", { className: "h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0", children: /*#__PURE__*/
                  _jsx(User, { className: "h-4 w-4 text-primary-foreground" }) }
                )] }, idx

              )
              ) }
            ) }
          ), /*#__PURE__*/


          _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
            _jsx(Input, {
              placeholder: "Ask me anything about your knowledge graph...",
              value: input,
              onChange: (e) => setInput(e.target.value),
              onKeyDown: (e) => e.key === 'Enter' && handleSend(),
              className: "flex-1" }
            ), /*#__PURE__*/
            _jsx(Button, { onClick: handleSend, children: /*#__PURE__*/
              _jsx(Send, { className: "h-4 w-4" }) }
            )] }
          ), /*#__PURE__*/


          _jsxs("div", { className: "flex gap-2 flex-wrap", children: [/*#__PURE__*/
            _jsx(Badge, { variant: "outline", className: "cursor-pointer hover:bg-primary/10", children: "Show all requirements" }

            ), /*#__PURE__*/
            _jsx(Badge, { variant: "outline", className: "cursor-pointer hover:bg-primary/10", children: "Find unlinked components" }

            ), /*#__PURE__*/
            _jsx(Badge, { variant: "outline", className: "cursor-pointer hover:bg-primary/10", children: "Simulation results summary" }

            )] }
          )] }
        ) }
      )] }
    ));

}
