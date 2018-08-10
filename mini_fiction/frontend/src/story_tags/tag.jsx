import React from 'react';

import classNames from 'classnames';
import { getSuggestionValue } from './autocomplete';

const PlainTag = ({ tag, children }) => {
  // TODO: Replace with styles
  const style = { 'background-color': tag.color };
  const classes = classNames(
    'tag-item',
    'tag-block',
    { 'tag-item-type-default': !tag.color },
  );
  return (
    <div className={classes} style={style}>
      {getSuggestionValue(tag)}
      {...children}
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
