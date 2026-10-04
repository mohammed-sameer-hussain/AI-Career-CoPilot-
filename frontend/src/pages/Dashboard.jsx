import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Briefcase,
  FileText,
  Bell,
  TrendingUp,
  Target,
  Plus,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function Dashboard() {
  const { user, updateUser } = useAuth();
  const [stats, setStats] = useState({});
  const [recentJobs, setRecentJobs] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const loadData = async () => {
    try {
      const [statsRes, jobsRes, notifRes] = await Promise.all([
        apiService.dashboard.get(),
        apiService.jobs.list({ ordering: '-discovered_at', limit: 5 }),
        apiService.notifications.list({ read: false, limit: 5 }),
      ]);
      setStats(statsRes.data);
      setRecentJobs(jobsRes.data.results || jobsRes.data);
      setNotifications(notifRes.data.results || notifRes.data);
    } catch (e) {
      console.error('Failed to load dashboard:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    if (!user) return;
    setScanning(true);
    try {
      await apiService.jobs.scan(user.id);
      await loadData();
    } catch (e) {
      console.error('Scan failed:', e);
    } finally {
      setScanning(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [user]);

  const statCards = [
    { label: 'Jobs Found', value: stats.jobs || 0, icon: Briefcase, color: 'blue' },
    { label: 'Applications', value: stats.applications || 0, icon: FileText, color: 'green' },
    { label: 'Unread Alerts', value: stats.notifications || 0, icon: Bell, color: 'orange' },
    { label: 'Match Rate', value: stats.match_rate ? `${stats.match_rate}%` : '—', icon: TrendingUp, color: 'purple' },
  ];

  if (loading) {
    return (
      <div className="page-loading">
        <Loader2 size={32} className="spin" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Welcome back, {user?.name?.split(' ')[0] || 'there'}! Here's your career overview.</p>
        </div>
        <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
          <RefreshCw size={18} className={scanning ? 'spin' : ''} />
          {scanning ? 'Scanning...' : 'Scan for Jobs'}
        </button>
      </div>

      <div className="stats-grid">
        {statCards.map((stat) => (
          <div key={stat.label} className={`stat-card ${stat.color}`}>
            <div className="stat-icon">
              <stat.icon size={24} />
            </div>
            <div className="stat-content">
              <span className="stat-label">{stat.label}</span>
              <strong className="stat-value">{stat.value}</strong>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <section className="section-card">
          <div className="section-header">
            <h2>Recent Job Matches</h2>
            <Link to="/jobs" className="view-all">View all</Link>
          </div>
          {recentJobs.length === 0 ? (
            <div className="empty-state">
              <Target size={48} />
              <h3>No jobs yet</h3>
              <p>Click "Scan for Jobs" to discover opportunities matching your profile.</p>
              <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
                <Plus size={18} /> Scan for Jobs
              </button>
            </div>
          ) : (
            <div className="job-list">
              {recentJobs.map((job) => (
                <article key={job.id} className="job-item">
                  <div className="job-info">
                    <span className="job-source">{job.source}</span>
                    <h4>{job.title}</h4>
                    <p className="job-meta">{job.company} · {job.location || 'Location not specified'}</p>
                  </div>
                  <div className="job-skills">
                    {(job.required_skills || []).slice(0, 4).map((skill) => (
                      <span key={skill} className="skill-tag">{skill}</span>
                    ))}
                  </div>
                  <Link to={`/jobs/${job.id}`} className="btn btn-secondary btn-sm">View</Link>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="section-card">
          <div className="section-header">
            <h2>Notifications</h2>
            <Link to="/notifications" className="view-all">View all</Link>
          </div>
          {notifications.length === 0 ? (
            <div className="empty-state small">
              <Bell size={32} />
              <p>No new notifications</p>
            </div>
          ) : (
            <ul className="notification-list">
              {notifications.map((notif) => (
                <li key={notif.id} className="notification-item">
                  <div className="notif-icon"><Bell size={18} /></div>
                  <div className="notif-content">
                    <strong>{notif.title}</strong>
                    <p>{notif.message}</p>
                    <span className="notif-time">{formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="section-card quick-actions">
        <h2>Quick Actions</h2>
        <div className="action-grid">
          <Link to="/jobs" className="action-card">
            <Briefcase size={28} />
            <span>Browse Jobs</span>
          </Link>
          <Link to="/profile" className="action-card">
            <Target size={28} />
            <span>Update Profile</span>
          </Link>
          <Link to="/applications" className="action-card">
            <FileText size={28} />
            <span>Track Applications</span>
          </Link>
        </div>
      </section>
    </div>
  );
}