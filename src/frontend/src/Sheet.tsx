import type { ReactNode } from "react";
import { Dialog } from "radix-ui";
import { X } from "lucide-react";

/** Bottom sheet (Radix Dialog: focus trap, Escape, backdrop), rendered inside the phone frame. */
export function Sheet({ title, open, onClose, container, children }: {
  title: string; open: boolean; onClose: () => void; container: HTMLElement | null; children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal container={container}>
        <Dialog.Overlay className="sheet-backdrop" />
        <Dialog.Content className="sheet" aria-describedby={undefined}>
          <div className="sheet-head">
            <Dialog.Title>{title}</Dialog.Title>
            <Dialog.Close className="icon-btn" aria-label="Close"><X size={22} /></Dialog.Close>
          </div>
          <div className="sheet-body">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
