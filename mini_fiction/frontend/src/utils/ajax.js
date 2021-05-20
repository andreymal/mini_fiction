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

const req = (input, init) => {
  let request;
  // eslint-disable-next-line no-prototype-builtins
  if (R.prototype.isPrototypeOf(input) && !init) {
    request = input;
  } else {
    request = new R(input, init);
  }
  request = new R(request, { credentials: 'include' });
  request.headers.set('Accept', 'application/json,*/*');
  request.headers.set('X-AJAX', '1');
  if (request.method !== 'GET') {
    request.headers.set('X-CSRFToken', getCsrfToken());
  }

  return window.fetch(request);
};

const post = (input, body, init = {}) => {
  const request = new R(input, { method: 'POST', body, ...init });
  return req(request);
};

const postJSON = (input, body) => post(input, JSON.stringify(body), { 'Content-Type': 'application/json' });

export {
  setCsrfToken,
  req,
  post,
  postJSON,
};
