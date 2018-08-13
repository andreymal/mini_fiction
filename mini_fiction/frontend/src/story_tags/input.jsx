import React from 'react';
import Autosuggest from 'react-autosuggest';

import {
  getSuggestion,
  getSuggestionValue,
  synthesizeSuggestion,
  shouldRenderSuggestion,
} from './autocomplete';
import { PlainTag } from './tag';


const ENTER = 13;


class Suggester extends React.Component {
  state = {
    suggestions: [],
    value: '',
    highlighted: null,
  };

  onChange = (event, { method, newValue: value }) => {
    const { onChange } = this.props;
    if (method === 'enter') {
      event.preventDefault();
    } else {
      onChange(event);
    }
    this.setState({ value });
  };

  onKeyDown = (event) => {
    const { addTag, syntheticTags, addFirst } = this.props;
    const { suggestions, value } = this.state;
    const { keyCode } = event;

    if (keyCode === ENTER) {
      event.preventDefault();
      if (syntheticTags && suggestions.length === 0) {
        addTag(synthesizeSuggestion(value));
      } else if (addFirst && suggestions.length === 1) {
        addTag(suggestions[0]);
      }
    }
  };

  onSuggestionsFetchRequested = ({ value }) => {
    getSuggestion(value)
      .then(suggestions => this.setState({ suggestions }));
  };

  onSuggestionsClearRequested = () => this.setState({ suggestions: [] });

  onSuggestionSelected = (e, { suggestion }) => {
    const { addTag } = this.props;
    addTag(suggestion);
  };

  onSuggestionHighlighted = ({ suggestion: highlighted }) => this.setState({ highlighted });

  renderSuggestionsContainer = ({ containerProps, children }) => {
    const { highlighted, suggestions } = this.state;
    const tag = highlighted || (suggestions.length === 1 && suggestions[0]);
    return (
      <div {...containerProps}>
        { children }
        <div className="tag-help">
          {tag && tag.description}
        </div>
      </div>
    );
  };

  render() {
    const { ref } = this.props;
    const { suggestions } = this.state;
    const inputProps = { ...this.props, onChange: this.onChange, onKeyDown: this.onKeyDown };

    return (
      <Autosuggest
        ref={ref}
        suggestions={suggestions}
        shouldRenderSuggestions={shouldRenderSuggestion}
        onSuggestionsFetchRequested={this.onSuggestionsFetchRequested}
        onSuggestionsClearRequested={this.onSuggestionsClearRequested}
        onSuggestionHighlighted={this.onSuggestionHighlighted}
        getSuggestionValue={getSuggestionValue}
        renderSuggestion={s => <PlainTag withCount tag={s} />}
        renderSuggestionsContainer={this.renderSuggestionsContainer}
        inputProps={inputProps}
        onSuggestionSelected={this.onSuggestionSelected}
      />
    );
  }
}

export default props => <Suggester {...props} />;
