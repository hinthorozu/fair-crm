import React from "react";
import { labels } from "../../labels";
import { NavIconClose } from "../layout/NavIcons";
import {
  FormDirtyHost,
  useFormDirtyRequestClose,
} from "./form/FormDirty";
import { IconButton } from "./IconButton";

interface DrawerProps {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}

function DrawerChrome({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const closeRef = React.useRef<HTMLButtonElement>(null);
  const requestClose = useFormDirtyRequestClose(() => undefined);

  React.useEffect(() => {
    closeRef.current?.focus();
  }, []);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [requestClose]);

  return (
    <>
      <div className="drawer-backdrop" role="presentation" onClick={requestClose} />
      <aside className="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <header className="drawer-header">
          <div className="drawer-header-text">
            <h2 id="drawer-title">{title}</h2>
            {subtitle ? <p className="drawer-subtitle text-muted">{subtitle}</p> : null}
          </div>
          <IconButton
            ref={closeRef}
            label={labels.cancel}
            icon={<NavIconClose />}
            onClick={requestClose}
          />
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}

/** Side panel — ADR-028 dirty guard via FormDirtyHost (no silent dismiss when dirty). */
export function Drawer({ title, subtitle, onClose, children }: DrawerProps) {
  return (
    <FormDirtyHost onClose={onClose}>
      <DrawerChrome title={title} subtitle={subtitle}>
        {children}
      </DrawerChrome>
    </FormDirtyHost>
  );
}
