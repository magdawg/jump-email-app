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
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Enable cookies to be sent with every request
axios.defaults.withCredentials = true;

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user just logged in (user_id in URL from OAuth redirect)
    const params = new URLSearchParams(window.location.search);
    const userIdParam = params.get('user_id');
    
    if (userIdParam) {
      // Store user ID and clean up URL
      localStorage.setItem('user_id', userIdParam);
      window.history.replaceState({}, document.title, "/");
      setUserId(userIdParam);
      checkAuth(userIdParam);
    } else {
      // Check if already authenticated
      const storedUserId = localStorage.getItem('user_id');
      if (storedUserId) {
        setUserId(storedUserId);
        checkAuth(storedUserId);
      } else {
        setLoading(false);
      }
    }
  }, []);

  const checkAuth = async (userIdToCheck) => {
    try {
      // Check if session is valid
      const response = await axios.get(`${API_URL}/auth/check`);
      setUser(response.data.user);
      
      // Fetch user data
      await Promise.all([
        fetchCategories(userIdToCheck),
        fetchGmailAccounts(userIdToCheck)
      ]);
      
      setLoading(false);
    } catch (error) {
      console.error('Not authenticated:', error);
      // Clear stored user ID if not authenticated
      localStorage.removeItem('user_id');
      setUserId(null);
      setUser(null);
      setLoading(false);
    }
  };

  const fetchCategories = async (userIdToUse = userId) => {
    try {
      const response = await axios.get(`${API_URL}/api/user/${userIdToUse}/categories`);
      setCategories(response.data || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories([]);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const fetchGmailAccounts = async (userIdToUse = userId) => {
    try {
      const response = await axios.get(`${API_URL}/api/user/${userIdToUse}/gmail-accounts`);
      setGmailAccounts(response.data || []);
    } catch (error) {
      console.error('Error fetching Gmail accounts:', error);
      setGmailAccounts([]);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleAuthError = () => {
    localStorage.removeItem('user_id');
    setUserId(null);
    setUser(null);
    alert('Your session has expired. Please log in again.');
  };

  const handleLogin = async () => {
    console.log('🔍 Attempting login...');
    console.log('🔍 API_URL:', API_URL);
    
    try {
      console.log('🔍 Fetching auth URL...');
      const response = await axios.get(`${API_URL}/auth/login`);
      console.log('🔍 Auth URL:', response.data.auth_url);
      
      console.log('🔍 Redirecting to Google...');
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('❌ Error logging in:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API_URL}/auth/logout`);
      localStorage.removeItem('user_id');
      setUserId(null);
      setUser(null);
      setCategories([]);
      setGmailAccounts([]);
      setSelectedCategory(null);
      setSelectedEmail(null);
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/user/${userId}/categories`, newCategory);
      await fetchCategories();
      setNewCategory({ name: '', description: '' });
      setShowAddCategory(false);
    } catch (error) {
      console.error('Error adding category:', error);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleSelectCategory = async (category) => {
    setSelectedCategory(category);
    setSelectedEmail(null);
    setSelectedEmailIds([]);
    try {
      const response = await axios.get(`${API_URL}/api/category/${category.id}/emails`);
      setCategoryEmails(response.data || []);
    } catch (error) {
      console.error('Error fetching emails:', error);
      setCategoryEmails([]);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleSelectEmail = async (email) => {
    try {
      const response = await axios.get(`${API_URL}/api/email/${email.id}`);
      setSelectedEmail(response.data);
    } catch (error) {
      console.error('Error fetching email details:', error);
      if (error.response?.status === 401) {
        handleAuthError();
      }
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
    
    const confirmed = window.confirm(
      `Are you sure you want to delete ${selectedEmailIds.length} email(s)?`
    );
    if (!confirmed) return;

    try {
      await axios.post(`${API_URL}/api/emails/delete`, selectedEmailIds);
      setCategoryEmails(prev => prev.filter(e => !selectedEmailIds.includes(e.id)));
      setSelectedEmailIds([]);
      await fetchCategories();
    } catch (error) {
      console.error('Error deleting emails:', error);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleUnsubscribeSelected = async () => {
    if (selectedEmailIds.length === 0) return;

    const confirmed = window.confirm(
      'This will attempt to unsubscribe from the selected emails. Continue?'
    );
    if (!confirmed) return;

    try {
      const response = await axios.post(`${API_URL}/api/emails/unsubscribe`, selectedEmailIds);

      const results = response.data.results || [];
      const successCount = results.filter(r => r.success === true).length;
      const failureCount = results.filter(r => r.success === false).length;

      if (successCount === selectedEmailIds.length) {
        alert('All selected emails were successfully unsubscribed.');
      } else if (successCount > 0) {
        alert(`Partial success: ${successCount} unsubscribed, ${failureCount} failed. Check console for details.`);
      } else {
        alert('Failed to unsubscribe any emails. Check console for details.');
      }

      console.log('Unsubscribe results:', response.data);
    } catch (error) {
      console.error('Error unsubscribing:', error);
      alert('An error occurred while attempting to unsubscribe.');
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleProcessEmails = async () => {
    try {
      await axios.post(`${API_URL}/api/process-emails`);
      alert('Email processing started. This may take a few minutes.');
      setTimeout(() => {
        fetchCategories();
        if (selectedCategory) {
          handleSelectCategory(selectedCategory);
        }
      }, 5000);
    } catch (error) {
      console.error('Error processing emails:', error);
      if (error.response?.status === 401) {
        handleAuthError();
      }
    }
  };

  const handleConnectAnotherAccount = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/login?user_id=${userId}`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Error connecting account:', error);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="App">
        <div className="login-container">
          <h1>AI Smart Email Sorter</h1>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  // Login screen
  if (!userId || !user) {
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

  // Email detail view
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

  // Category view
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

  // Dashboard view
  return (
    <div className="App">
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>AI Smart Email Sorter</h1>
          <div className="user-info">
            <span>Welcome, {user?.name || user?.email}</span>
            <button onClick={handleLogout} className="btn-secondary" style={{ marginLeft: '10px' }}>
              Logout
            </button>
          </div>
        </header>

        <div className="dashboard-content">
          <section className="section">
            <h2>Gmail Accounts</h2>
            <div className="gmail-accounts">
              {gmailAccounts.length === 0 ? (
                <p className="empty-state">No Gmail accounts connected yet.</p>
              ) : (
                gmailAccounts.map(account => (
                  <div key={account.id} className="gmail-account">
                    <span>{account.email}</span>
                    {account.is_primary && <span className="badge">Primary</span>}
                  </div>
                ))
              )}
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
              Emails are automatically processed every 5 minutes (max 10 emails at once).
              <br />
              Click the button to process immediately.
              <br />
              Refresh the page if categories don't update automatically.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
