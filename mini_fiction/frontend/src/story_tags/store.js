let isSettled = false;
let resolver;

const ephemeralStore = [];
const store = new Promise((res) => { resolver = res; });

const addEphemeral = value => ephemeralStore.push(value);

const getEphemeral = () => Promise.all(ephemeralStore);

const getStore = () => Promise
  .all([store, getEphemeral()])
  .then(([data, ephemeral]) => data.concat(ephemeral));

const setStoreFromUrl = (url) => {
  if (isSettled) return;

  window.fetch(url, { credentials: 'include' })
    .then(response => response.json())
    .then(({ tags }) => {
      resolver(tags);
      isSettled = true;
    });
};

export {
  addEphemeral,
  getStore,
  setStoreFromUrl,
};
