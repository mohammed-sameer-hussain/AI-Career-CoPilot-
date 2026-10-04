import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Loader2,
  Briefcase,
  MapPin,
  Clock,
  Tag,
  Target,
  Brain,
  FileText,
  HelpCircle,
  CheckCircle,
  XCircle,
  ArrowLeft,
  Download,
  Copy,
  AlertTriangle,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function JobDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [job, setJob] = useState(null);
  const [match, setMatch] = useState(null);
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const response = await apiService.jobs.get(id);
        setJob(response.data);
      } catch (e) {
        setError('Failed to load job');
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [id]);

  const handleMatch = async () => {
    if (!user) return;
    setMatching(true);
    setError('');
    try {
      const response = await apiService.jobs.match(id, user.id);
      setMatch(response.data);
      setActiveTab('analysis');
    } catch (e) {
      setError(e.response?.data?.detail || 'Matching failed');
    } finally {
      setMatching(false);
    }
  };

  const handleGenerateApplication = async () => {
    if (!user || !match) return;
    setGenerating(true);
    try {
      const response = await apiService.jobs.application(id, user.id);
      setApplication(response.data);
      setActiveTab('application');
    } catch (e) {
      setError(e.response?.data?.detail || 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="page-loading"><Loader2 size={32} className="spin" /></div>;
  }

  if (error && !job) {
    return (
      <div className="page">
        <div className="error-state">
          <AlertTriangle size={64} />
          <h2>Job not found</h2>
          <Link to="/jobs" className="btn btn-primary"><ArrowLeft size={18} /> Back to Jobs</Link>
        </div>
      </div>
    );
  }

  if (!job) return null;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Briefcase },
    { id: 'analysis', label: 'AI Analysis', icon: Brain, disabled: !match },
    { id: 'application', label: 'Application', icon: FileText, disabled: !application },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <Link to="/jobs" className="btn btn-ghost">
          <ArrowLeft size={18} /> Back
        </Link>
        <div className="header-actions">
          {!match && user && (
            <button className="btn btn-primary" onClick={handleMatch} disabled={matching}>
              <Target size={18} className={matching ? 'spin' : ''} />
              {matching ? 'Analyzing...' : 'Analyze Match'}
            </button>
          )}
          {match && !application && user && (
            <button className="btn btn-primary" onClick={handleGenerateApplication} disabled={generating}>
              <FileText size={18} className={generating ? 'spin' : ''} />
              {generating ? 'Generating...' : 'Generate Application'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="job-detail-layout">
        <div className="job-main">
          <article className="job-header-card">
            <div className="job-header-top">
              <div className="job-card-badges">
                <span className="job-source">{job.source}</span>
                {job.is_mnc && <span className="mnc-badge">MNC</span>}
              </div>
              <span className="job-date">Posted {job.posted_at ? formatDistanceToNow(new Date(job.posted_at), { addSuffix: true }) : 'Recently'}</span>
            </div>
            <h1>{job.title}</h1>
            <div className="job-meta-row">
              <span className="meta-item"><Briefcase size={16} /> {job.company}</span>
              {job.location && <span className="meta-item"><MapPin size={16} /> {job.location}</span>}
              {job.experience && <span className="meta-item"><Clock size={16} /> {job.experience}</span>}
            </div>
            <div className="job-tags">
              {(job.required_skills || []).map((skill) => (
                <span key={skill} className="tag required"><Tag size={14} /> {skill}</span>
              ))}
              {(job.preferred_skills || []).map((skill) => (
                <span key={skill} className="tag preferred"><Tag size={14} /> {skill} (preferred)</span>
              ))}
            </div>
            <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
              View Original Posting
            </a>
          </article>

          <section className="section-card">
            <h2>Job Description</h2>
            <div className="job-description">{job.description}</div>
          </section>
        </div>

        <aside className="job-sidebar">
          <div className="sidebar-card">
            <h3>Quick Actions</h3>
            <div className="action-buttons">
              <button className="btn btn-outline" onClick={() => navigator.clipboard.writeText(job.url)}>
                <Copy size={18} /> Copy Link
              </button>
              <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-outline">
                <Download size={18} /> Open in Browser
              </a>
            </div>
          </div>

          {match && (
            <div className="sidebar-card match-summary">
              <h3>Match Score</h3>
              <div className="score-circle" style={{ '--score': `${match.score}%` }}>
                <span>{match.score}</span>
              </div>
              <div className="score-breakdown">
                <div className="score-item">
                  <span>Skills</span>
                  <div className="score-bar"><div className="score-fill" style={{ width: `${match.skill_match}%` }}></div></div>
                  <span>{match.skill_match}%</span>
                </div>
                <div className="score-item">
                  <span>Experience</span>
                  <div className="score-bar"><div className="score-fill" style={{ width: `${match.experience_match}%` }}></div></div>
                  <span>{match.experience_match}%</span>
                </div>
                <div className="score-item">
                  <span>Seniority</span>
                  <div className="score-bar"><div className="score-fill" style={{ width: `${match.seniority_match}%` }}></div></div>
                  <span>{match.seniority_match}%</span>
                </div>
                <div className="score-item">
                  <span>Preferences</span>
                  <div className="score-bar"><div className="score-fill" style={{ width: `${match.preference_match}%` }}></div></div>
                  <span>{match.preference_match}%</span>
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>

      {match && (
        <div className="tabs-container">
          <div className="tabs" role="tablist">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                className={`tab ${activeTab === tab.id ? 'active' : ''} ${tab.disabled ? 'disabled' : ''}`}
                onClick={() => !tab.disabled && setActiveTab(tab.id)}
                disabled={tab.disabled}
              >
                <tab.icon size={18} />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="tab-panels">
            {activeTab === 'analysis' && (
              <div className="tab-panel" role="tabpanel">
                <div className="analysis-grid">
                  <section className="section-card">
                    <div className="section-title">
                      <CheckCircle size={20} className="text-green" />
                      <h3>Matching Skills</h3>
                    </div>
                    <div className="skills-list">
                      {(match.matching_skills || []).length > 0 ? (
                        (match.matching_skills || []).map((skill) => (
                          <span key={skill} className="skill-tag success">{skill}</span>
                        ))
                      ) : (
                        <p className="text-muted">No direct skill matches found</p>
                      )}
                    </div>
                  </section>

                  <section className="section-card">
                    <div className="section-title">
                      <XCircle size={20} className="text-red" />
                      <h3>Skill Gaps</h3>
                    </div>
                    <div className="skills-list">
                      {(match.missing_skills || []).length > 0 ? (
                        (match.missing_skills || []).map((skill) => (
                          <span key={skill} className="skill-tag gap">{skill}</span>
                        ))
                      ) : (
                        <p className="text-muted">No critical skill gaps identified</p>
                      )}
                    </div>
                  </section>

                  <section className="section-card full-width">
                    <div className="section-title">
                      <HelpCircle size={20} />
                      <h3>AI Explanation</h3>
                    </div>
                    <div className="explanation">{match.explanation}</div>
                  </section>
                </div>
              </div>
            )}

            {activeTab === 'application' && application && (
              <div className="tab-panel" role="tabpanel">
                <div className="application-grid">
                  <section className="section-card">
                    <div className="section-title">
                      <Target size={20} />
                      <h3>Resume Suggestions</h3>
                    </div>
                    <ul className="suggestions-list">
                      {(application.resume_suggestions || []).map((suggestion, i) => (
                        <li key={i}>{suggestion}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="section-card full-width">
                    <div className="section-title">
                      <FileText size={20} />
                      <h3>Cover Letter</h3>
                    </div>
                    <div className="cover-letter">
                      <pre>{application.cover_letter}</pre>
                      <button className="btn btn-secondary btn-sm" onClick={() => navigator.clipboard.writeText(application.cover_letter)}>
                        <Copy size={16} /> Copy
                      </button>
                    </div>
                  </section>

                  <section className="section-card full-width">
                    <div className="section-title">
                      <HelpCircle size={20} />
                      <h3>Interview Questions</h3>
                    </div>
                    {(application.interview_qa || []).length > 0 ? (
                      <div className="chat-qa">
                        {application.interview_qa.map((item, i) => (
                          <details key={i} className="chat-qa-item">
                            <summary>{item.question}</summary>
                            <div className="chat-qa-answer">{item.answer}</div>
                          </details>
                        ))}
                      </div>
                    ) : (
                      <ol className="questions-list">
                        {(application.interview_questions || []).map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ol>
                    )}
                    <button className="btn btn-secondary btn-sm" onClick={() => navigator.clipboard.writeText(JSON.stringify(application.interview_qa?.length ? application.interview_qa : application.interview_questions, null, 2))}>
                      <Copy size={16} /> Copy All
                    </button>
                  </section>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}