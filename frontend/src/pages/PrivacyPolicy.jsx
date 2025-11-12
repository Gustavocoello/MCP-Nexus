import React from "react";

const PrivacyPolicy = () => {
  return (
    <div className="max-w-3xl mx-auto p-6 text-gray-800 dark:text-gray-100">
      <h1 className="text-3xl font-bold mb-4">Privacy Policy</h1>
      <p className="mb-4 italic">Last updated: October 18, 2025</p>

      <p className="mb-4">
        At <strong>MCP-Nexus</strong>, we value your privacy. This Privacy Policy
        explains how we collect, use, store, and protect your data when using
        our services.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Data Accessed</h2>
      <p className="mb-4">
        MCP-Nexus accesses Google Calendar data, including event titles,
        descriptions, start and end times, and calendar IDs. This information is
        retrieved only after explicit user consent via the Google OAuth process.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. Data Usage</h2>
      <p className="mb-4">
        The accessed data is used solely to display, create, update, and manage
        calendar events within the MCP-Nexus assistant. We do not use your data
        for advertising or analytics purposes.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Data Sharing</h2>
      <p className="mb-4">
        No Google user data is shared with any third parties. All information
        remains confidential and is used only within the context of your session.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Data Storage & Protection</h2>
      <p className="mb-4">
        User data is transmitted and stored securely using HTTPS and encryption.
        We follow best practices to ensure your data is protected against
        unauthorized access.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Data Retention & Deletion</h2>
      <p className="mb-4">
        Data is retained only as long as necessary for the service to function.
        You may request deletion of your data at any time by contacting us at{" "}
        <a
          href="mailto:contact@mcp-nexus.app"
          className="text-blue-500 hover:underline"
        >
          contact@mcp-nexus.app
        </a>.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Contact</h2>
      <p>
        For questions about this Privacy Policy, please contact us at{" "}
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

export default PrivacyPolicy;
