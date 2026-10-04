import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Loader2,
  FileText,
  Clock,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  XCircle,
  HelpCircle,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const STATUS_CONFIG = {
  saved: { label: 'Saved', icon: FileText, color: 'gray' },
  interested: { label: 'Interested', icon: ArrowRight, color: 'blue' },
  applied: { label: 'Applied', icon: CheckCircle, color: 'green' },
  assessment: { label: 'Assessment', icon: AlertCircle, color: 'orange' },
  interview: { label: 'Interview', icon: HelpCircle, color: 'purple' },
  offer: { label: 'Offer', icon: CheckCircle, color: 'emerald' },
  rejected: { label: 'Rejected', icon: XCircle, color: 'red' },
  withdrawn: { label: 'Withdrawn', icon: XCircle, color: 'gray' },
};

const STATUS_ORDER = ['saved', 'interested', 'applied', 'assessment', 'interview', 'offer', 'rejected', 'withdrawn'];

export function ApplicationsPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [updating, setUpdating] = useState({});

  const loadApplications = async () => {
    setLoading(true);
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await apiService.applications.list(params);
      const data = response.data.results || response.data;
      setApplications(data);
    } catch (e) {
      console.error('Failed to load applications:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, [statusFilter]);

  const updateStatus = async (appId, newStatus) => {
    setUpdating(prev => ({ ...prev, [appId]: true }));
    try {
      await apiService.applications.update(appId, { status: newStatus });
      setApplications(prev => prev.map(app => app.id === appId ? { ...app, status: newStatus } : app));
    } catch (e) {
      console.error('Failed to update status:', e);
    } finally {
      setUpdating(prev => ({ ...prev, [appId]: false }));
    }
  };

  const statusCounts = applications.reduce((acc, app) => {
    acc[app.status] = (acc[app.status] || 0) + 1;
    return acc;
  }, {});

  if (loading) {
    return <div className="page-loading"><Loader2 size={32} className="spin" /></div>;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Applications</h1>
          <p>Track and manage your job applications</p>
        </div>
      </div>

      <div className="status-filters">
        <button
          className={`status-filter ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          All <span className="count">{applications.length}</span>
        </button>
        {STATUS_ORDER.map((status) => {
          const config = STATUS_CONFIG[status];
          const count = statusCounts[status] || 0;
          if (count === 0) return null;
          return (
            <button
              key={status}
              className={`status-filter ${statusFilter === status ? 'active' : ''} ${config.color}`}
              onClick={() => setStatusFilter(status)}
            >
              <config.icon size={16} /> {config.label} <span className="count">{count}</span>
            </button>
          );
        })}
      </div>

      {applications.length === 0 ? (
        <div className="empty-state">
          <FileText size={64} />
          <h3>No applications yet</h3>
          <p>Start by browsing jobs and analyzing matches</p>
          <Link to="/jobs" className="btn btn-primary">Browse Jobs</Link>
        </div>
      ) : (
        <div className="applications-list">
          {applications.map((app) => (
            <article key={app.id} className="application-card">
              <div className="app-header">
                <div className="app-info">
                  <Link to={`/jobs/${app.job.id}`} className="app-title">{app.job.title}</Link>
                  <p className="app-company">{app.job.company} · {app.job.location || 'Location not specified'}</p>
                </div>
                <div className="app-status">
                  <select
                    value={app.status}
                    onChange={(e) => updateStatus(app.id, e.target.value)}
                    disabled={updating[app.id]}
                    className={`status-select ${app.status}`}
                  >
                    {STATUS_ORDER.map((s) => (
                      <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="app-meta">
                <span><Clock size={14} /> Updated {formatDistanceToNow(new Date(app.updated_at), { addSuffix: true })}</span>
                {app.applied_at && <span><CheckCircle size={14} /> Applied {formatDistanceToNow(new Date(app.applied_at), { addSuffix: true })}</span>}
              </div>

              {app.resume_suggestions && app.resume_suggestions.length > 0 && (
                <div className="app-suggestions">
                  <strong>Resume Tips:</strong>
                  <ul>
                    {app.resume_suggestions.slice(0, 2).map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="app-actions">
                <Link to={`/jobs/${app.job.id}`} className="btn btn-secondary btn-sm">View Details</Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}