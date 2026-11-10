import { useId, type ReactNode } from "react";

export function PortalShell({ children }: { children: ReactNode }) {
  return (
    <div className="portal">
      <header className="portal__bar">
        <span className="brand__word">Wekil</span>
        <span className="small muted">Merchant onboarding</span>
      </header>
      <main className="portal__main">{children}</main>
      <footer className="portal__foot small muted">Your documents are used only to verify your business.</footer>
    </div>
  );
}

export function FilePick({ label, file, onPick }: { label: string; file: File | null; onPick: (f: File | null) => void }) {
  const id = useId();
  return (
    <div className={`pick ${file ? "pick--set" : ""}`}>
      <label htmlFor={id}>
        <span className="pick__label">{label}</span>
        <span className="pick__file">{file ? file.name : "Choose a photo or PDF"}</span>
      </label>
      <input id={id} type="file" accept="image/*,application/pdf" onChange={(e) => onPick(e.target.files?.[0] ?? null)} />
    </div>
  );
}
