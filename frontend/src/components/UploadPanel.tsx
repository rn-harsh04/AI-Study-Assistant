import { FormEvent, useRef, useState } from "react";
import { uploadDocument, type DocumentRecord } from "../lib/api";

type UploadPanelProps = {
  onUploaded: (document: DocumentRecord) => void;
};

export default function UploadPanel({ onUploaded }: UploadPanelProps) {
  const formRef = useRef<HTMLFormElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) {
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const document = await uploadDocument(file);
      onUploaded(document);
      setFile(null);
      formRef.current?.reset();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form ref={formRef} className="card stack" onSubmit={handleSubmit}>
      <div className="section-heading">
        <span className="eyebrow">Ingest</span>
        <h2>Upload a study document</h2>
        <p className="muted">PDFs, lecture notes, and text files are supported.</p>
      </div>

      <label className="file-drop">
        <input
          type="file"
          accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,application/pdf,text/plain,image/png,image/jpeg,image/webp"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <span>{file ? file.name : "Choose a PDF, text, or image file"}</span>
      </label>

      <button type="submit" disabled={!file || busy}>
        {busy ? "Indexing..." : "Upload and index"}
      </button>

      <p className="muted small-copy">Image files are supported. Some scanned PDFs may still need OCR preprocessing.</p>
      {error ? <p className="error">{error}</p> : null}
    </form>
  );
}
