'use client';

import { Brain, BarChart3, MessageSquare, Newspaper, LineChart, Shield, Scale, Zap } from 'lucide-react';

const agents = [
    {
        name: 'Market Analyst',
        icon: BarChart3,
        description: 'Analyzes price action, technical indicators (RSI, MACD, Bollinger Bands, SMA), and chart patterns.',
        type: 'analyst',
    },
    {
        name: 'Sentiment Analyst',
        icon: MessageSquare,
        description: 'Evaluates social sentiment, news headlines, and public mood for contrarian signals.',
        type: 'analyst',
    },
    {
        name: 'News Analyst',
        icon: Newspaper,
        description: 'Monitors breaking news, macro trends, insider transactions, and regulatory risks.',
        type: 'analyst',
    },
    {
        name: 'Fundamentals Analyst',
        icon: LineChart,
        description: 'Evaluates P/E, balance sheet health, cash flow quality, and competitive moat.',
        type: 'analyst',
    },
    {
        name: 'Bull Researcher',
        icon: Zap,
        description: 'Argues the bullish investment thesis using all analyst data. Counters bear arguments with evidence.',
        type: 'researcher',
    },
    {
        name: 'Bear Researcher',
        icon: Shield,
        description: 'Argues the bearish thesis, identifying downside risks, overvaluation, and red flags.',
        type: 'researcher',
    },
    {
        name: 'Research Judge',
        icon: Scale,
        description: 'Weighs bull vs bear arguments objectively and delivers a final investment thesis.',
        type: 'judge',
    },
    {
        name: 'Risk Manager',
        icon: Shield,
        description: '3 risk analysts (aggressive, conservative, neutral) debate, then CRO approves/rejects the trade.',
        type: 'risk',
    },
];

const pipelineSteps = [
    { label: '4 Analysts', desc: 'Parallel' },
    { label: 'Bull vs Bear', desc: '2 rounds' },
    { label: 'Judge', desc: 'Verdict' },
    { label: 'Trader', desc: 'Trade plan' },
    { label: 'Risk Debate', desc: '3-way' },
    { label: 'CRO', desc: 'Approve/Reject' },
];

export default function AgentsPage() {
    return (
        <div>
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Brain size={24} />
                    Agent Pipeline
                </h1>
                <p style={{ color: 'var(--text-muted)', marginTop: 4, fontSize: '0.85rem' }}>
                    9 specialized AI agents work together through parallel analysis, adversarial debate, and risk assessment.
                </p>
            </div>

            {/* Pipeline Visualization */}
            <div className="card" style={{ padding: 20, marginBottom: 32 }}>
                <h3 style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '1px' }}>
                    Pipeline Flow
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                    {pipelineSteps.map((step, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{
                                padding: '6px 14px',
                                borderRadius: 6,
                                background: 'var(--bg-secondary)',
                                border: '1px solid var(--border)',
                                textAlign: 'center',
                            }}>
                                <p style={{ fontWeight: 600, fontSize: '0.8rem' }}>{step.label}</p>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>{step.desc}</p>
                            </div>
                            {i < pipelineSteps.length - 1 && (
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>→</span>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Agent Cards */}
            <div className="grid-auto">
                {agents.map((agent) => (
                    <div
                        key={agent.name}
                        className="card"
                        style={{ padding: 20 }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                            <div style={{
                                padding: 8, borderRadius: 8,
                                background: 'var(--bg-secondary)',
                            }}>
                                <agent.icon size={18} color="var(--text-primary)" />
                            </div>
                            <div>
                                <h4 style={{ fontWeight: 600, fontSize: '0.9rem' }}>{agent.name}</h4>
                                <span style={{
                                    fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.5px',
                                    color: 'var(--text-muted)', fontWeight: 600,
                                }}>{agent.type}</span>
                            </div>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                            {agent.description}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
}
