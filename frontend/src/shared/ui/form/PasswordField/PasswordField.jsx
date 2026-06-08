// src/components/ui/PasswordField/PasswordField.js
import React, { useState } from 'react';
import './PasswordField.css';

const PasswordField = ({ label, name, value, onChange, placeholder }) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="input-wrapper">
      <label>{label}</label>
      <div className="password-input">
        <input
          type={visible ? 'text' : 'password'}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={() => setVisible(!visible)}
        >
          {visible ? '🙈' : '👁️'}
        </button>
      </div>
    </div>
  );
};

export default PasswordField;
