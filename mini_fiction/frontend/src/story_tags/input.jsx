import React from 'react';
import Autosuggest from 'react-autosuggest';
import autobind from 'autobind-decorator';

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


  @autobind
  onChange(event, { method, newValue: value }) {
    const { onChange } = this.props;
    if (method === 'enter') {
      event.preventDefault();
    } else {
      onChange(event);
    }
    this.setState({ value });
  }

  @autobind
  onKeyDown(event) {
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
  }

  @autobind
  onSuggestionsFetchRequested({ value }) {
    getSuggestion(value)
      .then(suggestions => this.setState({ suggestions }));
  }

  @autobind
  onSuggestionsClearRequested() {
    this.setState({ suggestions: [] });
  }

  @autobind
  onSuggestionSelected(e, { suggestion }) {
    const { addTag } = this.props;
    addTag(suggestion);
  }

  @autobind
  onSuggestionHighlighted({ suggestion: highlighted }) {
    this.setState({ highlighted });
  }

  @autobind
  renderSuggestionsContainer({ containerProps, children }) {
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
  }


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
