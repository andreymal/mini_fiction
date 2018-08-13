import React from 'react';
import ReactDOM from 'react-dom';

import autobind from 'autobind-decorator';
import TagsInput from 'react-tagsinput';

import { CloseableTag } from './tag';
import Input from './input';
import { getStore, setStoreFromUrl } from './store';
import { shouldRenderSuggestion } from './autocomplete';

const Layout = (tagComponents, inputComponent) => (
  <div className="tags-container">
    {tagComponents}
    {inputComponent}
  </div>
);

const getHolderValue = tags => tags.map(t => t.name).join(', ');

const extractPlainTags = node => node
  .getElementsByTagName('input')[0]
  .value
  .split(/,\s+/)
  .filter(shouldRenderSuggestion);

const transformPlainTag = data => name => data.filter(tag => tag.name === name)[0] || null;

class TagComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = { tags: [] };
  }

  @autobind
  componentDidMount() {
    const { rawTags } = this.props;
    getStore().then((data) => {
      const tagTransformer = transformPlainTag(data);
      const tags = rawTags.map(tagTransformer).filter(t => t !== null);
      this.setState({ tags });
    });
  }


  @autobind
  handleChange(tags) {
    this.setState({ tags });
  }

  render() {
    const { tags } = this.state;
    const { holderName } = this.props;
    const value = getHolderValue(tags);

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
        <input className="tags-input-container" name={holderName} value={value} />
      </div>
    );
  }
}

export default (node) => {
  const { autocompleteUrl, holderName } = node.dataset;
  const rawTags = extractPlainTags(node);
  setStoreFromUrl(autocompleteUrl);
  ReactDOM.render(<TagComponent holderName={holderName} rawTags={rawTags} />, node);
};
