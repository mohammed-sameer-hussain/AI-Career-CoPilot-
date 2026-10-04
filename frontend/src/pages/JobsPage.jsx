import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Search,
  Filter,
  Loader2,
  Briefcase,
  MapPin,
  Clock,
  Tag,
  ChevronDown,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function JobsPage() {
  const { user } = useAuth();
  const [urlParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(urlParams.get('search') || '');
  const [filters, setFilters] = useState({
    location: '',
    experience: '',
    source: '',
    mnc: false,
    company: '',
    level: '',
    south: false,
  });
  const FEATURED_MNCS = ['TCS','Infosys','Wipro','HCLTech','Tech Mahindra','Cognizant','Accenture','LTIMindtree','Capgemini','IBM','Oracle','Dell','Cisco','Zoho','Freshworks'];
  // ONLY cities with real tech parks / MNC / GCC offices.
  const LOCATION_CITIES = ['Bengaluru','Hyderabad','Chennai','Pune','Mumbai','Gurugram','Noida','Delhi','Kolkata','Ahmedabad','Kochi','Coimbatore','Remote'];
  const NEARBY_CITIES = ['Bengaluru','Hyderabad','Chennai','Pune','Mumbai','Gurugram','Noida','Delhi','Kolkata','Ahmedabad','Kochi','Coimbatore'];
  const [pagination, setPagination] = useState({ page: 1, total: 0, totalPages: 0 });
  const [showFilters, setShowFilters] = useState(false);
  const [scanError, setScanError] = useState('');

  const loadJobs = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.page,
        search,
        ...filters,
      };
      Object.keys(params).forEach(key => (params[key] === '' || params[key] === false) && delete params[key]);
      const response = await apiService.jobs.list(params);
      const data = response.data.results || response.data;
      setJobs(data);
      if (response.data.count) {
        setPagination(prev => ({ ...prev, total: response.data.count, totalPages: Math.ceil(response.data.count / 20) }));
      }
    } catch (e) {
      console.error('Failed to load jobs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, [pagination.page, search, filters]);

  // Keep in sync when the topbar search navigates here from another page.
  useEffect(() => {
    const query = urlParams.get('search') || '';
    setSearch((prev) => (prev === query ? prev : query));
    setPagination((prev) => (prev.page === 1 ? prev : { ...prev, page: 1 }));
  }, [urlParams]);

  const handleScan = async () => {
    if (!user) return;
    setScanError('');
    try {
      await apiService.jobs.scan(user.id);
      await loadJobs();
    } catch (e) {
      console.error('Scan failed:', e);
      setScanError(e.response?.data?.detail || 'Job scan failed - check the backend log and your internet connection.');
    }
  };

  const sources = [...new Set(jobs.map(j => j.source).filter(Boolean))];

  const postedLabel = (job) => {
    const value = job.posted_at || job.discovered_at;
    if (!value) return 'Recently';
    try {
      return formatDistanceToNow(new Date(value), { addSuffix: true });
    } catch {
      return 'Recently';
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Job Opportunities</h1>
          <p>Discover and analyze tech jobs tailored to your profile</p>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setShowFilters(!showFilters)}>
            <Filter size={18} /> Filters
          </button>
          {user && (
            <button className="btn btn-primary" onClick={handleScan}>
              <Briefcase size={18} /> Scan for Jobs
            </button>
          )}
        </div>
      </div>

      <div className="jobs-toolbar">
        <div className="search-box large">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search by title, company, skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="nearby-row">
          <span className="nearby-label"><MapPin size={14} /> Near you:</span>
          <div className="nearby-chips">
            {NEARBY_CITIES.map((city) => (
              <button
                key={city}
                type="button"
                className={`city-chip ${filters.location === city ? 'active' : ''}`}
                onClick={() => {
                  setFilters((prev) => ({ ...prev, location: prev.location === city ? '' : city }));
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
              >
                {city}
              </button>
            ))}
            {filters.location && (
              <button
                type="button"
                className="city-chip clear"
                onClick={() => {
                  setFilters((prev) => ({ ...prev, location: '' }));
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
              >
                Clear x
              </button>
            )}
          </div>
        </div>

        {showFilters && (
          <div className="filters-panel">
            <div className="filter-group">
              <label>Location (tech / MNC hub cities only)</label>
              <select value={filters.location} onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}>
                <option value="">All locations</option>
                {LOCATION_CITIES.map(h => <option key={h} value={h}>{h}</option>)}
              </select>
              <label className="mnc-toggle" style={{ marginTop: 6 }}>
                <input
                  type="checkbox"
                  checked={filters.south}
                  onChange={(e) => setFilters(prev => ({ ...prev, south: e.target.checked }))}
                />
                South India only
              </label>
            </div>
            <div className="filter-group">
              <label>Experience</label>
              <select value={filters.level} onChange={(e) => setFilters(prev => ({ ...prev, level: e.target.value, experience: e.target.value }))}>
                <option value="">All levels (fresher + senior)</option>
                <option value="fresher">Fresher (0-2 years)</option>
                <option value="mid">Mid (2-5 years)</option>
                <option value="senior">Senior (5+ years)</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Source</label>
              <select value={filters.source} onChange={(e) => setFilters(prev => ({ ...prev, source: e.target.value }))}>
                <option value="">All sources</option>
                {sources.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="filter-group">
              <label>Company type</label>
              <label className="mnc-toggle">
                <input
                  type="checkbox"
                  checked={filters.mnc}
                  onChange={(e) => setFilters(prev => ({ ...prev, mnc: e.target.checked }))}
                />
                MNCs only
              </label>
            </div>
            <div className="filter-group">
              <label>Top MNC</label>
              <select value={filters.company} onChange={(e) => setFilters(prev => ({ ...prev, company: e.target.value }))}>
                <option value="">All companies</option>
                {FEATURED_MNCS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
        )}
      </div>

      {scanError && <div className="alert error">{scanError}</div>}

      {loading ? (
        <div className="page-loading"><Loader2 size={32} className="spin" /></div>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <Briefcase size={64} />
          <h3>No jobs found</h3>
          <p>{search || filters.location ? 'Try adjusting your search or filters' : 'Click "Scan for Jobs" to discover opportunities'}</p>
          {user && !search && !filters.location && (
            <button className="btn btn-primary" onClick={handleScan}>
              <Briefcase size={18} /> Scan for Jobs
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="jobs-grid">
            {jobs.map((job) => (
              <article key={job.id} className="job-card">
                <div className="job-card-header">
                  <div className="job-card-badges">
                    <span className="job-source">{job.source}</span>
                    {job.is_mnc && <span className="mnc-badge">MNC</span>}
                  </div>
                  <span className="job-date">{postedLabel(job)}</span>
                </div>
                <h3>{job.title}</h3>
                <p className="job-company">
                  <span>{job.company}</span>
                  {job.location && <> · <MapPin size={14} /> {job.location}</>}
                </p>
                {job.experience && (
                  <p className="job-experience">
                    <Clock size={14} /> {job.experience}
                  </p>
                )}
                <div className="job-skills">
                  {(job.required_skills || []).slice(0, 5).map((skill) => (
                    <span key={skill} className="skill-tag">{skill}</span>
                  ))}
                  {(job.required_skills || []).length > 5 && (
                    <span className="skill-tag more">+{(job.required_skills.length - 5)}</span>
                  )}
                </div>
                <div className="job-card-footer">
                  <Link to={`/jobs/${job.id}`} className="btn btn-primary btn-sm">Analyze Match</Link>
                  <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                    View Original
                  </a>
                </div>
              </article>
            ))}
          </div>

          {pagination.totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                disabled={pagination.page === 1}
              >
                Previous
              </button>
              <span>Page {pagination.page} of {pagination.totalPages}</span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                disabled={pagination.page === pagination.totalPages}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}