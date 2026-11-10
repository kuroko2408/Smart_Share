import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { HomePage } from '@/features/home/HomePage';
import { AuthPage } from '@/features/auth/AuthPage';
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <AuthPage initialMode="signin" />,
  },
  {
    path: '/signup',
    element: <AuthPage initialMode="signup" />,
  },
  {
    path: '/forgot-password',
    element: <AuthPage initialMode="forgot" />,
  },
  {
    path: '/reset-password',
    element: <ResetPasswordPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <HomePage />
      </ProtectedRoute>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
