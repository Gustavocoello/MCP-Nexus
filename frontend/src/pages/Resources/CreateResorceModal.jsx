import React, { useState } from "react";
import { FaTimes } from "react-icons/fa";
import "./GuidesPage.css";

const CreateResourceModal = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    link: "",
    category: "Frontend",
    image: "",
    owner: ""
  });

  const categories = ["Frontend", "Backend", "AI/ML", "DevOps", "CSS", "Database", "Tools", "Other"];

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.title || !formData.link) {
      alert("Title and Link are required!");
      return;
    }
    onSubmit(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Resource</h2>
          <button className="btn-close" onClick={onClose}>
            <FaTimes />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="resource-form">
          <div className="form-group">
            <label>Title *</label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="e.g., React Documentation"
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Brief description of the resource..."
              rows="3"
            />
          </div>

          <div className="form-group">
            <label>Link *</label>
            <input
              type="url"
              name="link"
              value={formData.link}
              onChange={handleChange}
              placeholder="https://example.com"
              required
            />
          </div>

          <div className="form-group">
            <label>Image URL (optional)</label>
            <input
              type="url"
              name="image"
              value={formData.image}
              onChange={handleChange}
              placeholder="https://example.com/image.jpg"
            />
            <small className="form-hint">Leave empty to use placeholder</small>
          </div>

          <div className="form-group">
            <label>Your Name (optional)</label>
            <input
              type="text"
              name="owner"
              value={formData.owner}
              onChange={handleChange}
              placeholder="e.g., Gustavo Coello"
              maxLength="50"
            />
            <small className="form-hint">Leave empty to show only date</small>
          </div>

          <div className="form-group">
            <label>Category</label>
            <select
              name="category"
              value={formData.category}
              onChange={handleChange}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-submit">
              Create Resource
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateResourceModal;