/**
 * Route protection guard for authenticated application pages.
 * Prevents unauthorized access and avoids redirect flashes during session restoration.
 */
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { Car, Loader2 } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';

interface ProtectedRouteProps {
  children?: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 flex flex-col items-center gap-4 max-w-sm w-full text-center">
          <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 animate-pulse">
            <Car className="w-6 h-6 animate-bounce" />
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900">Smart Share</h3>
            <p className="text-xs text-gray-500 mt-1 flex items-center justify-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying session…
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children ? <>{children}</> : <Outlet />;
}
