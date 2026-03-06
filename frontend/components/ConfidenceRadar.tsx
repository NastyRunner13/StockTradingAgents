'use client';

import {
    ResponsiveContainer, RadarChart, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip,
} from 'recharts';

type ReportData = {
    sentiment?: string;
    confidence?: number;
};

type ConfidenceData = {
    market_report?: ReportData;
    sentiment_report?: ReportData;
    news_report?: ReportData;
    fundamentals_report?: ReportData;
};

const ANALYST_LABELS: Record<string, { name: string; color: string }> = {
    market_report: { name: 'Market', color: '#3b82f6' },
    sentiment_report: { name: 'Sentiment', color: '#a855f7' },
    news_report: { name: 'News', color: '#f97316' },
    fundamentals_report: { name: 'Fundamentals', color: '#10b981' },
};

function sentimentToScore(sentiment?: string): number {
    if (!sentiment) return 50;
    const s = sentiment.toLowerCase();
    if (s.includes('bullish') || s.includes('buy')) return 85;
    if (s.includes('bearish') || s.includes('sell')) return 25;
    return 55; // neutral/hold
}

export default function ConfidenceRadar({ result }: { result: ConfidenceData }) {
    const reports = ['market_report', 'sentiment_report', 'news_report', 'fundamentals_report'] as const;
    const hasData = reports.some(k => result[k]?.confidence);

    if (!hasData) return null;

    const data = reports.map(key => {
        const report = result[key];
        const label = ANALYST_LABELS[key];
        return {
            analyst: label.name,
            confidence: Math.round((report?.confidence || 0) * 100),
            sentiment: sentimentToScore(report?.sentiment),
        };
    });

    // Consensus
    const avgConfidence = data.reduce((sum, d) => sum + d.confidence, 0) / data.length;
    const sentiments = reports.map(k => result[k]?.sentiment?.toLowerCase() || '');
    const bullish = sentiments.filter(s => s.includes('bullish') || s.includes('buy')).length;
    const bearish = sentiments.filter(s => s.includes('bearish') || s.includes('sell')).length;
    const consensus = bullish > bearish ? 'Bullish' : bearish > bullish ? 'Bearish' : 'Mixed';
    const consensusColor = consensus === 'Bullish' ? 'var(--green)' : consensus === 'Bearish' ? 'var(--red)' : 'var(--yellow)';

    return (
        <div className="card" style={{ padding: 20, marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                    🎯 Agent Confidence
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                        fontSize: '0.7rem', padding: '3px 10px', borderRadius: 100,
                        background: `${consensusColor}15`, color: consensusColor, fontWeight: 600,
                    }}>
                        {consensus}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Avg: {avgConfidence.toFixed(0)}%
                    </span>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
                {/* Radar Chart */}
                <div style={{ flex: '1 1 200px', minWidth: 200 }}>
                    <ResponsiveContainer width="100%" height={220}>
                        <RadarChart data={data} outerRadius="75%">
                            <PolarGrid stroke="#f0f0f0" />
                            <PolarAngleAxis
                                dataKey="analyst"
                                tick={{ fontSize: 11, fill: '#999', fontFamily: 'Inter' }}
                            />
                            <PolarRadiusAxis
                                angle={90}
                                domain={[0, 100]}
                                tick={{ fontSize: 9, fill: '#ccc' }}
                                tickCount={5}
                            />
                            <Radar
                                name="Confidence"
                                dataKey="confidence"
                                stroke="#1a1a1a"
                                fill="#1a1a1a"
                                fillOpacity={0.06}
                                strokeWidth={1.5}
                            />
                            <Radar
                                name="Sentiment"
                                dataKey="sentiment"
                                stroke="#3b82f6"
                                fill="#3b82f6"
                                fillOpacity={0.04}
                                strokeWidth={1.5}
                                strokeDasharray="4 4"
                            />
                            <Tooltip
                                contentStyle={{
                                    background: '#fff', border: '1px solid #e5e5e5',
                                    borderRadius: 8, fontSize: '0.75rem', fontFamily: 'Inter',
                                }}
                            />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>

                {/* Legend / Details */}
                <div style={{ flex: '0 0 160px' }}>
                    {data.map((d, i) => {
                        const key = reports[i];
                        const report = result[key];
                        const label = ANALYST_LABELS[key];
                        return (
                            <div key={key} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '8px 0', borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <div style={{
                                        width: 8, height: 8, borderRadius: '50%',
                                        background: label.color,
                                    }} />
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                        {label.name}
                                    </span>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                                        {d.confidence}%
                                    </span>
                                    <span style={{
                                        fontSize: '0.6rem', marginLeft: 4,
                                        color: report?.sentiment?.toLowerCase().includes('bull') ? 'var(--green)' :
                                            report?.sentiment?.toLowerCase().includes('bear') ? 'var(--red)' : 'var(--text-muted)',
                                    }}>
                                        {report?.sentiment?.slice(0, 4) || '—'}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
