'use client';

import { useState, useEffect } from 'react';
import { History, Calendar, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Trade = {
    id: number;
    ticker: string;
    asset_type: string;
    action: string;
    quantity: number;
    price: number;
    confidence: number;
    reasoning: string;
    approval_status: string;
    pnl: number | null;
    created_at: string;
};

export default function TradesPage() {
    const [trades, setTrades] = useState<Trade[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE}/trades`)
            .then(r => r.json())
            .then(data => { setTrades(Array.isArray(data) ? data : []); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const getActionIcon = (action: string) => {
        if (action === 'buy') return <TrendingUp size={14} color="var(--green)" />;
        if (action === 'sell' || action === 'short') return <TrendingDown size={14} color="var(--red)" />;
        return <Minus size={14} color="var(--yellow)" />;
    };

    return (
        <div>
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <History size={24} />
                    Trade History
                </h1>
                <p style={{ color: 'var(--text-muted)', marginTop: 4, fontSize: '0.85rem' }}>
                    All trades executed and pending — with full reasoning transparency.
                </p>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: 60 }}>
                    <p style={{ color: 'var(--text-muted)' }}>Loading trades...</p>
                </div>
            ) : trades.length === 0 ? (
                <div className="card" style={{ padding: 48, textAlign: 'center' }}>
                    <Calendar size={40} color="var(--text-muted)" style={{ margin: '0 auto 16px', display: 'block' }} />
                    <h3 style={{ fontWeight: 600, marginBottom: 6, fontSize: '1rem' }}>No Trades Yet</h3>
                    <p style={{ color: 'var(--text-muted)', maxWidth: 380, margin: '0 auto', fontSize: '0.85rem' }}>
                        Run an analysis from the Dashboard and approve a trade to see it appear here.
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {/* Header Row */}
                    <div style={{
                        display: 'grid', gridTemplateColumns: '48px 1fr 120px',
                        alignItems: 'center', gap: 12, padding: '0 20px',
                    }}>
                        <div />
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Trade</p>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>P&L</p>
                    </div>
                    {trades.map((trade) => (
                        <div
                            key={trade.id}
                            className="card"
                            style={{
                                padding: '16px 20px',
                                display: 'grid', gridTemplateColumns: '48px 1fr 120px',
                                alignItems: 'center', gap: 12
                            }}
                        >
                            <div style={{
                                width: 36, height: 36, borderRadius: 8,
                                background: 'var(--bg-secondary)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                {getActionIcon(trade.action)}
                            </div>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{trade.ticker}</span>
                                    <span style={{
                                        textTransform: 'uppercase', fontSize: '0.7rem', fontWeight: 600,
                                        color: trade.action === 'buy' ? 'var(--green)' :
                                            trade.action === 'sell' ? 'var(--red)' : 'var(--yellow)',
                                    }}>{trade.action}</span>
                                </div>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 2 }}>
                                    {trade.quantity} shares @ ${trade.price?.toFixed(2)} — {trade.approval_status}
                                </p>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <p style={{ fontWeight: 600, fontSize: '0.9rem', color: trade.pnl && trade.pnl > 0 ? 'var(--green)' : trade.pnl && trade.pnl < 0 ? 'var(--red)' : 'var(--text-primary)' }}>
                                    {trade.pnl ? `${trade.pnl > 0 ? '+' : ''}$${trade.pnl.toFixed(2)}` : '—'}
                                </p>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginTop: 2 }}>
                                    {new Date(trade.created_at).toLocaleDateString()}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
