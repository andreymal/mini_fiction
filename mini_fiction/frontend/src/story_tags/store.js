import Deferred from 'fbjs/lib/Deferred';

const store = new Deferred();

const getStore = () => store;

const setStore = data => store.resolve(data);

export {
  getStore,
  setStore,
};
