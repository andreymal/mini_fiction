import React from 'react';
import ReactDOM from 'react-dom';

import autobind from 'autobind-decorator';
import TagsInput from 'react-tagsinput';

import { CloseableTag } from './tag';
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
        renderTag={CloseableTag}
        renderInput={Input}
        value={tags}
        onChange={this.handleChange}
        inputProps={{
          className: 'tag-block dropdown-input',
          placeholder: 'Добавить тег',
          addFirst: true,
          syntheticTags: false,
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
