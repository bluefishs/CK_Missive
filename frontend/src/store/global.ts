import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface GlobalState {
  // 使用者狀態
  user: {
    id?: number;
    name?: string;
    email?: string;
    role?: string;
  } | null;
  
  // 載入狀態
  isLoading: boolean;
  
  // 錯誤狀態
  error: string | null;
  
  // Actions
  setUser: (user: GlobalState['user']) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useGlobalStore = create<GlobalState>()(
  devtools(
    (set) => ({
      user: null,
      isLoading: false,
      error: null,
      
      setUser: (user) => set({ user }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'global-store',
    }
  )
);

export default useGlobalStore;
