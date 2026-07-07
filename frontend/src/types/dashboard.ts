export interface DashboardOverviewCards {
  totalCustomers: number;
  totalFairs: number;
  openTodos: number;
  todayFollowUps: number;
  sentMails: number;
  failedMails: number;
}

export interface DashboardTaskSummary {
  notStarted: number;
  inFollowUp: number;
  closed: number;
  overdueFollowUps: number;
}

export interface DashboardRecentActivity {
  id: string;
  customerId: string;
  customerName: string;
  activityType: string;
  noteSummary: string | null;
  activityDate: string;
}

export interface DashboardFairSummary {
  fairId: string;
  fairName: string;
  customerCount: number;
  customersWithActivity: number;
  customersWithMailSent: number;
  failedMailCount: number;
}

export interface DashboardMailStatusSummary {
  queued: number;
  sending: number;
  sent: number;
  failed: number;
  timeout: number;
}

export interface DashboardSummaryResponse {
  overview: DashboardOverviewCards;
  taskSummary: DashboardTaskSummary;
  recentActivities: DashboardRecentActivity[];
  fairSummaries: DashboardFairSummary[];
  mailStatus: DashboardMailStatusSummary;
}
