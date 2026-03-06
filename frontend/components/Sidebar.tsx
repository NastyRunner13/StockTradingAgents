'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Brain,
    History,
    Settings,
    TrendingUp,
    Moon,
    Sun,
} from 'lucide-react';
import { useTheme } from './ThemeProvider';

const navItems = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/agents', icon: Brain, label: 'Agents' },
    { href: '/trades', icon: History, label: 'Trades' },
    { href: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { theme, toggleTheme } = useTheme();

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
                    <TrendingUp size={18} color={theme === 'dark' ? '#0a0a0b' : '#fff'} />
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

            {/* Bottom section */}
            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                {/* Theme Toggle */}
                <button
                    onClick={toggleTheme}
                    className="theme-toggle"
                    title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                    {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                </button>

                {/* Status */}
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
