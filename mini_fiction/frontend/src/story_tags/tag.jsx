import React from 'react';

import classNames from 'classnames';
import { getSuggestionValue } from './autocomplete';

export default (props) => {
  const {
    tag,
    key,
    disabled,
    onRemove,
    classNameRemove,
    className,
    ...other
  } = props;

  const cls = classNames(className, 'tag-block', 'tag-item-type-default');
  const removeBtn = <span className={classNameRemove} onClick={() => onRemove(key)} />;
  // TODO: Replace with styles
  const style = { 'background-color': tag.color };
  return (
    <div key={key} className={cls} {...other} style={style}>
      {getSuggestionValue(tag)}
      {!disabled && removeBtn}
    </div>
  );
};
