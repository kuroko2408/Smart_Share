import { QueryProvider } from '@/app/providers';
import { AppRouter } from '@/app/router';

export default function App() {
  return (
    <QueryProvider>
      <AppRouter />
    </QueryProvider>
  );
}
