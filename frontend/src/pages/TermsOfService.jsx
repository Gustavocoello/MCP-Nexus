import React from "react";

const TermsOfService = () => {
  return (
    <div className="max-w-3xl mx-auto p-6 text-gray-800 dark:text-gray-100">
      <h1 className="text-3xl font-bold mb-4">Terms of Service</h1>
      <p className="mb-4 italic">Last updated: October 18, 2025</p>

      <p className="mb-4">
        Welcome to <strong>MCP-Nexus</strong>. By using our application, you
        agree to the following terms and conditions.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Purpose of the Service</h2>
      <p className="mb-4">
        MCP-Nexus provides intelligent automation and data integration powered
        by AI, enabling users to connect tools such as Google Calendar and other
        productivity platforms.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. User Responsibility</h2>
      <p className="mb-4">
        You agree to use MCP-Nexus responsibly and in compliance with applicable
        laws. You must not misuse the service or access data you are not
        authorized to.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Access to Google Data</h2>
      <p className="mb-4">
        MCP-Nexus uses Google APIs only after you grant permission through
        OAuth. Accessed data is limited to calendar events and related metadata,
        and it is used exclusively for the features described in our Privacy
        Policy.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Data Security and Privacy</h2>
      <p className="mb-4">
        All data is handled in accordance with our{" "}
        <a href="/privacy" className="text-blue-500 hover:underline">
          Privacy Policy
        </a>
        , which outlines how we protect, store, and manage user data.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Limitation of Liability</h2>
      <p className="mb-4">
        MCP-Nexus is provided “as is.” We make no warranties and are not liable
        for damages resulting from the use or inability to use the service.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Modifications to These Terms</h2>
      <p className="mb-4">
        We may update these terms periodically. Continued use of the service
        implies acceptance of any modifications.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Contact</h2>
      <p>
        For any inquiries, contact us at{" "}
        <a
          href="mailto:contact@mcp-nexus.app"
          className="text-blue-500 hover:underline"
        >
          coellog634@gmail.com
        </a>.
      </p>
    </div>
  );
};

export default TermsOfService;
