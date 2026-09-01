'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter, usePathname } from 'next/navigation';
import { Session } from '@supabase/supabase-js';

const AuthContext = createContext<{ session: Session | null | undefined }>({ session: undefined });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const router = useRouter();
  const pathname = usePathname();

    useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session || { access_token: 'fake', user: {} } as any);
      // if (!session && pathname !== '/login') {
      //   router.push('/login');
      // }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session || { access_token: 'fake', user: {} } as any);
      // if (!session && pathname !== '/login') {
      //   router.push('/login');
      // }
    });

    return () => subscription.unsubscribe();
  }, [router, pathname]);

  if (session === undefined) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{ session }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
