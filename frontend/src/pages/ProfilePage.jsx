import React, { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Loader2,
  User,
  Mail,
  MapPin,
  Target,
  FileText,
  Plus,
  Trash2,
  Eye,
  Edit,
  Save,
  X,
  Check,
  Upload,
  Brain,
  Briefcase,
  Target as TargetIcon,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

export function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    target_roles: [],
    preferred_locations: [],
    skills: [],
    summary: '',
  });
  const [newSkill, setNewSkill] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [jobMatches, setJobMatches] = useState([]);
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [matchesError, setMatchesError] = useState('');
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [skillPlan, setSkillPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [showMatchPanel, setShowMatchPanel] = useState(false);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const [profileRes, resumesRes] = await Promise.all([
          apiService.profiles.list(),
          apiService.resumes.list(),
        ]);
        const list = profileRes.data.results || profileRes.data || [];
        const profileData = list[0];
        if (profileData) {
          setProfile(profileData);
          setFormData({
            name: profileData.name || '',
            email: profileData.email || '',
            target_roles: profileData.target_roles || [],
            preferred_locations: profileData.preferred_locations || [],
            skills: profileData.skills || [],
            summary: profileData.summary || '',
          });
        }
        setResumes(resumesRes.data.results || resumesRes.data);
      } catch (e) {
        console.error('Failed to load profile:', e);
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await apiService.profiles.update(profile.id, formData);
      setProfile(response.data);
      updateUser(response.data);
      setEditing(false);
    } catch (e) {
      console.error('Failed to save:', e);
    } finally {
      setSaving(false);
    }
  };

  const onDrop = async (acceptedFiles) => {
    if (!profile) return;
    setUploading(true);
    setMatchesError('');
    try {
      const file = acceptedFiles[0];
      const response = await apiService.resumes.upload(profile.id, file);
      setResumes(prev => [response.data, ...prev]);
      // Automatically match the new resume against all jobs
      await loadJobMatches();
    } catch (e) {
      console.error('Upload failed:', e);
      setMatchesError(e.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const loadJobMatches = async () => {
    if (!profile) return;
    setMatchesLoading(true);
    setMatchesError('');
    try {
      const response = await apiService.jobs.matchAll(0);
      const matches = response.data?.matches || [];
      setJobMatches(matches);
      setShowMatchPanel(matches.length > 0);
      if (matches.length > 0) {
        setSelectedMatch(matches[0]);
      }
    } catch (e) {
      console.error('Failed to match jobs:', e);
      setMatchesError(e.response?.data?.detail || 'Could not analyze matches. Make sure jobs are scanned first.');
    } finally {
      setMatchesLoading(false);
    }
  };

  const loadSkillPlan = async (jobId) => {
    setPlanLoading(true);
    try {
      const response = await apiService.jobs.skillGapPlan(jobId);
      setSkillPlan(response.data);
    } catch (e) {
      console.error('Failed to load skill plan:', e);
    } finally {
      setPlanLoading(false);
    }
  };

  const selectMatch = (match) => {
    setSelectedMatch(match);
    setSkillPlan(null);
    if (match?.job?.id) {
      loadSkillPlan(match.job.id);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxSize: 5 * 1024 * 1024,
  });

  const deleteResume = async (id) => {
    try {
      await apiService.resumes.delete(id);
      setResumes(prev => prev.filter(r => r.id !== id));
    } catch (e) {
      console.error('Delete failed:', e);
    }
  };

  const addItem = (arr, item, setter) => {
    const trimmed = item.trim();
    if (trimmed && !arr.includes(trimmed)) {
      setter([...arr, trimmed]);
    }
  };

  const removeItem = (arr, item, setter) => {
    setter(arr.filter(i => i !== item));
  };

  if (loading) {
    return <div className="page-loading"><Loader2 size={32} className="spin" /></div>;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Profile</h1>
          <p>Manage your career profile and resumes</p>
        </div>
      </div>

      <div className="profile-layout">
        <div className="profile-main">
          <section className="section-card">
            <div className="section-header">
              <h2>Personal Information</h2>
              <button className="btn btn-secondary btn-sm" onClick={() => setEditing(!editing)}>
                {editing ? (<><X size={16} /> Cancel</>) : (<><Edit size={16} /> Edit</>)}
              </button>
            </div>

            {editing ? (
              <form onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="name">Full Name</label>
                    <div className="input-wrapper">
                      <User size={18} />
                      <input
                        id="name"
                        value={formData.name}
                        onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                        required
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <div className="input-wrapper">
                      <Mail size={18} />
                      <input
                        id="email"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                      />
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label>Target Roles</label>
                  <div className="tag-input">
                    <input
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem(formData.target_roles, newRole, (v) => setFormData(p => ({ ...p, target_roles: v }))), setNewRole(''))}
                      placeholder="Add role (press Enter)"
                    />
                    <div className="tags">
                      {formData.target_roles.map((role) => (
                        <span key={role} className="tag"><span>{role}</span><button type="button" onClick={() => removeItem(formData.target_roles, role, (v) => setFormData(p => ({ ...p, target_roles: v })))}>×</button></span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label>Preferred Locations</label>
                  <div className="tag-input">
                    <input
                      value={newLocation}
                      onChange={(e) => setNewLocation(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem(formData.preferred_locations, newLocation, (v) => setFormData(p => ({ ...p, preferred_locations: v }))), setNewLocation(''))}
                      placeholder="Add location (press Enter)"
                    />
                    <div className="tags">
                      {formData.preferred_locations.map((loc) => (
                        <span key={loc} className="tag"><span>{loc}</span><button type="button" onClick={() => removeItem(formData.preferred_locations, loc, (v) => setFormData(p => ({ ...p, preferred_locations: v })))}>×</button></span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label>Skills</label>
                  <div className="tag-input">
                    <input
                      value={newSkill}
                      onChange={(e) => setNewSkill(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem(formData.skills, newSkill, (v) => setFormData(p => ({ ...p, skills: v }))), setNewSkill(''))}
                      placeholder="Add skill (press Enter)"
                    />
                    <div className="tags">
                      {formData.skills.map((skill) => (
                        <span key={skill} className="tag"><span>{skill}</span><button type="button" onClick={() => removeItem(formData.skills, skill, (v) => setFormData(p => ({ ...p, skills: v })))}>×</button></span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="summary">Professional Summary</label>
                  <textarea
                    id="summary"
                    value={formData.summary}
                    onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
                    rows={4}
                    placeholder="Brief summary of your experience and career goals..."
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <Loader2 size={18} className="spin" /> : <Save size={18} />} Save Changes
                </button>
              </form>
            ) : (
              <div className="profile-view">
                <div className="profile-avatar">
                  {profile?.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <h3>{profile?.name || 'Not set'}</h3>
                <p className="profile-email"><Mail size={16} /> {profile?.email || 'Not set'}</p>

                <div className="profile-section">
                  <h4><Target size={18} /> Target Roles</h4>
                  <div className="tags">
                    {(formData.target_roles || []).map((role) => (
                      <span key={role} className="tag">{role}</span>
                    ))}
                    {(formData.target_roles || []).length === 0 && <span className="text-muted">Not set</span>}
                  </div>
                </div>

                <div className="profile-section">
                  <h4><MapPin size={18} /> Preferred Locations</h4>
                  <div className="tags">
                    {(formData.preferred_locations || []).map((loc) => (
                      <span key={loc} className="tag">{loc}</span>
                    ))}
                    {(formData.preferred_locations || []).length === 0 && <span className="text-muted">Not set</span>}
                  </div>
                </div>

                <div className="profile-section">
                  <h4><Brain size={18} /> Skills</h4>
                  <div className="tags">
                    {(formData.skills || []).map((skill) => (
                      <span key={skill} className="tag">{skill}</span>
                    ))}
                    {(formData.skills || []).length === 0 && <span className="text-muted">Not set</span>}
                  </div>
                </div>

                <div className="profile-section">
                  <h4>Professional Summary</h4>
                  <p>{formData.summary || <span className="text-muted">Not set</span>}</p>
                </div>
              </div>
            )}
          </section>
        </div>

        <aside className="profile-sidebar">
          <section className="section-card">
            <div className="section-header">
              <h2>Resumes</h2>
              {resumes.length > 0 && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={loadJobMatches}
                  disabled={matchesLoading}
                >
                  {matchesLoading ? <Loader2 size={16} className="spin" /> : <TargetIcon size={16} />}
                  {matchesLoading ? 'Analyzing...' : 'Re-analyze'}
                </button>
              )}
            </div>

            <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
              <input {...getInputProps()} />
              <Upload size={32} />
              <p>Drag & drop resume here</p>
              <span className="text-sm">PDF, DOCX, or TXT (max 5MB)</span>
              {uploading && <Loader2 size={24} className="spin" />}
            </div>

            {matchesError && <div className="alert error">{matchesError}</div>}

            {resumes.length > 0 && (
              <div className="resumes-list">
                {resumes.map((resume) => (
                  <div key={resume.id} className="resume-item">
                    <div className="resume-info">
                      <FileText size={20} />
                      <div>
                        <strong>{resume.file?.split('/').pop() || 'Resume'}</strong>
                        <span>Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="resume-actions">
                      {resume.extracted_text && (
                        <button className="btn btn-ghost btn-sm"><Eye size={16} /> Preview</button>
                      )}
                      <button className="btn btn-ghost btn-sm danger" onClick={() => deleteResume(resume.id)}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {resumes.length === 0 && !uploading && (
              <p className="text-center text-muted">No resumes uploaded yet</p>
            )}
          </section>

          {showMatchPanel && jobMatches.length > 0 && (
            <section className="section-card">
              <div className="section-header">
                <h2><TargetIcon size={20} /> Job Matches</h2>
                <span className="text-sm text-muted">{jobMatches.length} jobs analyzed</span>
              </div>

              {matchesLoading ? (
                <div className="page-loading"><Loader2 size={24} className="spin" /></div>
              ) : (
                <>
                  <div className="match-results">
                    {jobMatches.slice(0, 10).map((match) => (
                      <div
                        key={match.job.id}
                        className={`match-result-item ${selectedMatch?.job?.id === match.job.id ? 'selected' : ''}`}
                        onClick={() => selectMatch(match)}
                      >
                        <div className="match-result-header">
                          <div className="match-result-title">
                            <strong>{match.job.title}</strong>
                            <span className="text-muted">{match.job.company}</span>
                          </div>
                          <div className={`match-score ${match.score >= 70 ? 'high' : match.score >= 50 ? 'medium' : 'low'}`}>
                            {match.score}%
                          </div>
                        </div>
                        <div className="match-result-skills">
                          <div className="skill-row">
                            <CheckCircle size={14} className="text-green" />
                            <span className="text-sm">
                              {(match.matching_skills || []).slice(0, 3).join(', ') || 'No matching skills'}
                              {(match.matching_skills || []).length > 3 && ` +${match.matching_skills.length - 3}`}
                            </span>
                          </div>
                          {(match.missing_skills || []).length > 0 && (
                            <div className="skill-row">
                              <XCircle size={14} className="text-red" />
                              <span className="text-sm">
                                Missing: {(match.missing_skills || []).slice(0, 3).join(', ')}
                                {(match.missing_skills || []).length > 3 && ` +${match.missing_skills.length - 3}`}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedMatch && (
                    <div className="match-detail">
                      <div className="match-detail-header">
                        <h3>{selectedMatch.job.title}</h3>
                        <span className="text-muted">{selectedMatch.job.company}</span>
                        <Link to={`/jobs/${selectedMatch.job.id}`} className="btn btn-primary btn-sm">
                          View Job <ArrowRight size={14} />
                        </Link>
                      </div>

                      <div className="match-scores-grid">
                        <div className="score-box">
                          <span className="score-label">Skills</span>
                          <div className="score-bar"><div className="score-fill" style={{ width: `${selectedMatch.skill_match}%` }}></div></div>
                          <span className="score-value">{selectedMatch.skill_match}%</span>
                        </div>
                        <div className="score-box">
                          <span className="score-label">Experience</span>
                          <div className="score-bar"><div className="score-fill" style={{ width: `${selectedMatch.experience_match}%` }}></div></div>
                          <span className="score-value">{selectedMatch.experience_match}%</span>
                        </div>
                        <div className="score-box">
                          <span className="score-label">Seniority</span>
                          <div className="score-bar"><div className="score-fill" style={{ width: `${selectedMatch.seniority_match}%` }}></div></div>
                          <span className="score-value">{selectedMatch.seniority_match}%</span>
                        </div>
                        <div className="score-box">
                          <span className="score-label">Preferences</span>
                          <div className="score-bar"><div className="score-fill" style={{ width: `${selectedMatch.preference_match}%` }}></div></div>
                          <span className="score-value">{selectedMatch.preference_match}%</span>
                        </div>
                      </div>

                      <div className="match-skills-section">
                        <div className="skills-column">
                          <h4><CheckCircle size={16} className="text-green" /> Matching Skills</h4>
                          <div className="skills-tags">
                            {(selectedMatch.matching_skills || []).map((skill) => (
                              <span key={skill} className="skill-tag success">{skill}</span>
                            ))}
                            {(selectedMatch.matching_skills || []).length === 0 && (
                              <span className="text-muted">No matching skills found</span>
                            )}
                          </div>
                        </div>
                        <div className="skills-column">
                          <h4><XCircle size={16} className="text-red" /> Missing Skills</h4>
                          <div className="skills-tags">
                            {(selectedMatch.missing_skills || []).map((skill) => (
                              <span key={skill} className="skill-tag gap">{skill}</span>
                            ))}
                            {(selectedMatch.missing_skills || []).length === 0 && (
                              <span className="text-green">No missing skills - perfect match!</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {selectedMatch.explanation && (
                        <div className="match-explanation">
                          <h4><Brain size={16} /> AI Analysis</h4>
                          <p>{selectedMatch.explanation}</p>
                        </div>
                      )}

                      {skillPlan && skillPlan.plan && skillPlan.plan.length > 0 && (
                        <div className="skill-plan-section">
                          <h4><BookOpen size={16} /> How to Fix Missing Skills</h4>
                          <div className="skill-plan-list">
                            {skillPlan.plan.map((item, i) => (
                              <div key={i} className="skill-plan-item">
                                <div className="skill-plan-header">
                                  <strong>{item.skill}</strong>
                                  <span className={`priority-badge ${item.priority}`}>{item.priority}</span>
                                  <span className="text-muted text-sm">{item.estimated_time}</span>
                                </div>
                                <ul className="skill-plan-actions">
                                  {item.suggested_actions.map((action, j) => (
                                    <li key={j}>{action}</li>
                                  ))}
                                </ul>
                                <div className="skill-plan-resources">
                                  {item.resources.map((url, j) => (
                                    <a key={j} href={url} target="_blank" rel="noopener noreferrer" className="resource-link">
                                      <Zap size={12} /> {new URL(url).hostname.replace('www.', '')}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {planLoading && (
                        <div className="page-loading"><Loader2 size={20} className="spin" /></div>
                      )}
                    </div>
                  )}
                </>
              )}
            </section>
          )}

          {showMatchPanel && jobMatches.length === 0 && !matchesLoading && (
            <section className="section-card">
              <div className="empty-state">
                <AlertTriangle size={40} />
                <h3>No jobs to match yet</h3>
                <p>Scan for jobs first, then upload your resume to see matches.</p>
                <Link to="/jobs" className="btn btn-primary">Go to Jobs</Link>
              </div>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}