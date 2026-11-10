import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ResetPasswordPage } from '../ResetPasswordPage';
import * as AuthContextModule from '../AuthContext';
import type { AuthContextType } from '../AuthContext';

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockAuthContext = (overrides: Partial<AuthContextType> = {}) => {
    const updatePasswordMock = vi.fn().mockResolvedValue(undefined);
    const loginWithTokenMock = vi.fn();

    const defaultContext: AuthContextType = {
      session: null,
      user: null,
      isAuthenticated: true,
      isLoading: false,
      isSessionExpired: false,
      authError: null,
      loginWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      loginWithToken: loginWithTokenMock,
      logout: vi.fn(),
      sendPasswordReset: vi.fn(),
      updatePassword: updatePasswordMock,
      clearError: vi.fn(),
      ...overrides,
    };
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue(defaultContext);
    return { updatePasswordMock, loginWithTokenMock };
  };

  it('renders form inputs and password visibility toggles', () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /Set New Password/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/^New Password/i)).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText(/^Confirm New Password/i)).toHaveAttribute('type', 'password');

    // Toggle password visibility
    const toggles = screen.getAllByLabelText(/Show password/i);
    fireEvent.click(toggles[0]);
    expect(screen.getByLabelText(/^New Password/i)).toHaveAttribute('type', 'text');
  });

  it('validates password length (minimum 6 characters)', async () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    const newPassInput = screen.getByLabelText(/^New Password/i);
    const confirmPassInput = screen.getByLabelText(/^Confirm New Password/i);
    const submitBtn = screen.getByRole('button', { name: /Update Password/i });

    fireEvent.change(newPassInput, { target: { value: '12345' } });
    fireEvent.change(confirmPassInput, { target: { value: '12345' } });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Password must be at least 6 characters long/i)
    ).toBeInTheDocument();
  });

  it('validates matching passwords', async () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    const newPassInput = screen.getByLabelText(/^New Password/i);
    const confirmPassInput = screen.getByLabelText(/^Confirm New Password/i);
    const submitBtn = screen.getByRole('button', { name: /Update Password/i });

    fireEvent.change(newPassInput, { target: { value: 'secretPass123' } });
    fireEvent.change(confirmPassInput, { target: { value: 'differentPass' } });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Passwords do not match/i)
    ).toBeInTheDocument();
  });

  it('submits valid new password and displays success banner', async () => {
    const { updatePasswordMock } = mockAuthContext();

    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>
    );

    const newPassInput = screen.getByLabelText(/^New Password/i);
    const confirmPassInput = screen.getByLabelText(/^Confirm New Password/i);
    const submitBtn = screen.getByRole('button', { name: /Update Password/i });

    fireEvent.change(newPassInput, { target: { value: 'strongNewPassword123' } });
    fireEvent.change(confirmPassInput, { target: { value: 'strongNewPassword123' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(updatePasswordMock).toHaveBeenCalledWith('strongNewPassword123');
      expect(screen.getByText(/Password Updated Successfully!/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Go to Dashboard/i })).toBeInTheDocument();
    });
  });
});
