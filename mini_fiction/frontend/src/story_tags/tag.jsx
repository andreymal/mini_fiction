import React from 'react';

import classNames from 'classnames';

export default (props) => {
  const {
    tag,
    key,
    disabled,
    onRemove,
    classNameRemove,
    getTagDisplayValue,
    className,
    ...other
  } = props;

  const cls = classNames(className, 'tag-block', 'tag-item-type-default');

  return (
    <div key={key} className={cls} {...other}>
      {getTagDisplayValue(tag)}
      {!disabled
      && <span className={classNameRemove} onClick={() => onRemove(key)} />
      }
    </div>
  );
};
