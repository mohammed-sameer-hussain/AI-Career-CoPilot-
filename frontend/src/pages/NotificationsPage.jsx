import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Bell, CheckCheck, Loader2, Briefcase } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function NotificationsPage() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(false);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const response = await apiService.notifications.list();
      setNotifications(response.data.results || response.data);
    } catch (e) {
      console.error('Failed to load notifications:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, [user]);

  const markRead = async (id) => {
    try {
      await apiService.notifications.markRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (e) {
      console.error('Failed to mark notification read:', e);
    }
  };

  const markAllRead = async () => {
    setMarking(true);
    try {
      await apiService.notifications.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (e) {
      console.error('Failed to mark all read:', e);
    } finally {
      setMarking(false);
    }
  };

  if (loading) {
    return <div className="page-loading"><Loader2 size={32} className="spin" /></div>;
  }

  const unread = notifications.filter(n => !n.read).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Notifications</h1>
          <p>{unread > 0 ? `${unread} unread update${unread > 1 ? 's' : ''}` : 'You are all caught up'}</p>
        </div>
        {unread > 0 && (
          <button className="btn btn-secondary" onClick={markAllRead} disabled={marking}>
            {marking ? <Loader2 size={18} className="spin" /> : <CheckCheck size={18} />} Mark all read
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="empty-state">
          <Bell size={64} />
          <h3>No notifications yet</h3>
          <p>Run a job scan to get alerted about strong matches.</p>
          <Link to="/jobs" className="btn btn-primary">Browse Jobs</Link>
        </div>
      ) : (
        <ul className="notification-list">
          {notifications.map((notif) => (
            <li key={notif.id} className={`notification-item ${notif.read ? 'read' : 'unread'}`}>
              <div className="notif-icon"><Briefcase size={18} /></div>
              <div className="notif-content">
                <strong>{notif.title}</strong>
                <p>{notif.message}</p>
                <span className="notif-time">{formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })}</span>
              </div>
              {!notif.read && (
                <button className="btn btn-ghost btn-sm" onClick={() => markRead(notif.id)}>Mark read</button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
