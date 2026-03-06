'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    TrendingUp, TrendingDown, DollarSign, Activity,
    Zap, Brain, Search, ChevronDown, ChevronUp, X,
    Loader2, CheckCircle2, Database, MessageSquare,
    BarChart3, Newspaper, Landmark, HeartPulse,
    Clock, Radio, CircleDot,
} from 'lucide-react';
import dynamic from 'next/dynamic';

// Dynamic imports for chart components (avoid SSR issues)
const PriceChart = dynamic(() => import('./PriceChart'), { ssr: false });
const PortfolioChart = dynamic(() => import('./PortfolioChart'), { ssr: false });
const ConfidenceRadar = dynamic(() => import('./ConfidenceRadar'), { ssr: false });
const TradeApprovalModal = dynamic(() => import('./TradeApprovalModal'), { ssr: false });

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/live';

type ReportData = {
    summary?: string;
    sentiment?: string;
    confidence?: number;
    key_findings?: string[];
    reasoning?: string;
    raw_data?: Record<string, unknown>;
};

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
    market_report?: ReportData;
    sentiment_report?: ReportData;
    news_report?: ReportData;
    fundamentals_report?: ReportData;
    final_decision?: string;
    trade_approved?: boolean;
    thread_id?: string;
};

type TickerSuggestion = {
    symbol: string;
    name: string;
    type: string;
};

