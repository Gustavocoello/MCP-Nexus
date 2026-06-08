// src/pages/About/ContactPage.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Linkedin, Code, Briefcase, MessageSquare, Send } from 'lucide-react';
import EarthSVG from "/icons/earth.svg";
import './About.css';

const ContactPage = () => {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const handleCopyEmail = () => {
    navigator.clipboard.writeText('coellog634@gmail.com');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
      <div className="legal-container">
        <button onClick={() => navigate(-1)} className="back-button">
          Back
        </button>

        <div className="legal-header">
          <MessageSquare size={48} className="header-icon" />
          <h1>Get in Touch</h1>
          <p className="subtitle">Let's build something amazing together</p>
        </div>

        <div className="legal-content">
          {/* Hero Section with Earth SVG */}
          <section className="contact-hero">
            <div className="earth-animation">
              {/* Opción 1: Si tienes el SVG como archivo */}
              <img src={EarthSVG} alt="Earth" className="earth-svg" />
              
              {/* Opción 2: Si quieres el SVG inline (comenta la línea de arriba y usa esto) */}
              {/* 
              <svg className="earth-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                // Aquí va tu código SVG del earth.svg
                // Copia el contenido del archivo y pégalo aquí
              </svg>
              */}
            </div>
            <div className="hero-text">
              <h2>Building from Ecuador 🇪🇨</h2>
              <p>
                Open to collaboration, feedback, and opportunities. Whether you want to add a 
                feature, report a bug, or discuss a job opportunity—I'm all ears!
              </p>
            </div>
          </section>

          {/* Contact Cards */}
          <section className="contact-section">
            <h2>Ways to Connect</h2>
            
            <div className="contact-grid">
              {/* Email Card */}
              <div className="contact-card primary">
                <div className="card-icon">
                  <Mail size={32} />
                </div>
                <h3>Email Me</h3>
                <p className="contact-detail">coellog634@gmail.com</p>
                <div className="card-actions">
                  <a 
                    href="mailto:coellog634@gmail.com" 
                    className="contact-btn primary"
                  >
                    <Send size={18} />
                    Send Email
                  </a>
                  <button 
                    onClick={handleCopyEmail} 
                    className="contact-btn secondary"
                  >
                    {copied ? '✓ Copied!' : 'Copy Email'}
                  </button>
                </div>
              </div>

              {/* LinkedIn Card */}
              <div className="contact-card">
                <div className="card-icon linkedin">
                  <Linkedin size={32} />
                </div>
                <h3>LinkedIn</h3>
                <p className="contact-detail">Connect professionally</p>
                <a 
                  href="https://www.linkedin.com/in/gustavocoelloo" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="contact-btn primary"
                >
                  <Linkedin size={18} />
                  View Profile
                </a>
              </div>

              {/* GitHub Card (opcional) */}
              <div className="contact-card">
                <div className="card-icon github">
                  <Code size={32} />
                </div>
                <h3>GitHub</h3>
                <p className="contact-detail">Check out my code</p>
                <a 
                  href="https://github.com/Gustavocoello" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="contact-btn primary"
                >
                  <Code size={18} />
                  View Projects
                </a>
              </div>
            </div>
          </section>

          {/* What I'm Looking For */}
          <section className="contact-section">
            <h2>I'm Open To</h2>
            
            <div className="opportunities-grid">
              <div className="opportunity-card">
                <Briefcase className="opp-icon" />
                <h3>Job Opportunities</h3>
                <p>
                  Full-time, contract, or freelance positions in Full-Stack Development, 
                  AI/ML Engineering, or Cloud Architecture.
                </p>
              </div>

              <div className="opportunity-card">
                <Code className="opp-icon" />
                <h3>Collaborations</h3>
                <p>
                  Open-source contributions, hackathons, or building innovative projects 
                  with like-minded developers.
                </p>
              </div>

              <div className="opportunity-card">
                <MessageSquare className="opp-icon" />
                <h3>Feedback & Ideas</h3>
                <p>
                  Have suggestions for Jarvis? Found a bug? Want a new feature? 
                  I'd love to hear from you!
                </p>
              </div>
            </div>
          </section>

          {/* Tech Stack */}
          <section className="contact-section">
            <h2>What I Work With</h2>
            <div className="tech-stack">
              <span className="tech-badge">Python</span>
              <span className="tech-badge">MySQL</span>
              <span className="tech-badge">Azure</span>
              <span className="tech-badge">MCP</span>
              <span className="tech-badge">LangChain</span>
              <span className="tech-badge">Git</span>
              <span className="tech-badge">Flask</span>
              <span className="tech-badge">FastAPI</span>
              <span className="tech-badge">Docker</span>
              <span className="tech-badge">OpenRouter</span>
              <span className="tech-badge">OAuth 2.0</span>
            </div>
          </section>

          {/* Call to Action */}
          <section className="contact-section cta">
            <div className="cta-box">
              <h2>Let's Talk!</h2>
              <p>
                Whether you're hiring, collaborating, or just want to chat about tech—
                I'm always excited to connect with passionate people.
              </p>
              <div className="cta-buttons">
                <a 
                  href="mailto:coellog634@gmail.com?subject=Hello from Jarvis Website!" 
                  className="cta-button primary"
                >
                  <Mail size={20} />
                  Email Me Now
                </a>
                <a 
                  href="https://www.linkedin.com/in/gustavocoelloo" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="cta-button secondary"
                >
                  <Linkedin size={20} />
                  Connect on LinkedIn
                </a>
              </div>
            </div>
          </section>
        </div>

        <div className="legal-footer">
          <p>Based in Guayaquil, Ecuador 🇪🇨 | Available for remote work worldwide 🌍</p>
        </div>
      </div>
  );
};

export default ContactPage;