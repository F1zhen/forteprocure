import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiMessageSquare } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import styles from './TenderChat.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface TenderChatProps {
  analysis: {
    summary: string;
    key_fields: Record<string, unknown>;
    risk_analysis: Array<{
      risk_flag: string;
      severity: number;
      explanation: string;
      justification: string;
    }>;
    technical_analysis: Record<string, unknown>;
    contract_terms_detail: Record<string, unknown>;
    similar_tenders: unknown[];
    final_notes: string;
  };
}

const TenderChat: React.FC<TenderChatProps> = ({ analysis }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Здравствуйте! Я AI-ассистент по анализу тендеров. Задавайте вопросы о данном тендере, и я помогу вам разобраться в деталях.'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8003/chat-tender', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis: analysis,
          question: input
        })
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Извините, произошла ошибка при обработке вашего запроса. Попробуйте еще раз.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedQuestions = [
    'Какие основные риски у этого тендера?',
    'Стоит ли участвовать в этом тендере?',
    'Какие технические требования?',
  ];

  const handleSuggestionClick = (question: string) => {
    setInput(question);
  };

  return (
    <div className={styles.chatContainer}>
      <div className={styles.chatHeader}>
        <FiMessageSquare />
        <h3>AI-Ассистент по тендеру</h3>
      </div>

      <div className={styles.messagesContainer}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`${styles.message} ${
              msg.role === 'user' ? styles.userMessage : styles.assistantMessage
            }`}
          >
            <div className={styles.messageContent}>
              {msg.role === 'assistant' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className={`${styles.message} ${styles.assistantMessage}`}>
            <div className={styles.messageContent}>
              <div className={styles.typingIndicator}>
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className={styles.suggestions}>
          <p className={styles.suggestionsTitle}>Попробуйте спросить:</p>
          <div className={styles.suggestionButtons}>
            {suggestedQuestions.map((question, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(question)}
                className={styles.suggestionButton}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Задайте вопрос о тендере..."
          className={styles.input}
          rows={2}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className={styles.sendButton}
        >
          <FiSend />
        </button>
      </div>
    </div>
  );
};

export default TenderChat;