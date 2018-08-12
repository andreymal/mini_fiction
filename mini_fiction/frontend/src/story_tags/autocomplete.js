import { getStore } from './store';

const lookup = value => suggestion => suggestion
  .name
  .toLowerCase()
  .slice(0, value.length) === value;


const getSuggestion = (rawVal) => {
  const value = rawVal.trim().toLowerCase();

  if (value.length === 0) {
    return [];
  }

  return getStore().then(data => data.filter(lookup(value)));
};


const getSuggestionValue = suggestion => suggestion.name;

const synthesizeSuggestion = value => ({
  aliases: [],
  color: '#1D2A4F',
  description: '',
  id: 0,
  name: value,
  stories_count: 0,
  url: '',
});


export {
  getSuggestion,
  getSuggestionValue,
  synthesizeSuggestion,
};