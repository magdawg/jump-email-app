// # /*
// #  * -----------------------------------------------------------------------------
// #  *  Copyright (c) 2025 Magda Kowalska. All rights reserved.
// #  *
// #  *  This software and its source code are the intellectual property of
// #  *  Magda Kowalska. Unauthorized copying, reproduction, or use of this
// #  *  software, in whole or in part, is strictly prohibited without express
// #  *  written permission.
// #  *
// #  *  This software is protected under the Berne Convention for the Protection
// #  *  of Literary and Artistic Works, EU copyright law, and international
// #  *  copyright treaties.
// #  *
// #  *  Author: Magda Kowalska
// #  *  Created: 2025-11-02
// #  *  Last Modified: 2025-11-02
// #  * -----------------------------------------------------------------------------
// #  */

import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [categories, setCategories] = useState([]);
  const [gmailAccounts, setGmailAccounts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [categoryEmails, setCategoryEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [selectedEmailIds, setSelectedEmailIds] = useState([]);
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [newCategory, setNewCategory] = useState({ name: '', description: '' });

  useEffect(() => {
    // Check if user_id in URL
    const params = new URLSearchParams(window.location.search);
    const userIdParam = params.get('user_id');
    if (userIdParam) {
      setUserId(userIdParam);
      localStorage.setItem('user_id', userIdParam);
      window.history.replaceState({}, document.title, "/");
    } else {
      const storedUserId = localStorage.getItem('user_id');
      if (storedUserId) {
        setUserId(storedUserId);
      }
    }
  }, []);

  useEffect(() => {
    if (userId) {
      fetchUser();
      fetchCategories();
      fetchGmailAccounts();
    }
  }, [userId]);

  const fetchUser = async () => {
    try {
      const response = await fetch(`${API_URL}/api/user/${userId}`);
      const data = await response.json();
      setUser(data);
    } catch (error) {
      console.error('Error fetching user:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/user/${userId}/categories`);
      const data = await response.json();
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchGmailAccounts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/user/${userId}/gmail-accounts`);
      const data = await response.json();
      setGmailAccounts(data);
    } catch (error) {
      console.error('Error fetching Gmail accounts:', error);
    }
  };

  const handleLogin = async () => {
    console.log('🔍 Attempting login...');
    console.log('🔍 API_URL:', API_URL);
    
    try {
      console.log('🔍 Fetching auth URL...');
      const response = await fetch(`${API_URL}/auth/login`);
      console.log('🔍 Response:', response);
      
      const data = await response.json();
      console.log('🔍 Data received:', data);
      console.log('🔍 Auth URL:', data.auth_url);
      
      console.log('🔍 Redirecting to Google...');
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('❌ Error logging in:', error);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_URL}/api/user/${userId}/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCategory)
      });
      await fetchCategories();
      setNewCategory({ name: '', description: '' });
      setShowAddCategory(false);
    } catch (error) {
      console.error('Error adding category:', error);
    }
  };

  const handleSelectCategory = async (category) => {
    setSelectedCategory(category);
    setSelectedEmail(null);
    setSelectedEmailIds([]);
    try {
      const response = await fetch(`${API_URL}/api/category/${category.id}/emails`);
      const data = await response.json();
      setCategoryEmails(data);
    } catch (error) {
      console.error('Error fetching emails:', error);
    }
  };

  const handleSelectEmail = async (email) => {
    try {
      const response = await fetch(`${API_URL}/api/email/${email.id}`);
      const data = await response.json();
      setSelectedEmail(data);
    } catch (error) {
      console.error('Error fetching email details:', error);
    }
  };

  const handleToggleEmailSelection = (emailId) => {
    setSelectedEmailIds(prev =>
      prev.includes(emailId)
        ? prev.filter(id => id !== emailId)
        : [...prev, emailId]
    );
  };

  const handleSelectAll = () => {
    if (selectedEmailIds.length === categoryEmails.length) {
      setSelectedEmailIds([]);
    } else {
      setSelectedEmailIds(categoryEmails.map(e => e.id));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedEmailIds.length === 0) return;
    try {
      await fetch(`${API_URL}/api/emails/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedEmailIds)
      });
      setCategoryEmails(prev => prev.filter(e => !selectedEmailIds.includes(e.id)));
      setSelectedEmailIds([]);
      await fetchCategories();
    } catch (error) {
      console.error('Error deleting emails:', error);
    }
  };

  const handleUnsubscribeSelected = async () => {
    if (selectedEmailIds.length === 0) return;

    const confirmed = window.confirm(
      'This will attempt to unsubscribe from the selected emails. Continue?'
    );
    if (!confirmed) return;

    try {
      const response = await fetch(`${API_URL}/api/emails/unsubscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedEmailIds),
      });

      const data = await response.json();

      // Count successes and failures
      const results = data.results || [];
      const successCount = results.filter(r => r.success === true).length;
      const failureCount = results.filter(r => r.success === false).length;

      // Determine overall outcome
      if (successCount === selectedEmailIds.length) {
        alert('All selected emails were successfully unsubscribed.');
      } else if (successCount > 0) {
        alert(`Partial success: ${successCount} unsubscribed, ${failureCount} failed. Check console for details.`);
      } else {
        alert('Failed to unsubscribe any emails. Check console for details.');
      }

      console.log('Unsubscribe results:', data);
    } catch (error) {
      console.error('Error unsubscribing:', error);
      alert('An error occurred while attempting to unsubscribe.');
    }
  };
  

  const handleProcessEmails = async () => {
    try {
      await fetch(`${API_URL}/api/process-emails`, { method: 'POST' });
      alert('Email processing started. This may take a few minutes.');
      setTimeout(() => {
        fetchCategories();
        if (selectedCategory) {
          handleSelectCategory(selectedCategory);
        }
      }, 5000);
    } catch (error) {
      console.error('Error processing emails:', error);
    }
  };

  const handleConnectAnotherAccount = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/login?user_id=${userId}`);
      const data = await response.json();
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Error logging in:', error);
    }
  };

  if (!userId) {
    return (
      <div className="App">
        <div className="login-container">
          <h1>AI Smart Email Sorter</h1>
          <p>Automatically categorize and summarize your emails with AI</p>
          <button onClick={handleLogin} className="btn-primary">
            Sign in with Google
          </button>
        </div>
      </div>
    );
  }

  if (selectedEmail) {
    return (
      <div className="App">
        <div className="email-detail">
          <button onClick={() => setSelectedEmail(null)} className="btn-back">
            ← Back to {selectedCategory.name}
          </button>
          <div className="email-header">
            <h2>{selectedEmail.subject}</h2>
            <p className="email-sender">From: {selectedEmail.sender}</p>
            <p className="email-date">
              {new Date(selectedEmail.received_at).toLocaleString()}
            </p>
          </div>
          <div className="email-summary">
            <h3>AI Summary</h3>
            <p>{selectedEmail.summary}</p>
          </div>
          <div className="email-body">
            <h3>Original Email</h3>
            <pre>{selectedEmail.body}</pre>
          </div>
        </div>
      </div>
    );
  }

  if (selectedCategory) {
    return (
      <div className="App">
        <div className="category-view">
          <div className="category-header">
            <button onClick={() => setSelectedCategory(null)} className="btn-back">
              ← Back to Dashboard
            </button>
            <h2>{selectedCategory.name}</h2>
            <p>{selectedCategory.description}</p>
          </div>
          
          {categoryEmails.length > 0 && (
            <div className="bulk-actions">
              <label>
                <input
                  type="checkbox"
                  checked={selectedEmailIds.length === categoryEmails.length}
                  onChange={handleSelectAll}
                />
                Select All ({categoryEmails.length})
              </label>
              <button
                onClick={handleDeleteSelected}
                disabled={selectedEmailIds.length === 0}
                className="btn-danger"
              >
                Delete Selected ({selectedEmailIds.length})
              </button>
              <button
                onClick={handleUnsubscribeSelected}
                disabled={selectedEmailIds.length === 0}
                className="btn-secondary"
              >
                Unsubscribe Selected ({selectedEmailIds.length})
              </button>
            </div>
          )}

          <div className="email-list">
            {categoryEmails.length === 0 ? (
              <p className="empty-state">No emails in this category yet.</p>
            ) : (
              categoryEmails.map(email => (
                <div key={email.id} className="email-item">
                  <input
                    type="checkbox"
                    checked={selectedEmailIds.includes(email.id)}
                    onChange={() => handleToggleEmailSelection(email.id)}
                  />
                  <div
                    className="email-content"
                    onClick={() => handleSelectEmail(email)}
                  >
                    <h4>{email.subject}</h4>
                    <p className="email-sender">{email.sender}</p>
                    <p className="email-summary">{email.summary}</p>
                    <p className="email-date">
                      {new Date(email.received_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>AI Smart Email Sorter</h1>
          <div className="user-info">
            <span>Welcome, {user?.name || user?.email}</span>
          </div>
        </header>

        <div className="dashboard-content">
          <section className="section">
            <h2>Gmail Accounts</h2>
            <div className="gmail-accounts">
              {gmailAccounts.map(account => (
                <div key={account.id} className="gmail-account">
                  <span>{account.email}</span>
                  {account.is_primary && <span className="badge">Primary</span>}
                </div>
              ))}
              <button onClick={handleConnectAnotherAccount} className="btn-secondary">
                + Connect Another Account
              </button>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <h2>Categories</h2>
              <button onClick={() => setShowAddCategory(true)} className="btn-primary">
                + Add Category
              </button>
            </div>

            {showAddCategory && (
              <form onSubmit={handleAddCategory} className="add-category-form">
                <input
                  type="text"
                  placeholder="Category Name"
                  value={newCategory.name}
                  onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
                  required
                />
                <textarea
                  placeholder="Category Description (e.g., 'Promotional emails from retailers')"
                  value={newCategory.description}
                  onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
                  required
                />
                <div className="form-actions">
                  <button type="submit" className="btn-primary">Save</button>
                  <button
                    type="button"
                    onClick={() => setShowAddCategory(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            <div className="category-list">
              {categories.length === 0 ? (
                <p className="empty-state">
                  No categories yet. Add your first category to start organizing emails!
                </p>
              ) : (
                categories.map(category => (
                  <div
                    key={category.id}
                    className={`category-card ${category.name.toLowerCase() === 'uncategorized' ? 'uncategorized' : ''}`}
                    onClick={() => handleSelectCategory(category)}
                  >
                    <h3>{category.name}</h3>
                    <p>{category.description}</p>
                    <span className="email-count">{category.email_count} emails</span>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <h2>Email Processing</h2>
              <button onClick={handleProcessEmails} className="btn-primary">
                Process New Emails
              </button>
            </div>
            <p className="help-text">
              Emails are automatically processed every 5 minutes. Click the button to process immediately.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
