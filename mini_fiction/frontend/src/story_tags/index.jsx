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
    const { holderName } = this.props;
    const holderValue = tags.map(t => t.name).join(', ');

    return (
      <div>
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
        <input className="tags-input-container" name={holderName} value={holderValue} />
      </div>
    );
  }
}

export default (node) => {
  const { autocompleteUrl, holderName } = node.dataset;
  setStoreFromUrl(autocompleteUrl);
  ReactDOM.render(<TagComponent holderName={holderName} />, node);
};
