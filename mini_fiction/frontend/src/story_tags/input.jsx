import React from 'react';
import Autosuggest from 'react-autosuggest';
import autobind from 'autobind-decorator';

import { getSuggestion, getSuggestionValue } from './autocomplete';


const Suggestion = suggestion => (
  <span>
    {getSuggestionValue(suggestion)}
  </span>
);


class Suggester extends React.Component {
  static shouldRenderSuggestions(value) {
    return value && value.trim().length > 0;
  }

  state = { suggestions: [] };

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
    addTag(getSuggestionValue(suggestion));
  }

  render() {
    const { onChange, ref } = this.props;
    const { suggestions } = this.state;

    const handleOnChange = (e, { method }) => {
      if (method === 'enter') {
        e.preventDefault();
      } else {
        onChange(e);
      }
    };

    const inputProps = { ...this.props, onChange: handleOnChange };

    return (
      <Autosuggest
        ref={ref}
        suggestions={suggestions}
        shouldRenderSuggestions={Suggester.shouldRenderSuggestions}
        onSuggestionsFetchRequested={this.onSuggestionsFetchRequested}
        onSuggestionsClearRequested={this.onSuggestionsClearRequested}
        getSuggestionValue={getSuggestionValue}
        renderSuggestion={Suggestion}
        inputProps={inputProps}
        onSuggestionSelected={this.onSuggestionSelected}
      />
    );
  }
}

export default props => <Suggester {...props} />;
