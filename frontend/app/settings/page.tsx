'use client';

import { useState } from 'react';
import { Settings as SettingsIcon, Key, Cpu, Bell, Globe } from 'lucide-react';

export default function SettingsPage() {
    const [apiUrl, setApiUrl] = useState('http://localhost:8000');
    const [autoTrade, setAutoTrade] = useState(false);
    const [confidenceThreshold, setConfidenceThreshold] = useState(85);

    return (
        <div style={{ maxWidth: 640 }}>
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <SettingsIcon size={24} />
                    Settings
                </h1>
                <p style={{ color: 'var(--text-muted)', marginTop: 4, fontSize: '0.85rem' }}>
                    Configure your NexusTrade instance.
                </p>
            </div>

            {/* API Configuration */}
            <div className="card" style={{ padding: 24, marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Globe size={18} color="var(--text-primary)" />
                    <h3 style={{ fontWeight: 600, fontSize: '0.9rem' }}>API Connection</h3>
                </div>
                <div>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Backend URL
                    </label>
                    <input
                        type="text"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        style={{
                            width: '100%', padding: '10px 14px', borderRadius: 8,
                            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                            color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: '0.85rem',
                            outline: 'none',
                        }}
                    />
                </div>
            </div>

            {/* Trading Configuration */}
            <div className="card" style={{ padding: 24, marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Cpu size={18} color="var(--text-primary)" />
                    <h3 style={{ fontWeight: 600, fontSize: '0.9rem' }}>Trading</h3>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div>
                        <p style={{ fontWeight: 500, fontSize: '0.85rem' }}>Auto-Trade Mode</p>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                            Automatically execute trades above confidence threshold
                        </p>
                    </div>
                    <label style={{
                        width: 44, height: 24, borderRadius: 12, cursor: 'pointer',
                        background: autoTrade ? 'var(--accent)' : 'var(--border)',
                        position: 'relative', transition: 'background 0.2s',
                        display: 'block', flexShrink: 0,
                    }}>
                        <input
                            type="checkbox"
                            checked={autoTrade}
                            onChange={(e) => setAutoTrade(e.target.checked)}
                            style={{ display: 'none' }}
                        />
                        <div style={{
                            width: 18, height: 18, borderRadius: '50%',
                            background: '#fff', position: 'absolute', top: 3,
                            left: autoTrade ? 23 : 3, transition: 'left 0.2s',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                        }} />
                    </label>
                </div>

                <div>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block', marginBottom: 6 }}>
                        Auto-Trade Confidence Threshold: {confidenceThreshold}%
                    </label>
                    <input
                        type="range"
                        min={50}
                        max={100}
                        value={confidenceThreshold}
                        onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                        style={{ width: '100%', accentColor: 'var(--accent)' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        <span>50% (Risky)</span>
                        <span>100% (Safe)</span>
                    </div>
                </div>
            </div>

            {/* API Keys */}
            <div className="card" style={{ padding: 24, marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Key size={18} color="var(--text-primary)" />
                    <h3 style={{ fontWeight: 600, fontSize: '0.9rem' }}>API Keys</h3>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                    API keys are configured in the backend <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>.env</code> file.
                    Required keys: <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>GROQ_API_KEY</code>,
                    <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>ALPACA_API_KEY</code>,
                    <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>ALPACA_SECRET_KEY</code>.
                </p>
            </div>

            {/* Notifications */}
            <div className="card" style={{ padding: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Bell size={18} color="var(--text-primary)" />
                    <h3 style={{ fontWeight: 600, fontSize: '0.9rem' }}>Notifications</h3>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                    Optional: Configure Telegram or Discord alerts in the backend <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>.env</code> file.
                    Set <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>TELEGRAM_BOT_TOKEN</code> and
                    <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>TELEGRAM_CHAT_ID</code> for trade alerts.
                </p>
            </div>
        </div>
    );
}
