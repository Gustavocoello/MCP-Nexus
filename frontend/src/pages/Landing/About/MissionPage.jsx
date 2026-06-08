// src/pages/About/MissionPage.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, Code, Zap, Users, Lock, Heart } from 'lucide-react';
import './About.css';

const MissionPage = () => {
  const navigate = useNavigate();

  return (
      <div className="legal-container">
        <button onClick={() => navigate(-1)} className="back-button">
          Back
        </button>

        <div className="legal-header">
          <Target size={48} className="header-icon" />
          <h1>Our Mission</h1>
          <p className="subtitle">Educational Innovation & Open Access to AI</p>
        </div>

        <div className="legal-content">
          {/* Main Mission Statement */}
          <section className="mission-section">
            <div className="mission-card primary">
              <Heart className="section-icon" />
              <h2>100% Educational Purpose</h2>
              <p>
                This project is entirely educational and non-commercial. We will <strong>never sell, 
                monetize, or commercialize</strong> this platform or your data to third parties. 
                Our commitment is to learning, innovation, and demonstrating what's possible with 
                dedication and code.
              </p>
            </div>
          </section>

          {/* Core Values */}
          <section className="mission-section">
            <h2>What Drives Us</h2>
            
            <div className="mission-grid">
              <div className="mission-card">
                <Code className="section-icon" />
                <h3>Showcase Technical Skills</h3>
                <p>
                  Demonstrate real-world problem-solving abilities through clean, scalable code 
                  and modern architecture patterns.
                </p>
              </div>

              <div className="mission-card">
                <Zap className="section-icon" />
                <h3>Solve Real Problems</h3>
                <p>
                  Many AI chat platforms limit access behind paywalls and subscriptions. We're 
                  breaking those barriers by maximizing free API credits and creating unlimited 
                  access.
                </p>
              </div>

              <div className="mission-card">
                <Users className="section-icon" />
                <h3>Free & Accessible</h3>
                <p>
                  100% personalized LLM access, MCP integration with your services, image support, 
                  and more—all completely free. No hidden costs, no premium tiers.
                </p>
              </div>

              <div className="mission-card">
                <Lock className="section-icon" />
                <h3>Privacy First</h3>
                <p>
                  Your data belongs to you. We use secure encryption, OAuth 2.0, and never share 
                  your information with third parties.
                </p>
              </div>
            </div>
          </section>

          {/* The Problem We're Solving */}
          <section className="mission-section">
            <h2>The Problem We're Solving</h2>
            <div className="problem-solution">
              <div className="problem-box">
                <h3>Traditional AI Platforms</h3>
                <ul>
                  <li>Limited free messages per month</li>
                  <li>Expensive subscription plans ($20-$40/month)</li>
                  <li>No integration with your personal tools</li>
                  <li>Generic responses without context</li>
                  <li>Data sold to third parties</li>
                </ul>
              </div>

              <div className="solution-box">
                <h3>✅ Jarvis (MCP-Nexus)</h3>
                <ul>
                  <li>Unlimited free access</li>
                  <li>Multiple API keys for maximum uptime</li>
                  <li>MCP integration (Google Calendar, Notion, Slack...)</li>
                  <li>Contextual memory for personalized responses</li>
                  <li>Your data stays private—forever</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Our Approach */}
          <section className="mission-section">
            <h2>Our Approach</h2>
            <div className="approach-list">
              <div className="approach-item">
                <div className="approach-number">1</div>
                <div className="approach-content">
                  <h3>Smart API Key Rotation</h3>
                  <p>
                    We use multiple OpenRouter API keys to distribute requests efficiently, 
                    maximizing free tier usage without hitting rate limits.
                  </p>
                </div>
              </div>

              <div className="approach-item">
                <div className="approach-number">2</div>
                <div className="approach-content">
                  <h3>Model Context Protocol (MCP)</h3>
                  <p>
                    Seamless integration with your productivity tools—Google Calendar, Notion, 
                    Slack, Gmail—all accessible through natural conversation.
                  </p>
                </div>
              </div>

              <div className="approach-item">
                <div className="approach-number">3</div>
                <div className="approach-content">
                  <h3>Intelligent Memory System</h3>
                  <p>
                    Context-aware conversations with automatic summarization, ensuring relevant 
                    and personalized responses without token waste.
                  </p>
                </div>
              </div>

              <div className="approach-item">
                <div className="approach-number">4</div>
                <div className="approach-content">
                  <h3>Modern Tech Stack</h3>
                  <p>
                    React, Flask, FastAPI, Docker, Azure—production-grade technologies deployed 
                    with best practices.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Important Note */}
          <section className="mission-section">
            <div className="mission-card warning">
              <h2>⚠️ Important Disclaimer</h2>
              <p>
                This project is <strong>not designed for massive user loads</strong>. It's a 
                proof-of-concept demonstrating what's possible with creativity, dedication, and 
                modern development practices. Think of it as a portfolio piece and educational 
                tool, not a commercial product.
              </p>
              <p>
                We're here to <strong>learn, build, and inspire</strong>—not to compete with 
                enterprise AI platforms.
              </p>
            </div>
          </section>

          {/* Call to Action */}
          <section className="mission-section cta">
            <h2>Join the Journey</h2>
            <p>
              Whether you're a developer, student, or AI enthusiast, we invite you to explore 
              what we've built. Have questions? Want to contribute? Interested in hiring?
            </p>
            <button onClick={() => navigate('/contact')} className="cta-button">
              Get in Touch →
            </button>
          </section>
        </div>

        <div className="legal-footer">
          <p>Last updated: December 2025</p>
        </div>
    </div>
  );
};

export default MissionPage;