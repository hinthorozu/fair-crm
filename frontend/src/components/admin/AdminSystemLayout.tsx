import React from "react";
import { UsersAdminPage } from "../../pages/UsersAdminPage";
import { RoleManagementPage } from "../../pages/RoleManagementPage";
import { CostCatalogPage } from "../../pages/CostCatalogPage";
import { FairStandCatalogAdminPage } from "../../pages/FairStandCatalogAdminPage";
import { FairStandUnitsAdminPage } from "../../pages/FairStandUnitsAdminPage";
import { FairStandItemsAdminPage } from "../../pages/FairStandItemsAdminPage";
import { FairStandPreviewsAdminPage } from "../../pages/FairStandPreviewsAdminPage";
import { FairStandSettingsAdminPage } from "../../pages/FairStandSettingsAdminPage";
import {
  FairStandItemTypesAdminPage,
  FairStandRuleTypesAdminPage,
  FairStandRulesAdminPage,
} from "../../pages/FairStandSnapCatalogAdminPage";

interface AdminSystemLayoutProps {
  children: React.ReactNode;
}

export function AdminSystemLayout({ children }: AdminSystemLayoutProps) {
  const pathname = window.location.pathname.replace(/\/$/, "");
  const usersRouteActive = pathname === "/admin/system/users";
  const rolesRouteActive = pathname === "/admin/system/roles";
  const costCatalogRouteActive = pathname === "/admin/cost-catalog";
  const fairStandCatalogRouteActive = pathname === "/admin/fair-stand/catalog";
  const fairStandUnitsRouteActive = pathname === "/admin/fair-stand/units";
  const fairStandItemsRouteActive =
    pathname === "/admin/fair-stand/items" || pathname.startsWith("/admin/fair-stand/items/");
  const fairStandItemTypesRouteActive = pathname === "/admin/fair-stand/item-types";
  const fairStandRuleTypesRouteActive = pathname === "/admin/fair-stand/rule-types";
  const fairStandRulesRouteActive = pathname === "/admin/fair-stand/rules";
  const fairStandPreviewsRouteActive = pathname === "/admin/fair-stand/previews";
  const fairStandSettingsRouteActive = pathname === "/admin/fair-stand/settings";
  const resolvedChildren = usersRouteActive ? (
    <UsersAdminPage />
  ) : rolesRouteActive ? (
    <RoleManagementPage />
  ) : costCatalogRouteActive ? (
    <CostCatalogPage />
  ) : fairStandCatalogRouteActive ? (
    <FairStandCatalogAdminPage />
  ) : fairStandUnitsRouteActive ? (
    <FairStandUnitsAdminPage />
  ) : fairStandItemsRouteActive ? (
    <FairStandItemsAdminPage />
  ) : fairStandItemTypesRouteActive ? (
    <FairStandItemTypesAdminPage />
  ) : fairStandRuleTypesRouteActive ? (
    <FairStandRuleTypesAdminPage />
  ) : fairStandRulesRouteActive ? (
    <FairStandRulesAdminPage />
  ) : fairStandPreviewsRouteActive ? (
    <FairStandPreviewsAdminPage />
  ) : fairStandSettingsRouteActive ? (
    <FairStandSettingsAdminPage />
  ) : (
    children
  );

  return <div className="admin-system-layout">{resolvedChildren}</div>;
}
