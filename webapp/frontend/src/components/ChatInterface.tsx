
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Send, Upload, Bot, User } from "lucide-react";
import { ChatMessage } from "../types/nellia";
import { useTranslation } from "../hooks/useTranslation";

const agents = [
  { id: 'intake', name: 'lead_intake', status: 'active' },
  { id: 'analysis', name: 'analysis', status: 'processing' },
  { id: 'persona', name: 'persona_creation', status: 'inactive' },
  { id: 'strategy', name: 'approach_strategy', status: 'inactive' },
  { id: 'message', name: 'message_crafting', status: 'inactive' }
];

export const ChatInterface = () => {
  const { t } = useTranslation();
  const [activeAgent, setActiveAgent] = useState('intake');
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({
    intake: [
      {
        id: '1',
        agent_id: 'intake',
        content: 'Olá! Sou o agente de captação de leads. Envie os dados do seu lead para processamento.',
        timestamp: new Date().toISOString(),
        type: 'agent'
      }
    ],
    analysis: [],
    persona: [],
    strategy: [],
    message: []
  });

  const handleSendMessage = () => {
    if (!message.trim()) return;

    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      agent_id: activeAgent,
      content: message,
      timestamp: new Date().toISOString(),
      type: 'user'
    };

    setMessages(prev => ({
      ...prev,
      [activeAgent]: [...(prev[activeAgent] || []), newMessage]
    }));

    setMessage('');

    // Simulate agent response
    setTimeout(() => {
      const agentResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        agent_id: activeAgent,
        content: `Processando sua solicitação... ${message}`,
        timestamp: new Date().toISOString(),
        type: 'agent'
      };

      setMessages(prev => ({
        ...prev,
        [activeAgent]: [...(prev[activeAgent] || []), agentResponse]
      }));
    }, 1000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'processing': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <Card className="h-[600px] bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-white text-lg">{t('chat')}</CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col h-full space-y-4">
        <Tabs value={activeAgent} onValueChange={setActiveAgent} className="flex-1 flex flex-col">
          <TabsList className="grid grid-cols-5 bg-slate-800 border border-slate-700">
            {agents.map((agent) => (
              <TabsTrigger 
                key={agent.id} 
                value={agent.id}
                className="relative data-[state=active]:bg-slate-700 text-white text-xs"
              >
                <div className={`absolute top-1 right-1 w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />
                {t(agent.name)}
              </TabsTrigger>
            ))}
          </TabsList>

          {agents.map((agent) => (
            <TabsContent key={agent.id} value={agent.id} className="flex-1 mt-4">
              <ScrollArea className="h-[400px] border border-slate-700 rounded-lg p-4 bg-slate-800/50">
                <div className="space-y-3">
                  {(messages[agent.id] || []).map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[70%] rounded-lg p-3 ${
                          msg.type === 'user'
                            ? 'bg-green-600 text-white'
                            : 'bg-slate-700 text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-2 mb-1">
                          {msg.type === 'user' ? (
                            <User className="w-3 h-3" />
                          ) : (
                            <Bot className="w-3 h-3" />
                          )}
                          <span className="text-xs opacity-70">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm">{msg.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>
          ))}
        </Tabs>

        <div className="flex space-x-2">
          <Button variant="outline" size="sm" className="shrink-0">
            <Upload className="w-4 h-4" />
          </Button>
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder={t('type_message')}
            className="bg-slate-800 border-slate-600 text-white"
          />
          <Button onClick={handleSendMessage} size="sm" className="shrink-0">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
