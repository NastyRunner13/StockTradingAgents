'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Brain,
    History,
    Settings,
    TrendingUp,
} from 'lucide-react';

const navItems = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/agents', icon: Brain, label: 'Agents' },
    { href: '/trades', icon: History, label: 'Trades' },
    { href: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <nav className="sidebar">
            {/* Logo */}
            <div style={{ marginBottom: 32 }}>
                <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    background: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                    <TrendingUp size={18} color="#fff" />
                </div>
            </div>

            {/* Nav Items */}
            {navItems.map(({ href, icon: Icon, label }) => (
                <Link key={href} href={href} title={label}>
                    <div className={`sidebar-icon ${pathname === href ? 'active' : ''}`}>
                        <Icon size={18} />
                    </div>
                </Link>
            ))}

            {/* Status */}
            <div style={{ marginTop: 'auto', marginBottom: 16 }}>
                <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: 'var(--green)',
                }} title="System Online" />
            </div>
        </nav>
    );
}
