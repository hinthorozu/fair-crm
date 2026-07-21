import React from "react";
import { ApiError } from "../api/client";
import { getDashboardSummary } from "../api/dashboard";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { TableEntityLink } from "../components/ui/TableEntityLink";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import { activityTypeLabels } from "../labels/activityLabels";
import { dashboardLabels } from "../labels/dashboardLabels";
import type {
  DashboardFairSummary,
  DashboardOverviewCards,
  DashboardRecentActivity,
  DashboardSummaryResponse,
  DashboardTaskSummary,
  DashboardMailStatusSummary,
} from "../types/dashboard";
import type { ActivityType } from "../types/activity";
import { Card } from "../components/ui/Card";
import { PageShell } from "../components/ui/PageShell";

function formatNumber(value: number): string {
  return value.toLocaleString("tr-TR");
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR");
}

function SummaryCards({ overview }: { overview: DashboardOverviewCards }) {
  const cards = [
    { label: dashboardLabels.cardTotalCustomers, value: overview.totalCustomers },
    { label: dashboardLabels.cardTotalFairs, value: overview.totalFairs },
    { label: dashboardLabels.cardOpenTodos, value: overview.openTodos },
    { label: dashboardLabels.cardTodayFollowUps, value: overview.todayFollowUps },
    { label: dashboardLabels.cardSentMails, value: overview.sentMails },
    { label: dashboardLabels.cardFailedMails, value: overview.failedMails },
  ];

  return (
    <div className="dashboard-summary-grid">
      {cards.map((card) => (
        <Card padding="none" className="dashboard-summary-card" key={card.label}>
          <p className="dashboard-summary-label">{card.label}</p>
          <p className="dashboard-summary-value">{formatNumber(card.value)}</p>
        </Card>
      ))}
    </div>
  );
}

function TaskSummaryCards({ summary }: { summary: DashboardTaskSummary }) {
  const cards = [
    { label: dashboardLabels.taskNotStarted, value: summary.notStarted },
    { label: dashboardLabels.taskInFollowUp, value: summary.inFollowUp },
    { label: dashboardLabels.taskClosed, value: summary.closed },
    { label: dashboardLabels.taskOverdueFollowUps, value: summary.overdueFollowUps },
  ];

  return (
    <div className="dashboard-task-grid">
      {cards.map((card) => (
        <Card padding="none" className="dashboard-summary-card" key={card.label}>
          <p className="dashboard-summary-label">{card.label}</p>
          <p className="dashboard-summary-value">{formatNumber(card.value)}</p>
        </Card>
      ))}
    </div>
  );
}

function MailStatusCards({ mailStatus }: { mailStatus: DashboardMailStatusSummary }) {
  const cards = [
    { label: dashboardLabels.mailQueued, value: mailStatus.queued },
    { label: dashboardLabels.mailSending, value: mailStatus.sending },
    { label: dashboardLabels.mailSent, value: mailStatus.sent },
    { label: dashboardLabels.mailFailed, value: mailStatus.failed },
    { label: dashboardLabels.mailTimeout, value: mailStatus.timeout },
  ];

  return (
    <div className="dashboard-mail-grid">
      {cards.map((card) => (
        <Card padding="none" className="dashboard-summary-card" key={card.label}>
          <p className="dashboard-summary-label">{card.label}</p>
          <p className="dashboard-summary-value">{formatNumber(card.value)}</p>
        </Card>
      ))}
    </div>
  );
}

function buildRecentActivityColumns(
  onOpenCustomer: (customerId: string) => void,
): UniversalDataTableColumn<DashboardRecentActivity>[] {
  return [
    {
      key: "customer_name",
      title: dashboardLabels.colCustomerName,
      sortable: false,
      render: (row) => (
        <TableEntityLink onClick={() => onOpenCustomer(row.customerId)}>
          {row.customerName}
        </TableEntityLink>
      ),
    },
    {
      key: "activity_type",
      title: dashboardLabels.colActivityType,
      sortable: false,
      render: (row) =>
        activityTypeLabels[row.activityType as ActivityType] ?? row.activityType,
    },
    {
      key: "note_summary",
      title: dashboardLabels.colNoteSummary,
      sortable: false,
      priority: "secondary",
      render: (row) => <span className="text-truncate-2">{row.noteSummary ?? "—"}</span>,
    },
    {
      key: "activity_date",
      title: dashboardLabels.colDate,
      sortable: false,
      render: (row) => formatDateTime(row.activityDate),
    },
  ];
}

