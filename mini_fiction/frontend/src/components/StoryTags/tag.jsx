import React from 'react';

import classNames from 'classnames';
import { getSuggestionValue } from './autocomplete';

const PlainTag = ({ tag, children, withCount = false }) => {
  // TODO: Replace with styles
  const style = { 'background-color': tag.color };
  const classes = classNames(
    'tag-item',
    'tag-block',
    { 'tag-item-type-default': !tag.color },
  );
  let text;
  if (withCount) {
    text = `${getSuggestionValue(tag)} (${tag.stories_count || 0})`;
  } else {
    text = getSuggestionValue(tag);
  }
  return (
    <div className={classes} style={style}>
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
