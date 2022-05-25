const { document } = window;
const notifications = () => document.getElementById('popup-notifications');

/** Скрывает переданный HTML-элемент, который был ранее отображён как уведомление */
const popNotification = (not) => {
  if (not.parentNode !== notifications() || not.classList.contains('notice-hidden')) {
    return false;
  }
  not.classList.add('notice-hidden');
  setTimeout(() => {
    notifications().removeChild(not);
  }, 300);
  return true;
};

/** Отображает переданный HTML-элемент как ошибку */
const putNotification = (not) => {
  not.classList.add('popup-notification');
  not.classList.add('notice-hidden');
  not.addEventListener('click', (e) => {
    e.preventDefault();
    popNotification(not);
    return false;
  });
  setTimeout(() => {
    popNotification(not);
  }, 10000);
  notifications().appendChild(not);
  // eslint-disable-next-line no-unused-expressions
  not.offsetWidth; // force reflow
  not.classList.remove('notice-hidden');
};

/** Показывает уведомление с переданным текстом */
const notify = (text) => {
  const not = document.createElement('div');
  not.textContent = text;
  putNotification(not);
};

/** Показывает уведомление-ошибку с переданным текстом */
const notifyError = (text) => {
  const not = document.createElement('div');
  not.classList.add('notice-error');
  not.textContent = text;
  putNotification(not);
};

export { notify, notifyError };
