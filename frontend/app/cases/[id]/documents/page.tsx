"use client";

import { CaseSubpage } from "../../../../components/case-subpage";

export default function DocumentsPage() {
  return (
    <CaseSubpage
      title="Документы"
      description="Загруженные документы, extracted text и статусы."
      render={(data) => (
        <section className="card stack">
          {data.documents.length === 0 ? (
            <div className="muted-box">Документы ещё не загружены.</div>
          ) : (
            <div className="list">
              {data.documents.map((document) => (
                <article className="list-item" key={document.id}>
                  <div>
                    <strong>{document.fileName}</strong>
                    <div className="muted">{document.mimeType}</div>
                    <div className="subtle">{document.extractedText || "Текст ещё не извлечён."}</div>
                  </div>
                  <span className="pill">{document.status}</span>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    />
  );
}
