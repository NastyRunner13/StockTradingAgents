'use client';

import { useEffect, useState } from 'react';
import {
    ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts';
import { useTheme } from './ThemeProvider';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type PortfolioEntry = {
    date: string;
    total_value: number;
    cash: number;
    equity: number;
    daily_pnl: number;
};

const CHART_COLORS = {
    light: {
        grid: '#f0f0f0',
        axis: '#e5e5e5',
        tick: '#999',
        tooltipBg: '#ffffff',
        tooltipBorder: '#e5e5e5',
        refLine: '#e5e5e5',
    },
    dark: {
        grid: '#27272a',
        axis: '#27272a',
        tick: '#71717a',
        tooltipBg: '#27272a',
        tooltipBorder: '#3f3f46',
        refLine: '#3f3f46',
    },
};

export default function PortfolioChart() {
    const [data, setData] = useState<PortfolioEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const { theme } = useTheme();

    useEffect(() => {
        fetch(`${API_BASE}/portfolio/history?limit=100`)
            .then(res => res.json())
            .then((history: PortfolioEntry[]) => {
                setData(history.length > 0 ? history : [
                    { date: new Date().toISOString().split('T')[0], total_value: 100000, cash: 100000, equity: 0, daily_pnl: 0 },
                ]);
                setLoading(false);
            })
            .catch(() => {
                setData([
                    { date: new Date().toISOString().split('T')[0], total_value: 100000, cash: 100000, equity: 0, daily_pnl: 0 },
                ]);
                setLoading(false);
            });
    }, []);

    const startValue = data[0]?.total_value || 100000;
    const currentValue = data[data.length - 1]?.total_value || 100000;
    const pnl = currentValue - startValue;
    const pnlPct = startValue > 0 ? (pnl / startValue) * 100 : 0;
    const isPositive = pnl >= 0;
    const colors = CHART_COLORS[theme];
    const greenColor = theme === 'dark' ? '#22c55e' : '#16a34a';
    const redColor = theme === 'dark' ? '#ef4444' : '#dc2626';

    return (
        <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                    <h3 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 4 }}>
                        💰 Portfolio Equity Curve
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Total Value: ${currentValue.toLocaleString()}
                    </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <p style={{
                        fontSize: '1rem', fontWeight: 700,
                        color: isPositive ? 'var(--green)' : 'var(--red)',
                    }}>
                        {isPositive ? '+' : ''}{pnlPct.toFixed(2)}%
                    </p>
                    <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {isPositive ? '+' : ''}${pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                </div>
            </div>

            {loading ? (
                <div style={{
                    height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'var(--bg-secondary)', borderRadius: 8,
                }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading...</p>
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                        <defs>
                            <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={isPositive ? greenColor : redColor} stopOpacity={0.12} />
                                <stop offset="95%" stopColor={isPositive ? greenColor : redColor} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
                        <XAxis
                            dataKey="date"
                            tick={{ fontSize: 10, fill: colors.tick }}
                            tickLine={false}
                            axisLine={{ stroke: colors.axis }}
                        />
                        <YAxis
                            tick={{ fontSize: 10, fill: colors.tick }}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                            domain={['auto', 'auto']}
                        />
                        <Tooltip
                            contentStyle={{
                                background: colors.tooltipBg,
                                border: `1px solid ${colors.tooltipBorder}`,
                                borderRadius: 8,
                                fontSize: '0.75rem',
                                fontFamily: 'Inter',
                                color: theme === 'dark' ? '#fafafa' : '#1a1a1a',
                            }}
                            formatter={(value: number | undefined) => [`$${(value ?? 0).toLocaleString()}`, 'Total Value']}
                        />
                        <ReferenceLine y={startValue} stroke={colors.refLine} strokeDasharray="3 3" />
                        <Area
                            type="monotone"
                            dataKey="total_value"
                            stroke={isPositive ? greenColor : redColor}
                            strokeWidth={2}
                            fill="url(#portfolioGradient)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}
