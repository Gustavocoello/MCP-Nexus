import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import InputField from '../../../../components/ui/Form/InputField/InputField';
import PasswordField from '../../../../components/ui/Form/PasswordField/PasswordField';
import { registerUser } from '../authService';
import './RegisterPage.css';

const RegisterPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await registerUser(formData);
      console.log('User registered:', res.user);
      navigate('/');
    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.error || 'Registration failed');
    } finally {
      setLoading(false);
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
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="login-page-container">
          <img src="/icons/jarvis00.png" alt="Jarvis Icon" className="jarvis-logo1" />
          <h2>Create Account</h2>
        </div>

        <InputField
          label="Name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          required
        />
        <InputField
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          required
        />
        <PasswordField
          label="Password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          required
        />

        {error && <p className="auth-error">{error}</p>}

        <button type="submit" className="auth-button" disabled={loading}>
          {loading ? 'Registering...' : 'Sign Up'}
        </button>

        <div className="auth-links">
          <p>
            Already have an account?{' '}
            <span className="auth-link" onClick={() => navigate('/login')}>
              Back to Log In
            </span>
          </p>
        </div>
      </form>
    </div>
  );
};

export default RegisterPage;
