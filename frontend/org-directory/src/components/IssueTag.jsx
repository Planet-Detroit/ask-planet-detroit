import React from 'react';

const IssueTag = ({ issue }) => {
  // Color mapping for different focus areas
  const getColorForIssue = (issue) => {
    const colors = {
      'Water': '#3b82f6',
      'Air': '#06b6d4',
      'Climate': '#ef4444',
      'Energy': '#f59e0b',
      'Wildlife': '#10b981',
      'Land': '#84cc16',
      'Toxics': '#8b5cf6',
      'Transportation': '#6366f1',
      'Food': '#f97316',
      'Justice': '#ec4899',
      'Policy': '#6b7280',
      'Education': '#14b8a6',
      'Health': '#f43f5e',
      'Conservation': '#22c55e'
    };
    
    return colors[issue] || '#64748b'; // Default gray if not found
  };

  const backgroundColor = getColorForIssue(issue);

  return (
    <span 
      className="issue-tag"
      style={{ 
        backgroundColor: backgroundColor + '20', // 20 = ~12% opacity
        color: backgroundColor,
        border: `1px solid ${backgroundColor}40`
      }}
    >
      {issue}
      
      <style jsx>{`
        .issue-tag {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          white-space: nowrap;
        }
      `}</style>
    </span>
  );
};

export default IssueTag;
