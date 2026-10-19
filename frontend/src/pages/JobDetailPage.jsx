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
              <h3>Match & Hiring Evaluation</h3>
              
              <div className="dual-score-container">
                <div className="dual-score-item">
                  <span className="dual-score-label">Match Score</span>
                  <div className="score-circle" style={{ '--score': `${match.score}%` }}>
                    <span>{match.score}%</span>
                  </div>
                  <span className="text-sm text-muted">Technical Fit</span>
                </div>

                <div className="dual-score-item">
                  <span className="dual-score-label">Hire Odds</span>
                  <div
                    className="score-circle hiring-circle"
                    style={{
                      '--score': `${match.hiring_probability || 0}%`,
                      '--hire-color': (match.hiring_probability >= 70 ? '#059669' : match.hiring_probability >= 50 ? '#2563eb' : match.hiring_probability >= 30 ? '#d97706' : '#dc2626')
                    }}
                  >
                    <span>{match.hiring_probability || 0}%</span>
                  </div>
                  <span className={`hiring-tier-badge tier-${(match.hiring_probability >= 70 ? 'high' : match.hiring_probability >= 50 ? 'competitive' : match.hiring_probability >= 30 ? 'moderate' : 'reach')}`}>
                    {match.hiring_factors?.hiring_tier || (match.hiring_probability >= 70 ? 'High Odds' : match.hiring_probability >= 50 ? 'Competitive' : match.hiring_probability >= 30 ? 'Moderate' : 'Reach')}
                  </span>
                </div>
              </div>

              <div className="score-breakdown">
                <div className="score-item">
                  <span>Skills</span>
                  <div className="score-bar"><div className="score-fill" style={{ width: `${match.skill_match}%` }}></div></div>
                  <span>{match.skill_match}%</span>
                </div>
                {match.semantic_similarity > 0 && (
                  <div className="score-item">
                    <span>Embeddings</span>
                    <div className="score-bar"><div className="score-fill" style={{ width: `${match.semantic_similarity}%`, background: '#7c3aed' }}></div></div>
                    <span>{match.semantic_similarity}%</span>
                  </div>
                )}
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

              <div className="metrics-diff-callout">
                <div className="metrics-diff-header">
                  <Brain size={16} />
                  <span>Match Score vs. Hire Odds</span>
                </div>
                <p>
                  <strong>Match Score ({match.score}%)</strong> measures qualification & resume skills alignment. 
                  <strong> Hire Probability ({match.hiring_probability || 0}%)</strong> models real-world odds factoring in applicant volume, company selectivity ({job.is_mnc ? 'Tier-1 MNC' : 'Market'}), and screening gates.
                </p>
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
                      <h3>Exact Skill Matches</h3>
                    </div>
                    <div className="skills-list">
                      {match.skill_breakdown?.exact_matches?.length > 0 ? (
                        match.skill_breakdown.exact_matches.map((item, idx) => (
                          <span key={idx} className="skill-tag success" title={`Direct canonical match: ${item.required_skill}`}>
                            {item.canonical || item.required_skill}
                          </span>
                        ))
                      ) : (match.matching_skills || []).length > 0 ? (
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
                      <Brain size={20} style={{ color: '#2563eb' }} />
                      <h3>Semantic Equivalent Matches</h3>
                    </div>
                    <div className="skills-list">
                      {match.skill_breakdown?.semantic_matches?.length > 0 ? (
                        match.skill_breakdown.semantic_matches.map((item, idx) => (
                          <span key={idx} className="skill-tag semantic" title={item.relation}>
                            <strong>{item.canonical}</strong>
                            <span className="skill-relation">({item.relation || 'related'})</span>
                          </span>
                        ))
                      ) : (
                        <p className="text-muted">No semantic equivalent transfers needed</p>
                      )}
                    </div>
                  </section>

                  <section className="section-card">
                    <div className="section-title">
                      <XCircle size={20} className="text-red" />
                      <h3>Critical Skill Gaps</h3>
                    </div>
                    <div className="skills-list">
                      {(match.skill_breakdown?.missing_critical || match.missing_skills || []).length > 0 ? (
                        (match.skill_breakdown?.missing_critical || match.missing_skills || []).map((skill) => (
                          <span key={skill} className="skill-tag gap">{skill}</span>
                        ))
                      ) : (
                        <p className="text-muted text-green">No critical skill gaps identified - full coverage!</p>
                      )}
                    </div>
                  </section>

                  <section className="section-card">
                    <div className="section-title">
                      <Target size={20} style={{ color: '#7c3aed' }} />
                      <h3>Hiring Market Factors</h3>
                    </div>
                    <div className="factors-list">
                      {(match.hiring_factors?.positive_factors || []).map((factor, i) => (
                        <div key={`pos-${i}`} className="factor-item positive">
                          <CheckCircle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                          <span>{factor}</span>
                        </div>
                      ))}
                      {(match.hiring_factors?.risk_factors || []).map((risk, i) => (
                        <div key={`risk-${i}`} className="factor-item risk">
                          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                          <span>{risk}</span>
                        </div>
                      ))}
                      {(!match.hiring_factors?.positive_factors?.length && !match.hiring_factors?.risk_factors?.length) && (
                        <p className="text-muted">Standard market competition tier.</p>
                      )}
                    </div>
                  </section>

                  <section className="section-card full-width">
                    <div className="section-title">
                      <HelpCircle size={20} />
                      <h3>AI Decision Synthesis & Explanation</h3>
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