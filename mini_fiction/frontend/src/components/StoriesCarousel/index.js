const DURATION_MS = 3000;

export default (node) => {
  let current = 0;

  const inputs = [...node.getElementsByTagName('input')];
  const looper = setInterval(() => {
    inputs[current % inputs.length].checked = true;
    current += 1;
  }, DURATION_MS);

  // Do not loop further on user interaction
  node.addEventListener('click', () => clearInterval(looper));

  return () => clearInterval(looper);
};
