'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

const navLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/data-sources', label: 'Data Sources' },
  { href: '/ai-providers', label: 'AI Providers' },
  { href: '/tasks', label: 'Tasks' },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-64 bg-white shadow-md">
        <div className="p-6">
          <h1 className="text-xl font-bold text-indigo-600">AutoReportAI</h1>
        </div>
        <nav className="mt-6">
          <ul>
            {navLinks.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="block px-6 py-3 text-gray-700 hover:bg-gray-100">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="absolute bottom-0 w-64 p-6">
            <button 
              onClick={handleLogout}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              Logout
            </button>
        </div>
      </aside>
      <main className="flex-1 p-10">
        {children}
      </main>
    </div>
  );
} 