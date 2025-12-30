import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase (uses your .env variables)
const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);

// Organization types
const ORG_TYPES = [
  { value: '501c3', label: '501(c)(3) Nonprofit' },
  { value: '501c4', label: '501(c)(4) Social Welfare' },
  { value: 'llc', label: 'LLC (Limited Liability Company)' },
  { value: 'for-profit', label: 'For-Profit Corporation' },
  { value: 'government', label: 'Government Agency' },
  { value: 'unincorporated', label: 'Informal/Unincorporated Group' },
  { value: 'other', label: 'Other' }
];

const SubmissionForm = () => {
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    mission_statement_text: '',
    focus: [],
    org_type: '',
    submitted_by_name: '',
    submitted_by_email: ''
  });

  const [focusAreas, setFocusAreas] = useState([]);
  const [loadingFocusAreas, setLoadingFocusAreas] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  // Load focus areas from Supabase on component mount
  useEffect(() => {
    loadFocusAreas();
  }, []);

  const loadFocusAreas = async () => {
    try {
      setLoadingFocusAreas(true);
      
      // Get all organizations with focus areas
      const { data, error } = await supabase
        .from('organizations')
        .select('focus')
        .not('focus', 'is', null)
        .eq('status', 'approved');

      if (error) throw error;

      // Extract unique focus areas
      const focusSet = new Set();
      data.forEach(org => {
        if (org.focus && Array.isArray(org.focus)) {
          org.focus.forEach(area => focusSet.add(area));
        }
      });

      // Convert to sorted array
      const uniqueFocusAreas = Array.from(focusSet).sort();
      setFocusAreas(uniqueFocusAreas);
      
    } catch (err) {
      console.error('Error loading focus areas:', err);
      // Fallback to a basic set if loading fails
      setFocusAreas([
        'Air Quality',
        'Climate',
        'Energy',
        'Environmental Justice',
        'Water Quality',
        'Wildlife & Habitat'
      ]);
    } finally {
      setLoadingFocusAreas(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFocusChange = (focusArea) => {
    setFormData(prev => {
      const currentFocus = prev.focus || [];
      const newFocus = currentFocus.includes(focusArea)
        ? currentFocus.filter(f => f !== focusArea)
        : [...currentFocus, focusArea];
      
      return { ...prev, focus: newFocus };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      // Validate required fields
      if (!formData.name || !formData.city) {
        throw new Error('Organization name and city are required');
      }

      if (!formData.submitted_by_email) {
        throw new Error('Your email is required');
      }

      // Generate slug from organization name
      const slug = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');

      // Submit to Supabase with status='pending'
      const { data, error: submitError } = await supabase
        .from('organizations')
        .insert([{
          ...formData,
          slug: slug,
          status: 'pending',
          created_at: new Date().toISOString()
        }]);

      if (submitError) throw submitError;

      // Success!
      setSubmitted(true);
      
      // Reset form
      setFormData({
        name: '',
        url: '',
        email: '',
        phone: '',
        address: '',
        city: '',
        mission_statement_text: '',
        focus: [],
        org_type: '',
        submitted_by_name: '',
        submitted_by_email: ''
      });

    } catch (err) {
      console.error('Submission error:', err);
      setError(err.message || 'Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Success message
  if (submitted) {
    return (
      <div className="submission-success">
        <div className="success-icon">✅</div>
        <h2>Thank You for Your Submission!</h2>
        <p>
          We've received your organization submission and will review it soon. 
          If approved, it will appear in the directory within a few days.
        </p>
        <button 
          onClick={() => setSubmitted(false)}
          className="btn-secondary"
        >
          Submit Another Organization
        </button>
        
        <style jsx>{`
          .submission-success {
            max-width: 600px;
            margin: 0 auto;
            padding: 60px 20px;
            text-align: center;
          }
          
          .success-icon {
            font-size: 72px;
            margin-bottom: 20px;
          }
          
          .submission-success h2 {
            color: #10b981;
            margin-bottom: 15px;
            font-size: 28px;
          }
          
          .submission-success p {
            color: #64748b;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 30px;
          }
          
          .btn-secondary {
            background: #f1f5f9;
            color: #1e293b;
            border: 2px solid #e2e8f0;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
          }
          
          .btn-secondary:hover {
            background: #e2e8f0;
            border-color: #cbd5e1;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="submission-form-container">
      {/* Back to Directory Link */}
      <Link to="/" className="back-link">
        ← Back to Directory
      </Link>
      
      <div className="form-header">
        <h1>Submit an Organization</h1>
        <p>
          Know an environmental organization in Michigan that's missing from our directory? 
          Submit it here and we'll review it for inclusion.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="submission-form">
        
        {/* Organization Information */}
        <div className="form-section">
          <h3>Organization Information</h3>
          
          <div className="form-group">
            <label htmlFor="name">
              Organization Name <span className="required">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="e.g., Detroit River Project"
            />
          </div>

          <div className="form-group">
            <label htmlFor="city">
              City <span className="required">*</span>
            </label>
            <input
              type="text"
              id="city"
              name="city"
              value={formData.city}
              onChange={handleChange}
              required
              placeholder="e.g., Detroit"
            />
          </div>

          <div className="form-group">
            <label htmlFor="org_type">Organization Type (Optional)</label>
            <select
              id="org_type"
              name="org_type"
              value={formData.org_type}
              onChange={handleChange}
            >
              <option value="">Select type...</option>
              {ORG_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="address">Address (Optional)</label>
            <input
              type="text"
              id="address"
              name="address"
              value={formData.address}
              onChange={handleChange}
              placeholder="Street address"
            />
          </div>

          <div className="form-group">
            <label htmlFor="url">Website (Optional)</label>
            <input
              type="url"
              id="url"
              name="url"
              value={formData.url}
              onChange={handleChange}
              placeholder="https://example.org"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="email">Organization Email (Optional)</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="contact@example.org"
              />
            </div>

            <div className="form-group">
              <label htmlFor="phone">Phone (Optional)</label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="(313) 555-1234"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="mission_statement_text">
              Mission or Description (Optional)
            </label>
            <textarea
              id="mission_statement_text"
              name="mission_statement_text"
              value={formData.mission_statement_text}
              onChange={handleChange}
              rows={4}
              placeholder="Brief description of what the organization does..."
            />
          </div>

          <div className="form-group">
            <label>Focus Areas (Optional)</label>
            <p className="field-help">
              {loadingFocusAreas 
                ? 'Loading focus areas from directory...' 
                : `Select all that apply (${focusAreas.length} areas available)`
              }
            </p>
            {loadingFocusAreas ? (
              <div className="loading-state">Loading...</div>
            ) : (
              <div className="checkbox-grid">
                {focusAreas.map(area => (
                  <label key={area} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.focus.includes(area)}
                      onChange={() => handleFocusChange(area)}
                    />
                    <span>{area}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Submitter Information */}
        <div className="form-section">
          <h3>Your Information</h3>
          <p className="section-description">
            We'll use this to follow up if we have questions about the organization.
          </p>

          <div className="form-group">
            <label htmlFor="submitted_by_name">Your Name (Optional)</label>
            <input
              type="text"
              id="submitted_by_name"
              name="submitted_by_name"
              value={formData.submitted_by_name}
              onChange={handleChange}
              placeholder="Your name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="submitted_by_email">
              Your Email <span className="required">*</span>
            </label>
            <input
              type="email"
              id="submitted_by_email"
              name="submitted_by_email"
              value={formData.submitted_by_email}
              onChange={handleChange}
              required
              placeholder="your@email.com"
            />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {/* Submit Button */}
        <button 
          type="submit" 
          className="submit-btn"
          disabled={submitting}
        >
          {submitting ? 'Submitting...' : 'Submit Organization'}
        </button>

        <p className="privacy-note">
          By submitting, you confirm this information is accurate. 
          We'll review your submission and add it to the directory if appropriate.
        </p>
      </form>

      <style jsx>{`
        .submission-form-container {
          max-width: 800px;
          margin: 0 auto;
          padding: 40px 20px;
        }

        .back-link {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          color: #64748b;
          text-decoration: none;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 20px;
          padding: 8px 12px;
          border-radius: 6px;
          transition: all 0.2s;
        }

        .back-link:hover {
          color: #1e293b;
          background: #f1f5f9;
        }

        .form-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .form-header h1 {
          color: #1e293b;
          font-size: 32px;
          margin-bottom: 12px;
        }

        .form-header p {
          color: #64748b;
          font-size: 16px;
          line-height: 1.6;
          max-width: 600px;
          margin: 0 auto;
        }

        .submission-form {
          background: white;
          border-radius: 12px;
          padding: 40px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .form-section {
          margin-bottom: 40px;
          padding-bottom: 40px;
          border-bottom: 1px solid #e5e7eb;
        }

        .form-section:last-of-type {
          border-bottom: none;
        }

        .form-section h3 {
          color: #1e293b;
          font-size: 20px;
          margin-bottom: 8px;
        }

        .section-description {
          color: #64748b;
          font-size: 14px;
          margin-bottom: 20px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        label {
          display: block;
          color: #1e293b;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 6px;
        }

        .required {
          color: #ef4444;
        }

        .field-help {
          color: #64748b;
          font-size: 13px;
          margin: 4px 0 12px 0;
        }

        .loading-state {
          padding: 20px;
          text-align: center;
          color: #64748b;
          font-style: italic;
        }

        input[type="text"],
        input[type="email"],
        input[type="tel"],
        input[type="url"],
        select,
        textarea {
          width: 100%;
          padding: 10px 14px;
          border: 2px solid #e2e8f0;
          border-radius: 6px;
          font-size: 15px;
          font-family: inherit;
          transition: border-color 0.2s;
        }

        select {
          cursor: pointer;
          background: white;
        }

        input:focus,
        select:focus,
        textarea:focus {
          outline: none;
          border-color: #3b82f6;
        }

        textarea {
          resize: vertical;
          min-height: 100px;
        }

        .checkbox-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 12px;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          padding: 8px;
          border-radius: 4px;
          transition: background 0.2s;
        }

        .checkbox-label:hover {
          background: #f9fafb;
        }

        .checkbox-label input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
        }

        .checkbox-label span {
          font-size: 14px;
          color: #1e293b;
        }

        .error-message {
          background: #fee2e2;
          border: 1px solid #fecaca;
          color: #991b1b;
          padding: 12px 16px;
          border-radius: 6px;
          margin-bottom: 20px;
          font-size: 14px;
        }

        .submit-btn {
          width: 100%;
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          border: none;
          padding: 14px 24px;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .submit-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .privacy-note {
          text-align: center;
          color: #64748b;
          font-size: 13px;
          margin-top: 16px;
          line-height: 1.5;
        }

        @media (max-width: 768px) {
          .submission-form {
            padding: 30px 20px;
          }

          .form-row {
            grid-template-columns: 1fr;
          }

          .checkbox-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default SubmissionForm;
