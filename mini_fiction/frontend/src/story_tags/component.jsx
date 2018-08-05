// eslint-disable-next-line import/no-extraneous-dependencies, import/no-unresolved
import React from 'react';
import autobind from 'autobind-decorator';
import TagsInput from 'react-tagsinput';
import classNames from 'classnames';

const renderLayout = (tagComponents, inputComponent) => (
  <span className="tags-container">
    {tagComponents}
    {inputComponent}
  </span>
);

const renderTag = (props) => {
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

  const cls = classNames(className, 'tag-item-type-default');

  return (
    <div
      key={key}
      className={cls}
      {...other}
    >
      {getTagDisplayValue(tag)}
      {!disabled
        && <a className={classNameRemove} onClick={() => onRemove(key)} />
        }
    </div>
  );
};

const tagProps = {
  className: 'tag-item',
  classNameRemove: 'tag-remove',
};

class TagComponent extends React.Component {
  constructor() {
    super();
    this.state = { tags: [] };
  }

  @autobind
  handleChange(tags) {
    this.setState({ tags });
  }

  render() {
    const { tags } = this.state;
    return (
      <TagsInput
        renderLayout={renderLayout}
        renderTag={renderTag}
        tagProps={tagProps}
        value={tags}
        onChange={this.handleChange}
      />
    );
  }
}

export default TagComponent;
