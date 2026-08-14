# User & Organization Management

## Scope

Fair CRM admin user-management UI is backed by reusable identity and organization-management APIs in `kyrox-core`.

## Admin UI

Admin navigation contains **Kimlik ve Erişim** with:

- **Organizasyonlar** (`/admin/organizations`)
  - list organizations
  - create organization
  - edit organization
  - soft-delete organization
- **Kullanıcılar** (`/admin/users`)
  - organization selection is required
  - create user with a temporary password
  - invite user by email

## User creation flows

### Temporary password

The admin selects an organization and creates the user with a temporary password. The Core sets `must_change_password=true`. The user must change the password on first login before accessing protected APIs.

### Invitation

The admin selects an organization and sends an invitation. The invitee registers/accepts the invitation and receives membership in the selected organization.

## Core API dependencies

Organization administration uses global super-admin endpoints under:

- `GET /api/v1/admin/organizations`
- `POST /api/v1/admin/organizations`
- `GET /api/v1/admin/organizations/{organization_id}`
- `PATCH /api/v1/admin/organizations/{organization_id}`
- `DELETE /api/v1/admin/organizations/{organization_id}`

Organization deletion is soft-delete.

User creation uses organization-scoped identity endpoints. User/role management authorization is provided by reusable identity permissions in Kyrox Core rather than Fair CRM-specific permission logic.

## Validation

Before merge, the Fair CRM feature branch passed the frontend build and test workflow. The corresponding Kyrox Core feature branch passed its backend migration/test workflow.
