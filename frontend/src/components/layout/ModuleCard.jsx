import React from "react";

export default function ModuleCard({
  id,
  title,
  description,
  subtitle,
  badge,
  badgeType = "primary",
  actionText,
  onAction,
  href,
  onClick,
  interactive,
  className = "",
  children,
  ...rest
}) {
  const descText = description || subtitle;
  const isInteractive = Boolean(interactive || onClick || (href && !children));

  function handleCardClick(e) {
    if (onClick) {
      onClick(e);
    } else if (href && href.startsWith("#")) {
      const targetEl = document.querySelector(href);
      if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function handleActionClick(e) {
    e.stopPropagation();
    if (onAction) {
      onAction(e);
    } else if (href && href.startsWith("#")) {
      const targetEl = document.querySelector(href);
      if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div
      id={id}
      className={`module-card card ${isInteractive ? `interactive badge-${badgeType}` : ""} ${className}`}
      onClick={isInteractive ? handleCardClick : undefined}
      role={isInteractive && !children ? "button" : undefined}
      tabIndex={isInteractive && !children ? 0 : undefined}
      onKeyDown={
        isInteractive && !children
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleCardClick(e);
              }
            }
          : undefined
      }
      {...rest}
    >
      {(title || descText || badge || actionText) && (
        <div className="module-card-header">
          <div className="module-card-title-group">
            {title && <h2 className="module-card-title">{title}</h2>}
            {descText && <p className="module-card-description">{descText}</p>}
          </div>

          <div className="module-card-actions">
            {badge && (
              <span className={`module-card-badge badge-${badgeType}`}>{badge}</span>
            )}
          </div>
        </div>
      )}

      {children && <div className="module-card-body">{children}</div>}

      {actionText && (
        <div>
          <button
            type="button"
            className="module-card-link-btn"
            onClick={handleActionClick}
          >
            {actionText}
          </button>
        </div>
      )}
    </div>
  );
}