type LogEntry = {
    agent: string;
    stage: string;
    message: string;
    details: string;
    timestamp: string;
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

/* ─── Agent Config (icons + colors) ─────────────────── */
const AGENT_CONFIG: Record<string, { color: string; icon: typeof BarChart3 }> = {
    'Market Analyst': { color: '#3b82f6', icon: BarChart3 },
    'Sentiment Analyst': { color: '#a855f7', icon: HeartPulse },
    'News Analyst': { color: '#f97316', icon: Newspaper },
    'Fundamentals Analyst': { color: '#10b981', icon: Landmark },
};

const STAGE_CONFIG: Record<string, { label: string; icon: typeof Loader2 }> = {
    'started': { label: 'Starting', icon: Radio },
    'data_fetched': { label: 'Data Loaded', icon: Database },
    'llm_call': { label: 'AI Thinking', icon: Brain },
    'llm_response': { label: 'AI Response', icon: MessageSquare },
    'completed': { label: 'Complete', icon: CheckCircle2 },
};

/* ─── Data Explorer (Tabbed Raw Data View) ─────────── */
function DataExplorer({ result }: { result: AnalysisResult }) {
    const [activeTab, setActiveTab] = useState<'technicals' | 'news' | 'fundamentals' | 'sentiment'>('technicals');

    const marketRaw = result.market_report?.raw_data || {};
    const newsRaw = result.news_report?.raw_data || {};
    const fundRaw = result.fundamentals_report?.raw_data || {};
    const sentRaw = result.sentiment_report?.raw_data || {};

    const tabs = [
        { id: 'technicals' as const, label: 'Technicals', icon: BarChart3, color: '#3b82f6', count: Object.keys(marketRaw).length },
        { id: 'news' as const, label: 'News', icon: Newspaper, color: '#f97316', count: (newsRaw.news as unknown[] || []).length },
        { id: 'fundamentals' as const, label: 'Fundamentals', icon: Landmark, color: '#10b981', count: Object.keys(fundRaw).length },
        { id: 'sentiment' as const, label: 'Sentiment', icon: HeartPulse, color: '#a855f7', count: (sentRaw.headlines as unknown[] || []).length },
    ];

    const formatValue = (key: string, val: unknown): string => {
        if (val === null || val === undefined) return '—';
        if (typeof val === 'number') {
            if (key.includes('market_cap') || key.includes('revenue') || key.includes('Revenue') || key.includes('Capitalization')) {
                if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
                if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
                if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
                return `$${val.toLocaleString()}`;
            }
            if (key.includes('pct') || key.includes('change') || key.includes('yield') || key.includes('margin') || key.includes('roe')) {
                return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
            }
            if (key.includes('price') || key.includes('sma') || key.includes('ema') || key.includes('bollinger')) {
                return `$${val.toFixed(2)}`;
            }
            return val.toFixed(4).replace(/\.?0+$/, '') || val.toString();
        }
        return String(val);
    };

    const getMetricColor = (key: string, val: unknown): string | undefined => {
        if (typeof val !== 'number') return undefined;
        if (key.includes('rsi')) {
            if (val > 70) return 'var(--red)';
            if (val < 30) return 'var(--green)';
        }
        if (key.includes('change') || key.includes('macd_hist')) {
            return val >= 0 ? 'var(--green)' : 'var(--red)';
        }
        return undefined;
    };

    return (
        <div className="card" style={{ marginBottom: 24, overflow: 'hidden' }}>
            {/* Tab Bar */}
            <div style={{
                display: 'flex', borderBottom: '1px solid var(--border)',
                padding: '0 4px', gap: 0,
            }}>
                {tabs.map((tab) => {
                    const TabIcon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '12px 16px', border: 'none', cursor: 'pointer',
                                background: 'transparent', fontFamily: 'Inter',
                                fontSize: '0.8rem', fontWeight: isActive ? 600 : 400,
                                color: isActive ? tab.color : 'var(--text-muted)',
                                borderBottom: isActive ? `2px solid ${tab.color}` : '2px solid transparent',
                                transition: 'all 0.2s ease',
                            }}
                        >
                            <TabIcon size={14} />
                            {tab.label}
                            {tab.count > 0 && (
                                <span style={{
                                    fontSize: '0.6rem', padding: '1px 6px', borderRadius: 100,
                                    background: isActive ? `${tab.color}15` : 'var(--bg-secondary)',
                                    color: isActive ? tab.color : 'var(--text-muted)',
                                    fontWeight: 600,
                                }}>
                                    {tab.count}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Tab Content */}
            <div style={{ padding: 20, maxHeight: 500, overflowY: 'auto' }}>
                {/* ─── Technicals Tab ─── */}
                {activeTab === 'technicals' && (
                    <div>
                        {Object.keys(marketRaw).length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: 20 }}>No technical data available</p>
                        ) : (
                            <div style={{
                                display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                                gap: 12,
                            }}>
                                {Object.entries(marketRaw).filter(([, v]) => v !== null && v !== undefined).map(([key, val]) => (
                                    <div key={key} style={{
                                        padding: '12px 14px', borderRadius: 8,
                                        background: 'var(--bg-secondary)',
                                        border: '1px solid var(--border)',
                                    }}>
                                        <p style={{
                                            fontSize: '0.65rem', color: 'var(--text-muted)',
                                            textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4,
                                        }}>
                                            {key.replace(/_/g, ' ')}
                                        </p>
                                        <p style={{
                                            fontSize: '1rem', fontWeight: 700,
                                            color: getMetricColor(key, val) || 'var(--text-primary)',
                                        }}>
                                            {formatValue(key, val)}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ─── News Tab ─── */}
                {activeTab === 'news' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {((newsRaw.news as Array<Record<string, string>>) || []).length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: 20 }}>No news data available</p>
                        ) : (
                            ((newsRaw.news as Array<Record<string, string>>) || []).map((article, i) => (
                                <div key={i} style={{
                                    padding: '14px 16px', borderRadius: 8,
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--border)',
                                    transition: 'border-color 0.2s',
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                                        <div style={{ flex: 1 }}>
                                            <a
                                                href={article.link || article.url || '#'}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{
                                                    fontSize: '0.85rem', fontWeight: 600,
                                                    color: 'var(--text-primary)',
                                                    textDecoration: 'none', lineHeight: 1.4,
                                                }}
                                            >
                                                {article.title || 'Untitled'}
                                            </a>
                                            <div style={{ display: 'flex', gap: 10, marginTop: 6, flexWrap: 'wrap' }}>
                                                {article.publisher && (
                                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                                        {article.publisher}
                                                    </span>
                                                )}
                                                {article.published && (
                                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                                        {article.published.substring(0, 10)}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        {article.overall_sentiment && (
                                            <span style={{
                                                fontSize: '0.65rem', padding: '3px 8px', borderRadius: 100,
                                                fontWeight: 600, whiteSpace: 'nowrap',
                                                background: article.overall_sentiment?.toLowerCase().includes('bull') || article.overall_sentiment?.toLowerCase().includes('positive')
                                                    ? 'rgba(34, 197, 94, 0.12)' : article.overall_sentiment?.toLowerCase().includes('bear') || article.overall_sentiment?.toLowerCase().includes('negative')
                                                        ? 'rgba(239, 68, 68, 0.12)' : 'var(--bg-card)',
                                                color: article.overall_sentiment?.toLowerCase().includes('bull') || article.overall_sentiment?.toLowerCase().includes('positive')
                                                    ? 'var(--green)' : article.overall_sentiment?.toLowerCase().includes('bear') || article.overall_sentiment?.toLowerCase().includes('negative')
                                                        ? 'var(--red)' : 'var(--text-muted)',
                                                border: '1px solid var(--border)',
                                            }}>
                                                {article.overall_sentiment}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* ─── Fundamentals Tab ─── */}
                {activeTab === 'fundamentals' && (
                    <div>
                        {Object.keys(fundRaw).length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: 20 }}>No fundamentals data available</p>
                        ) : (
                            <div style={{
                                display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                                gap: 12,
                            }}>
                                {Object.entries(fundRaw)
                                    .filter(([, v]) => v !== null && v !== undefined && v !== '')
                                    .map(([key, val]) => (
                                        <div key={key} style={{
                                            padding: '12px 14px', borderRadius: 8,
                                            background: 'var(--bg-secondary)',
                                            border: '1px solid var(--border)',
                                        }}>
                                            <p style={{
                                                fontSize: '0.65rem', color: 'var(--text-muted)',
                                                textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4,
                                            }}>
                                                {key.replace(/_/g, ' ')}
                                            </p>
                                            <p style={{
                                                fontSize: typeof val === 'string' && val.length > 30 ? '0.78rem' : '1rem',
                                                fontWeight: typeof val === 'string' && val.length > 30 ? 400 : 700,
                                                color: 'var(--text-primary)',
                                                lineHeight: 1.4,
                                                wordBreak: 'break-word',
                                            }}>
                                                {formatValue(key, val)}
                                            </p>
                                        </div>
                                    ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ─── Sentiment Tab ─── */}
                {activeTab === 'sentiment' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {sentRaw.current_price && (
                            <div style={{
                                padding: '12px 16px', borderRadius: 8,
                                background: 'linear-gradient(135deg, rgba(168,85,247,0.08), rgba(59,130,246,0.08))',
                                border: '1px solid var(--border)',
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            }}>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Current Price</span>
                                <span style={{ fontSize: '1.2rem', fontWeight: 700 }}>${Number(sentRaw.current_price).toFixed(2)}</span>
                            </div>
                        )}
                        {((sentRaw.headlines as Array<Record<string, string>>) || []).length === 0 ? (
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: 20 }}>No sentiment data available</p>
                        ) : (
                            ((sentRaw.headlines as Array<Record<string, string>>) || []).map((h, i) => (
                                <div key={i} style={{
                                    padding: '10px 14px', borderRadius: 8,
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--border)',
                                    fontSize: '0.82rem', color: 'var(--text-secondary)',
                                    lineHeight: 1.5,
                                }}>
                                    {typeof h === 'string' ? h : h.title || JSON.stringify(h)}
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

/* ─── Live Activity Panel (Premium) ────────────────── */
function LiveActivityPanel({ logs, isAnalyzing }: { logs: LogEntry[]; isAnalyzing: boolean }) {
    const [expanded, setExpanded] = useState(true);
    const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set());
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    if (logs.length === 0 && !isAnalyzing) return null;

    // Build agent status map
    const agentStatus: Record<string, { stage: string; message: string }> = {};
    logs.forEach((l) => {
        agentStatus[l.agent] = { stage: l.stage, message: l.message };
    });

    const totalAgents = 4;
    const doneCount = Object.values(agentStatus).filter(s => s.stage === 'completed').length;

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
            style={{ marginBottom: 24, overflow: 'hidden' }}
        >
            {/* Header */}
            <div
                onClick={() => setExpanded(!expanded)}
                style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '14px 20px', cursor: 'pointer',
                    borderBottom: expanded ? '1px solid var(--border)' : 'none',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                        width: 28, height: 28, borderRadius: 8,
                        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Activity size={14} color="#fff" />
                    </div>
                    <div>
                        <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>Live Activity</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginLeft: 8 }}>
                            {doneCount}/{totalAgents} agents
                        </span>
                    </div>
                    {isAnalyzing && (
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                        >
                            <Loader2 size={14} color="var(--accent)" />
                        </motion.div>
                    )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                        width: 60, height: 4, borderRadius: 2,
                        background: 'var(--bg-secondary)', overflow: 'hidden',
                    }}>
                        <motion.div
                            animate={{ width: `${(doneCount / totalAgents) * 100}%` }}
                            style={{
                                height: '100%', borderRadius: 2,
                                background: doneCount === totalAgents ? 'var(--green)' : 'var(--accent)',
                            }}
                        />
                    </div>
                    {expanded
                        ? <ChevronUp size={14} color="var(--text-muted)" />
                        : <ChevronDown size={14} color="var(--text-muted)" />
                    }
                </div>
            </div>

            {/* Agent Status Bar — 4-column grid */}
            {expanded && (
                <div style={{
                    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0,
                    borderBottom: '1px solid var(--border)',
                }}>
                    {['Market Analyst', 'Sentiment Analyst', 'News Analyst', 'Fundamentals Analyst'].map((agent, idx) => {
                        const status = agentStatus[agent];
                        const config = AGENT_CONFIG[agent];
                        const AgentIcon = config.icon;
                        const isDone = status?.stage === 'completed';
                        const isActive = status && !isDone;
                        return (
                            <div key={agent} style={{
                                display: 'flex', alignItems: 'center', gap: 8,
                                padding: '10px 16px',
                                borderRight: idx < 3 ? '1px solid var(--border)' : 'none',
                                background: isDone ? `${config.color}06` : 'transparent',
                            }}>
                                <div style={{
                                    width: 28, height: 28, borderRadius: 6,
                                    background: isDone ? `${config.color}15` : isActive ? `${config.color}08` : 'var(--bg-secondary)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    border: `1px solid ${isDone ? `${config.color}30` : 'var(--border)'}`,
                                    transition: 'all 0.3s ease',
                                }}>
                                    {isDone
                                        ? <CheckCircle2 size={14} color={config.color} />
                                        : isActive
                                            ? <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}>
                                                <Loader2 size={14} color={config.color} />
                                            </motion.div>
                                            : <AgentIcon size={14} color="var(--text-muted)" />
                                    }
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <p style={{
                                        fontSize: '0.72rem', fontWeight: 600,
                                        color: isDone ? config.color : 'var(--text-secondary)',
                                    }}>
                                        {agent.replace(' Analyst', '')}
                                    </p>
                                    <p style={{
                                        fontSize: '0.65rem', color: 'var(--text-muted)',
                                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                    }}>
                                        {isDone ? 'Done' : isActive ? (STAGE_CONFIG[status.stage]?.label || status.stage) : 'Waiting'}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Log Feed */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        style={{ overflow: 'hidden' }}
                    >
                        <div
                            ref={scrollRef}
                            style={{
                                maxHeight: 420, overflowY: 'auto',
                                padding: '4px 0',
                            }}
                        >
                            {logs.map((log, i) => {
                                const config = AGENT_CONFIG[log.agent] || { color: 'var(--text-muted)', icon: CircleDot };
                                const stageConf = STAGE_CONFIG[log.stage] || { label: log.stage, icon: CircleDot };
                                const StageIcon = stageConf.icon;
                                const hasDetails = log.details && log.details.trim().length > 0;
                                const isExpanded = expandedLogs.has(i);
                                return (
                                    <div key={i}>
                                        <motion.div
                                            initial={{ opacity: 0, x: -6 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ duration: 0.15 }}
                                            className="activity-log-row"
                                            onClick={() => {
                                                if (hasDetails) {
                                                    setExpandedLogs(prev => {
                                                        const next = new Set(prev);
                                                        if (next.has(i)) next.delete(i);
                                                        else next.add(i);
                                                        return next;
                                                    });
                                                }
                                            }}
                                            style={{ cursor: hasDetails ? 'pointer' : 'default' }}
                                        >
                                            {/* Timestamp */}
                                            <div className="activity-col-time">
                                                <Clock size={10} color="var(--text-muted)" />
                                                <span>
                                                    {new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                                </span>
                                            </div>

                                            {/* Agent */}
                                            <div className="activity-col-agent" style={{
                                                color: config.color,
                                                background: `${config.color}10`,
                                                borderColor: `${config.color}25`,
                                            }}>
                                                {log.agent.replace(' Analyst', '')}
                                            </div>

                                            {/* Stage */}
                                            <div className="activity-col-stage">
                                                <StageIcon size={11} color="var(--text-muted)" />
                                                <span>{stageConf.label}</span>
                                            </div>

                                            {/* Message + expand indicator */}
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
                                                <span className="activity-col-message" style={{ flex: 1 }}>
                                                    {log.message}
                                                </span>
                                                {hasDetails && (
                                                    <motion.div
                                                        animate={{ rotate: isExpanded ? 180 : 0 }}
                                                        transition={{ duration: 0.2 }}
                                                        style={{ flexShrink: 0 }}
                                                    >
                                                        <ChevronDown size={12} color="var(--text-muted)" />
                                                    </motion.div>
                                                )}
                                            </div>
                                        </motion.div>

                                        {/* Expandable detail panel */}
                                        <AnimatePresence>
                                            {isExpanded && hasDetails && (
                                                <motion.div
                                                    initial={{ height: 0, opacity: 0 }}
                                                    animate={{ height: 'auto', opacity: 1 }}
                                                    exit={{ height: 0, opacity: 0 }}
                                                    transition={{ duration: 0.2 }}
                                                    style={{ overflow: 'hidden' }}
                                                >
                                                    <div className="activity-detail-panel" style={{
                                                        margin: '0 20px 8px 20px',
                                                        padding: '10px 14px',
                                                        background: 'var(--bg-secondary)',
                                                        borderRadius: 8,
                                                        borderLeft: `3px solid ${config.color}`,
                                                        fontSize: '0.75rem',
                                                        color: 'var(--text-secondary)',
                                                        lineHeight: 1.6,
                                                        fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', monospace",
                                                        whiteSpace: 'pre-wrap',
                                                        wordBreak: 'break-word',
                                                        maxHeight: 200,
                                                        overflowY: 'auto',
                                                    }}>
                                                        {log.details}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                );
                            })}
                            {logs.length === 0 && isAnalyzing && (
                                <div style={{
                                    padding: '24px', textAlign: 'center',
                                    color: 'var(--text-muted)', fontSize: '0.8rem',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                }}>
                                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
                                        <Loader2 size={14} />
                                    </motion.div>
                                    Waiting for agent events...
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

/* ─── Main Dashboard ──────────────────────────────── */
export default function DashboardContent() {
    const [ticker, setTicker] = useState('AAPL');
    const [assetType, setAssetType] = useState('stock');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState('');

    // Autocomplete state
    const [suggestions, setSuggestions] = useState<TickerSuggestion[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [activeSuggestion, setActiveSuggestion] = useState(-1);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Live activity log state — session-scoped
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const wsRef = useRef<WebSocket | null>(null);
    const analysisIdRef = useRef<string | null>(null);

    // WebSocket connection
    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    // Only accept events matching our current analysis session
                    if (msg.type === 'analysis_log') {
                        const myId = analysisIdRef.current;
                        if (myId && msg.analysis_id === myId) {
                            setLogs((prev) => [...prev, msg.data as LogEntry]);
                        }
                    }
                } catch {
                    // ignore parse errors
                }
            };

            ws.onclose = () => {
                setTimeout(connect, 3000);
            };
        };

        connect();
        return () => {
            wsRef.current?.close();
        };
    }, []);

    // Click outside to close suggestions
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    // Fetch suggestions
    const fetchSuggestions = useCallback(async (query: string) => {
        if (query.length < 1) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&asset_type=${assetType}&limit=8`);
            if (res.ok) {
                const data: TickerSuggestion[] = await res.json();
                setSuggestions(data);
                setShowSuggestions(data.length > 0);
                setActiveSuggestion(-1);
            }
        } catch {
            // silent fail
        }
    }, [assetType]);

    const handleTickerChange = (value: string) => {
        const upper = value.toUpperCase();
        setTicker(upper);

        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => fetchSuggestions(upper), 300);
    };

    const selectSuggestion = (s: TickerSuggestion) => {
        setTicker(s.symbol);
        setAssetType(s.type);
        setShowSuggestions(false);
        setSuggestions([]);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!showSuggestions || suggestions.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveSuggestion((prev) => Math.min(prev + 1, suggestions.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveSuggestion((prev) => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter' && activeSuggestion >= 0) {
            e.preventDefault();
            selectSuggestion(suggestions[activeSuggestion]);
        } else if (e.key === 'Escape') {
            setShowSuggestions(false);
        }
    };

    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setError('');
        setResult(null);
        setLogs([]); // Clear previous logs

        // Generate a session ID that we'll match against WebSocket events
        // We listen for analysis_start to capture the backend's analysis_id
        // OR we can pre-generate and send, but simpler: listen for the first event
        analysisIdRef.current = null; // Will be set from first WS event

        // Temporarily accept all events until we get our analysis_id
        const tempHandler = (event: MessageEvent) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'analysis_start' && !analysisIdRef.current) {
                    analysisIdRef.current = msg.analysis_id;
                }
                if (msg.type === 'analysis_log' && msg.analysis_id && analysisIdRef.current === null) {
                    // First log event — capture ID
                    analysisIdRef.current = msg.analysis_id;
                    setLogs((prev) => [...prev, msg.data as LogEntry]);
                }
            } catch { /* ignore */ }
        };

        wsRef.current?.addEventListener('message', tempHandler);

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
            wsRef.current?.removeEventListener('message', tempHandler);
        }
    };

    return (
        <div>
            {/* Header */}
            <div className="dashboard-header">
                <div className="dashboard-header-title">
                    <h1>
                        NexusTrade <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>Dashboard</span>
                    </h1>
                    <p>Multi-Agent AI Trading Intelligence</p>
                </div>

                {/* Quick Analyze */}
                <div className="dashboard-header-actions">
                    <div ref={dropdownRef} className="autocomplete-container">
                        <div className="card" style={{
                            display: 'flex', alignItems: 'center', padding: '8px 14px', gap: 8
                        }}>
                            <Search size={14} color="var(--text-muted)" />
                            <input
                                ref={inputRef}
                                type="text"
                                value={ticker}
                                onChange={(e) => handleTickerChange(e.target.value)}
                                onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
                                onKeyDown={handleKeyDown}
                                placeholder="Search ticker..."
                                style={{
                                    background: 'transparent', border: 'none', outline: 'none',
                                    color: 'var(--text-primary)', fontFamily: 'Inter', fontSize: '0.85rem',
                                    width: 120, minWidth: 0, flex: 1,
                                }}
                                autoComplete="off"
                            />
                            <select
                                value={assetType}
                                onChange={(e) => { setAssetType(e.target.value); setSuggestions([]); }}
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

                        {/* Autocomplete Dropdown */}
                        <AnimatePresence>
                            {showSuggestions && suggestions.length > 0 && (
                                <motion.div
                                    initial={{ opacity: 0, y: -4 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -4 }}
                                    transition={{ duration: 0.15 }}
                                    className="autocomplete-dropdown"
                                >
                                    {suggestions.map((s, i) => (
                                        <div
                                            key={`${s.symbol}-${s.type}`}
                                            className={`autocomplete-item ${i === activeSuggestion ? 'active' : ''}`}
                                            onClick={() => selectSuggestion(s)}
                                            onMouseEnter={() => setActiveSuggestion(i)}
                                        >
                                            <span className="autocomplete-symbol">{s.symbol}</span>
                                            <span className="autocomplete-name">{s.name}</span>
                                            <span className="autocomplete-type">{s.type}</span>
                                        </div>
                                    ))}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <button
                        className="btn-primary"
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
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

            {/* Price Chart + Portfolio Curve */}
            <div className={`chart-grid${ticker ? '' : ' no-ticker'}`}>
                {ticker && <PriceChart ticker={ticker} />}
                <PortfolioChart />
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

            {/* Live Activity Panel */}
            <LiveActivityPanel logs={logs} isAnalyzing={isAnalyzing} />

            {/* Trade Approval Modal (HITL) */}
            {result?.thread_id && result?.final_decision === 'awaiting_approval' && result?.trade_signal && (
                <TradeApprovalModal
                    threadId={result.thread_id}
                    tradeSignal={result.trade_signal}
                    ticker={result.ticker || ticker}
                    onDecision={() => {
                        // Refresh the result after approval/rejection
                        setResult(prev => prev ? { ...prev, final_decision: 'decided' } : prev);
                    }}
                />
            )}

            {/* Analysis Result */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        {/* Agent Confidence Radar */}
                        <ConfidenceRadar result={result} />
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
                                const report = result[key as keyof AnalysisResult] as ReportData | undefined;
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

                        {/* Data Explorer — Raw Data Tabs */}
                        <h3 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Raw Data Explorer
                        </h3>
                        <DataExplorer result={result} />

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
