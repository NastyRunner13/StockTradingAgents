'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    TrendingUp, TrendingDown, DollarSign, Activity,
    Zap, Brain, Search,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type AnalysisResult = {
    ticker?: string;
    trade_signal?: {
        action: string;
        confidence: number;
        entry_price?: number;
        target_price?: number;
        stop_loss?: number;
        position_size_pct?: number;
        reasoning?: string;
    };
    investment_debate?: {
        judge_verdict?: string;
        judge_confidence?: number;
        investment_thesis?: string;
        bull_arguments?: Array<{ content: string }>;
        bear_arguments?: Array<{ content: string }>;
    };
    risk_debate?: {
        judge_verdict?: string;
        recommended_position_size?: number;
    };
    market_report?: { summary?: string; sentiment?: string; confidence?: number };
    sentiment_report?: { summary?: string; sentiment?: string; confidence?: number };
    news_report?: { summary?: string; sentiment?: string; confidence?: number };
    fundamentals_report?: { summary?: string; sentiment?: string; confidence?: number };
    final_decision?: string;
    trade_approved?: boolean;
};

/* ─── Stat Card ───────────────────────────────────── */
function StatCard({
    icon: IconComponent, label, value, change
}: {
    icon: typeof DollarSign; label: string; value: string; change?: string; color?: string
}) {
    return (
        <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 700 }}>{value}</p>
                    {change && (
                        <p style={{
                            color: change.startsWith('+') ? 'var(--green)' : 'var(--red)',
                            fontSize: '0.8rem', fontWeight: 600, marginTop: 4
                        }}>
                            {change}
                        </p>
                    )}
                </div>
                <div style={{
                    padding: 8, borderRadius: 8,
                    background: 'var(--bg-secondary)',
                }}>
                    <IconComponent size={18} color="var(--text-muted)" />
                </div>
            </div>
        </div>
    );
}

/* ─── Sentiment Badge ─────────────────────────────── */
function SentimentBadge({ sentiment }: { sentiment?: string }) {
    if (!sentiment) return null;
    const cls = sentiment.includes('bull') ? 'badge-bullish' :
        sentiment.includes('bear') ? 'badge-bearish' : 'badge-neutral';
    return <span className={`badge ${cls}`}>{sentiment.replace('_', ' ')}</span>;
}

