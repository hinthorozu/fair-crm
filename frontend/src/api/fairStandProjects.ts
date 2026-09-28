import { apiRequest } from "./client";

const base = "/api/v1/fair-stand/projects";

export type FairStandProjectSummary = {
  id: string;
  organizationId: string;
  customerId: string;
  name: string;
  version: number;
  createdAt: number;
  updatedAt: number;
};

type ListProjectsResponse = {
  projects: FairStandProjectSummary[];
};

export function listFairStandProjects(customerId?: string): Promise<FairStandProjectSummary[]> {
  const query = customerId ? `?customerId=${encodeURIComponent(customerId)}` : "";
  return apiRequest<ListProjectsResponse>(`${base}${query}`).then((body) =>
    Array.isArray(body?.projects) ? body.projects : [],
  );
}

export function assignFairStandProjectCustomer(
  projectId: string,
  customerId: string,
): Promise<FairStandProjectSummary> {
  return apiRequest<FairStandProjectSummary>(`${base}/${encodeURIComponent(projectId)}/customer`, {
    method: "PATCH",
    body: JSON.stringify({ customerId }),
  });
}

export function deleteFairStandProject(projectId: string): Promise<void> {
  return apiRequest<void>(`${base}/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
}
