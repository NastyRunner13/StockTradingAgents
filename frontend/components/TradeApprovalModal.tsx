'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle2, XCircle, Shield } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type TradeSignal = {
    action?: string;
    confidence?: number;
    entry_price?: number;
    target_price?: number;
    stop_loss?: number;
    position_size_pct?: number;
    reasoning?: string;
};

type Props = {
    threadId: string;
    tradeSignal: TradeSignal;
    ticker: string;
    onDecision: (approved: boolean) => void;
};

export default function TradeApprovalModal({ threadId, tradeSignal, ticker, onDecision }: Props) {
    const [submitting, setSubmitting] = useState(false);
    const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);

    const confidencePct = ((tradeSignal.confidence || 0) * 100).toFixed(1);
    const isLowConfidence = (tradeSignal.confidence || 0) < 0.7;

    async function handleDecision(approval: 'approve' | 'reject') {
        setSubmitting(true);
        setDecision(approval);
        try {
            const res = await fetch(`${API_BASE}/trades/${threadId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approval }),
            });
            if (!res.ok) throw new Error('Failed to submit');
            onDecision(approval === 'approve');
        } catch (err) {
            console.error('Trade approval error:', err);
            setSubmitting(false);
            setDecision(null);
        }
    }

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{
                    position: 'fixed', inset: 0, zIndex: 1000,
                    background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    padding: 20,
                }}
            >
                <motion.div
                    initial={{ scale: 0.95, y: 20 }}
                    animate={{ scale: 1, y: 0 }}
                    exit={{ scale: 0.95, y: 20 }}
                    className="card"
                    style={{
                        width: '100%', maxWidth: 520, padding: 32,
                        borderColor: isLowConfidence ? 'var(--yellow)' : 'var(--border)',
                    }}
                >
                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
                        <div style={{
                            padding: 10, borderRadius: 12,
                            background: isLowConfidence ? 'var(--yellow-soft)' : 'var(--accent-soft)',
                        }}>
                            {isLowConfidence
                                ? <AlertTriangle size={20} color="var(--yellow)" />
                                : <Shield size={20} color="var(--accent)" />
                            }
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                                Trade Approval Required
                            </h2>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                {ticker} — Confidence: {confidencePct}%
                            </p>
                        </div>
                    </div>

                    {/* Trade Details */}
                    <div style={{
                        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12,
                        marginBottom: 20, padding: 16, borderRadius: 10,
                        background: 'var(--bg-secondary)',
                    }}>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>ACTION</p>
                            <p style={{
                                fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase',
                                color: tradeSignal.action === 'buy' ? 'var(--green)' :
                                    tradeSignal.action === 'sell' ? 'var(--red)' : 'var(--yellow)',
                            }}>
                                {tradeSignal.action || '—'}
                            </p>
                        </div>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>ENTRY</p>
                            <p style={{ fontSize: '1rem', fontWeight: 700 }}>${tradeSignal.entry_price?.toFixed(2) || '—'}</p>
                        </div>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>SIZE</p>
                            <p style={{ fontSize: '1rem', fontWeight: 700 }}>{((tradeSignal.position_size_pct || 0) * 100).toFixed(1)}%</p>
                        </div>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>TARGET</p>
                            <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--green)' }}>${tradeSignal.target_price?.toFixed(2) || '—'}</p>
                        </div>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>STOP LOSS</p>
                            <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--red)' }}>${tradeSignal.stop_loss?.toFixed(2) || '—'}</p>
                        </div>
                        <div>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>CONFIDENCE</p>
                            <p style={{ fontSize: '1rem', fontWeight: 700 }}>{confidencePct}%</p>
                        </div>
                    </div>

                    {/* Reasoning */}
                    {tradeSignal.reasoning && (
                        <div style={{
                            background: 'var(--bg-secondary)', borderRadius: 8, padding: 14,
                            borderLeft: '3px solid var(--accent)', marginBottom: 24,
                        }}>
                            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                REASONING
                            </p>
                            <p style={{
                                color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5,
                                maxHeight: 100, overflow: 'auto',
                            }}>
                                {tradeSignal.reasoning}
                            </p>
                        </div>
                    )}

                    {/* Warning for low confidence */}
                    {isLowConfidence && (
                        <div style={{
                            padding: 12, borderRadius: 8, marginBottom: 20,
                            background: 'var(--yellow-soft)', border: '1px solid var(--yellow)',
                        }}>
                            <p style={{ fontSize: '0.8rem', color: 'var(--yellow)', fontWeight: 600 }}>
                                ⚠ Low confidence trade ({confidencePct}%). Consider rejecting.
                            </p>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: 12 }}>
                        <button
                            onClick={() => handleDecision('reject')}
                            disabled={submitting}
                            style={{
                                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                padding: '12px 20px', borderRadius: 10, border: '1px solid var(--red)',
                                background: submitting && decision === 'reject' ? 'var(--red-soft)' : 'transparent',
                                color: 'var(--red)', fontWeight: 600, fontSize: '0.85rem',
                                cursor: submitting ? 'not-allowed' : 'pointer', fontFamily: 'Inter',
                                opacity: submitting && decision !== 'reject' ? 0.4 : 1,
                                transition: 'all 0.2s',
                            }}
                        >
                            <XCircle size={16} />
                            Reject
                        </button>
                        <button
                            onClick={() => handleDecision('approve')}
                            disabled={submitting}
                            style={{
                                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                padding: '12px 20px', borderRadius: 10, border: 'none',
                                background: submitting && decision === 'approve' ? '#14532d' : 'var(--green)',
                                color: '#ffffff', fontWeight: 600, fontSize: '0.85rem',
                                cursor: submitting ? 'not-allowed' : 'pointer', fontFamily: 'Inter',
                                opacity: submitting && decision !== 'approve' ? 0.4 : 1,
                                transition: 'all 0.2s',
                            }}
                        >
                            <CheckCircle2 size={16} />
                            {submitting && decision === 'approve' ? 'Approving...' : 'Approve Trade'}
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
