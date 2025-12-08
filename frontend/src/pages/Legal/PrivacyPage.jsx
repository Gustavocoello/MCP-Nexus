import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, Eye, Database, Clock, Mail, Download, Trash2 } from 'lucide-react';
import '../About/About.css';

const PrivacyPage = () => {
  const navigate = useNavigate();

  return (
      <div className="legal-container">
        <button onClick={() => navigate(-1)} className="back-button">
          Back
        </button>

        <div className="legal-header">
          <Shield size={48} className="header-icon" />
          <h1>Privacy Policy</h1>
          <p className="subtitle">Your data, your control. Always.</p>
        </div>

        <div className="legal-content">
          {/* Introduction */}
          <section className="terms-section">
            <p className="intro-text">
              At <strong>Jarvis (MCP-Nexus)</strong>, we value your privacy above all. 
              This Privacy Policy explains how we collect, use, store, and protect your data 
              when using our services. We are committed to transparency and giving you full 
              control over your information.
            </p>
            <div className="info-box">
              <Lock className="info-icon" />
              <p>
                <strong>Key Promise:</strong> We will NEVER sell, rent, or share your personal 
                data with third parties. This is an educational project—your trust is everything.
              </p>
            </div>
          </section>

          {/* Data We Collect */}
          <section className="terms-section">
            <h2>1. Data We Access</h2>
            <p>
              With your <strong>explicit consent</strong>, we access the following data:
            </p>

            <div className="data-grid">
              <div className="data-card">
                <Database className="data-icon" />
                <h3>Google Calendar Data</h3>
                <p>
                  Event titles, descriptions, start/end times, and calendar IDs via Google 
                  OAuth (MCP integration). This data is fetched in real-time and not 
                  permanently stored.
                </p>
              </div>

              <div className="data-card">
                <Eye className="data-icon" />
                <h3>Images</h3>
                <p>
                  Images you upload for analysis are temporarily processed and stored only 
                  for usage tracking purposes (monthly analysis count to prevent exceeding 
                  API limits and avoid unexpected costs).
                </p>
              </div>

              <div className="data-card">
                <Database className="data-icon" />
                <h3>Conversation Data</h3>
                <p>
                  Messages and interactions with the AI assistant to provide conversational 
                  context and improve your experience. Stored securely and can be deleted 
                  at any time.
                </p>
              </div>

              <div className="data-card">
                <Lock className="data-icon" />
                <h3>Authentication Data</h3>
                <p>
                  Username, email, and encrypted OAuth tokens for secure multi-user 
                  authentication via Clerk.
                </p>
              </div>
            </div>
          </section>

          {/* How We Use Data */}
          <section className="terms-section">
            <h2>2. How We Use Your Data</h2>
            <p>Your data is used exclusively to:</p>
            
            <ul className="terms-list">
              <li>Display, create, update, and manage your calendar events within the assistant</li>
              <li>Analyze images you provide and track monthly usage to stay within service limits</li>
              <li>Maintain conversation context for a seamless AI experience</li>
              <li>Authenticate users securely in our multi-user system</li>
              <li>Enable productivity tools and MCP workflows</li>
            </ul>

            <div className="responsibility-grid">
              <div className="responsibility-card do">
                <h3>✅ We DO</h3>
                <ul>
                  <li>Encrypt all sensitive data</li>
                  <li>Use HTTPS for all communications</li>
                  <li>Allow you to delete your data anytime</li>
                  <li>Keep your data private and confidential</li>
                </ul>
              </div>

              <div className="responsibility-card dont">
                <h3>❌ We DO NOT</h3>
                <ul>
                  <li>Use your data for advertising</li>
                  <li>Sell, rent, or share with third parties</li>
                  <li>Train AI models on your private data</li>
                  <li>Track you across other websites</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Data Sharing */}
          <section className="terms-section">
            <h2>3. Data Sharing</h2>
            <p>
              <strong>No user data is shared with third parties.</strong> All information 
              remains confidential and is used only within the context of your session and 
              account.
            </p>
            <p>The only external services we integrate with are:</p>
            
            <div className="service-list">
              <span className="service-badge">Google Calendar API (OAuth-protected)</span>
              <span className="service-badge">OpenRouter API (AI models)</span>
              <span className="service-badge">Clerk (Authentication)</span>
              <span className="service-badge">Azure (Image analysis)</span>
            </div>

            <div className="info-box">
              <Shield className="info-icon" />
              <p>
                These services have their own privacy policies. We only share the minimal 
                data necessary for functionality (e.g., sending your message to OpenRouter 
                for AI responses).
              </p>
            </div>
          </section>

          {/* Security */}
          <section className="terms-section">
            <h2>4. Data Storage & Protection</h2>
            <p>We take security seriously:</p>

            <div className="security-grid">
              <div className="security-feature">
                <Lock size={24} />
                <h4>Encryption</h4>
                <p>All data transmitted via HTTPS. OAuth tokens encrypted with AES-256.</p>
              </div>

              <div className="security-feature">
                <Shield size={24} />
                <h4>Password Hashing</h4>
                <p>Passwords hashed using industry-standard bcrypt/Argon2 algorithms.</p>
              </div>

              <div className="security-feature">
                <Database size={24} />
                <h4>Secure Storage</h4>
                <p>Data stored in Azure MySQL with access controls and monitoring.</p>
              </div>

              <div className="security-feature">
                <Clock size={24} />
                <h4>Auto-Deletion</h4>
                <p>Images automatically deleted after 60 days or upon request.</p>
              </div>
            </div>
          </section>

          {/* Data Retention */}
          <section className="terms-section">
            <h2>5. Data Retention & Deletion</h2>
            <p>Data is retained only as long as necessary for the service to function:</p>

            <div className="retention-table">
              <div className="retention-row header">
                <div className="retention-col">Data Type</div>
                <div className="retention-col">Retention Period</div>
                <div className="retention-col">Deletion</div>
              </div>

              <div className="retention-row">
                <div className="retention-col">
                  <Database size={18} />
                  Conversation History
                </div>
                <div className="retention-col">Until you delete</div>
                <div className="retention-col">
                  <Trash2 size={16} /> Anytime via UI
                </div>
              </div>

              <div className="retention-row">
                <div className="retention-col">
                  <Eye size={18} />
                  Images
                </div>
                <div className="retention-col">60 days max</div>
                <div className="retention-col">
                  <Trash2 size={16} /> Auto or on request
                </div>
              </div>

              <div className="retention-row">
                <div className="retention-col">
                  <Database size={18} />
                  Calendar Data
                </div>
                <div className="retention-col">Not stored</div>
                <div className="retention-col">Fetched in real-time</div>
              </div>

              <div className="retention-row">
                <div className="retention-col">
                  <Lock size={18} />
                  Account Data
                </div>
                <div className="retention-col">Until closure</div>
                <div className="retention-col">
                  <Trash2 size={16} /> 7 days after request
                </div>
              </div>
            </div>

            <div className="info-box">
              <Mail className="info-icon" />
              <p>
                You may request deletion of your data at any time by contacting us at{' '}
                <strong>coellog634@gmail.com</strong>
              </p>
            </div>
          </section>

          {/* Your Rights */}
          <section className="terms-section">
            <h2>6. Your Rights</h2>
            <p>You have the right to:</p>

            <div className="rights-grid">
              <div className="right-card">
                <Eye className="right-icon" />
                <h3>Access</h3>
                <p>View all personal data stored in our system</p>
              </div>

              <div className="right-card">
                <Download className="right-icon" />
                <h3>Export</h3>
                <p>Download your conversation history</p>
              </div>

              <div className="right-card">
                <Trash2 className="right-icon" />
                <h3>Delete</h3>
                <p>Request complete data deletion</p>
              </div>

              <div className="right-card">
                <Shield className="right-icon" />
                <h3>Revoke</h3>
                <p>Remove Google Calendar access anytime</p>
              </div>
            </div>
          </section>

          {/* Third-Party Services */}
          <section className="terms-section">
            <h2>7. Third-Party Services</h2>
            <p>
              This application uses <strong>Google OAuth</strong> to request access to your 
              Google Calendar data. Access is limited strictly to reading and managing calendar 
              events for your personal use within Jarvis.
            </p>
            <p>
              We do not use this data for advertising, analytics, or share it with any third 
              parties. You can revoke access at any time from your{' '}
              <a 
                href="https://myaccount.google.com/permissions" 
                target="_blank" 
                rel="noopener noreferrer"
                style={{color: '#3b82f6', textDecoration: 'underline'}}
              >
                Google Account permissions page
              </a>.
            </p>

            <div className="service-policies">
              <h3>External Service Policies:</h3>
              <ul className="terms-list">
                <li>
                  <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">
                    Google Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener noreferrer">
                    OpenAI Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="https://clerk.com/privacy" target="_blank" rel="noopener noreferrer">
                    Clerk Privacy Policy
                  </a>
                </li>
              </ul>
            </div>
          </section>

          {/* Changes */}
          <section className="terms-section">
            <h2>8. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. The "Last updated" date 
              at the top will reflect any changes. Continued use of the service after changes 
              constitutes acceptance of the updated policy.
            </p>
          </section>

          {/* Contact */}
          <section className="terms-section">
            <h2>9. Contact Us</h2>
            <p>
              For questions about this Privacy Policy or to exercise your rights, please contact:
            </p>
            <div className="contact-info">
              <p><strong>📧 Email:</strong> coellog634@gmail.com</p>
              <p><strong>💼 LinkedIn:</strong> linkedin.com/in/gustavocoelloo</p>
              <p><strong>🌐 Website:</strong> gustavocoello.space</p>
            </div>
            <button onClick={() => navigate('/contact')} className="cta-button primary">
              Get in Touch
            </button>
          </section>

          {/* Final Note */}
          <section className="terms-section final">
            <div className="acknowledgment-box">
              <h3>Important Note</h3>
              <p>
                <strong>Jarvis (MCP-Nexus)</strong> is a personal portfolio project designed 
                to showcase AI integration skills and modern full-stack development. It runs 
                primarily on secure cloud infrastructure, ensuring maximum privacy and control 
                over your data.
              </p>
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

export default PrivacyPage;