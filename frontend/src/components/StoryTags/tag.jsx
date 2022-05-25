import React from 'react';

import { getSuggestionValue } from './autocomplete';

const PlainTag = ({ tag, children, withCount = false }) => {
  let text;
  if (withCount) {
    text = `${getSuggestionValue(tag)} (${tag.stories_count || 0})`;
  } else {
    text = getSuggestionValue(tag);
  }
  return (
    <div className="tag-item tag-block" data-category-id={tag.category_id}>
      {text}
      {children}
    </div>
  );
};

const CloseableTag = ({
  tag, key, disabled, onRemove,
}) => {
  const removeBtn = <span className="tag-remove" onClick={() => onRemove(key)} />;
  return (
    <PlainTag tag={tag}>
      {!disabled && removeBtn}
    </PlainTag>
  );
};

export {
  PlainTag,
  CloseableTag,
};
