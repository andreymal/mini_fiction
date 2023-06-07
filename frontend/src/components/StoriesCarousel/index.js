const DURATION_MS = 7500;
const SLEEP_MS = DURATION_MS * 10;

export default (node) => {
  const inputs = [...node.getElementsByTagName('input')];
  let current = 0;
  let interval;
  let paused = false;

  const loop = () => setInterval(() => {
    if (inputs.length === 0) return;
    inputs[current % inputs.length].checked = true;
    current += 1;
  }, DURATION_MS);
  interval = loop();

  const pause = () => {
    if (paused) return;
    paused = true;
    clearInterval(interval);
    setTimeout(() => {
      interval = loop();
      paused = false;
    }, SLEEP_MS);
  };

  // Pause loop further on user interaction
  node.addEventListener('mouseenter', pause);

  return () => clearInterval(interval);
};
