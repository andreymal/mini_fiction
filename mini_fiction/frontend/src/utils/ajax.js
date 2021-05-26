let csrfToken = null;
const R = window.Request;

const getCsrfToken = () => {
  if (csrfToken === null) {
    csrfToken = window.document.querySelector('meta[name=csrf-token]').content;
  }
  return csrfToken;
};

const setCsrfToken = (token) => {
  csrfToken = token;
  window.document.querySelector('meta[name=csrf-token]').content = token;
};

const defaultHeaders = [
  ['Accept', 'application/json,*/*'],
];

const request = (originalRequest, headers = []) => {
  const r = new R(originalRequest, { credentials: 'include' });
  [...defaultHeaders, ...headers].forEach(([name, value]) => r.headers.set(name, value));
  if (r.method !== 'GET') {
    r.headers.set('X-CSRFToken', getCsrfToken());
  }
  return window.fetch(r);
};

const get = (url) => request(new R(url, { credentials: 'include' }));

const post = (url, body) => request(new R(url, { method: 'POST', body }));

const postJSON = (url, body) => request(
  new R(url, { method: 'POST', body: JSON.stringify(body) }),
  [['Content-Type', 'application/json']],
);

export {
  setCsrfToken,
  get,
  post,
  postJSON,
};
