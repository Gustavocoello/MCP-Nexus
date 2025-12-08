import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import '../About/About.css';

const TermsPage = () => {
  const navigate = useNavigate();

  return (
      <div className="legal-container">
        <button onClick={() => navigate(-1)} className="back-button">
          Back
        </button>

        <div className="legal-header">
          <FileText size={48} className="header-icon" />
          <h1>Terms of Service</h1>
          <p className="subtitle">Educational Project - Non-Commercial Use Only</p>
        </div>

        <div className="legal-content">
          {/* Acceptance */}
          <section className="terms-section">
            <h2>1. Acceptance of Terms</h2>
            <p>
              By accessing and using Jarvis (MCP-Nexus), you acknowledge that you have read, 
              understood, and agree to be bound by these Terms of Service. This is an 
              <strong> educational, non-commercial project</strong> created solely for 
              learning and demonstration purposes.
            </p>
            <div className="info-box">
              <CheckCircle className="info-icon" />
              <p>
                <strong>Important:</strong> This platform is NOT intended for commercial use, 
                production environments, or handling sensitive business data.
              </p>
            </div>
          </section>

          {/* Educational Purpose */}
          <section className="terms-section">
            <h2>2. Educational Purpose & Limitations</h2>
            <p>
              Jarvis is a <strong>proof-of-concept portfolio project</strong> designed to:
            </p>
            <ul className="terms-list">
              <li>Demonstrate modern full-stack development skills</li>
              <li>Showcase integration with AI models and MCP protocols</li>
              <li>Provide free access to AI capabilities for educational use</li>
              <li>Explore innovative solutions to common AI platform limitations</li>
            </ul>
            
            <div className="warning-box">
              <AlertTriangle className="warning-icon" />
              <div>
                <h3>Not Suitable For:</h3>
                <ul className="warning-list">
                  <li>Commercial applications or business operations</li>
                  <li>High-volume or mission-critical workloads</li>
                  <li>Storing confidential or proprietary information</li>
                  <li>Production environments requiring SLAs or guarantees</li>
                </ul>
              </div>
            </div>
          </section>

          {/* User Responsibilities */}
          <section className="terms-section">
            <h2>3. User Responsibilities</h2>
            <p>By using this service, you agree to:</p>
            
            <div className="responsibility-grid">
              <div className="responsibility-card do">
                <CheckCircle className="card-icon" />
                <h3>✅ You May</h3>
                <ul>
                  <li>Use for personal learning and exploration</li>
                  <li>Test features and integrations</li>
                  <li>Provide feedback and suggestions</li>
                  <li>Share your experience (non-commercially)</li>
                </ul>
              </div>

              <div className="responsibility-card dont">
                <XCircle className="card-icon" />
                <h3>❌ You May Not</h3>
                <ul>
                  <li>Use for commercial purposes</li>
                  <li>Abuse or overload the system</li>
                  <li>Attempt to hack or reverse-engineer</li>
                  <li>Share credentials with third parties</li>
                  <li>Violate applicable laws or regulations</li>
                </ul>
              </div>
            </div>
          </section>

          {/* API Usage & Rate Limits */}
          <section className="terms-section">
            <h2>4. API Usage & Rate Limits</h2>
            <p>
              We use free-tier API keys from OpenRouter and other services to provide unlimited 
              access. However:
            </p>
            <ul className="terms-list">
              <li>Service availability depends on third-party API limits</li>
              <li>We may implement rate limiting to ensure fair usage</li>
              <li>Features may be temporarily unavailable due to API quota exhaustion</li>
              <li>We reserve the right to restrict access to users who abuse the system</li>
            </ul>
          </section>

          {/* Data & Privacy */}
          <section className="terms-section">
            <h2>5. Data Collection & Privacy</h2>
            <p>
              Your privacy is important to us. Please review our{' '}
              <span 
                onClick={() => navigate('/privacy')} 
                style={{color: '#3b82f6', cursor: 'pointer', textDecoration: 'underline'}}
              >
                Privacy Policy
              </span>{' '}
              for detailed information. Key points:
            </p>
            <ul className="terms-list">
              <li>We collect minimal data necessary for functionality</li>
              <li>OAuth tokens are encrypted and stored securely</li>
              <li>We will NEVER sell your data to third parties</li>
              <li>Chat history is stored to provide context and memory features</li>
              <li>You can request data deletion at any time</li>
            </ul>
          </section>

          {/* Third-Party Services */}
          <section className="terms-section">
            <h2>6. Third-Party Services & Integrations</h2>
            <p>
              This platform integrates with external services including:
            </p>
            <div className="service-list">
              <span className="service-badge">OpenRouter</span>
              <span className="service-badge">Google Calendar</span>
              <span className="service-badge">Clerk Auth</span>
              <span className="service-badge">Azure</span>
              <span className="service-badge">Render</span>
            </div>
            <p>
              Each service has its own Terms of Service and Privacy Policies. By using our 
              platform, you also agree to comply with their terms.
            </p>
          </section>

          {/* Disclaimers */}
          <section className="terms-section">
            <h2>7. Disclaimers & Limitations of Liability</h2>
            
            <div className="disclaimer-box">
              <Shield className="disclaimer-icon" />
              <div>
                <h3>AS-IS Service</h3>
                <p>
                  This service is provided <strong>"AS IS"</strong> without warranties of any kind. 
                  We make no guarantees regarding:
                </p>
                <ul>
                  <li>Uptime, availability, or performance</li>
                  <li>Accuracy or reliability of AI-generated responses</li>
                  <li>Data integrity or backup guarantees</li>
                  <li>Security against all possible threats</li>
                </ul>
              </div>
            </div>

            <p>
              <strong>Limitation of Liability:</strong> To the maximum extent permitted by law, 
              we shall not be liable for any indirect, incidental, special, or consequential 
              damages arising from your use of this service.
            </p>
          </section>

          {/* Intellectual Property */}
          <section className="terms-section">
            <h2>8. Intellectual Property</h2>
            <p>
              The source code, design, and original content of this project are created by 
              Gustavo Coello. While the project may be open-sourced in the future, all rights 
              are currently reserved.
            </p>
            <p>
              AI-generated content created through this platform is provided for your personal 
              use. We claim no ownership over your conversations or generated content.
            </p>
          </section>

          {/* Termination */}
          <section className="terms-section">
            <h2>9. Account Termination</h2>
            <p>
              We reserve the right to suspend or terminate your access at any time, without 
              notice, for:
            </p>
            <ul className="terms-list">
              <li>Violation of these Terms of Service</li>
              <li>Abuse or misuse of the platform</li>
              <li>Suspicious or fraudulent activity</li>
              <li>Any reason we deem necessary to protect the service or other users</li>
            </ul>
          </section>

          {/* Changes to Terms */}
          <section className="terms-section">
            <h2>10. Changes to These Terms</h2>
            <p>
              We may update these Terms of Service from time to time. Significant changes will 
              be communicated through the platform. Continued use after changes constitutes 
              acceptance of the new terms.
            </p>
          </section>

          {/* Contact */}
          <section className="terms-section">
            <h2>11. Contact & Questions</h2>
            <p>
              If you have questions about these Terms, please contact:
            </p>
            <div className="contact-info">
              <p><strong>Email:</strong> coellog634@gmail.com</p>
              <p><strong>LinkedIn:</strong> linkedin.com/in/gustavocoelloo</p>
            </div>
            <button onClick={() => navigate('/contact')} className="cta-button primary">
              Get in Touch
            </button>
          </section>

          {/* Acknowledgment */}
          <section className="terms-section final">
            <div className="acknowledgment-box">
              <h3>By using Jarvis, you acknowledge that:</h3>
              <ul>
                <li>This is an educational, non-commercial project</li>
                <li>Service may be unstable or temporarily unavailable</li>
                <li>You use the platform at your own risk</li>
                <li>Your data is handled according to our Privacy Policy</li>
                <li>You agree to all terms outlined in this document</li>
              </ul>
            </div>
          </section>
        </div>

        <div className="legal-footer">
          <p>Last updated: December 2025</p>
          <p>Jarvis (MCP-Nexus) • Educational Project by Gustavo Coello</p>
        </div>
      </div>
  );
};

export default TermsPage;