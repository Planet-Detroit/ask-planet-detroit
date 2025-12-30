import React from 'react';

const FilterPanel = ({ allFocusAreas = [], selectedFocus = [], onFocusChange }) => {
  const handleFocusChange = (focus) => {
    if (selectedFocus.includes(focus)) {
      onFocusChange(selectedFocus.filter(f => f !== focus));
    } else {
      onFocusChange([...selectedFocus, focus]);
    }
  };

  if (allFocusAreas.length === 0) {
    return (
      <div className="filter-panel">
        <h3>Focus Areas</h3>
        <p className="no-focus">Loading focus areas...</p>
      </div>
    );
  }

  return (
    <div className="filter-panel">
      <h3>Focus Areas</h3>
      <div className="focus-list">
        {allFocusAreas.map(focus => (
          <label key={focus} className="focus-checkbox">
            <input
              type="checkbox"
              checked={selectedFocus.includes(focus)}
              onChange={() => handleFocusChange(focus)}
            />
            <span className="focus-label">{focus}</span>
          </label>
        ))}
      </div>

      <style jsx>{`
        .filter-panel {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .filter-panel h3 {
          margin: 0 0 15px 0;
          color: #1e293b;
          font-size: 16px;
        }

        .no-focus {
          color: #9ca3af;
          font-size: 14px;
          font-style: italic;
        }

        .focus-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
          max-height: 300px;
          overflow-y: auto;
        }

        .focus-checkbox {
          display: flex;
          align-items: center;
          cursor: pointer;
          padding: 4px 0;
        }

        .focus-checkbox input[type="checkbox"] {
          margin-right: 10px;
          cursor: pointer;
        }

        .focus-label {
          font-size: 14px;
          color: #374151;
        }

        .focus-checkbox:hover .focus-label {
          color: #10b981;
        }
      `}</style>
    </div>
  );
};

export default FilterPanel;
