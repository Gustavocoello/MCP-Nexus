import React from "react";

const PrivacyPage = () => {
  return (
    <div className="max-w-3xl mx-auto p-6 text-gray-800 dark:text-gray-100">
      <h1 className="text-3xl font-bold mb-4">Privacy Policy</h1>
      <p className="mb-4 italic">Last updated: November 15, 2025</p>

      <p className="mb-4">
        At <strong>AI Assistant (Jarvis)</strong>, we value your privacy. This Privacy Policy
        explains how we collect, use, store, and protect your data when using
        our services.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Data We Access</h2>
      <p className="mb-4">AI Assistant accesses the following data with your explicit consent:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>
          <strong>Google Calendar Data:</strong> Event titles, descriptions, start/end times,
          and calendar IDs via Google OAuth (MCP integration).
        </li>
        <li>
          <strong>Images:</strong> Images you upload for analysis are temporarily processed
          and stored only for usage tracking purposes (monthly analysis count to prevent
          exceeding API limits and avoid unexpected costs).
        </li>
        <li>
          <strong>Conversation Data:</strong> Messages and interactions with the AI assistant
          to provide conversational context and improve your experience.
        </li>
        <li>
          <strong>Authentication Data:</strong> Username, email, and encrypted passwords for
          multi-user authentication.
        </li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. How We Use Your Data</h2>
      <p className="mb-4">Your data is used exclusively to:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>Display, create, update, and manage your calendar events within the assistant.</li>
        <li>Analyze images you provide and track monthly usage to stay within service limits.</li>
        <li>Maintain conversation context for a seamless ChatGPT-like experience.</li>
        <li>Authenticate users securely in our multi-user system.</li>
        <li>Enable productivity tools and LangChain workflows for developers.</li>
      </ul>
      <p className="mb-4">
        <strong>We do NOT:</strong>
      </p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>Use your data for advertising or third-party analytics.</li>
        <li>Sell, rent, or share your personal information with external parties.</li>
        <li>Train AI models on your private data without explicit consent.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Data Sharing</h2>
      <p className="mb-4">
        No user data is shared with third parties. All information remains confidential
        and is used only within the context of your session and account. The only external
        services we integrate with are:
      </p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>
          <strong>Google Calendar API:</strong> For calendar management (OAuth-protected).
        </li>
        <li>
          <strong>OpenAI API:</strong> For AI-powered conversations (data not stored by OpenAI).
        </li>
        <li>
          <strong>LangChain:</strong> For advanced workflow orchestration (local processing).
        </li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Data Storage & Protection</h2>
      <p className="mb-4">We take security seriously:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>All data is transmitted securely using <strong>HTTPS encryption</strong>.</li>
        <li>Passwords are hashed using industry-standard algorithms (bcrypt/Argon2).</li>
        <li>
          Images are stored temporarily with metadata (analysis count) and automatically
          deleted after 30 days or upon user request.
        </li>
        <li>Your local AI runs entirely on your PC, ensuring maximum privacy.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Data Retention & Deletion</h2>
      <p className="mb-4">Data is retained only as long as necessary for the service to function:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>
          <strong>Conversation history:</strong> Stored locally or server-side (depending on
          configuration) and can be cleared at any time.
        </li>
        <li>
          <strong>Images:</strong> Automatically deleted after 30 days or immediately upon request.
        </li>
        <li>
          <strong>Calendar data:</strong> Not permanently stored; fetched in real-time from Google.
        </li>
        <li>
          <strong>Account data:</strong> Deleted within 7 days of account closure request.
        </li>
      </ul>
      <p className="mb-4">
        You may request deletion of your data at any time by contacting us at{" "}
        <a href="mailto:coellog634@gmail.com" className="text-blue-500 hover:underline">
          coellog634@gmail.com
        </a>
        .
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Your Rights</h2>
      <p className="mb-4">You have the right to:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>Access your personal data stored in our system.</li>
        <li>Request correction of inaccurate information.</li>
        <li>Request deletion of your account and associated data.</li>
        <li>Revoke Google Calendar access at any time via Google Account settings.</li>
        <li>Export your conversation history (if supported).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Third-Party Services</h2>
      <p className="mb-4">
        This application uses Google OAuth to request access to your Google Calendar data. 
        Access is limited strictly to reading and managing calendar events for your personal use 
        within the AI Assistant. We do not use this data for advertising, analytics, or share it 
        with any third parties. You can revoke access at any time from your Google Account 
        permissions page.
      </p>
      <p className="mb-4">AI Assistant integrates with:</p>
      <ul className="list-disc ml-6 mb-4 space-y-2">
        <li>
          <strong>Google Calendar API:</strong> Subject to{" "}
          <a
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noreferrer"
            className="text-blue-500 hover:underline"
          >
            Google's Privacy Policy
          </a>
          .
        </li>
        <li>
          <strong>OpenAI API:</strong> Subject to{" "}
          <a
            href="https://openai.com/privacy"
            target="_blank"
            rel="noreferrer"
            className="text-blue-500 hover:underline"
          >
            OpenAI's Privacy Policy
          </a>
          .
        </li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">8. Changes to This Policy</h2>
      <p className="mb-4">
        We may update this Privacy Policy from time to time. The "Last updated" date at the top
        will reflect any changes. Continued use of the service after changes constitutes
        acceptance of the updated policy.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">9. Contact Us</h2>
      <p className="mb-4">For questions about this Privacy Policy or to exercise your rights, please contact us:</p>
      <ul className="list-none ml-0 mb-4 space-y-2">
        <li>
          📧 Email:{" "}
          <a href="mailto:coellog634@gmail.com" className="text-blue-500 hover:underline">
            coellog634@gmail.com
          </a>
        </li>
        <li>
          🌐 Website:{" "}
          <a
            href="https://www.gustavocoello.space"
            target="_blank"
            rel="noreferrer"
            className="text-blue-500 hover:underline"
          >
            gustavocoello.space
          </a>
        </li>
        <li>
          💼 Portfolio:{" "}
          <a
            href="https://cv-gus.vercel.app"
            target="_blank"
            rel="noreferrer"
            className="text-blue-500 hover:underline"
          >
            cv-gus.vercel.app
          </a>
        </li>
      </ul>

      <div className="mt-8 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> AI Assistant (Jarvis) is a personal portfolio project designed
          to showcase AI integration skills. It runs primarily locally on your machine,
          ensuring maximum privacy and control over your data.
        </p>
      </div>
    </div>
  );
};

export default PrivacyPage;