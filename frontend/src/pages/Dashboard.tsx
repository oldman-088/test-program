import { useCallback, useEffect, useState } from 'react';
import { api, type QueryType } from '../lib/api';
import { useHealth } from '../hooks/useHealth';
import { useLocale } from '../hooks/useLocale';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';

const SEARCH_TYPES: QueryType[] = [
  'name',
  'username',
  'email',
  'phone',
  'url',
  'domain',
  'entity',
];

type SectionState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; data: T };

function SectionError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="space-y-2">
      <p className="text-sm text-destructive">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

function SectionLoading() {
  return (
    <div className="space-y-2" aria-label="Loading">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

export function Dashboard() {
  const { t } = useLocale();
  const { health, healthDb, loading: healthLoading, error: healthError, refresh: refreshHealth } =
    useHealth();

  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState<QueryType>('username');
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [recent, setRecent] = useState<SectionState<Awaited<ReturnType<typeof api.getRecentInvestigations>>>>({
    status: 'loading',
  });
  const [stats, setStats] = useState<SectionState<Awaited<ReturnType<typeof api.getStats>>>>({
    status: 'loading',
  });
  const [integrations, setIntegrations] = useState<
    SectionState<Awaited<ReturnType<typeof api.getIntegrations>>>
  >({ status: 'loading' });
  const [aiProvider, setAiProvider] = useState<
    SectionState<Awaited<ReturnType<typeof api.getAiProvider>>>
  >({ status: 'loading' });
  const [tasks, setTasks] = useState<SectionState<Awaited<ReturnType<typeof api.getTaskProgress>>>>({
    status: 'loading',
  });
  const [reports, setReports] = useState<
    SectionState<Awaited<ReturnType<typeof api.getLatestReports>>>
  >({ status: 'loading' });

  const loadSections = useCallback(async () => {
    setRecent({ status: 'loading' });
    setStats({ status: 'loading' });
    setIntegrations({ status: 'loading' });
    setAiProvider({ status: 'loading' });
    setTasks({ status: 'loading' });
    setReports({ status: 'loading' });

    const [rRecent, rStats, rIntegrations, rAi, rTasks, rReports] = await Promise.allSettled([
      api.getRecentInvestigations(5),
      api.getStats(),
      api.getIntegrations(),
      api.getAiProvider(),
      api.getTaskProgress(),
      api.getLatestReports(5),
    ]);

    setRecent(
      rRecent.status === 'fulfilled'
        ? { status: 'ok', data: rRecent.value }
        : { status: 'error', message: rRecent.reason instanceof Error ? rRecent.reason.message : 'Request failed' },
    );
    setStats(
      rStats.status === 'fulfilled'
        ? { status: 'ok', data: rStats.value }
        : { status: 'error', message: rStats.reason instanceof Error ? rStats.reason.message : 'Request failed' },
    );
    setIntegrations(
      rIntegrations.status === 'fulfilled'
        ? { status: 'ok', data: rIntegrations.value }
        : { status: 'error', message: rIntegrations.reason instanceof Error ? rIntegrations.reason.message : 'Request failed' },
    );
    setAiProvider(
      rAi.status === 'fulfilled'
        ? { status: 'ok', data: rAi.value }
        : { status: 'error', message: rAi.reason instanceof Error ? rAi.reason.message : 'Request failed' },
    );
    setTasks(
      rTasks.status === 'fulfilled'
        ? { status: 'ok', data: rTasks.value }
        : { status: 'error', message: rTasks.reason instanceof Error ? rTasks.reason.message : 'Request failed' },
    );
    setReports(
      rReports.status === 'fulfilled'
        ? { status: 'ok', data: rReports.value }
        : { status: 'error', message: rReports.reason instanceof Error ? rReports.reason.message : 'Request failed' },
    );
  }, []);

  useEffect(() => {
    void loadSections();
  }, [loadSections]);

  async function handleStartInvestigation(e: React.FormEvent) {
    e.preventDefault();
    setSubmitMessage(null);
    setSubmitError(null);
    if (!query.trim()) {
      setSubmitError(t('dashboard.queryRequired'));
      return;
    }
    setSubmitting(true);
    try {
      await api.createInvestigation({ query: query.trim(), query_type: queryType });
      setSubmitMessage(t('dashboard.investigationStarted'));
      void loadSections();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Logo / title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('app.name')}</h1>
        <p className="text-sm text-muted-foreground">{t('dashboard.title')}</p>
      </div>

      {/* Backend + DB health (real /api/health and /api/health/db) */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.backendStatus')}</CardTitle>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <SectionLoading />
          ) : healthError || !health || !healthDb ? (
            <div role="alert" className="space-y-2">
              <p className="text-sm text-destructive">
                {healthError ?? t('dashboard.backendUnavailable')}
              </p>
              <Button variant="outline" size="sm" onClick={() => void refreshHealth()}>
                {t('common.retry')}
              </Button>
            </div>
          ) : (
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">{t('dashboard.backendStatus')}</dt>
                <dd>
                  <Badge variant={health.status === 'ok' ? 'default' : 'destructive'}>
                    {health.status}
                  </Badge>{' '}
                  <span className="text-muted-foreground">v{health.version}</span>
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('dashboard.databaseStatus')}</dt>
                <dd>
                  <Badge variant={healthDb.status === 'ok' ? 'default' : 'destructive'}>
                    {healthDb.status}
                  </Badge>{' '}
                  <span className="text-muted-foreground">
                    {healthDb.database} · {healthDb.latency_ms}ms
                  </span>
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Search + start investigation */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.startInvestigation')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleStartInvestigation} className="space-y-4">
            <div>
              <label htmlFor="search-query" className="mb-1 block text-sm font-medium">
                {t('dashboard.searchLabel')}
              </label>
              <Input
                id="search-query"
                name="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('dashboard.searchPlaceholder')}
                aria-describedby={submitError ? 'search-error' : undefined}
                aria-invalid={Boolean(submitError)}
              />
            </div>
            <div>
              <label htmlFor="search-type" className="mb-1 block text-sm font-medium">
                {t('dashboard.searchTypeLabel')}
              </label>
              <Select
                id="search-type"
                name="query_type"
                value={queryType}
                onChange={(e) => setQueryType(e.target.value as QueryType)}
              >
                {SEARCH_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`searchType.${type}`)}
                  </option>
                ))}
              </Select>
            </div>
            <Button type="submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? t('common.loading') : t('dashboard.startInvestigation')}
            </Button>
            {submitMessage && (
              <p role="status" className="text-sm text-foreground">
                {submitMessage}
              </p>
            )}
            {submitError && (
              <p id="search-error" role="alert" className="text-sm text-destructive">
                {submitError}
              </p>
            )}
          </form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Recent investigations */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.recentInvestigations')}</CardTitle>
          </CardHeader>
          <CardContent>
            {recent.status === 'loading' ? (
              <SectionLoading />
            ) : recent.status === 'error' ? (
              <SectionError message={recent.message} onRetry={() => void loadSections()} />
            ) : recent.data.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('dashboard.noData')}</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {recent.data.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-2">
                    <span className="text-start">{item.query}</span>
                    <Badge variant="secondary">{item.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Search statistics */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.searchStats')}</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.status === 'loading' ? (
              <SectionLoading />
            ) : stats.status === 'error' ? (
              <SectionError message={stats.message} onRetry={() => void loadSections()} />
            ) : (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">{t('stats.totalInvestigations')}</dt>
                  <dd className="text-lg font-semibold">{stats.data.total_investigations}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('stats.totalSearches')}</dt>
                  <dd className="text-lg font-semibold">{stats.data.total_searches}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('stats.successRate')}</dt>
                  <dd className="text-lg font-semibold">{stats.data.success_rate}%</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('stats.avgDuration')}</dt>
                  <dd className="text-lg font-semibold">{stats.data.avg_duration_ms}ms</dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        {/* Integrations */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.integrations')}</CardTitle>
          </CardHeader>
          <CardContent>
            {integrations.status === 'loading' ? (
              <SectionLoading />
            ) : integrations.status === 'error' ? (
              <SectionError message={integrations.message} onRetry={() => void loadSections()} />
            ) : integrations.data.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('dashboard.noData')}</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {integrations.data.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-2">
                    <span className="text-start">{item.name}</span>
                    <Badge variant={item.status === 'available' ? 'default' : 'secondary'}>
                      {item.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* AI provider */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.aiProvider')}</CardTitle>
          </CardHeader>
          <CardContent>
            {aiProvider.status === 'loading' ? (
              <SectionLoading />
            ) : aiProvider.status === 'error' ? (
              <SectionError message={aiProvider.message} onRetry={() => void loadSections()} />
            ) : (
              <dl className="space-y-1 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Provider</dt>
                  <dd>{aiProvider.data.provider}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Model</dt>
                  <dd>{aiProvider.data.model}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">{t('common.status')}</dt>
                  <dd>
                    <Badge variant={aiProvider.data.status === 'available' ? 'default' : 'secondary'}>
                      {aiProvider.data.status}
                    </Badge>
                  </dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        {/* Task progress */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.taskProgress')}</CardTitle>
          </CardHeader>
          <CardContent>
            {tasks.status === 'loading' ? (
              <SectionLoading />
            ) : tasks.status === 'error' ? (
              <SectionError message={tasks.message} onRetry={() => void loadSections()} />
            ) : tasks.data.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('dashboard.noData')}</p>
            ) : (
              <ul className="space-y-3 text-sm">
                {tasks.data.items.map((item) => (
                  <li key={item.id}>
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-start">{item.name}</span>
                      <span className="text-muted-foreground">{item.progress}%</span>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuenow={item.progress}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={item.name}
                      className="h-2 w-full overflow-hidden rounded-full bg-muted"
                    >
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Latest reports */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.latestReports')}</CardTitle>
          </CardHeader>
          <CardContent>
            {reports.status === 'loading' ? (
              <SectionLoading />
            ) : reports.status === 'error' ? (
              <SectionError message={reports.message} onRetry={() => void loadSections()} />
            ) : reports.data.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('dashboard.noData')}</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {reports.data.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-2">
                    <span className="text-start">{item.title}</span>
                    <Badge variant="secondary">{item.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
