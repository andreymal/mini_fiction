// eslint-disable-next-line import/no-extraneous-dependencies, import/no-unresolved
import React from 'react';
import ReactDOM from 'react-dom';

import autobind from 'autobind-decorator';
import TagsInput from 'react-tagsinput';

import Tag from './tag';
import Input from './input';
import { setStoreFromUrl } from './store';

const Layout = (tagComponents, inputComponent) => (
  <span className="tags-container">
    {tagComponents}
    {inputComponent}
  </span>
);


class TagComponent extends React.Component {
  state = { tags: [] };

  @autobind
  handleChange(tags) {
    this.setState({ tags });
  }

  render() {
    const { tags } = this.state;
    return (
      <TagsInput
        onlyUnique
        renderLayout={Layout}
        renderTag={Tag}
        renderInput={Input}
        value={tags}
        onChange={this.handleChange}
        tagProps={{
          className: 'tag-item',
          classNameRemove: 'tag-remove',
        }}
        inputProps={{
          className: 'tag-block dropdown-input',
          placeholder: 'Добавить тег',
        }}
      />
    );
  }
}

export default (node) => {
  const { autocompleteUrl } = node.dataset;
  setStoreFromUrl(autocompleteUrl);
  ReactDOM.render(ReactDOM.createElement(TagComponent), node);
};
