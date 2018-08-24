import 'whatwg-fetch';

let isSettled = false;
let resolver;
const store = new Promise((res) => { resolver = res; });

const getStore = () => store;

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
  getStore,
  setStoreFromUrl,
};
