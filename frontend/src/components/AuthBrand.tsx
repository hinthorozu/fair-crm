import React from "react";

/** Full logo and product name on public auth screens. */
export function AuthBrand() {
  return (
    <>
      <img className="login-page-logo" src="/logo-full.png" alt="" width={560} height={171} />
      <h1 className="login-page-title">Fuar CRM</h1>
    </>
  );
}
