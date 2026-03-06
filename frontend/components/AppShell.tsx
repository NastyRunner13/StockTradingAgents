'use client';

import Sidebar from '@/components/Sidebar';
import ThemeProvider from '@/components/ThemeProvider';

export default function AppShell({ children }: { children: React.ReactNode }) {
    return (
        <ThemeProvider>
            <Sidebar />
            <main className="main-content">
                {children}
            </main>
        </ThemeProvider>
    );
}