function buildFairSummaryColumns(): UniversalDataTableColumn<DashboardFairSummary>[] {
  return [
    {
      key: "fair_name",
      title: dashboardLabels.colFairName,
      sortable: false,
      render: (row) => row.fairName,
    },
    {
      key: "customer_count",
      title: dashboardLabels.colCustomerCount,
      sortable: false,
      render: (row) => formatNumber(row.customerCount),
    },
    {
      key: "customers_with_activity",
      title: dashboardLabels.colCustomersWithActivity,
      sortable: false,
      priority: "secondary",
      render: (row) => formatNumber(row.customersWithActivity),
    },
    {
      key: "customers_with_mail_sent",
      title: dashboardLabels.colCustomersWithMailSent,
      sortable: false,
      priority: "secondary",
      render: (row) => formatNumber(row.customersWithMailSent),
    },
    {
      key: "failed_mail_count",
      title: dashboardLabels.colFailedMailCount,
      sortable: false,
      priority: "secondary",
      render: (row) => formatNumber(row.failedMailCount),
    },
  ];
}

function QuickActions({ onNavigate }: { onNavigate: (path: string) => void }) {
  const actions = [
    { label: dashboardLabels.actionNewCustomer, path: "/customers" },
    { label: dashboardLabels.actionNewTodo, path: "/todos" },
    { label: dashboardLabels.actionStartImport, path: "/data-integration/imports/new" },
    { label: dashboardLabels.actionSmtpSettings, path: "/admin/smtp-operations/accounts" },
    { label: dashboardLabels.actionGoToTodos, path: "/todos" },
  ];

  return (
    <div className="dashboard-quick-actions">
      {actions.map((action) => (
        <button
          key={action.label}
          type="button"
          className="btn secondary"
          onClick={() => onNavigate(action.path)}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}

function DashboardSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card as="section" className="dashboard-section">
      <h2 className="dashboard-section-title">{title}</h2>
      {children}
    </Card>
  );
}

export function DashboardPage({
  onOpenCustomer,
  onNavigate,
}: {
  onOpenCustomer: (customerId: string) => void;
  onNavigate: (path: string) => void;
}) {
  const [data, setData] = React.useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getDashboardSummary();
      setData(summary);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : dashboardLabels.loadError);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadData();
  }, [loadData]);

  const recentActivityColumns = React.useMemo(
    () => buildRecentActivityColumns(onOpenCustomer),
    [onOpenCustomer],
  );
  const fairSummaryColumns = React.useMemo(() => buildFairSummaryColumns(), []);

  if (loading) {
    return (
      <PageShell className="dashboard-page">
        <PageHeader title={dashboardLabels.pageTitle} />
        <LoadingState />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell className="dashboard-page">
        <PageHeader title={dashboardLabels.pageTitle} />
        <EmptyState title={error} description="" actionLabel="Tekrar Dene" onAction={() => void loadData()} />
      </PageShell>
    );
  }

  const summary = data ?? {
    overview: {
      totalCustomers: 0,
      totalFairs: 0,
      openTodos: 0,
      todayFollowUps: 0,
      sentMails: 0,
      failedMails: 0,
    },
    taskSummary: {
      notStarted: 0,
      inFollowUp: 0,
      closed: 0,
      overdueFollowUps: 0,
    },
    recentActivities: [],
    fairSummaries: [],
    mailStatus: {
      queued: 0,
      sending: 0,
      sent: 0,
      failed: 0,
      timeout: 0,
    },
  };

  return (
    <PageShell className="dashboard-page">
      <PageHeader title={dashboardLabels.pageTitle} />

      <DashboardSection title={dashboardLabels.sectionOverview}>
        <SummaryCards overview={summary.overview} />
      </DashboardSection>

      <DashboardSection title={dashboardLabels.sectionTaskSummary}>
        <TaskSummaryCards summary={summary.taskSummary} />
      </DashboardSection>

      <div className="dashboard-two-column">
        <DashboardSection title={dashboardLabels.sectionRecentActivities}>
          {summary.recentActivities.length === 0 ? (
            <EmptyState
              title={dashboardLabels.emptyRecentActivitiesTitle}
              description={dashboardLabels.emptyRecentActivitiesDescription}
            />
          ) : (
            <UniversalDataTable
              columns={recentActivityColumns}
              items={summary.recentActivities}
              rowKey={(row) => row.id}
            />
          )}
        </DashboardSection>

        <DashboardSection title={dashboardLabels.sectionQuickActions}>
          <QuickActions onNavigate={onNavigate} />
        </DashboardSection>
      </div>

      <DashboardSection title={dashboardLabels.sectionFairSummary}>
        {summary.fairSummaries.length === 0 ? (
          <EmptyState
            title={dashboardLabels.emptyFairSummariesTitle}
            description={dashboardLabels.emptyFairSummariesDescription}
          />
        ) : (
          <UniversalDataTable
            columns={fairSummaryColumns}
            items={summary.fairSummaries}
            rowKey={(row) => row.fairId}
          />
        )}
      </DashboardSection>

      <DashboardSection title={dashboardLabels.sectionMailStatus}>
        <MailStatusCards mailStatus={summary.mailStatus} />
      </DashboardSection>
    </PageShell>
  );
}
