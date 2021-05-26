export default (filename) => (n) => (
  filename().then((f) => (f.default)(n))
);
