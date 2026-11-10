import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthPage } from '../AuthPage';
import * as AuthContextModule from '../AuthContext';
import type { AuthContextType } from '../AuthContext';

describe('AuthPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockAuthContext = (overrides: Partial<AuthContextType> = {}) => {
    const loginWithEmailMock = vi.fn().mockResolvedValue(undefined);
    const signUpWithEmailMock = vi.fn().mockResolvedValue({ requiresEmailConfirmation: false });
    const loginWithTokenMock = vi.fn();
    const sendPasswordResetMock = vi.fn().mockResolvedValue(undefined);
    const clearErrorMock = vi.fn();

    const defaultContext: AuthContextType = {
      session: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isSessionExpired: false,
      authError: null,
      loginWithEmail: loginWithEmailMock,
      signUpWithEmail: signUpWithEmailMock,
      loginWithToken: loginWithTokenMock,
      logout: vi.fn(),
      sendPasswordReset: sendPasswordResetMock,
      updatePassword: vi.fn(),
      clearError: clearErrorMock,
      ...overrides,
    };

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue(defaultContext);

    return {
      loginWithEmailMock,
      signUpWithEmailMock,
      loginWithTokenMock,
      sendPasswordResetMock,
      clearErrorMock,
    };
  };

  it('renders branding, Mumbai mobility highlights, and tab navigation', () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    // Branding & Mumbai highlights
    expect(screen.getByRole('heading', { name: 'Smart Share' })).toBeInTheDocument();
    expect(screen.getByText(/Intelligent Cab-Pooling for Mumbai/i)).toBeInTheDocument();
    expect(screen.getByText(/Smart Corridor Matching/i)).toBeInTheDocument();
    expect(screen.getByText(/Fair & Consented Fare Splitting/i)).toBeInTheDocument();

    // Tabs
    expect(screen.getByRole('tab', { name: /Sign In/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Create Account/i })).toBeInTheDocument();
  });

  it('switches between Sign In, Create Account, and Forgot Password modes', () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    // Default mode is Sign In
    expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();

    // Switch to Create Account
    const signupTab = screen.getByRole('tab', { name: /Create Account/i });
    fireEvent.click(signupTab);
    expect(screen.getByRole('button', { name: /Create Smart Share Account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();

    // Switch to Forgot Password via link
    const signinTab = screen.getByRole('tab', { name: /Sign In/i });
    fireEvent.click(signinTab);
    const forgotLink = screen.getByRole('button', { name: /Forgot password\?/i });
    fireEvent.click(forgotLink);
    expect(screen.getByRole('heading', { name: /Reset Your Password/i })).toBeInTheDocument();

    // Back to Sign In
    const backBtn = screen.getByRole('button', { name: /Back to Sign In/i });
    fireEvent.click(backBtn);
    expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();
  });

  it('validates required fields and email format on Sign In', async () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/Email Address/i);
    const submitBtn = screen.getByRole('button', { name: /^Sign In$/i });

    // Invalid email format
    fireEvent.change(emailInput, { target: { value: 'invalid-email-string' } });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Please enter a valid email address/i)).toBeInTheDocument();
  });

  it('toggles password visibility with accessible attributes', () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    const passInput = screen.getByLabelText(/^Password/i);
    expect(passInput).toHaveAttribute('type', 'password');

    const toggleBtn = screen.getByRole('button', { name: /Show password/i });
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(toggleBtn);
    expect(passInput).toHaveAttribute('type', 'text');
    expect(toggleBtn).toHaveAttribute('aria-label', 'Hide password');
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('submits valid Sign In and invokes loginWithEmail with rememberMe choice', async () => {
    const { loginWithEmailMock } = mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/Email Address/i);
    const passInput = screen.getByLabelText(/^Password/i);
    const rememberMeBox = screen.getByLabelText(/Remember this device/i);
    const submitBtn = screen.getByRole('button', { name: /^Sign In$/i });

    fireEvent.change(emailInput, { target: { value: 'commuter@smartshare.in' } });
    fireEvent.change(passInput, { target: { value: 'ValidPass123' } });
    expect(rememberMeBox).toBeChecked();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(loginWithEmailMock).toHaveBeenCalledWith('commuter@smartshare.in', 'ValidPass123', true);
    });
  });

  it('validates password length and matching confirmation on Sign Up', async () => {
    mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage initialMode="signup" />
      </MemoryRouter>
    );

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const passInput = screen.getByLabelText(/^Password/i);
    const confirmInput = screen.getByLabelText(/Confirm Password/i);
    const termsBox = screen.getByLabelText(/I agree to the Smart Share Terms of Service/i);
    const submitBtn = screen.getByRole('button', { name: /Create Smart Share Account/i });

    fireEvent.change(nameInput, { target: { value: 'Rajesh Patil' } });
    fireEvent.change(emailInput, { target: { value: 'rajesh@mumbai.in' } });
    fireEvent.change(passInput, { target: { value: 'short' } });
    fireEvent.change(confirmInput, { target: { value: 'short' } });
    fireEvent.click(termsBox);
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Password must be at least 6 characters long/i)
    ).toBeInTheDocument();

    // Mismatched passwords
    fireEvent.change(passInput, { target: { value: 'validPassword123' } });
    fireEvent.change(confirmInput, { target: { value: 'differentPassword456' } });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Passwords do not match/i)
    ).toBeInTheDocument();
  });

  it('handles email confirmation required flow on Sign Up', async () => {
    mockAuthContext({
      signUpWithEmail: vi.fn().mockResolvedValue({ requiresEmailConfirmation: true }),
    });

    render(
      <MemoryRouter>
        <AuthPage initialMode="signup" />
      </MemoryRouter>
    );

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const passInput = screen.getByLabelText(/^Password/i);
    const confirmInput = screen.getByLabelText(/Confirm Password/i);
    const termsBox = screen.getByLabelText(/I agree to the Smart Share Terms of Service/i);
    const submitBtn = screen.getByRole('button', { name: /Create Smart Share Account/i });

    fireEvent.change(nameInput, { target: { value: 'Aditi Varma' } });
    fireEvent.change(emailInput, { target: { value: 'aditi@mumbai.in' } });
    fireEvent.change(passInput, { target: { value: 'SecurePass2026' } });
    fireEvent.change(confirmInput, { target: { value: 'SecurePass2026' } });
    fireEvent.click(termsBox);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Verify Your Email/i })).toBeInTheDocument();
      expect(screen.getByText(/aditi@mumbai.in/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Return to Sign In/i })).toBeInTheDocument();
    });
  });

  it('handles Forgot Password recovery request submission', async () => {
    const { sendPasswordResetMock } = mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage initialMode="forgot" />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/Account Email Address/i);
    const submitBtn = screen.getByRole('button', { name: /Send Recovery Link/i });

    fireEvent.change(emailInput, { target: { value: 'rider@example.com' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(sendPasswordResetMock).toHaveBeenCalledWith('rider@example.com');
      expect(screen.getByText(/A password recovery link has been dispatched/i)).toBeInTheDocument();
    });
  });

  it('connects via Developer & Testing Token Access drawer', () => {
    const { loginWithTokenMock } = mockAuthContext();

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    // Toggle developer drawer
    const devToggle = screen.getByRole('button', { name: /Developer & Testing Token Access/i });
    fireEvent.click(devToggle);

    const tokenInput = screen.getByLabelText(/Bearer Access Token/i);
    const connectBtn = screen.getByRole('button', { name: /Connect Session/i });

    fireEvent.change(tokenInput, { target: { value: 'mock.developer.jwt' } });
    fireEvent.click(connectBtn);

    expect(loginWithTokenMock).toHaveBeenCalledWith('mock.developer.jwt');
  });

  it('displays error alerts with accessible alert role', () => {
    mockAuthContext({ authError: 'Invalid email or password. Please check your credentials.' });

    render(
      <MemoryRouter>
        <AuthPage />
      </MemoryRouter>
    );

    const alertBanner = screen.getByRole('alert');
    expect(alertBanner).toBeInTheDocument();
    expect(alertBanner).toHaveTextContent(/Invalid email or password/i);
  });
});
