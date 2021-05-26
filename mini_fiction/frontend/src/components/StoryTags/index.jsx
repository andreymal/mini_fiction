import React from 'react';
import ReactDOM from 'react-dom';

import TagsInput from 'react-tagsinput';

import { CloseableTag } from './tag';
import Input from './input';
import { getStore, setStoreFromUrl } from './store';
import { shouldRenderSuggestion, synthesizeSuggestion } from './autocomplete';

const Layout = (tagComponents, inputComponent) => (
  <div className="tags-container">
    {tagComponents}
    {inputComponent}
  </div>
);

const getHolderValue = (tags) => tags.map((t) => t.name).join(', ');

const extractPlainTags = (node) => node
  .getElementsByTagName('input')[0]
  .value
  .split(/,\s+/)
  .filter(shouldRenderSuggestion);

const transformPlainTag = (data) => (name) => (
  data.filter((tag) => tag.name === name)[0] || synthesizeSuggestion(name)
);

const splitSeparators = [',', ';', '\\(', '\\)', '\\*', '/', ':', '\\?', '\n', '\r'];
const splitRegex = new RegExp(splitSeparators.join('|'));

const capitalize = (v) => v.charAt(0).toUpperCase() + v.slice(1);

const normalize = (v) => v.toLowerCase().trim();

const pasteSplit = (input) => input
  .split(splitRegex)
  .map(normalize)
  .map(capitalize)
  .map(synthesizeSuggestion);

class TagComponent extends React.Component {
  // eslint-disable-next-line react/state-in-constructor
  state = { tags: [] };

  componentDidMount = () => {
    const { rawTags } = this.props;
    getStore().then((data) => {
      const tagTransformer = transformPlainTag(data);
      // TODO: Fix O(N*M) complexity; consider migration to more efficient structure
      const tags = rawTags.map(tagTransformer);
      this.setState({ tags });
    });
  };

  handleChange = (tags) => this.setState({ tags });

  render() {
    const { tags } = this.state;
    const { holderName, allowSyntheticTags } = this.props;
    const value = getHolderValue(tags);

    return (
      <div>
        <TagsInput
          onlyUnique
          addOnPaste
          renderLayout={Layout}
          renderTag={CloseableTag}
          renderInput={Input}
          value={tags}
          onChange={this.handleChange}
          pasteSplit={pasteSplit}
          inputProps={{
            className: 'tag-block dropdown-input',
            placeholder: 'Добавить тег',
            addFirst: true,
            allowSyntheticTags,
          }}
        />
        <input className="tags-input-container" name={holderName} value={value} />
      </div>
    );
  }
}

const getKey = (prefix, key) => {
  const k = key.slice(prefix.length);
  return k.charAt(0).toLowerCase() + k.slice(1);
};

const filterParams = (prefix, obj) => Object.keys(obj)
  .filter((k) => k.startsWith(prefix))
  .reduce((acc, k) => {
    acc[getKey(prefix, k)] = obj[k];
    return acc;
  }, {});

export default (node) => {
  const attrPrefix = 'ti';
  const {
    autocompleteUrl,
    holderName,
    syntheticTags,
  } = filterParams(attrPrefix, node.dataset);
  const rawTags = extractPlainTags(node);
  setStoreFromUrl(autocompleteUrl);
  ReactDOM.render(<TagComponent
    holderName={holderName}
    rawTags={rawTags}
    allowSyntheticTags={syntheticTags !== undefined}
  />, node);
};
