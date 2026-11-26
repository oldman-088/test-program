import { RouterProvider } from 'react-router-dom';
import { useDirection } from './hooks/useDirection';
import { useUiStore } from './store/uiStore';
import { router } from './routes';

export default function App() {
  useDirection();
  const theme = useUiStore((s) => s.theme);

  // Dark is the default theme; light is opt-in via uiStore.
  document.documentElement.classList.toggle('dark', theme === 'dark');

  return <RouterProvider router={router} />;
}
