import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import InputField from '../../../../components/ui/Form/InputField/InputField';
import PasswordField from '../../../../components/ui/Form/PasswordField/PasswordField';
import { loginUser, getCurrentUser, loginWithGoogle, loginWithGitHub } from '../authService';
import { BiLogoGithub } from 'react-icons/bi';
import { FaGoogle } from 'react-icons/fa';
import './LoginPage.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await loginUser(email, password);
      const user = await getCurrentUser();
      console.log('Usuario autenticado:', user);
      navigate('/');
    } catch (err) {
      setError(err?.message || 'Error al iniciar sesión');
    }
  };

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  return (
    <div className="auth-container">
      <form className="auth-form" onSubmit={handleLogin}>
        <div className="login-page-container">
          <img src="/icons/jarvis00.png" alt="Jarvis Icon" className="jarvis-logo1" />
          <h2>Log In</h2>
        </div>

        <InputField
          label="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          required
        />
        <PasswordField
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="auth-error">{error}</p>}
        <button type="submit" className="auth-button">Log In</button>

        <div className="oauth-icon-row">
          <div className="oauth-icon-button google" title="Continue with Google" onClick={loginWithGoogle}>
            <FaGoogle />
          </div>
          <div className="oauth-icon-button github" title="Continue with GitHub" onClick={loginWithGitHub}>
            <BiLogoGithub />
          </div>
        </div>

        <div className="auth-links">
          <p>
            Don’t have an account?{' '}
            <span className="auth-link" onClick={() => navigate('/register')}>
              Create one
            </span>
          </p>
          <p>
            <span className="auth-link" onClick={() => alert('Feature coming soon')}>
              Forgot your password?
            </span>
          </p>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
