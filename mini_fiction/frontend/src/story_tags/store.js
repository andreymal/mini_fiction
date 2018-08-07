import Deferred from 'fbjs/lib/Deferred';

const store = new Deferred();

const getStore = () => store;

const setStoreFromUrl = (url) => {
  fetch(url, { credentials: 'include' })
    .then(response => response.json())
    .then(({ tags }) => {
      store.resolve(tags);
    });
};

export {
  getStore,
  setStoreFromUrl,
};
