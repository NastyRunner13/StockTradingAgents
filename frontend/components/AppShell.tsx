'use client';

import Sidebar from '@/components/Sidebar';

export default function AppShell({ children }: { children: React.ReactNode }) {
    return (
        <>
            <Sidebar />
            <main className="main-content">
                {children}
            </main>
        </>
    );
}
