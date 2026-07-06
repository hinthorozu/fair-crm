import React from "react";
import { applyDocumentTitle, type DocumentTitleContext } from "../utils/documentTitle";

export function useDocumentTitle(context: DocumentTitleContext): void {
  const {
    route,
    customerName,
    fairName,
    adapterName,
    adapterKey,
    dataOperationKey,
  } = context;

  React.useEffect(() => {
    const syncTitle = () => {
      applyDocumentTitle({
        route,
        pathname: window.location.pathname,
        search: window.location.search,
        customerName,
        fairName,
        adapterName,
        adapterKey,
        dataOperationKey,
      });
    };

    syncTitle();
    window.addEventListener("popstate", syncTitle);
    return () => window.removeEventListener("popstate", syncTitle);
  }, [route, customerName, fairName, adapterName, adapterKey, dataOperationKey]);
}
