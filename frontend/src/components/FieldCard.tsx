import { Check } from "lucide-react";
import { fieldLabels, type ExtractedField } from "../types";

type Props = {
  field: ExtractedField;
  focused: boolean;
  edit: string;
  busy: boolean;
  canReview: boolean;
  onFocus: () => void;
  onEdit: (value: string) => void;
  onSave: () => void;
};

export function FieldCard({
  field,
  focused,
  edit,
  busy,
  canReview,
  onFocus,
  onEdit,
  onSave,
}: Props) {
  return (
    <div className={`field ${focused ? "focused" : ""}`}>
      <button className="field-select" onClick={onFocus}>
        <span>
          {fieldLabels[field.name] || field.name}
          {field.reviewed ? (
            <Check size={14} />
          ) : field.needs_review ? (
            <i className="review-dot" />
          ) : null}
        </span>
        <strong>{field.value || "Not found"}</strong>
        <small>
          {field.reviewed
            ? "Human verified · original machine score"
            : "Machine confidence"}{" "}
          {Math.round(field.confidence * 100)}%
          {field.page ? ` · p. ${field.page}` : " · source unavailable"}
        </small>
      </button>
      {focused && (
        <div className="field-editor">
          {field.quote && (
            <>
              <small>Original machine source quote</small>
              <blockquote>{field.quote}</blockquote>
            </>
          )}
          <label>
            Verify or correct value
            <input
              aria-label={`Edit ${fieldLabels[field.name]}`}
              value={edit}
              onChange={(e) => onEdit(e.target.value)}
            />
          </label>
          <button
            className="primary compact"
            disabled={busy || !edit.trim() || !canReview}
            onClick={onSave}
          >
            <Check size={14} /> Verify field
          </button>
          <small>
            Edits preserve the original machine evidence; the new value is not
            automatically grounded.
          </small>
        </div>
      )}
    </div>
  );
}
