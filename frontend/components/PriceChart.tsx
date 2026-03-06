'use client';

import { useEffect, useRef, useState } from 'react';
import { useTheme } from './ThemeProvider';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type CandlestickData = {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
};

const THEME_COLORS = {
    light: {
        bg: '#ffffff',
        text: '#999999',
        grid: '#f0f0f0',
        crosshair: '#e5e5e5',
        border: '#e5e5e5',
        upColor: '#16a34a',
        downColor: '#dc2626',
        volumeUp: 'rgba(22,163,74,0.15)',
        volumeDown: 'rgba(220,38,38,0.15)',
    },
    dark: {
        bg: '#18181b',
        text: '#71717a',
        grid: '#27272a',
        crosshair: '#3f3f46',
        border: '#27272a',
        upColor: '#22c55e',
        downColor: '#ef4444',
        volumeUp: 'rgba(34,197,94,0.2)',
        volumeDown: 'rgba(239,68,68,0.2)',
    },
};

export default function PriceChart({ ticker, assetType = 'stock' }: { ticker: string; assetType?: string }) {
    const chartRef = useRef<HTMLDivElement>(null);
    const chartInstanceRef = useRef<unknown>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { theme } = useTheme();

    useEffect(() => {
        if (!ticker || !chartRef.current) return;

        let cancelled = false;

        async function initChart() {
            setLoading(true);
            setError('');

            try {
                const { createChart, CandlestickSeries, HistogramSeries } = await import('lightweight-charts');

                const res = await fetch(`${API_BASE}/price/${ticker}/chart?asset_type=${assetType}`);
                if (!res.ok) throw new Error(`Failed to fetch chart data: ${res.status}`);
                const data: CandlestickData[] = await res.json();

                if (cancelled || !chartRef.current) return;

                // Remove old chart
                if (chartInstanceRef.current) {
                    (chartInstanceRef.current as { remove: () => void }).remove();
                }

                const colors = THEME_COLORS[theme];

                const chart = createChart(chartRef.current, {
                    width: chartRef.current.clientWidth,
                    height: 380,
                    layout: {
                        background: { color: colors.bg },
                        textColor: colors.text,
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                    },
                    grid: {
                        vertLines: { color: colors.grid },
                        horzLines: { color: colors.grid },
                    },
                    crosshair: {
                        mode: 0,
                        vertLine: { color: colors.crosshair, width: 1, style: 2 },
                        horzLine: { color: colors.crosshair, width: 1, style: 2 },
                    },
                    rightPriceScale: {
                        borderColor: colors.border,
                    },
                    timeScale: {
                        borderColor: colors.border,
                        timeVisible: true,
                    },
                });

                const candleSeries = chart.addSeries(CandlestickSeries, {
                    upColor: colors.upColor,
                    downColor: colors.downColor,
                    borderUpColor: colors.upColor,
                    borderDownColor: colors.downColor,
                    wickUpColor: colors.upColor,
                    wickDownColor: colors.downColor,
                });

                candleSeries.setData(data.map(d => ({
                    time: d.time,
                    open: d.open,
                    high: d.high,
                    low: d.low,
                    close: d.close,
                })));

                if (data.some(d => d.volume)) {
                    const volumeSeries = chart.addSeries(HistogramSeries, {
                        priceFormat: { type: 'volume' },
                        priceScaleId: 'volume',
                    });

                    chart.priceScale('volume').applyOptions({
                        scaleMargins: { top: 0.8, bottom: 0 },
                    });

                    volumeSeries.setData(data.filter(d => d.volume).map(d => ({
                        time: d.time,
                        value: d.volume!,
                        color: d.close >= d.open ? colors.volumeUp : colors.volumeDown,
                    })));
                }

                chart.timeScale().fitContent();
                chartInstanceRef.current = chart;

                // Resize observer
                const ro = new ResizeObserver(entries => {
                    for (const entry of entries) {
                        chart.applyOptions({ width: entry.contentRect.width });
                    }
                });
                ro.observe(chartRef.current);

                setLoading(false);

                return () => {
                    ro.disconnect();
                    chart.remove();
                };
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : 'Failed to load chart');
                    setLoading(false);
                }
            }
        }

        initChart();
        return () => { cancelled = true; };
    }, [ticker, assetType, theme]);

    return (
        <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                    📈 Price Chart — {ticker}
                </h3>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Daily OHLCV
                </span>
            </div>
            {error ? (
                <div style={{
                    height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'var(--bg-secondary)', borderRadius: 8,
                }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {error}
                    </p>
                </div>
            ) : loading ? (
                <div style={{
                    height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'var(--bg-secondary)', borderRadius: 8,
                }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        Loading chart...
                    </p>
                </div>
            ) : null}
            <div ref={chartRef} style={{ display: loading || error ? 'none' : 'block', borderRadius: 8, overflow: 'hidden' }} />
        </div>
    );
}
