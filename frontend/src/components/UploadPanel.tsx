import { FormEvent, useRef, useState, DragEvent } from "react";
import { uploadDocument, type DocumentRecord } from "../lib/api";

type UploadPanelProps = {
  onUploaded: (document: DocumentRecord) => void;
};

export default function UploadPanel({ onUploaded }: UploadPanelProps) {
  const formRef = useRef<HTMLFormElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) {
      return;
    }

    setBusy(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const document = await uploadDocument(file);
      onUploaded(document);
      setSuccessMsg(`"${file.name}" uploaded! Indexing in background...`);
      setFile(null);
      formRef.current?.reset();
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  function handleDragOver(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  }

  return (
    <form ref={formRef} className="card upload-card stack" onSubmit={handleSubmit} aria-label="Upload study materials">
      <div className="section-heading">
        <span className="eyebrow">Ingest Material</span>
        <h2>Upload Document</h2>
        <p className="muted">PDFs, lecture notes, textbooks, diagrams, or text files.</p>
      </div>

      <label
        htmlFor="document-file-input"
        className={`file-drop ${isDragging ? "file-drop-dragging" : ""} ${file ? "file-drop-has-file" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          id="document-file-input"
          type="file"
          aria-label="Select PDF, text, or image study document"
          accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,application/pdf,text/plain,image/png,image/jpeg,image/webp"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
          }}
        />
        <div className="drop-content">
          <span className="drop-icon" aria-hidden="true">{file ? "📄" : "📤"}</span>
          <div className="drop-text">
            {file ? (
              <>
                <strong className="file-name">{file.name}</strong>
                <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </>
            ) : (
              <>
                <strong>Click to browse or drag & drop</strong>
                <span className="muted">PDF, TXT, PNG, JPG (up to 50MB)</span>
              </>
            )}
          </div>
        </div>
      </label>

      <button type="submit" className="btn-primary" disabled={!file || busy}>
        {busy ? (
          <>
            <span className="spinner-mini" aria-hidden="true"></span> Uploading & Processing...
          </>
        ) : (
          "🚀 Upload & Index"
        )}
      </button>

      {successMsg && <div className="alert alert-success" role="status">{successMsg}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
    </form>
  );
}