export default function DashboardContent() {
    const [ticker, setTicker] = useState('AAPL');
    const [assetType, setAssetType] = useState('stock');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState('');

    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setError('');
        setResult(null);

        try {
            const res = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, asset_type: assetType }),
            });

            if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
            const data = await res.json();
            setResult(data);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Analysis failed');
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                        NexusTrade <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>Dashboard</span>
                    </h1>
                    <p style={{ color: 'var(--text-muted)', marginTop: 2, fontSize: '0.85rem' }}>Multi-Agent AI Trading Intelligence</p>
                </div>

                {/* Quick Analyze */}
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <div className="card" style={{
                        display: 'flex', alignItems: 'center', padding: '8px 14px', gap: 8
                    }}>
                        <Search size={14} color="var(--text-muted)" />
                        <input
                            type="text"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                            placeholder="Ticker..."
                            style={{
                                background: 'transparent', border: 'none', outline: 'none',
                                color: 'var(--text-primary)', fontFamily: 'Inter', fontSize: '0.85rem',
                                width: 80,
                            }}
                        />
                        <select
                            value={assetType}
                            onChange={(e) => setAssetType(e.target.value)}
                            style={{
                                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                                borderRadius: 6, padding: '3px 8px', color: 'var(--text-primary)',
                                fontFamily: 'Inter', fontSize: '0.8rem',
                            }}
                        >
                            <option value="stock">Stock</option>
                            <option value="crypto">Crypto</option>
                        </select>
                    </div>
                    <button
                        className="btn-primary"
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                        {isAnalyzing ? (
                            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1 }}>
                                <Activity size={14} />
                            </motion.div>
                        ) : (
                            <Zap size={14} />
                        )}
                        {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                    </button>
                </div>
            </div>

            {/* Stat Cards */}
            <div className="grid-4" style={{ marginBottom: 24 }}>
                <StatCard icon={DollarSign} label="Portfolio Value" value="$100,000" change="+0.00%" />
                <StatCard icon={TrendingUp} label="Total P&L" value="$0.00" />
                <StatCard icon={Activity} label="Win Rate" value="—" />
                <StatCard icon={Brain} label="Analyses Run" value={result ? '1' : '0'} />
            </div>

            {/* Error */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                        className="card"
                        style={{ padding: 16, marginBottom: 24, borderColor: 'var(--red)' }}
                    >
                        <p style={{ color: 'var(--red)', fontWeight: 600, fontSize: '0.9rem' }}>⚠ {error}</p>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 4 }}>
                            Make sure the backend is running: <code style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>cd backend && uvicorn api.main:app --reload</code>
                        </p>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Analysis Result */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        {/* Trade Decision Card */}
                        <div className="card" style={{
                            padding: 24, marginBottom: 24,
                            borderColor: result.trade_approved ? 'var(--green)' : 'var(--red)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                                    {result.trade_approved ? '✅' : '❌'} Trade Decision — {result.ticker || ticker}
                                </h2>
                                <SentimentBadge sentiment={result.trade_signal?.action} />
                            </div>

                            {result.trade_signal && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginBottom: 16 }}>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>ACTION</p>
                                        <p style={{
                                            fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', color:
                                                result.trade_signal.action === 'buy' ? 'var(--green)' :
                                                    result.trade_signal.action === 'sell' ? 'var(--red)' : 'var(--yellow)'
                                        }}>
                                            {result.trade_signal.action}
                                        </p>
                                    </div>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>CONFIDENCE</p>
                                        <p style={{ fontSize: '1rem', fontWeight: 700 }}>{(result.trade_signal.confidence * 100).toFixed(1)}%</p>
                                    </div>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>ENTRY</p>
                                        <p style={{ fontSize: '1rem', fontWeight: 700 }}>${result.trade_signal.entry_price?.toFixed(2) || '—'}</p>
                                    </div>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>TARGET</p>
                                        <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--green)' }}>${result.trade_signal.target_price?.toFixed(2) || '—'}</p>
                                    </div>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>STOP LOSS</p>
                                        <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--red)' }}>${result.trade_signal.stop_loss?.toFixed(2) || '—'}</p>
                                    </div>
                                    <div>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>POSITION SIZE</p>
                                        <p style={{ fontSize: '1rem', fontWeight: 700 }}>{((result.trade_signal.position_size_pct || 0) * 100).toFixed(1)}%</p>
                                    </div>
                                </div>
                            )}

                            {result.trade_signal?.reasoning && (
                                <div style={{
                                    background: 'var(--bg-secondary)', borderRadius: 8, padding: 16,
                                    borderLeft: '3px solid var(--accent)'
                                }}>
                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>TRADER REASONING</p>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.6 }}>
                                        {result.trade_signal.reasoning}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Agent Reports Grid */}
                        <h3 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Agent Reports
                        </h3>
                        <div className="grid-auto" style={{ marginBottom: 24 }}>
                            {['market_report', 'sentiment_report', 'news_report', 'fundamentals_report'].map((key) => {
                                const report = result[key as keyof AnalysisResult] as AnalysisResult['market_report'];
                                if (!report) return null;
                                const labels: Record<string, string> = {
                                    market_report: 'Market Analyst',
                                    sentiment_report: 'Sentiment Analyst',
                                    news_report: 'News Analyst',
                                    fundamentals_report: 'Fundamentals Analyst',
                                };
                                return (
                                    <div
                                        key={key}
                                        className="card"
                                        style={{ padding: 20 }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                                            <h4 style={{ fontSize: '0.85rem', fontWeight: 600 }}>{labels[key]}</h4>
                                            <SentimentBadge sentiment={report.sentiment} />
                                        </div>
                                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                                            {report.summary}
                                        </p>
                                        <div style={{ marginTop: 10 }}>
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                                                Confidence: {((report.confidence || 0) * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Investment Debate */}
                        {result.investment_debate && (
                            <div className="card" style={{ padding: 24, marginBottom: 24 }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 16 }}>
                                    Bull / Bear Debate
                                </h3>
                                <div className="grid-2">
                                    <div style={{ borderLeft: '3px solid var(--green)', paddingLeft: 16 }}>
                                        <p style={{ color: 'var(--green)', fontWeight: 600, fontSize: '0.8rem', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Bull Case</p>
                                        {result.investment_debate.bull_arguments?.map((arg, i) => (
                                            <p key={i} style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5, marginBottom: 8 }}>
                                                {arg.content?.substring(0, 300)}...
                                            </p>
                                        ))}
                                    </div>
                                    <div style={{ borderLeft: '3px solid var(--red)', paddingLeft: 16 }}>
                                        <p style={{ color: 'var(--red)', fontWeight: 600, fontSize: '0.8rem', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Bear Case</p>
                                        {result.investment_debate.bear_arguments?.map((arg, i) => (
                                            <p key={i} style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5, marginBottom: 8 }}>
                                                {arg.content?.substring(0, 300)}...
                                            </p>
                                        ))}
                                    </div>
                                </div>
                                {result.investment_debate.investment_thesis && (
                                    <div style={{
                                        marginTop: 16, background: 'var(--bg-secondary)', borderRadius: 8, padding: 16,
                                        borderTop: '2px solid var(--accent)',
                                    }}>
                                        <p style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.8rem', marginBottom: 6 }}>
                                            JUDGE VERDICT: {result.investment_debate.judge_verdict?.toUpperCase()}
                                            {' '}({((result.investment_debate.judge_confidence || 0) * 100).toFixed(0)}% confidence)
                                        </p>
                                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.6 }}>
                                            {result.investment_debate.investment_thesis}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Empty State */}
            {!result && !isAnalyzing && (
                <div style={{ textAlign: 'center', padding: '80px 20px' }}>
                    <div style={{
                        width: 64, height: 64, margin: '0 auto 20px',
                        borderRadius: '50%', background: 'var(--bg-secondary)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Zap size={28} color="var(--text-muted)" />
                    </div>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 6 }}>Ready to Analyze</h3>
                    <p style={{ color: 'var(--text-muted)', maxWidth: 380, margin: '0 auto', fontSize: '0.85rem', lineHeight: 1.5 }}>
                        Enter a ticker symbol above and click Analyze to run the multi-agent AI pipeline.
                        All 4 analysts run in parallel for maximum speed.
                    </p>
                </div>
            )}

            {/* Loading State */}
            {isAnalyzing && (
                <div style={{ textAlign: 'center', padding: '80px 20px' }}>
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                        style={{
                            width: 48, height: 48, margin: '0 auto 20px',
                            border: '2px solid var(--border)',
                            borderTop: '2px solid var(--accent)',
                            borderRadius: '50%',
                        }}
                    />
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 6 }}>Agents Working...</h3>
                    <p style={{ color: 'var(--text-muted)', maxWidth: 380, margin: '0 auto', fontSize: '0.85rem', lineHeight: 1.5 }}>
                        4 analysts are analyzing {ticker} in parallel. Bull/Bear researchers will debate,
                        then the risk team evaluates. This takes 30–60 seconds.
                    </p>
                </div>
            )}
        </div>
    );
}
