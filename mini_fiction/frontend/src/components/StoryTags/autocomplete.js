import { getStore } from './store';

const find = (haystack, needle) => haystack
  .toLowerCase()
  .slice(0, needle.length) === needle;

const lookup = (value) => ({ name, aliases }) => find(name, value)
    || aliases.findIndex((alias) => find(alias, value)) !== -1;

const getSuggestion = (rawVal) => {
  const value = rawVal.trim().toLowerCase();

  if (value.length === 0) {
    return [];
  }

  return getStore().then((data) => data.filter(lookup(value)));
};

const getSuggestionValue = (suggestion) => suggestion.name;

const synthesizeSuggestion = (value) => ({
  aliases: [],
  category_id: 0,
  description: '',
  id: 0,
  name: value,
  stories_count: 0,
  url: '',
});

const shouldRenderSuggestion = (value) => value && value.trim().length > 0;

export {
  getSuggestion,
  getSuggestionValue,
  synthesizeSuggestion,
  shouldRenderSuggestion,
};
