// src/components/ui/InputField/InputField.js
import React from 'react';
import '../../Form/FormField.css';

export default function InputField({ label, type = "text", name, value, onChange, placeholder }) {
  return (
    <div className="input-group">
      {label && <label htmlFor={name}>{label}</label>}
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="form-field"
      />
    </div>
  );
}
