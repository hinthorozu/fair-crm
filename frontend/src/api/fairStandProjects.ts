import { apiRequest } from "./client";

const base = "/api/v1/fair-stand/projects";

export type FairStandProjectSummary = {
  id: string;
  organizationId: string;
  name: string;
  version: number;
  createdAt: number;
  updatedAt: number;
};

type ListProjectsResponse = {
  projects: FairStandProjectSummary[];
};

export function listFairStandProjects(): Promise<FairStandProjectSummary[]> {
  return apiRequest<ListProjectsResponse>(base).then((body) =>
    Array.isArray(body?.projects) ? body.projects : [],
  );
}

export function deleteFairStandProject(projectId: string): Promise<void> {
  return apiRequest<void>(`${base}/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
}
