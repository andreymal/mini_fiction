const DURATION_MS = 3000;
const SLEEP_MS = DURATION_MS * 10;

export default (node) => {
  const inputs = [...node.getElementsByTagName('input')];
  let current = 0;
  let interval;

  const loop = () => setInterval(() => {
    inputs[current % inputs.length].checked = true;
    current += 1;
  }, DURATION_MS);
  interval = loop();

  const pause = () => {
    clearInterval(interval);
    setTimeout(() => {
      interval = loop();
    }, SLEEP_MS);
  };

  // Pause loop further on user interaction
  node.addEventListener('click', pause);
  node.addEventListener('mouseenter', pause);

  return () => clearInterval(interval);
};
