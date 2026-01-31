import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom/client';

// Icons Mirroring Google AI Studio / Material
const SearchIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>;
const AttachIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>;
const ToolsIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>;
const HistoryIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>;
const SettingsIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>;

interface Message {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}

interface RunConfig {
  model: string;
  temperature: number;
  topP: number;
  topK: number;
  systemInstruction: string;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingStep, setThinkingStep] = useState('');
  const [sessionId] = useState(() => crypto.randomUUID());

  const [config, setConfig] = useState<RunConfig>({
    model: 'vision-model_QWEN',
    temperature: 0.7,
    topP: 0.9,
    topK: 40,
    systemInstruction: 'You are the Punisher Mission Control. Provide strategic tactical advice, intel analysis, and mission planning. Be precise, gritty, and direct.'
  });
  const [intelFeed, setIntelFeed] = useState<string[]>(['Satellite link established...']);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // SSE handler
  useEffect(() => {
    const eventSource = new EventSource('/api/events');
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const contentStr = typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2);
        const isFeed = contentStr.includes('[POS]') || contentStr.includes('[WALLET]') || contentStr.includes('[TRADE]');

        if (contentStr.includes('PUNISHER IS THINKING')) {
          setIsLoading(true);
          setThinkingStep(contentStr.replace('PUNISHER IS THINKING... ', '').replace('[', '').replace(']', ''));
          return;
        }

        const newMessage: Message = {
          id: Date.now().toString() + Math.random(),
          role: data.type === 'response' ? 'model' : 'model',
          content: contentStr,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        if (isFeed) {
          setIntelFeed(prev => [contentStr.replace(/\[POS\]|\[WALLET\]|\[TRADE\]/g, '').trim(), ...prev.slice(0, 50)]);
        } else {
          if (data.type === 'response') {
            setIsLoading(false);
            setThinkingStep('');
          }
          setMessages(prev => [...prev, newMessage]);
        }
      } catch (e) {
        console.error(e);
      }
    };
    return () => eventSource.close();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setThinkingStep('UPLINKING');

    try {
      await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: userMessage.content, session_id: sessionId })
      });
    } catch (err) {
      setIsLoading(false);
      setThinkingStep('');
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'model',
        content: `CRITICAL ERROR: ${err}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSendMessage();
    }
  };

  return (
    <div className="punisher-dashboard">
      <header className="main-header">
        <div className="header-left">
          <div className="app-logo">
            <div className="logo-symbol"></div>
            <h1>Punisher Mission Control</h1>
          </div>
        </div>
        <div className="header-right">
          <button className="btn-secondary">Get Intel Code</button>
          <div className="user-profile"></div>
        </div>
      </header>

      <div className="dashboard-content">
        <aside className="sidebar left-sidebar no-scrollbar">
          <div className="sidebar-section">
            <div className="section-header">
              <HistoryIcon />
              <span>Mission History</span>
            </div>
            <div className="history-list">
              <div className="history-item active">Current Operation</div>
              <div className="history-item">Op: Cerberus</div>
              <div className="history-item">Intel Sweep 09-B</div>
              <div className="history-item">Target Log #442</div>
            </div>
          </div>
        </aside>

        <main className="central-canvas no-scrollbar">
          <div className="canvas-container">
            <div className="message-area" ref={scrollRef}>
              {messages.length === 0 && !isLoading && (
                <div className="canvas-empty">
                  <div className="empty-graphic">P</div>
                  <h2>Awaiting Deployment</h2>
                  <p>Define mission parameters or request tactical assessment below.</p>
                </div>
              )}
              {messages.map((msg) => (
                <div key={msg.id} className={`message-row ${msg.role}`}>
                  <div className="message-header">
                    <span className="role-label">{msg.role === 'user' ? 'USER' : 'PUNISHER'}</span>
                    <span className="timestamp">{msg.timestamp}</span>
                  </div>
                  <div className="message-body">
                    {msg.content}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message-row model thinking">
                  <div className="message-header">
                    <span className="role-label">PUNISHER</span>
                    <span className="shimmer-dot"></span>
                    {thinkingStep && <span className="timestamp ml-2 opacity-50 uppercase text-[9px] tracking-widest">{thinkingStep}</span>}
                  </div>
                  <div className="message-body shimmer-text">
                    Processing intelligence stream...
                  </div>
                </div>
              )}
            </div>

            <div className="prompt-anchor">
              <div className="prompt-card">
                <textarea
                  ref={inputRef}
                  placeholder="Insert tactical request..."
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = `${e.target.scrollHeight}px`;
                  }}
                  onKeyDown={handleKeyDown}
                />
                <div className="prompt-actions">
                  <div className="action-group">
                    <button className="icon-btn" title="Attach Files"><AttachIcon /></button>
                    <button className="icon-btn" title="Mission Tools"><ToolsIcon /></button>
                    <button className="pill-btn"><SearchIcon /> Search Intel</button>
                  </div>
                  <button
                    className={`run-btn ${(!inputValue.trim() || isLoading) ? 'disabled' : ''}`}
                    onClick={handleSendMessage}
                  >
                    RUN MISSION
                  </button>
                </div>
              </div>
              <div className="keyboard-hint">Ctrl + Enter to dispatch</div>
            </div>
          </div>
        </main>

        <aside className="sidebar right-sidebar no-scrollbar">
          <div className="sidebar-section">
            <div className="section-header">
              <SettingsIcon />
              <span>Run Settings</span>
            </div>

            <div className="setting-group">
              <label>Model</label>
              <select
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
              >
                <option value="vision-model_QWEN">vision-model_QWEN</option>
                <option value="gemini-3-pro">Gemini 3 Pro</option>
                <option value="strategic">Strategic Visualization</option>
              </select>
            </div>

            <div className="setting-group">
              <label>System Instructions</label>
              <textarea
                className="system-text"
                value={config.systemInstruction}
                onChange={(e) => setConfig({ ...config, systemInstruction: e.target.value })}
              />
            </div>

            <div className="setting-group">
              <div className="slider-header">
                <label>Temperature</label>
                <span>{config.temperature}</span>
              </div>
              <input
                type="range" min="0" max="1" step="0.1"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              />
            </div>

            <div className="setting-group">
              <div className="slider-header">
                <label>Top P</label>
                <span>{config.topP}</span>
              </div>
              <input
                type="range" min="0" max="1" step="0.05"
                value={config.topP}
                onChange={(e) => setConfig({ ...config, topP: parseFloat(e.target.value) })}
              />
            </div>

            <div className="setting-divider"></div>

            <div className="section-header">
              <span>Live Intel Feed</span>
            </div>
            <div className="live-intel no-scrollbar overflow-y-auto">
              {intelFeed.length === 0 && <div className="intel-line">Synchronizing Link...</div>}
              {intelFeed.map((line, i) => (
                <div key={i} className="intel-line">{line}</div>
              ))}
            </div>
          </div>
          <div className="mt-auto py-4 text-center opacity-30 text-[10px] uppercase tracking-widest font-mono">
            Latency: 42ms
          </div>
        </aside>
      </div>
    </div>
  );
}

const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(<React.StrictMode><App /></React.StrictMode>);
}

export default App;
